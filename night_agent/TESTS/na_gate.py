#!/usr/bin/env python3
"""Night Agent v11.1 transition guard. Prints ALLOW or BLOCK with reasons.

Usage:
  python3 na_gate.py <run> GATE
  python3 na_gate.py <run> GENERATE | BASELINE | DIRECT
  python3 na_gate.py <run> CHECK   --stage-dir stage-02-fmea
  python3 na_gate.py <run> CLOSE   --stage-dir stage-02-fmea
  python3 na_gate.py <run> OPERATE --op FMEA
  python3 na_gate.py <run> REVIEW
  python3 na_gate.py <run> FINAL
  python3 na_gate.py <run> VERIFY
  python3 na_gate.py <run> DECIDE  --record exp-003
  python3 na_gate.py <run> SEND    --seat G2 --stage-dir stage-02-fmea

Exit 0 on ALLOW, 1 on BLOCK. Implements NIGHT_AGENT_SPEC.md section 15. Reads files only.
"""
import sys, os, re, json, argparse

STATUSES = ["PASSED", "FAILED", "JUDGEMENT CALL", "NOT TESTABLE", "BLOCKED", "INCONCLUSIVE"]
SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SCHEMA.json")
STAMP = re.compile(r"^STAGE (\d\d) ([A-Z\-]+) SEAT ([A-Za-z0-9]+) TIME (\d\d:\d\d)\s*$")
CLAIM = re.compile(r"^CLAIM\s+(\S+)\s+\[([^\]]+)\]\s+\"(.*)\"\s*$")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def parse_claims(text):
    claims, cur = [], None
    for line in text.splitlines():
        m = CLAIM.match(line)
        if m:
            cur = {"id": m.group(1), "result": "", "retrieved": "", "settle": "", "method": "", "source": ""}
            claims.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        for key in ("RETRIEVED", "RESULT", "SETTLE", "METHOD", "SOURCE"):
            if s.startswith(key):
                cur[key.lower()] = s[len(key):].strip()
    return claims


def keep_defects(rec, base, gate):
    """Why a KEEP would be wrong (spec 5 COMPARE and DECIDE, guard G-9). Empty list means the KEEP is sound."""
    out = []
    noise = rec.get("noise", base.get("noise"))
    min_delta = (gate.get("budget", {}) or {}).get("min_delta")
    thr = noise if noise is not None else min_delta
    direction = rec.get("direction") or base.get("direction")
    if not direction:
        for o in gate.get("objectives", []) or []:
            if o.get("name") == (rec.get("metric") or base.get("metric")):
                direction = o.get("direction")
    if direction not in ("lower", "higher"):
        out.append("metric direction unknown (record, baseline.json or gate objectives must say lower or higher)")
    delta = rec.get("delta")
    if delta is None:
        out.append("no delta")
    elif thr is None:
        out.append("noise unknown and no MIN_DELTA set")
    else:
        improved = (delta < 0) if direction == "lower" else (delta > 0) if direction == "higher" else False
        if direction in ("lower", "higher") and not improved:
            out.append(f"delta {delta} is not an improvement for a {direction}-is-better metric")
        elif abs(delta) <= abs(thr):
            out.append(f"delta {delta} not beyond noise/min_delta {thr}")
    if rec.get("repeat_value") is None:
        out.append("no repeat run (repeat_value null)")
    elif rec.get("baseline_value", base.get("baseline_value")) is not None and thr is not None and direction in ("lower", "higher"):
        bv = rec.get("baseline_value", base.get("baseline_value"))
        rdelta = rec["repeat_value"] - bv
        rimp = (rdelta < 0) if direction == "lower" else (rdelta > 0)
        if not rimp or abs(rdelta) <= abs(thr):
            out.append(f"repeat run {rec['repeat_value']} does not improve on baseline {bv} beyond {thr}")
    if rec.get("within_budget") is False:
        out.append("run exceeded EXPERIMENT_BUDGET_S (must be INCONCLUSIVE)")
    for g in rec.get("guardrails", []) or []:
        if g.get("value") is not None and g.get("baseline") is not None and g.get("tolerance") is not None:
            if abs(g["value"] - g["baseline"]) > abs(g["tolerance"]):
                out.append(f"guardrail {g.get('name')} beyond tolerance")
    if not rec.get("constraints_checked"):
        out.append("no hard constraints checked")
    return out


