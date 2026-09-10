#!/usr/bin/env python3
"""Night Agent v11 conformance checker.

Usage:
  python3 na_check.py <run_folder>            audit one run folder, exit 1 on any FAIL
  python3 na_check.py --package <package_dir> audit the package itself (spec, prompts, schema)

Every check prints  PASS <id> <message>  or  FAIL <id> <message>.
Nothing here asks a model anything. It reads files.
"""
import sys, os, re, json, hashlib, itertools

STATUSES = ["PASSED", "FAILED", "JUDGEMENT CALL", "NOT TESTABLE", "BLOCKED", "INCONCLUSIVE"]
NEED_RETRIEVED = {"PASSED", "FAILED"}
NEED_SETTLE = {"JUDGEMENT CALL", "NOT TESTABLE", "BLOCKED", "INCONCLUSIVE"}
PROV = re.compile(r"\[(G?\d+|R|X-[A-Za-z0-9\-]+|D|OP)\]")
STAMP = re.compile(r"^STAGE (\d\d) ([A-Z\-]+) SEAT ([A-Za-z0-9]+) TIME (\d\d:\d\d)\s*$")
CLAIM = re.compile(r"^CLAIM\s+(\S+)\s+\[([^\]]+)\]\s+\"(.*)\"\s*$")
DELIV_SECTIONS = ["1 THE RESULT", "2 WHAT SURVIVED", "3 WHY IT SURVIVED", "4 OBJECTIVE RESULTS", "5 WHAT DIED AND WHY",
                  "6 TRADE-OFFS", "7 OUTSIDE REVIEW", "8 STILL OPEN", "9 CONFIDENCE", "10 RUN INTEGRITY", "11 EFFICIENCY", "12 NEXT QUESTION"]

results = []


def rep(ok, cid, msg):
    results.append((ok, cid, msg))
    print(("PASS " if ok else "FAIL ") + cid + " " + msg)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_claims(text):
    """Return list of dicts for every CLAIM block in a check file."""
    claims = []
    cur = None
    for line in text.splitlines():
        m = CLAIM.match(line)
        if m:
            cur = {"id": m.group(1), "prov": m.group(2), "text": m.group(3), "method": "", "action": "", "retrieved": "", "result": "", "settle": ""}
            claims.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        for key in ("METHOD", "ACTION", "RETRIEVED", "RESULT", "SETTLE", "SOURCE"):
            if s.startswith(key):
                cur[key.lower()] = s[len(key):].strip()
    return claims


SUPPORT_OK = {"SUPPORTED": "PASSED", "CONTRADICTED": "FAILED", "NOT_FOUND": "FAILED", "PARTIAL": "INCONCLUSIVE", "UNSUPPORTED": "INCONCLUSIVE", "UNVERIFIED": "BLOCKED"}


def check_source_lines(claims, tag):
    for c in claims:
        if c.get("method") in ("source", "document"):
            src = c.get("source", "")
            rep(bool(src), f"SRC-0-{tag}-{c['id']}", "source/document claim has a SOURCE line")
            m = re.search(r"support=([A-Z_]+)", src)
            if m:
                exp = SUPPORT_OK.get(m.group(1))
                if c["result"] == "PASSED":
                    rep(m.group(1) == "SUPPORTED" and "grade=A" in src, f"SRC-1-{tag}-{c['id']}", f"PASSED source claim has support=SUPPORTED grade=A ({m.group(1)})")
                elif exp:
                    rep(c["result"] == exp, f"SRC-2-{tag}-{c['id']}", f"support {m.group(1)} maps to {exp} (got {c['result']})")


