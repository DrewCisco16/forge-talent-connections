"""Deterministic seats for rehearsal and CI. No network, no model, no spend.

FakeSeat answers every prompt kind with text that satisfies the prompt's headings and the checker's rules
by construction, derived from the packet it receives (so the closer's LIST and MERGE closes are built from
the check results Dispatch actually wrote). Layer B fault knobs (TESTS/ADVERSARIAL_TESTS.md) are switched on
with --fault Bn[:seat[:stage]].

LocalExecutor is the executor for fake mode: it runs the gate's procedures with subprocess inside the
working copy and applies the one-line mutations the fake proposals name. It is deterministic and needs no model.
"""
import os
import re
import subprocess
import time

from .. import parse
from ..packets import Packet
from .base import Reply

GEN_TEXT = {
    "G1": ("CANDIDATES\n"
           "A. Validate every row against a declared schema before it is inserted.\n"
           "   APPROACH: parse, validate against the column schema, insert only valid rows.\n"
           "   ASSUMPTIONS: the schema is known before import.\n"
           "   REQUIRED CLAIMS: 1, 2\n"
           "   FALSIFICATION CONDITIONS: runtime rises more than five percent on the twelve column file.\n"
           "   EXPECTED UPSIDE: every malformed row is caught at the door.\n"
           "   FAILURE MODES: a schema that lags the data rejects valid rows.\n"
           "   MEASURABLE PREDICTIONS: runtime_s rises under five percent with the schema cached.\n"
           "   DISTINGUISHING EXPERIMENT: cache the schema and time the import.\n"
           "B. Two pass import: count and type the columns first, then load in a second pass.\n"
           "   APPROACH: a cheap first pass finds malformed rows and writes the reject report.\n"
           "   ASSUMPTIONS: reading the file twice is affordable.\n"
           "   REQUIRED CLAIMS: 2\n"
           "   FALSIFICATION CONDITIONS: the second pass exceeds the timing budget.\n"
           "   EXPECTED UPSIDE: the reject report is complete before any insert.\n"
           "   FAILURE MODES: doubled input cost on very large files.\n"
           "   MEASURABLE PREDICTIONS: runtime_s rises about twenty percent.\n"
           "   DISTINGUISHING EXPERIMENT: time both passes on the benchmark file.\n"
           "CLAIMS\n"
           "1. The current importer handles 21600 rows in 12 seconds, that is 1800 rows per second (sum: 21600 / 12 = 1800).\n"
           "2. The project brief requires malformed rows to be reported, not dropped (document: brief.md, \"every rejected row is written to rejects.csv with its line number\").\n"
           "KNOCKDOWN\n"
           "A dies if schema validation doubles the runtime. B dies if the second pass alone exceeds the budget.\n"
           "MISSING\n"
           "A timing baseline on the widest file the brief mentions.\n"),
    "G2": ("CANDIDATES\n"
           "A. Reject rows at parse time using the parser library strict mode.\n"
           "   APPROACH: turn on strict mode so ragged rows raise and are logged.\n"
           "   ASSUMPTIONS: the pinned library version exposes strict mode.\n"
           "   REQUIRED CLAIMS: 1, 2\n"
           "   FALSIFICATION CONDITIONS: strict mode is absent from the pinned version.\n"
           "   EXPECTED UPSIDE: no second code path to maintain.\n"
           "   FAILURE MODES: strict mode rejects rows the schema would accept.\n"
           "   MEASURABLE PREDICTIONS: monthly throughput stays near 700 rows per unit.\n"
           "   DISTINGUISHING EXPERIMENT: none\n"
           "CLAIMS\n"
           "1. The parser library documents a strict mode that rejects ragged rows (source: DOI 10.1000/xyz123, \"strict mode raises on malformed input\").\n"
           "2. Twelve monthly figures totalling 9000 give a mean of 700 rows per month (sum: 9000 / 12 = 700).\n"
           "KNOCKDOWN\n"
           "A dies if the strict flag is missing from the version the project pins.\n"
           "MISSING\n"
           "Which library version the project actually pins.\n"),
    "G3": ("CANDIDATES\n"
           "A. Sample a tenth of the rows and validate the sample only.\n"
           "   APPROACH: statistical spot check instead of full validation.\n"
           "   ASSUMPTIONS: malformed rows cluster, so a sample finds them.\n"
           "   REQUIRED CLAIMS: 1, 2\n"
           "   FALSIFICATION CONDITIONS: a malformed row escapes the sample.\n"
           "   EXPECTED UPSIDE: almost no runtime cost.\n"
           "   FAILURE MODES: silent acceptance of bad rows.\n"
           "   MEASURABLE PREDICTIONS: runtime_s falls by a tenth.\n"
           "   DISTINGUISHING EXPERIMENT: plant five malformed rows and count how many the sample finds.\n"
           "CLAIMS\n"
           "1. Sampling validation is standard practice in comparable importers (judgement call, no way to check it).\n"
           "2. The brief allows partial loads when a reject is found (document: brief.md, \"partial loads are permitted\").\n"
           "KNOCKDOWN\n"
           "A dies if a single planted malformed row survives the sample.\n"
           "MISSING\n"
           "What sample rate the operator would accept.\n"),
    "G4": ("CANDIDATES\n"
           "A. Quarantine table: load everything, then move rows that fail a post-load audit to a quarantine table.\n"
           "   APPROACH: audit after insert with a database constraint sweep.\n"
           "   ASSUMPTIONS: the database can hold malformed rows temporarily.\n"
           "   REQUIRED CLAIMS: 1, 2\n"
           "   FALSIFICATION CONDITIONS: downstream consumers read the table before the sweep runs.\n"
           "   EXPECTED UPSIDE: the import path itself is untouched.\n"
           "   FAILURE MODES: a window in which bad rows are visible.\n"
           "   MEASURABLE PREDICTIONS: none\n"
           "   DISTINGUISHING EXPERIMENT: none\n"
           "CLAIMS\n"
           "1. Post-load audits are common in warehouse pipelines (judgement call, no way to check it).\n"
           "2. The widest production file has forty columns (document: brief.md, \"The widest production file has forty columns\").\n"
           "KNOCKDOWN\n"
           "A dies if any consumer reads between load and sweep.\n"
           "MISSING\n"
           "The read schedule of downstream consumers.\n"),
}

