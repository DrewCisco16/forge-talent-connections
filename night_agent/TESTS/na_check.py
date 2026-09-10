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
REPLY_HEADINGS = {"generate": ["CANDIDATES", "CLAIMS", "KNOCKDOWN", "MISSING"], "direct": ["ANSWER", "CLAIMS", "OPEN"],
                  "operate": ["WRONG", "MISSING", "KILLS", "OPEN"], "review": ["HITS", "GAPS", "HOLDS", "OPEN"],
                  "verifier": ["CONTRADICTIONS", "CONFIRMED", "NOT COVERED", "MATERIAL OMISSIONS"]}


def check_headings(path, kind, tag):
    """A reply is saved only if every heading its prompt requires is present (DISPATCH 3.1, 3.5, 3.6, 3.8, 5)."""
    txt = read(path)
    missing = [h for h in REPLY_HEADINGS[kind] if re.search(rf"^{re.escape(h)}\b", txt, re.M) is None]
    rep(len(missing) == 0, f"HEAD-{tag}", f"{path}: required headings present ({missing})")


DELIV_SECTIONS = ["1 THE RESULT", "2 WHAT SURVIVED", "3 WHY IT SURVIVED", "4 OBJECTIVE RESULTS", "5 WHAT DIED AND WHY",
                  "6 TRADE-OFFS", "7 OUTSIDE REVIEW", "8 STILL OPEN", "9 CONFIDENCE", "10 RUN INTEGRITY", "11 EFFICIENCY", "12 NEXT QUESTION"]

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SCHEMA.json")

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
            if src:
                rep(m is not None and m.group(1) in SUPPORT_OK, f"SRC-3-{tag}-{c['id']}", "SOURCE line carries a support= status from the six")
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
        if c["result"] in NEED_RETRIEVED:
            rep(c["method"] != "none", f"EVID-5-{tag}-{c['id']}", f"{c['result']} has a check method (METHOD none can only be JUDGEMENT CALL)")
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
    if os.path.exists(p) and upto_stage_dir is None:  # reviewer claims exist only from REVIEW onward, never in a stage close
        ids |= {c["id"] for c in parse_claims(read(p)) if c["result"] == "PASSED"}
    return ids


def failed_claim_ids(run, upto_stage_dir):
    """Normalised ids (leading C dropped) of claims marked FAILED in check files up to and including upto_stage_dir."""
    ids = set()
    for d in sorted(d for d in os.listdir(run) if re.match(r"stage-\d\d-", d)):
        if upto_stage_dir and d > upto_stage_dir:
            continue
        p = os.path.join(run, d, "check.md")
        if os.path.exists(p):
            ids |= {c["id"].upper().lstrip("C") for c in parse_claims(read(p)) if c["result"] == "FAILED"}
    return ids


def check_kills_earned(path, tag, run, upto):
    """Every KILLS entry names a FAILED claim or an explicit hard constraint (spec 4.3: only those two things kill)."""
    text = read(path)
    m = re.search(r"^KILLS\b[^\n]*\n(.*?)(?=^(?:\d+ )?[A-Z][A-Z \-]{3,}\s*$|\Z)", text, re.S | re.M)
    body = m.group(1) if m else ""
    failed = failed_claim_ids(run, upto)
    bad = []
    for l in body.splitlines():
        if not l.strip().startswith(("-", "*")) and not re.match(r"^\s*\d+[\.\)]", l):
            continue
        cited = {x.upper().lstrip("C") for x in re.findall(r"\bclaim\s+(C?\w+)", l, re.I)} | {x.lstrip("C") for x in re.findall(r"\bC\d+\b", l)}
        cited |= {x.strip().upper().lstrip("C") for grp in CIDS.findall(l) for x in grp.split(",") if x.strip()}
        if "constraint" not in l.lower() and not (cited & failed):
            bad.append(l.strip()[:60])
    rep(len(bad) == 0, f"KILL-EARNED-{tag}", f"{path} KILLS: every entry names a FAILED claim or a hard constraint ({bad})")