# ------------------------------------------------------------------ evidence checks
def check_evidence_file(path, tag):
    claims = parse_claims(read(path))
    rep(len(claims) > 0, f"EVID-0-{tag}", f"{path}: {len(claims)} claim records found")
    for c in claims:
        ok_status = c["result"] in STATUSES
        rep(ok_status, f"EVID-1-{tag}-{c['id']}", f"status is one of the six ({c['result']!r})")
        if c["result"] in NEED_RETRIEVED:
            rep(bool(c["retrieved"]), f"EVID-2-{tag}-{c['id']}", f"{c['result']} has RETRIEVED evidence beside it")
        if c["result"] in NEED_SETTLE:
            rep(bool(c["settle"]), f"EVID-3-{tag}-{c['id']}", f"{c['result']} has a SETTLE condition")
        rep(bool(PROV.match("[" + c["prov"] + "]")), f"EVID-4-{tag}-{c['id']}", f"provenance tag valid ({c['prov']})")
    check_source_lines(claims, tag)
    return claims


# ------------------------------------------------------------------ provenance in merge / final
CIDS = re.compile(r"\{([^}]*)\}")


def passed_claim_ids(run, upto_stage_dir=None):
    """Set of claim ids marked PASSED in every check file up to and including upto_stage_dir (and the review check)."""
    ids = set()
    if not run:
        return None
    dirs = sorted(d for d in os.listdir(run) if re.match(r"stage-\d\d-", d))
    if upto_stage_dir:
        dirs = [d for d in dirs if d <= upto_stage_dir]
    for d in dirs:
        p = os.path.join(run, d, "check.md")
        if os.path.exists(p):
            ids |= {c["id"] for c in parse_claims(read(p)) if c["result"] == "PASSED"}
    p = os.path.join(run, "review", "check-review.md")
    if os.path.exists(p):
        ids |= {c["id"] for c in parse_claims(read(p)) if c["result"] == "PASSED"}
    return ids


def check_provenance_in_text(path, section_names, tag, run=None, upto=None):
    text = read(path)
    allowed = passed_claim_ids(run, upto) if run else None
    for sec in section_names:
        m = re.search(rf"^{re.escape(sec)}\b[^\n]*\n(.*?)(?=^(?:\d+ )?[A-Z][A-Z \-]{{3,}}\s*$|\Z)", text, re.S | re.M)
        body = m.group(1) if m else ""
        lines = [l for l in body.splitlines() if l.strip().startswith(("-", "*", "CLAIM")) or re.match(r"^\s*\d+[\.\)]", l)]
        untagged = [l for l in lines if not PROV.search(l)]
        rep(len(untagged) == 0, f"PROV-{tag}-{sec.split()[0]}", f"{path} {sec}: {len(untagged)} untagged claim line(s)")
        if allowed is not None and sec in ("MERGED", "3 WHY IT SURVIVED"):
            nocid = [l for l in lines if not CIDS.search(l)]
            rep(len(nocid) == 0, f"CID-{tag}-{sec.split()[0]}", f"{path} {sec}: {len(nocid)} line(s) without claim ids in braces")
            bad = []
            for l in lines:
                for grp in CIDS.findall(l):
                    for cid in [x.strip() for x in grp.split(",") if x.strip()]:
                        norm_id = cid[1:] if cid.upper().startswith("C") else cid
                        if norm_id not in allowed and cid not in allowed:
                            bad.append(cid)
            rep(len(bad) == 0, f"CIDP-{tag}-{sec.split()[0]}", f"{path} {sec}: every cited claim id is PASSED ({bad})")