OPERATE_TEXT = {
    ("FMEA", "G1"): ("WRONG\nnone\nMISSING\nfailure visibility when a sampled check misses a malformed row\n"
                     "KILLS\n- Option 4: the study it leans on does not exist; the cited DOI 10.9999/notreal.1 does not resolve (source: DOI 10.9999/notreal.1).\n"
                     "OPEN\nwhat sample rate the brief would accept; settle by reading brief.md section 5\n"),
    ("FMEA", "G2"): ("WRONG\n- The 1800 rows per second figure holds only at twelve columns; at forty columns 9000 rows in 12 seconds is 750 rows per second (sum: 9000 / 12 = 750).\n"
                     "MISSING\na widest-file benchmark\nKILLS\nnone\nOPEN\nwhether the brief names a widest file; settle by reading brief.md\n"),
    ("FMEA", "G3"): ("WRONG\nnone\nMISSING\nwhat happens to a partially loaded file when a reject is found\nKILLS\nnone\nOPEN\nnone\n"),
    ("FMEA", "G4"): ("WRONG\nnone\nMISSING\nrollback behaviour after a rejected batch\nKILLS\nnone\nOPEN\nnone\n"),
    ("IDOV", "G1"): ("WRONG\nnone\nMISSING\na measured runtime for option 1 on the twelve column file\nKILLS\nnone\n"
                     "OPEN\nwhether option 2 can be built inside the timing budget; settle with the harness\n"),
    ("IDOV", "G2"): ("WRONG\n- The reference branch test suite passes (command: `python3 test_importer.py`).\nMISSING\nnone\nKILLS\nnone\nOPEN\nnone\n"),
    ("IDOV", "G3"): ("WRONG\nnone\nMISSING\nan acceptance test for the reject report format\nKILLS\nnone\nOPEN\nnone\n"),
    ("IDOV", "G4"): ("WRONG\nnone\nMISSING\nnone\nKILLS\nnone\nOPEN\nnone\n"),
}
GENERIC_OPERATE = "WRONG\nnone\nMISSING\nnothing this lens adds\nKILLS\nnone\nOPEN\nnone\n"