def log_lines(run):
    p = os.path.join(run, "log.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in read(p).splitlines() if l.strip()]


def stages(run):
    return sorted(d for d in os.listdir(run) if re.match(r"stage-\d\d-", d)) if os.path.isdir(run) else []


def jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in read(p).splitlines() if l.strip()]


def guard(run, stage, stage_dir=None, op=None, record=None, seat=None):
    reasons = []
    j = lambda *a: os.path.join(run, *a)
    gate = jload(j("gate", "gate.json"), {}) or {}
    mincrew = int(gate.get("min_crew", 2))
    status = jload(j("status.json"), {}) or {}
    captures = {c.get("dispatch_id"): c for c in jsonl(j("capture.jsonl"))}
    dispatches = jsonl(j("dispatch.jsonl"))

    if stage == "GATE":  # G-1
        if not os.path.exists(j("ask.md")):
            reasons.append("G-1 ask.md missing")
        reg = jload(j("registry.json"), {}) or {}
        seats = reg.get("seats", [])
        gens = [s for s in seats if s.get("role", "generator" if s.get("id", "").startswith("G") else "") == "generator" and s.get("ready")]
        closer = [s for s in seats if (s.get("role") == "closer" or s.get("id") == "CLOSER") and s.get("ready")]
        if len(gens) < mincrew:
            reasons.append(f"G-1 READY generators {len(gens)} < MIN_CREW {mincrew}")
        if not closer:
            reasons.append("G-1 no READY CLOSER")

    elif stage in ("GENERATE", "BASELINE", "DIRECT"):  # G-2
        if not gate or not gate.get("class"):
            reasons.append("G-2 gate/gate.json missing or has no CLASS")
        else:
            allowed = {"GENERATE": ("DELIBERATION", "HYBRID", "HYBRID-NO-EXEC"), "DIRECT": ("DIRECT",), "BASELINE": ("EXPERIMENT", "HYBRID")}[stage]
            if gate.get("class") not in allowed:
                reasons.append(f"G-2 CLASS {gate.get('class')} does not enter {stage} (allowed: {', '.join(allowed)})")

    elif stage == "CHECK":  # G-3
        if not stage_dir or not os.path.isdir(j(stage_dir)):
            reasons.append("G-3 stage dir missing")
        else:
            ok = 0
            for f in os.listdir(j(stage_dir)):
                if f.startswith("seat-"):
                    txt = read(j(stage_dir, f))
                    lines = txt.splitlines()
                    first = lines[0] if txt.strip() else ""
                    sm = STAMP.match(first)
                    if not sm:
                        continue
                    if sm.group(1) != stage_dir.rstrip("/")[6:8] or sm.group(2) != stage_dir.rstrip("/").split("-", 2)[2].upper():
                        reasons.append(f"G-3 {f}: stamp {sm.group(1)} {sm.group(2)} is not this stage (not counted)")
                        continue
                    ready_ids = {x.get("id") for x in (jload(j("registry.json"), {}) or {}).get("seats", []) if x.get("ready")}
                    if ready_ids and sm.group(3) not in ready_ids:
                        reasons.append(f"G-3 {f}: seat {sm.group(3)} is not a READY registered seat (not counted)")
                        continue
                    did = lines[1].split()[1] if len(lines) > 1 and lines[1].startswith("DISPATCH ") else None
                    cap = captures.get(did) if did else None
                    if captures and (cap is None or not cap.get("completion_signal_observed") or cap.get("partial")):
                        reasons.append(f"G-3 {f}: capture incomplete or missing (not counted)")
                        continue
                    ok += 1
            need = 1 if stage_dir.rstrip("/").endswith("-direct") else mincrew  # DISPATCH 5: DIRECT has one generator
            if ok < need:
                reasons.append(f"G-3 {ok} complete stamped seat files < MIN_CREW {need}")

    elif stage == "CLOSE":  # G-4
        cp = j(stage_dir or "", "check.md")
        if not stage_dir or not os.path.exists(cp):
            reasons.append("G-4 check.md missing")
        else:
            cl = parse_claims(read(cp))
            if not cl:
                reasons.append("G-4 check.md has no claim records")
            for c in cl:
                if c["result"] not in STATUSES:
                    reasons.append(f"G-4 claim {c['id']} status {c['result']!r} not one of the six")
                elif c["result"] in ("PASSED", "FAILED") and not c["retrieved"]:
                    reasons.append(f"G-4 claim {c['id']} {c['result']} without RETRIEVED (bare)")
                elif c["result"] in ("PASSED", "FAILED") and c["method"] == "none":
                    reasons.append(f"G-4 claim {c['id']} {c['result']} with METHOD none (no check can have happened)")
                elif c["result"] == "PASSED" and c["method"] in ("source", "document") and not ("support=SUPPORTED" in c["source"] and "grade=A" in c["source"]):
                    reasons.append(f"G-4 claim {c['id']} PASSED source/document claim without support=SUPPORTED grade=A on its SOURCE line")
                elif c["result"] not in ("PASSED", "FAILED") and not c["settle"]:
                    reasons.append(f"G-4 claim {c['id']} {c['result']} without SETTLE")

    elif stage == "OPERATE":  # G-5
        st = stages(run)
        if not st or not os.path.exists(j(st[-1], "close.md")):
            reasons.append("G-5 previous close.md missing")
        if status.get("stop_reason"):
            reasons.append(f"G-5 stop reason already recorded: {status['stop_reason']}")
        if op:
            done = [d for d in st if d.lower().endswith("-" + op.lower())]
            if done:
                reasons.append(f"G-5 operator {op} already run ({done[0]})")
            library = (jload(SCHEMA, {}) or {}).get("operators", {})
            if library and op.upper() not in library:
                reasons.append(f"G-5 operator {op} is not in the SCHEMA operator library")
            ran = [d for d in st if not d.endswith(("-generate", "-direct"))]
            max_ops = int((gate.get("budget", {}) or {}).get("max_operators", 4) or 4)
            if len(ran) >= max_ops:
                reasons.append(f"G-5 max_operators {max_ops} already reached ({len(ran)} operator stages)")
        else:
            reasons.append("G-5 --op required")

    elif stage == "REVIEW":  # G-6
        st = stages(run)
        if not st or not os.path.exists(j(st[-1], "close.md")):
            reasons.append("G-6 last close.md missing")
        log = log_lines(run)
        hs = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") == "handshake"]
        if len(hs) != 1:
            reasons.append(f"G-6 reviewer handshake count {len(hs)} != 1")
        sends = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") in ("send", "prompt")]
        if sends:
            reasons.append(f"G-6 reviewer already received {len(sends)} send(s) after handshake")
        first_gen = next((i for i, l in enumerate(log) if l.get("stage") == "GENERATE" and l.get("action") in ("send", "prompt")), None)
        hs_idx = next((i for i, l in enumerate(log) if l.get("seat") == "REVIEWER" and l.get("action") == "handshake"), None)
        if first_gen is not None and hs_idx is not None and hs_idx > first_gen:
            reasons.append("G-6 reviewer handshake was logged after GENERATE began; the window did not sit outside the run")

    elif stage == "FINAL":  # G-7
        if os.path.exists(j("final", "DELIVERABLE.md")):
            reasons.append("G-7 final/DELIVERABLE.md already exists (write once)")
        for f in ("kills-all.md", "metrics-summary.json"):
            if not os.path.exists(j("final", f)):
                reasons.append(f"G-7 final/{f} missing")
        if os.path.exists(j("final", "kills-all.md")):
            ka = read(j("final", "kills-all.md"))
            for d in stages(run):
                cp = j(d, "close.md")
                if os.path.exists(cp):
                    m = re.search(r"^KILLS\b[^\n]*\n(.*?)(?=^(?:\d+ )?[A-Z][A-Z \-]{3,}\s*$|\Z)", read(cp), re.S | re.M)
                    for l in (m.group(1) if m else "").splitlines():
                        e = l.strip()
                        if (e.startswith(("-", "*")) or re.match(r"^\d+[\.\)]", e)) and e not in ka:
                            reasons.append(f"G-7 kills-all.md omits a KILLS entry of {d}: {e[:50]}")
        has_review = os.path.exists(j("review", "review.md")) and os.path.exists(j("review", "check-review.md"))
        flags = set(status.get("flags", [])) | set((jload(j("ledger.json"), {}) or {}).get("flags", []))
        if not has_review and "NO_OUTSIDE_REVIEW" not in flags:
            reasons.append("G-7 neither (review.md and check-review.md) nor NO_OUTSIDE_REVIEW flag present")

    elif stage == "VERIFY":  # G-8
        if not os.path.exists(j("final", "DELIVERABLE.md")):
            reasons.append("G-8 DELIVERABLE.md missing")
        if os.path.exists(j("final", "verifier.md")):
            reasons.append("G-8 verifier.md already exists")
        if os.path.exists(j("final", "DELIVERABLE.md")):
            d = read(j("final", "DELIVERABLE.md"))
            tail = d.split("PRIVATE DOCUMENT VERIFICATION", 1)[1] if "PRIVATE DOCUMENT VERIFICATION" in d else ""
            if tail.strip():
                reasons.append("G-8 DELIVERABLE.md section 14 already has content; the verifier output goes to verifier.md, never into the deliverable (I3)")

    elif stage == "DECIDE":  # G-9
        if not record:
            reasons.append("G-9 --record required")
        else:
            rec = jload(j("experiments", record, "record.json"))
            base = jload(j("experiments", "baseline.json"), {}) or {}
            if rec is None:
                reasons.append("G-9 record.json missing")
            elif rec.get("decision") == "KEEP":
                reasons += ["G-9 KEEP: " + d for d in keep_defects(rec, base, gate)]
    elif stage == "SEND":  # G-11
        if not seat:
            reasons.append("G-11 --seat required")
        else:
            reg = jload(j("registry.json"), {}) or {}
            seats = {x.get("id"): x for x in reg.get("seats", [])}
            ids = [d.get("dispatch_id") for d in dispatches]
            dupes = {x for x in ids if ids.count(x) > 1}
            if dupes:
                reasons.append(f"G-11 duplicate dispatch_id(s) already in dispatch.jsonl: {sorted(dupes)}")
            mine = [d for d in dispatches if d.get("seat_id") == seat]
            if mine:
                last = mine[-1]
                cap = captures.get(last.get("dispatch_id"))
                if cap is None or not cap.get("completion_signal_observed"):
                    reasons.append(f"G-11 seat {seat}: previous slot {last.get('dispatch_id')} has no complete capture")
                url = seats.get(seat, {}).get("url")
                if url and last.get("conversation_url") and last.get("conversation_url") != url:
                    reasons.append(f"G-11 seat {seat}: observed conversation_url differs from registry")
            tail = int(status.get("sends_reserved_for_tail", 0) or 0)
            cap_sends = (gate.get("budget", {}) or {}).get("max_calls")
            used = int(status.get("sends_used", 0) or 0)
            if cap_sends and used + 1 + tail > int(cap_sends):
                reasons.append(f"G-11 reservation: used {used} + this send + tail {tail} exceeds max_calls {cap_sends}")
    else:
        reasons.append(f"unknown stage {stage}")

    return reasons


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("stage")
    ap.add_argument("--stage-dir")
    ap.add_argument("--op")
    ap.add_argument("--record")
    ap.add_argument("--seat")
    a = ap.parse_args()
    rs = guard(a.run, a.stage.upper(), a.stage_dir, a.op, a.record, a.seat)
    if rs:
        print("BLOCK " + a.stage.upper())
        for r in rs:
            print("  " + r)
        sys.exit(1)
    print("ALLOW " + a.stage.upper())
    sys.exit(0)