# ------------------------------------------------------------------ run audit
def audit_run(run):
    j = lambda *a: os.path.join(run, *a)
    # required files
    for f in ["ask.md", "registry.json", "gate/gate.json", "status.json", "log.jsonl"]:
        rep(os.path.exists(j(f)), "FILE-" + f.replace("/", "_"), f"{f} exists")
    if not os.path.exists(j("log.jsonl")):
        return
    log = [json.loads(l) for l in read(j("log.jsonl")).splitlines() if l.strip()]
    stages = sorted(d for d in os.listdir(run) if re.match(r"stage-\d\d-", d))

    # stamps and headings
    for st in stages:
        seats = [f for f in os.listdir(j(st)) if f.startswith("seat-")]
        for s in seats:
            first = read(j(st, s)).splitlines()[0] if read(j(st, s)).strip() else ""
            m = STAMP.match(first)
            rep(bool(m), f"STAMP-{st}-{s}", f"line 1 is a stamp ({first[:40]!r})")
            if m:
                rep(m.group(1) == st[6:8], f"STAMP-MATCH-{st}-{s}", "stamp stage number matches folder")
        # completeness
        gate = json.load(open(j("gate/gate.json")))
        mincrew = gate.get("min_crew", 2)
        rep(len(seats) >= mincrew, f"CREW-{st}", f"{len(seats)} seat replies >= min_crew {mincrew}")
        if os.path.exists(j(st, "check.md")):
            check_evidence_file(j(st, "check.md"), st)
        else:
            rep(False, f"FILE-{st}-check", "check.md exists")
        if os.path.exists(j(st, "close.md")):
            close = read(j(st, "close.md"))
            need = ["OPTIONS", "KILLS", "OPEN", "METRICS"] if st.endswith("generate") else ["MERGED", "KILLS", "OPEN", "CONFLICT", "METRICS"]
            for h in need:
                rep(re.search(rf"^{h}\b", close, re.M) is not None, f"CLOSE-{st}-{h}", f"close.md has heading {h}")
            if "MERGED" in need:
                check_provenance_in_text(j(st, "close.md"), ["MERGED"], st, run=run, upto=st)
        else:
            rep(False, f"FILE-{st}-close", "close.md exists")

    # no new options after generate
    if stages:
        gen_close = j(stages[0], "close.md")
        if os.path.exists(gen_close):
            opts0 = set(re.findall(r"^\s*(\d+)[\.\)]\s", re.split(r"^KILLS", read(gen_close), 1, re.M)[0], re.M))
            for st in stages[1:]:
                p = j(st, "close.md")
                if os.path.exists(p):
                    txt = read(p)
                    m = re.search(r"^OPTIONS STANDING.*?$(.*?)(?=^[A-Z]{4,}|\Z)", txt, re.S | re.M)
                    opts = set(re.findall(r"^\s*(\d+)[\.\)]\s", m.group(1) if m else "", re.M))
                    new = opts - opts0
                    rep(len(new) == 0, f"NOOPT-{st}", f"no option numbers outside the generate list ({sorted(new)})")

    # reviewer isolation: no send to REVIEWER between handshake and REVIEW stage
    sends = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") in ("send", "prompt")]
    before_review = [l for l in sends if l.get("stage") not in ("REVIEW", "REGISTRY") and l.get("action") != "handshake"]
    hs = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") == "handshake"]
    rep(len(hs) == 1, "ISO-3", f"reviewer handshaked exactly once ({len(hs)})")
    rep(len(before_review) == 0, "ISO-2", f"reviewer received no run content before REVIEW ({len(before_review)} violations)")

    # review package must not contain seat files or kills
    if os.path.exists(j("review", "package.md")):
        pk = read(j("review", "package.md"))
        leak = re.search(r"STAGE \d\d [A-Z\-]+ SEAT", pk) or re.search(r"^KILLS\b", pk, re.M)
        rep(leak is None, "ISO-2b", "review package contains no seat file stamp and no KILLS section")
        names = re.findall(r"(Sol|Gemini|Grok|Magistral|Fable|Astra|GPT|Claude|Mistral)", pk)
        rep(len(names) == 0, "ISO-4", f"review package has attribution stripped ({len(names)} model-name hits)")
    if os.path.exists(j("review", "check-review.md")):
        check_evidence_file(j("review", "check-review.md"), "review")

    # generate wall leak heuristic: identical unusual 12-word sequences across seat files
    if stages:
        seatfiles = [j(stages[0], f) for f in os.listdir(j(stages[0])) if f.startswith("seat-")]
        shingles = {}
        for sf in seatfiles:
            words = re.findall(r"[a-z]{3,}", read(sf).lower())
            sh = set(" ".join(words[i:i + 12]) for i in range(0, max(0, len(words) - 12)))
            shingles[sf] = sh
        leaks = 0
        for a, b in itertools.combinations(seatfiles, 2):
            common = shingles[a] & shingles[b]
            common = {s for s in common if not s.startswith(("reply with", "do not", "you are one"))}
            if len(common) >= 3:
                leaks += 1
        rep(leaks == 0, "ISO-1", f"no shared 12-word sequences across generate files beyond prompt boilerplate ({leaks} suspicious pairs)")

    # write-once: file hashes recorded in log must match disk
    hashed = [l for l in log if l.get("sha256") and l.get("file")]
    bad = 0
    for l in hashed:
        p = j(l["file"])
        if os.path.exists(p):
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h != l["sha256"] and l["file"] != "status.json":
                bad += 1
    rep(bad == 0, "WO-1", f"every hashed file unchanged since its write log ({bad} altered)")

    # final
    if os.path.exists(j("final", "DELIVERABLE.md")):
        d = read(j("final", "DELIVERABLE.md"))
        for sec in DELIV_SECTIONS:
            rep(re.search(rf"^{re.escape(sec)}\b", d, re.M) is not None, f"DELIV-{sec.split()[0]}", f"deliverable has section {sec}")
        check_provenance_in_text(j("final", "DELIVERABLE.md"), ["3 WHY IT SURVIVED"], "final", run=run)
        rep("PRIVATE DOCUMENT VERIFICATION" in d and not re.search(r"CONTRADICTIONS\s*-", d), "DELIV-14", "section 14 present and empty in DELIVERABLE.md (verifier lives in its own file)")
        if os.path.exists(j("final", "verifier.md")) and os.path.exists(j("final", "DELIVERABLE_ASSEMBLED.md")):
            asm = read(j("final", "DELIVERABLE_ASSEMBLED.md"))
            rep(asm.startswith(d.rstrip()[:200]), "WO-2", "assembled deliverable starts with the unedited DELIVERABLE.md")
    # dispatch and capture records
    def jsonl(pth):
        return [json.loads(l) for l in read(pth).splitlines() if l.strip()] if os.path.exists(pth) else []
    disp = jsonl(j("dispatch.jsonl")); caps = jsonl(j("capture.jsonl"))
    if disp:
        ids = [d.get("dispatch_id") for d in disp]
        rep(len(ids) == len(set(ids)), "DISP-1", f"dispatch ids unique ({len(ids) - len(set(ids))} duplicates)")
        capmap = {c.get("dispatch_id"): c for c in caps}
        stale = 0; missing = 0
        for st in stages:
            for f in os.listdir(j(st)):
                if f.startswith("seat-"):
                    lines = read(j(st, f)).splitlines()
                    did = lines[1].split()[1] if len(lines) > 1 and lines[1].startswith("DISPATCH ") else None
                    d = next((x for x in disp if x.get("dispatch_id") == did), None)
                    if d is None:
                        missing += 1
                    elif d.get("stage_id") and d["stage_id"] != st:
                        stale += 1
                    if did and did in capmap and (not capmap[did].get("completion_signal_observed") or capmap[did].get("partial")):
                        rep(False, f"CAP-{st}-{f}", "counted seat file has a complete capture record")
        rep(missing == 0, "DISP-2", f"every seat file cites a dispatch record ({missing} missing)")
        rep(stale == 0, "DISP-3", f"no seat file cites a dispatch from another stage ({stale} stale)")
    # neutrality of packets
    for pk in [j("review", "package.md")] + [j(st, "packet.md") for st in stages]:
        if os.path.exists(pk):
            txt = read(pk).lower()
            hits = [w for w in ("winner", "the best option", "recommended option", "final verdict", "previous final", "strongest seat") if w in txt]
            rep(len(hits) == 0, f"NEUT-{os.path.basename(os.path.dirname(pk))}", f"packet has no winner label or prior verdict ({hits})")
    # classification present once in the deliverable
    if os.path.exists(j("final", "DELIVERABLE.md")):
        d_ = read(j("final", "DELIVERABLE.md"))
        cls = re.findall(r"\b(KEEP_FOR_DEVELOPMENT|REVERT|PARTIAL_REPORT)\b", d_)
        rep(len(set(cls)) == 1, "CLASS-1", f"exactly one classification in the deliverable ({sorted(set(cls))})")
    # final written exactly once
    fw = [l for l in log if l.get("file") == "final/DELIVERABLE.md" and l.get("action") in ("send", "write")]
    rep(len(fw) <= 1, "FINAL-ONCE", f"DELIVERABLE.md written at most once in the log ({len(fw)})")
    # experiments: KEEP needs a repeat run
    expdir = j("experiments")
    if os.path.isdir(expdir):
        for d in sorted(os.listdir(expdir)):
            rp = os.path.join(expdir, d, "record.json")
            if os.path.exists(rp):
                rec = json.load(open(rp))
                if rec.get("decision") == "KEEP":
                    rep(rec.get("repeat_value") is not None, f"EXP-KEEP-{d}", "KEEP has a repeat run")
                    rep(bool(rec.get("constraints_checked")), f"EXP-CONS-{d}", "KEEP has hard constraints checked")
                rep(rec.get("decision") in ("KEEP", "REVERT", "INCONCLUSIVE"), f"EXP-DEC-{d}", f"decision is one of three ({rec.get('decision')})")
    # architecture decisions: paired floor and predefined criterion
    ad = os.path.join(run, "..", "..", "architecture", "decisions.jsonl")
    if os.path.exists(ad):
        for line in read(ad).splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("decision") == "KEEP":
                rep(int(d.get("paired_runs", 0)) >= 8, f"ARCH-FLOOR-{d.get('id')}", "KEEP has at least 8 paired HOLDOUT runs")
                rep(d.get("split") == "HOLDOUT", f"ARCH-SPLIT-{d.get('id')}", "KEEP decided on HOLDOUT tasks")
                rep(d.get("ci_low") is not None and d.get("criterion_id"), f"ARCH-CI-{d.get('id')}", "KEEP cites a bootstrap interval and a predefined criterion id")
    # status resume sanity
    if os.path.exists(j("status.json")):
        stt = json.load(open(j("status.json")))
        for k in ("run", "stage", "step", "last_complete", "next"):
            rep(k in stt, f"STATUS-{k}", f"status.json has {k}")
        if stt.get("last_complete"):
            rep(os.path.exists(j(stt["last_complete"])), "STATUS-LC", "status.last_complete exists on disk")