PADDING = "".join(f"{n}. Padding claim number {n} about importer folklore (judgement call, no way to check it).\n" for n in range(3, 23))


LABEL_LINE = re.compile(r"^[A-Z][A-Z /]{2,}(\s{2,}\S|\s*$)", re.M)


def _packet_field(text: str, label: str) -> str:
    """Value of a filled packet field: the rest of the label line, or the lines that follow it up to the next
    label line or blank line (a multi-line value starts on the line after its label)."""
    m = re.search(rf"^{re.escape(label)}[ \t]{{2,}}(.*)$", text, re.M)
    if not m:
        return ""
    if m.group(1).strip():
        return m.group(1).strip()
    val = []
    for l in text[m.end():].split("\n")[1:]:
        if not l.strip() or LABEL_LINE.match(l):
            break
        val.append(l.strip())
    return "\n".join(val).strip()


def _packet_block(text: str, label: str, next_labels: list) -> str:
    """A multi-line packet value: from the label line to the next named label line."""
    m = re.search(rf"^{re.escape(label)}[ \t]{{2,}}", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    end = len(rest)
    for nl in next_labels:
        mm = re.search(rf"^{re.escape(nl)}(\s{{2,}}\S|[ \t]*$)", rest, re.M)
        if mm:
            end = min(end, mm.start())
    return rest[:end].strip("\n")


class FakeSeat:
    def __init__(self, spec, knobs: dict | None = None, world=None):
        self.spec = spec
        self.knobs = knobs or {}
        self.world = world if world is not None else {}
        self.calls = 0

    def _fault(self, code: str, stage: str) -> bool:
        k = self.knobs.get(code)
        if k is None:
            return False
        if k.get("seat") and k["seat"] != self.spec.id:
            return False
        if k.get("stage") and k["stage"] != stage:
            return False
        if k.get("once") and k.get("_used"):
            return False
        k["_used"] = True
        return True

    def send(self, packet: Packet, timeout_s: float, slot_id: str) -> Reply:
        self.calls += 1
        kind = packet.kind
        stage = {"P2": "GENERATE", "P3": "OPERATE", "P4": "CLOSE", "P5": "REVIEW", "P6": "FINAL", "P7": "VERIFY", "P1": "GATE", "P8": "PROPOSE", "P9": "DIRECT"}.get(kind, kind)
        if self._fault("B1", stage) or self._fault("B9", stage):
            return Reply(text="", completed=False, aborted=True, error="fake seat: no reply within MAX_WAIT", session_id=slot_id, served_model="fake")
        text = getattr(self, "_" + kind.lower(), self._unknown)(packet, stage)
        return Reply(text=text, completed=True, session_id=slot_id, served_model="fake", cost_usd=0.0,
                     usage={"input_tokens": len(packet.text) // 4, "output_tokens": len(text) // 4},
                     start_boundary="fake-first-message", end_boundary="fake-result")

    def _unknown(self, packet, stage):
        return "none\n"

    # ---- P0
    def _p0(self, packet, stage):
        return "READY\n"

    # ---- P1 gate (closer)
    def _p1(self, packet, stage):
        cls_line = _packet_field(packet.text, "OPERATOR CLASS")
        seats = _packet_field(packet.text, "SEATS AVAILABLE")
        executor = "executor yes" in seats
        if self._fault("B13", stage):
            return ("CLASS        - EXPERIMENT\nCLASS BASIS  - it feels measurable.\nKIND         - build\nSUCCESS      - faster\n"
                    "CONSTRAINTS  - none given\nGROUND TRUTH - none\nOBJECTIVES   - speed, higher is better\nBUDGET       - defaults\nPROFILE      - adaptive\n")
        if "DIRECT" in cls_line:
            return ("CLASS        - DIRECT OPERATOR SET\nCLASS BASIS  - The operator pre-set the class. A single checkable computation over one document needs no orchestration.\n"
                    "KIND         - answer\nSUCCESS      - the sum of the twelve figures, checkable by arithmetic against figures.csv\n"
                    "CONSTRAINTS  - none given\nGROUND TRUTH - project documents: figures.csv\nOBJECTIVES   - none\nBUDGET       - defaults\nPROFILE      - adaptive\n")
        cls = "HYBRID" if executor else "DELIBERATION"
        obj = ("- name runtime_s; direction lower; procedure python3 bench.py --n 10000; not measured: memory;\n"
               "  gamed by: skipping validation on large files; guardrail output_hash_changed, tolerance 0" if executor else "none")
        return (f"CLASS        - {cls}\nCLASS BASIS  - A timing harness exists for the importer, so part of the ask is measurable. The validation policy itself is judgement.\n"
                "KIND         - build\nSUCCESS      - tests pass; p95 import time within 5 percent of baseline; every malformed row reported\n"
                "CONSTRAINTS  - output hash unchanged on valid inputs\nGROUND TRUTH - project documents: brief.md; test suite: python3 test_importer.py; timing harness bench.py\n"
                f"OBJECTIVES   - {obj}\nBUDGET       - max operators 3, max experiments 2, max wait 10 min\nPROFILE      - adaptive\n")

    # ---- P2 generate
    def _p2(self, packet, stage):
        text = GEN_TEXT.get(self.spec.id, GEN_TEXT["G4"])
        if self._fault("B2", stage):
            text = text.replace("KNOCKDOWN\n", "").replace("A dies if schema validation doubles the runtime. B dies if the second pass alone exceeds the budget.\n", "")
        if self._fault("B19", stage):
            text = text.replace("KNOCKDOWN\n", PADDING + "KNOCKDOWN\n", 1)
        return text

    # ---- P3 operate
    def _p3(self, packet, stage):
        lens = _packet_field(packet.text, "YOUR LENS").split(":")[0].split(" ")[0].upper()
        self.world["lens"] = lens
        return OPERATE_TEXT.get((lens, self.spec.id), GENERIC_OPERATE)

    # ---- P4 close
    def _p4(self, packet, stage):
        mode = _packet_field(packet.text, "MODE").upper()
        replies = _packet_block(packet.text, "REVIEWER REPLIES", ["CHECK RESULTS", "OPTIONS STANDING"])
        check_md = _packet_block(packet.text, "CHECK RESULTS", ["OPTIONS STANDING"])
        check_md = check_md.split("\nIf MODE is LIST", 1)[0]
        this_stage, _, earlier = check_md.partition("EARLIER PASSED CLAIMS")
        claims = parse.parse_claims(check_md)
        stage_claims = parse.parse_claims(this_stage)
        by_id = {c["id"]: c for c in claims}
        # which reply/local claim produced which C id
        local = {}
        for c in claims:
            m = re.search(r"reply (\d+) \((?:CLAIMS|WRONG|KILLS) (\d+)\)", c.get("action", ""))
            if m:
                local[(int(m.group(1)), int(m.group(2)))] = c["id"]
        failed = {c["id"] for c in claims if c["result"] == "FAILED"}
        passed = [c for c in claims if c["result"] == "PASSED"]
        open_lines = [f"- {c['id']} {c['result'].lower()}: {c['settle']}" for c in claims if c["result"] not in ("PASSED", "FAILED")]
        if mode == "LIST":
            options, kills = [], []
            n = 0
            for i, block in enumerate(re.split(r"^REPLY \d+\n", replies, flags=re.M)[1:], 1):
                cands = parse.lettered_candidates(parse.sections(block, parse.REPLY_HEADINGS["generate"]).get("CANDIDATES", ""))
                for letter, first, labels in cands:
                    n += 1
                    req_local = [int(x) for x in re.findall(r"\d+", labels.get("REQUIRED CLAIMS", ""))]
                    req = [local[(i, k)] for k in req_local if (i, k) in local]
                    fals = labels.get("FALSIFICATION CONDITIONS", "none stated")
                    name = first.rstrip(".")
                    options.append(f"{n}. {name}. Requires {', '.join(req) or 'no checkable claim'}. Falsified if {fals.rstrip('.')}.")
                    dead = [r for r in req if r in failed]
                    if dead:
                        kills.append(f"- Option {n} killed by claim {dead[0]} FAILED ({by_id[dead[0]]['text']}), EARNED")
            self.world["options"] = n
            metrics = _metrics(claims, options_created=n, standing=n - len(kills), earned=len(kills), depri=0)
            return ("OPTIONS\n" + "\n".join(options) + "\nKILLS\n" + ("\n".join(kills) if kills else "none") + "\nOPEN\n"
                    + ("\n".join(open_lines) if open_lines else "none") + "\nMETRICS\n" + metrics + "\n")
        # MERGE
        standing_block = _packet_block(packet.text, "OPTIONS STANDING", ["If MODE is LIST"])
        standing = [l.strip() for l in standing_block.splitlines() if parse.NUMBERED.match(l)]
        merged = [f"- {c['text']}. [{c['prov']}] {{{c['id']}}}" for c in passed]
        if self._fault("B8", stage):
            merged.insert(0, "- A model also found option one safer, so it is the better choice.")
        this_stage_failed = [c for c in stage_claims if c["result"] == "FAILED"]
        kills, still = [], []
        for line in standing:
            n = int(parse.NUMBERED.match(line).group(1))
            killer = next((c for c in this_stage_failed if re.search(rf"\b[Oo]ption {n}\b", c["text"])
                           or (n in self.world.get("requires", {}) and c["id"] in self.world["requires"][n])), None)
            if killer:
                kills.append(f"- Option {n} killed by claim {killer['id']} FAILED ({killer['text']}), EARNED")
            else:
                still.append(line)
        depri = []
        if any(l.startswith("2.") for l in still) and len(still) > 1 and self.world.get("lens") == "FMEA":
            depri.append("- Option 2: the seats found the second pass less persuasive on cost; it stays standing")
        changed = "yes" if kills or any(c["result"] == "PASSED" for c in stage_claims) else "no"
        metrics = _metrics(stage_claims, options_created=0, standing=len(still), earned=len(kills), depri=len(depri), changed=changed)
        return ("MERGED\n" + ("\n".join(merged) if merged else "none") + "\nKILLS\n" + ("\n".join(kills) if kills else "none")
                + "\nDEPRIORITIZED\n" + ("\n".join(depri) if depri else "none") + "\nOPEN\n" + ("\n".join(open_lines) if open_lines else "none")
                + "\nCONFLICT\nnone\nOPTIONS STANDING\n" + ("\n".join(still) if still else "none") + "\nMETRICS\n" + metrics + "\n")

    # ---- P5 review
    def _p5(self, packet, stage):
        claims = _packet_block(packet.text, "ITS CLAIMS", ["OPTIONS STANDING"])
        passed_ids = re.findall(r"^(C\d+) PASSED", claims, re.M)
        hold_id = passed_ids[0] if passed_ids else "C1"
        if self._fault("B7", stage):
            return ("HITS\n1. The conclusion feels optimistic about adoption (judgement call, no way to check it).\n"
                    "GAPS\n1. Team appetite for strict validation is unknown (judgement call, no way to check it).\n"
                    f"HOLDS\n1. {hold_id} holds: the quoted wording is unambiguous.\nOPEN\nnone\n")
        hit = ("1. The throughput figure was measured on a twelve column file; the brief's widest file has forty columns, where 9000 rows in 12 seconds is 750 rows per second (sum: 9000 / 12 = 750)."
               if not self._fault("B6", stage) else
               "1. The throughput figure is wrong: 21600 rows in 12 seconds is 1600 rows per second (sum: 21600 / 12 = 1600).")
        return (f"HITS\n{hit}\n"
                "GAPS\n1. Nothing states what happens to a partially loaded file when a reject is found (document: brief.md, \"partial loads are rolled back\").\n"
                f"HOLDS\n1. {hold_id} holds: the quoted wording of the brief is unambiguous.\n"
                "OPEN\nnone\n")

    # ---- P6 final
    def _p6(self, packet, stage):
        t = packet.text
        mode = _packet_field(t, "MODE")
        merged = _packet_block(t, "WORKING ANSWER", ["OPTIONS STANDING"])
        standing = _packet_block(t, "OPTIONS STANDING", ["STILL OPEN"])
        open_ = _packet_block(t, "STILL OPEN", ["CONFLICT"])
        kills = _packet_block(t, "ALL KILLS", ["REVIEW"])
        review = _packet_block(t, "REVIEW", ["REVIEW CHECK"])
        review_check = _packet_block(t, "REVIEW CHECK", ["EXPERIMENTS"])
        experiments = _packet_block(t, "EXPERIMENTS", ["METRICS"])
        metrics = _packet_block(t, "METRICS", ["FLAGS"])
        flags = _packet_block(t, "FLAGS", ["CLASSIFICATION"])
        classification = _packet_block(t, "CLASSIFICATION", ["Rules for what you may change."]).split()[0]
        merged_lines = [l.strip() for l in merged.splitlines() if l.strip().startswith("-")]
        standing_lines = [l.strip() for l in standing.splitlines() if parse.NUMBERED.match(l)]
        rc = parse.parse_claims(review_check)
        h_passed = [c for c in rc if c["result"] == "PASSED" and c["id"].startswith("H")]
        why = list(merged_lines) + [f"- {c['text']} [R] {{{c['id']}}}" for c in h_passed]
        survived = []
        passed_by_id = {}
        for l in merged_lines:
            for tag_ids in re.findall(r"(\[[^\]]+\]\s*\{[^}]+\})", l):
                for cid in re.findall(r"C\d+", tag_ids):
                    passed_by_id.setdefault(cid, tag_ids)
        for line in standing_lines:
            m = parse.NUMBERED.match(line)
            req = re.findall(r"\bC\d+\b", m.group(2))
            tags = " ".join(passed_by_id[c] for c in req if c in passed_by_id)
            survived.append(f"- Option {m.group(1)}: {m.group(2).split('. Requires')[0].rstrip('.')}." + (f" {tags}" if tags else " (no PASSED claim of its own)"))
        if len(standing_lines) > 1:
            survived.append(f"{len(standing_lines)} options survive.")
        dispositions = []
        for c in rc:
            disp = {"PASSED": "FIXED (the claim it struck is removed from section 2 and 3)", "FAILED": "REJECTED (the check failed it)"}.get(c["result"], "OPEN")
            dispositions.append(f"{c['id']} {c['result']}: {disp}.")
        holds = re.findall(r"^HOLD \d+ HOLD-\w+.*$", review_check, re.M)
        result_line = (merged_lines[0].split(" [")[0].lstrip("- ") if merged_lines else "No claim survived the checks; see section 8.")
        sections = [
            "1 THE RESULT", result_line if mode != "DIRECT" else (_packet_block(t, "WORKING ANSWER", ["OPTIONS STANDING"]).splitlines()[0] if merged else "none"),
            "2 WHAT SURVIVED", "\n".join(survived) if survived else "none",
            "3 WHY IT SURVIVED", "\n".join(why) if why else "none",
            "4 OBJECTIVE RESULTS", experiments if experiments and experiments.lower() != "none" else "not applicable",
            "5 WHAT DIED AND WHY", kills if kills else "none",
            "6 TRADE-OFFS", "option 1 is faster to build and option 2 reports more; not resolved by arithmetic" if len(standing_lines) > 1 else "none",
            "7 OUTSIDE REVIEW", ("\n".join(dispositions + holds) + "\nSURVIVING DEFECTS: none known.") if rc else ("NO REVIEW" if "NO REVIEW" in review else "none"),
            "8 STILL OPEN", open_ if open_ else "none",
            "9 CONFIDENCE", "Medium for option 1: its throughput claim was scoped by the review. Low for any other standing option." if standing_lines else "Low: nothing stands.",
            "10 RUN INTEGRITY", f"earned kills and deprioritized counts as in METRICS; stages and stop reason as recorded by Dispatch; seats failed: none reported; closer swaps: none reported; review {'ran' if rc else 'did not run'}; flags {flags or 'none'}; classification {classification}",
            "11 EFFICIENCY", re.sub(r"\s+", " ", metrics) or "none",
            "12 NEXT QUESTION", "Run the timing harness on option 1 with the widest file the brief names.",
            "14 PRIVATE DOCUMENT VERIFICATION", ""]
        out = "\n".join(sections) + "\n"
        if self._fault("B8F", stage):
            out = out.replace("14 PRIVATE DOCUMENT VERIFICATION\n", "14 PRIVATE DOCUMENT VERIFICATION\nnothing to add\n")
        return out

    # ---- P7 verify
    def _p7(self, packet, stage):
        if self._fault("B12", stage):
            return ("CONTRADICTIONS\n1. The result says rejected rows may be dropped; brief.md section 4 says every rejected row is written to rejects.csv (brief.md, section 4).\n"
                    "CONFIRMED\nnone\nNOT COVERED\nthe throughput figure\nMATERIAL OMISSIONS\nnone\n")
        return ("CONTRADICTIONS\nnone\nCONFIRMED\n1. The reject report requirement is confirmed by brief.md section 4.\n"
                "NOT COVERED\nthe throughput figure and the library strict mode\nMATERIAL OMISSIONS\nnone\n")

    # ---- P8 propose
    def _p8(self, packet, stage):
        log = _packet_block(packet.text, "EXPERIMENT LOG", ["ARTIFACT"])
        n = len(re.findall(r'"id": "exp-', log)) + 1
        if n == 1:
            return ("ID               - exp-001\nHYPOTHESIS       - caching the parsed schema halves the import runtime\n"
                    "PRIMARY CHANGE   - set USE_CACHE = True in importer.py\nEXPECTED EFFECT  - runtime_s falls by about four seconds because the schema is parsed once\n"
                    "GUARDRAIL RISK   - output_hash_changed, visible if the bench prints a nonzero value\nPROCEDURE        - python3 bench.py --n 10000\n"
                    "COST             - two runs, under a minute\nDECISION RULE    - keep if runtime_s falls by more than the noise on both runs; revert if it rises; inconclusive within noise\n")
        return ("ID               - exp-%03d\nHYPOTHESIS       - skipping validation on large files makes imports faster\n"
                "PRIMARY CHANGE   - set SKIP_LARGE = True in importer.py\nEXPECTED EFFECT  - runtime_s falls further\n"
                "GUARDRAIL RISK   - output_hash_changed: skipped validation changes the output on malformed input\nPROCEDURE        - python3 bench.py --n 10000\n"
                "COST             - two runs, under a minute\nDECISION RULE    - keep only if the guardrail stays zero\n" % n)

    # ---- P9 direct
    def _p9(self, packet, stage):
        return ("ANSWER\nThe twelve monthly figures in figures.csv sum to 9420.\n"
                "CLAIMS\n1. The twelve figures sum to 9420 (sum: 700 + 720 + 750 + 810 + 790 + 760 + 800 + 830 + 820 + 780 + 770 + 890 = 9420).\n"
                "2. figures.csv lists one figure per month for twelve months (document: figures.csv, \"month,figure\").\n"
                "OPEN\nWhether any figure is a duplicate of another month; settle by reading the distractor document.\n")


def _metrics(claims, options_created, standing, earned, depri, changed=None):
    key = {"PASSED": "passed", "FAILED": "failed", "JUDGEMENT CALL": "judgement", "NOT TESTABLE": "not_testable",
           "BLOCKED": "blocked", "INCONCLUSIVE": "inconclusive"}
    c = {v: 0 for v in key.values()}
    for cl in claims:
        if cl["result"] in key:
            c[key[cl["result"]]] += 1
    s = (f"options_created={options_created} options_standing={standing} claims_total={len(claims)} "
         f"claims_checkable={sum(1 for cl in claims if cl.get('method') != 'none')} passed={c['passed']} failed={c['failed']} "
         f"judgement={c['judgement']} not_testable={c['not_testable']} blocked={c['blocked']} inconclusive={c['inconclusive']} "
         f"earned_kills={earned} deprioritized={depri}")
    if changed is not None:
        s += f" decision_changed={changed}"
    return s


class LocalExecutor:
    """Executor for fake mode: subprocess in the working copy, one-line mutations of the form
    'set NAME = VALUE in file'. Deterministic, no model."""

    def __init__(self, spec, sandbox: str):
        self.spec = spec
        self.sandbox = os.path.abspath(sandbox)

    def _inside(self, cwd):
        p = os.path.abspath(cwd or self.sandbox)
        return p

    def send(self, packet: Packet, timeout_s: float, slot_id: str) -> Reply:
        """The executor answers the handshake and the command micro-packets; it never writes prose into a stage."""
        return Reply(text="READY\n", completed=True, session_id=slot_id, served_model="local", cost_usd=0.0,
                     start_boundary="local", end_boundary="local")

    def run_command(self, cmd: str, cwd: str | None = None, timeout_s: float | None = None) -> dict:
        t0 = time.time()
        try:
            r = subprocess.run(cmd, shell=True, cwd=self._inside(cwd), capture_output=True, text=True, timeout=timeout_s or 120)
        except subprocess.TimeoutExpired:
            return {"output": "", "returncode": None, "error": f"timeout after {timeout_s} s", "elapsed_s": round(time.time() - t0, 2)}
        except OSError as e:
            return {"output": "", "returncode": None, "error": str(e), "elapsed_s": round(time.time() - t0, 2)}
        return {"output": (r.stdout + r.stderr), "returncode": r.returncode, "error": None, "elapsed_s": round(time.time() - t0, 2)}

    def apply_mutation(self, change: str, workdir: str) -> dict:
        m = re.search(r"set\s+(\w+)\s*=\s*(\S+)\s+in\s+([\w\-.]+)", change)
        if not m:
            return {"ok": False, "error": f"mutation not understood: {change}"}
        name, value, fname = m.groups()
        p = os.path.join(workdir, fname)
        if not os.path.isfile(p):
            return {"ok": False, "error": f"{fname} not in the working copy"}
        src = open(p, encoding="utf-8").read()
        new, n = re.subn(rf"^{name}\s*=.*$", f"{name} = {value}", src, flags=re.M)
        if n == 0:
            new = src.rstrip("\n") + f"\n{name} = {value}\n"
        open(p, "w", encoding="utf-8").write(new)
        return {"ok": True, "error": None, "log": f"{fname}: {name} = {value}"}

    def measure(self, procedure: str, workdir: str, timeout_s: float) -> dict:
        return self.run_command(procedure, cwd=workdir, timeout_s=timeout_s)