def check_provenance_in_text(path, section_names, tag, run=None, upto=None):
    text = read(path)
    allowed = passed_claim_ids(run, upto) if run else None
    for sec in section_names:
        m = re.search(rf"^{re.escape(sec)}\b[^\n]*\n(.*?)(?=^(?:\d+ )?[A-Z][A-Z \-]{{3,}}\s*$|\Z)", text, re.S | re.M)
        body = m.group(1) if m else ""
        lines = [l for l in body.splitlines() if l.strip().startswith(("-", "*", "CLAIM")) or re.match(r"^\s*\d+[\.\)]", l)]
        untagged = [l for l in lines if not PROV.search(l)]
        rep(len(untagged) == 0, f"PROV-{tag}-{sec.split()[0]}", f"{path} {sec}: {len(untagged)} untagged claim line(s)")
        if sec == "MERGED":
            early_r = [l for l in lines if "[R]" in l]
            rep(len(early_r) == 0, f"PROV-R-{tag}", f"{path} MERGED: {len(early_r)} line(s) carry [R] before REVIEW ran")
        if allowed is not None and sec in ("MERGED", "3 WHY IT SURVIVED"):
            nocid = [l for l in lines if not any(g.strip() for g in CIDS.findall(l))]
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
    gate = json.load(open(j("gate/gate.json"))) if os.path.exists(j("gate/gate.json")) else {}
    stages = sorted(d for d in os.listdir(run) if re.match(r"stage-\d\d-", d))
    registry = json.load(open(j("registry.json"))) if os.path.exists(j("registry.json")) else {}
    seat_ids = {s.get("id") for s in registry.get("seats", [])}
    direct = bool(stages) and stages[0].endswith("-direct")  # DISPATCH 5: one generator, check, final; no close, no review
    flags_all = set((json.load(open(j("ledger.json"))) if os.path.exists(j("ledger.json")) else {}).get("flags", []))
    flags_all |= set((json.load(open(j("status.json"))) if os.path.exists(j("status.json")) else {}).get("flags", []))

    # stamps and headings
    for st in stages:
        seats = [f for f in os.listdir(j(st)) if f.startswith("seat-")]
        for s in seats:
            first = read(j(st, s)).splitlines()[0] if read(j(st, s)).strip() else ""
            m = STAMP.match(first)
            rep(bool(m), f"STAMP-{st}-{s}", f"line 1 is a stamp ({first[:40]!r})")
            if m:
                rep(m.group(1) == st[6:8], f"STAMP-MATCH-{st}-{s}", "stamp stage number matches folder")
                rep(m.group(2) == st.split("-", 2)[2].upper(), f"STAMP-OP-{st}-{s}", f"stamp stage name matches folder ({m.group(2)} vs {st.split('-', 2)[2].upper()})")
                rep(m.group(3) == s[5:-3], f"STAMP-FILE-{st}-{s}", f"stamp seat id matches file name ({m.group(3)})")
                if seat_ids:
                    ready = {x.get("id") for x in registry.get("seats", []) if x.get("ready")}
                    rep(m.group(3) in seat_ids, f"STAMP-REG-{st}-{s}", f"stamp seat id is in the registry ({m.group(3)})")
                    rep(m.group(3) in ready, f"STAMP-READY-{st}-{s}", f"stamp seat is READY in the registry ({m.group(3)})")
            check_headings(j(st, s), "generate" if st.endswith("-generate") else "direct" if st.endswith("-direct") else "operate", f"{st}-{s}")
        # completeness
        gate = json.load(open(j("gate/gate.json")))
        mincrew = 1 if st.endswith("-direct") else gate.get("min_crew", 2)
        rep(len(seats) >= mincrew, f"CREW-{st}", f"{len(seats)} seat replies >= min_crew {mincrew}")
        ready_gens = [x for x in registry.get("seats", []) if x.get("ready") and (x.get("role") == "generator" or (not x.get("role") and str(x.get("id", "")).startswith("G")))]
        if ready_gens and not st.endswith("-direct") and len(seats) < len(ready_gens):
            rep("REDUCED_CREW" in flags_all, f"REDUCED-{st}", f"{len(seats)} replies from {len(ready_gens)} READY generators is flagged REDUCED_CREW (spec 7)")
        if os.path.exists(j(st, "check.md")):
            check_evidence_file(j(st, "check.md"), st)
        else:
            rep(False, f"FILE-{st}-check", "check.md exists")
        if os.path.exists(j(st, "close.md")):
            close = read(j(st, "close.md"))
            need = ["OPTIONS", "KILLS", "OPEN", "METRICS"] if st.endswith("generate") else ["MERGED", "KILLS", "DEPRIORITIZED", "OPEN", "CONFLICT", "OPTIONS STANDING", "METRICS"]
            for h in need:
                rep(re.search(rf"^{h}\b", close, re.M) is not None, f"CLOSE-{st}-{h}", f"close.md has heading {h}")
            if st.endswith("generate"):  # P4 LIST mode: the closer lists, it does not merge
                rep(re.search(r"^MERGED\b", close, re.M) is None, f"CLOSE-{st}-NOMERGE", "LIST-mode close has no MERGED section")
            check_kills_earned(j(st, "close.md"), st, run, st)
            if "MERGED" in need:
                check_provenance_in_text(j(st, "close.md"), ["MERGED"], st, run=run, upto=st)
        elif not st.endswith("-direct"):
            rep(False, f"FILE-{st}-close", "close.md exists")

    # reused conversations (spec 7): a seat whose window carries prior history is never independent; the run must say CONTAMINATION
    reused = [x.get("id") for x in registry.get("seats", []) if x.get("fresh") is False]
    if reused:
        rep("CONTAMINATION" in flags_all, "FRESH", f"reused conversation(s) {reused} are flagged CONTAMINATION")

    # minimum crew floor (spec 2: two generators plus a closer; below that the night stops with CREW)
    if gate:
        rep(int(gate.get("min_crew", 2)) >= 2, "GATE-MINCREW", f"gate min_crew is at least 2 ({gate.get('min_crew')})")

    # gate record enumerations (spec 1, 4.4): CLASS and PROFILE must be values the schema defines
    if gate and os.path.exists(SCHEMA):
        sc = json.load(open(SCHEMA))
        rep(gate.get("class") in sc.get("classes", []), "GATE-CLASS", f"gate CLASS is one of the schema classes ({gate.get('class')!r})")
        rep(gate.get("profile") in sc.get("profiles", {}), "GATE-PROFILE", f"gate PROFILE is one of the schema profiles ({gate.get('profile')!r})")

    # the run layout follows the gate class (spec 1, 4, 5; DISPATCH 3, 4, 5)
    cls = gate.get("class")
    if cls == "DIRECT":
        rep(stages == ["stage-01-direct"], "LAYOUT-DIRECT", f"DIRECT run has exactly stage-01-direct ({stages})")
    elif cls in ("DELIBERATION", "HYBRID", "HYBRID-NO-EXEC"):
        rep(bool(stages) and stages[0] == "stage-01-generate", "LAYOUT-GENERATE", f"{cls} run starts with stage-01-generate ({stages[:1]})")
    elif cls == "EXPERIMENT":
        rep(not stages and os.path.exists(j("experiments", "baseline.json")), "LAYOUT-EXPERIMENT", f"EXPERIMENT run has a baseline and no evidence stages ({stages})")

    # operator selection: each operator at most once, inside the library, within the gate's max_operators (spec 4.4, 6)
    ops = [st.split("-", 2)[2].upper() for st in stages if not st.endswith(("-generate", "-direct"))]
    library = set((json.load(open(SCHEMA)).get("operators", {}) if os.path.exists(SCHEMA) else {}).keys())
    rep(len(ops) == len(set(ops)), "OP-ONCE", f"no operator ran twice ({sorted(o for o in set(ops) if ops.count(o) > 1)})")
    if library:
        rep(set(ops) <= library, "OP-LIB", f"every operator stage is in the SCHEMA library ({sorted(set(ops) - library)})")
    max_ops = (gate.get("budget", {}) or {}).get("max_operators", 4) if os.path.exists(j("gate/gate.json")) else 4
    rep(len(ops) <= int(max_ops), "OP-MAX", f"operator stages {len(ops)} <= max_operators {max_ops}")
    if gate.get("profile") == "v10-fixed":  # spec 4.4: the fixed profile runs FMEA, IDOV, TRIZ, BAYES in that order
        fixed = (json.load(open(SCHEMA)).get("profiles", {}).get("v10-fixed", {}).get("order") if os.path.exists(SCHEMA) else None) or ["FMEA", "IDOV", "TRIZ", "BAYES"]
        rep(ops == fixed[:len(ops)], "OP-FIXED", f"v10-fixed operators ran in the fixed order ({ops} vs {fixed})")

    # claim ids are unique across the run (otherwise a cited id is ambiguous and CIDP means nothing)
    seen = {}
    for pth in [j(st, "check.md") for st in stages] + [j("review", "check-review.md")]:
        if os.path.exists(pth):
            for c in parse_claims(read(pth)):
                seen.setdefault(c["id"], []).append(os.path.relpath(pth, run))
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    rep(len(dupes) == 0, "CID-UNIQ", f"every claim id appears once across all check files ({dupes})")

    # no new options after generate
    if stages and not direct:
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
            # the same wall applies to the review package and the deliverable: no option that GENERATE did not create
            for rel, sec in (("review/package.md", "OPTIONS STANDING"), ("final/DELIVERABLE.md", "2 WHAT SURVIVED")):
                if os.path.exists(j(rel)):
                    txt = read(j(rel))
                    m = re.search(rf"^{re.escape(sec)}.*?$(.*?)(?=^(?:\d+ )?[A-Z][A-Z \-]{{3,}}\s*$|\Z)", txt, re.S | re.M)
                    body = m.group(1) if m else ""
                    opts = set(re.findall(r"^\s*(\d+)[\.\)]\s", body, re.M)) | {n for n in re.findall(r"\bOption (\d+)\b", body)}
                    new = opts - opts0
                    rep(len(new) == 0, f"NOOPT-{rel.split('/')[0]}", f"{rel} {sec}: no option numbers outside the generate list ({sorted(new)})")

    # reviewer isolation: no send to REVIEWER between handshake and REVIEW stage
    sends = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") in ("send", "prompt")]
    before_review = [l for l in sends if l.get("stage") not in ("REVIEW", "REGISTRY") and l.get("action") != "handshake"]
    hs = [l for l in log if l.get("seat") == "REVIEWER" and l.get("action") == "handshake"]
    if "REVIEWER" in seat_ids:
        rep(len(hs) == 1, "ISO-3", f"reviewer handshaked exactly once ({len(hs)})")
        first_gen = next((i for i, l in enumerate(log) if l.get("stage") == "GENERATE" and l.get("action") in ("send", "prompt")), None)
        hs_idx = next((i for i, l in enumerate(log) if l.get("seat") == "REVIEWER" and l.get("action") == "handshake"), None)
        if first_gen is not None and hs_idx is not None:
            rep(hs_idx < first_gen, "ISO-5", "reviewer handshake precedes the first GENERATE send (isolation starts before the run has content)")
    rep(len(before_review) == 0, "ISO-2", f"reviewer received no run content before REVIEW ({len(before_review)} violations)")

    # review package must not contain seat files or kills
    if os.path.exists(j("review", "package.md")):
        pk = read(j("review", "package.md"))
        leak = re.search(r"STAGE \d\d [A-Z\-]+ SEAT", pk) or re.search(r"^KILLS\b", pk, re.M)
        rep(leak is None, "ISO-2b", "review package contains no seat file stamp and no KILLS section")
        names = re.findall(r"(Sol|Gemini|Grok|Magistral|Fable|Astra|GPT|Claude|Mistral)", pk)
        rep(len(names) == 0, "ISO-4", f"review package has attribution stripped ({len(names)} model-name hits)")
    if os.path.exists(j("review", "review.md")):
        check_headings(j("review", "review.md"), "review", "review")
    if os.path.exists(j("final", "verifier.md")):
        check_headings(j("final", "verifier.md"), "verifier", "verifier")
        vt = read(j("final", "verifier.md"))
        m = re.search(r"^CONTRADICTIONS\b[^\n]*\n(.*?)(?=^[A-Z][A-Z ]{3,}\s*$|\Z)", vt, re.S | re.M)
        items = [l for l in (m.group(1) if m else "").splitlines() if re.match(r"^\s*(\d+[\.\)]|[-*])\s*\S", l) and l.strip().lower() not in ("- none", "* none")]
        if items:
            rep("PROVISIONAL" in flags_all, "PROVISIONAL", f"{len(items)} verifier CONTRADICTION(s) mark the run PROVISIONAL (spec 4.8)")
    if os.path.exists(j("review", "check-review.md")):
        rc = check_evidence_file(j("review", "check-review.md"), "review")
        notr = [c["id"] for c in rc if c["prov"] != "R"]
        rep(len(notr) == 0, "REV-PROV", f"every check-review claim carries [R] ({notr})")

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

    # every file Dispatch produced has a log record (DISPATCH 6: one line per action, file written, sha256)
    logged_files = {l.get("file") for l in log if l.get("file")}
    unlogged = []
    for top in stages + ["review", "final"]:
        if os.path.isdir(j(top)):
            for f in sorted(os.listdir(j(top))):
                rel = f"{top}/{f}"
                if os.path.isfile(j(rel)) and rel not in logged_files:
                    unlogged.append(rel)
    rep(len(unlogged) == 0, "LOG-ALL", f"every stage, review and final file has a log record ({unlogged})")

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
        tail = d.split("PRIVATE DOCUMENT VERIFICATION", 1)[1] if "PRIVATE DOCUMENT VERIFICATION" in d else "x"
        rep("PRIVATE DOCUMENT VERIFICATION" in d and not tail.strip(), "DELIV-14", "section 14 present and empty in DELIVERABLE.md (verifier lives in its own file, I3)")
        if os.path.exists(j("final", "verifier.md")) and os.path.exists(j("final", "DELIVERABLE_ASSEMBLED.md")):
            asm = read(j("final", "DELIVERABLE_ASSEMBLED.md"))
            rep(asm.startswith(d.rstrip()[:200]), "WO-2", "assembled deliverable starts with the unedited DELIVERABLE.md")
            ver = read(j("final", "verifier.md"))
            rep(asm.rstrip().endswith(ver.rstrip()) and len(asm) >= len(d) + len(ver.rstrip()), "WO-3", "assembled deliverable is DELIVERABLE.md followed by verifier.md")
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
        # capture records describe the saved reply (spec 7): a real byte hash, matching the file, and the right length
        badcap = []
        for c in caps:
            p_ = j(c.get("file", ""))
            if not c.get("file") or not os.path.exists(p_):
                continue
            t = read(p_)
            if not re.fullmatch(r"[0-9a-f]{64}", str(c.get("byte_hash", ""))):
                badcap.append(f"{c['file']}: byte_hash is not a sha256")
            elif c["byte_hash"] != hashlib.sha256(t.encode("utf-8")).hexdigest():
                badcap.append(f"{c['file']}: byte_hash differs from the file")
            if c.get("char_count") != len(t):
                badcap.append(f"{c['file']}: char_count {c.get('char_count')} != {len(t)}")
        rep(len(badcap) == 0, "CAP-MATCH", f"every capture record matches its saved reply ({badcap[:3]})")
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