# ------------------------------------------------------------------ package audit
def audit_package(pkg):
    spec = read(os.path.join(pkg, "NIGHT_AGENT_SPEC.md"))
    disp = read(os.path.join(pkg, "DISPATCH.md"))
    schema = json.load(open(os.path.join(pkg, "SCHEMA.json")))
    prompts = {f: read(os.path.join(pkg, "PROMPTS", f)) for f in sorted(os.listdir(os.path.join(pkg, "PROMPTS")))}
    # six statuses everywhere
    for name, txt in [("spec", spec), ("dispatch", disp), ("P4", prompts["P4_close.md"]), ("P6", prompts["P6_final.md"])]:
        missing = [s for s in STATUSES if s not in txt]
        rep(len(missing) == 0, f"PKG-STATUS-{name}", f"all six statuses named ({missing})")
    rep(set(schema["statuses"]) == set(STATUSES), "PKG-STATUS-schema", "schema statuses equal the six")
    # nevers count
    nev = re.findall(r"^\d\. Never ", disp, re.M)
    rep(len(nev) == 8, "PKG-NEVERS", f"DISPATCH lists eight nevers ({len(nev)})")
    # contradiction probes (regressions of I1..I11)
    rep("three times" not in disp and "three times" not in spec.split("## 12.")[0], "PKG-I4", "no 'three times in one round' rule survives")
    rep("merged-5 and its claims only" not in spec.split("## 12.")[0], "PKG-I2", "no 'merged-5 and its claims only' rule survives outside the resolution table")
    rep("paste the verifier" not in disp.lower() or "never edit deliverable.md" in disp.lower(), "PKG-I3", "verifier is not pasted into DELIVERABLE.md")
    rep("powercfg /change" not in disp.split("## 1.")[0] or "may not run" in disp, "PKG-I7", "Dispatch may not run powercfg /change")
    rep("three non-negotiables" in disp and "(1)" in disp and "(3)" in disp, "PKG-I8", "the three non-negotiables are named")
    rep("HOLD-ACCEPTED" in prompts["P6_final.md"] and "HOLD-ACCEPTED" in disp, "PKG-I9", "HOLD recording semantics present in P6 and DISPATCH")
    rep("ALL KILLS" in prompts["P6_final.md"] and "THE ASK" in prompts["P6_final.md"], "PKG-I10", "P6 supplies ASK and ALL KILLS")
    rep("INHERITED, UNVERIFIED" in spec, "PKG-I11", "inherited model claims labelled unverified")
    rep("one of several reviewers" in prompts["P2_generate.md"] and "forbids content" in spec, "PKG-I1", "wall defined as content, P2 keeps the independence sentence")
    rep("na_gate.py" in disp and os.path.exists(os.path.join(pkg, "TESTS", "na_gate.py")), "PKG-GUARDS", "DISPATCH invokes na_gate.py and it exists")
    rep("HOLDOUT" in spec and "paired" in spec.lower(), "PKG-ARCH", "spec has HOLDOUT split and paired design")
    rep("{C1,C3}" in prompts["P4_close.md"] and "{C<n>}" in prompts["P6_final.md"], "PKG-CID", "P4 and P6 require claim ids in braces")
    rep("not a reproduction" in spec, "PKG-AUTORESEARCH", "AutoResearch labelled as an adaptation, not a reproduction")
    rep("DEPRIORITIZED" in prompts["P4_close.md"] and "STRUCTURAL" not in prompts["P4_close.md"], "PKG-DEPRI", "P4 uses DEPRIORITIZED and no STRUCTURAL kills")
    rep("support=SUPPORTED" in spec and "quote" in spec.lower(), "PKG-SRC", "spec separates quotation presence from support")
    rep("dispatch.jsonl" in disp and "capture" in disp.lower(), "PKG-DISPATCH", "DISPATCH writes dispatch and capture records")
    rep("KEEP_FOR_DEVELOPMENT" in prompts["P6_final.md"] and "PARTIAL_REPORT" in spec, "PKG-CLASS", "classification present in P6 and spec")
    rep("UNMEASURED" in prompts["P3_operate.md"], "PKG-APPLIC", "P3 requires UNMEASURED for uncomputed statistics")
    # every prompt referenced in DISPATCH exists
    refs = set(re.findall(r"PROMPTS/(P\d_[a-z]+\.md)", disp))
    missing = [r for r in refs if r not in prompts]
    rep(len(missing) == 0, "PKG-PROMPTS", f"every prompt referenced by DISPATCH exists ({missing})")
    # deliverable sections consistent between P6 and schema
    for sec in DELIV_SECTIONS:
        rep(sec.split(" ", 1)[1] in prompts["P6_final.md"], f"PKG-DELIV-{sec.split()[0]}", f"P6 names section {sec}")
    # no em-dashes anywhere
    for name, txt in [("spec", spec), ("dispatch", disp)] + list(prompts.items()):
        rep("\u2014" not in txt, f"PKG-EMDASH-{name}", "no em-dash")
    # prompt width for the workbook
    for name, txt in prompts.items():
        rep(max(len(l) for l in txt.splitlines()) <= 72, f"PKG-WIDTH-{name}", "prompt lines fit 72 columns")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "--package":
        audit_package(sys.argv[2])
    else:
        audit_run(sys.argv[1])
    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} passed, {len(fails)} failed")
    sys.exit(1 if fails else 0)
