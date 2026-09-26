"""The CHECK stage: every claim a reply makes becomes a claim record in check.md (SCHEMA claim_record_text_format).

Claim ids are global to the run (CID-UNIQ): the allocator continues from every check file already on disk,
so ids stay unique after a resume. PASSED and FAILED always carry RETRIEVED; the other four always carry SETTLE.
"""
import re
from dataclasses import dataclass, field

from .. import parse
from . import arith, commands, documents, sources

STATUSES = ("PASSED", "FAILED", "JUDGEMENT CALL", "NOT TESTABLE", "BLOCKED", "INCONCLUSIVE")


@dataclass
class ClaimRecord:
    id: str
    prov: str
    text: str
    method: str
    action: str
    retrieved: str
    result: str
    settle: str
    source: str = ""
    seat: str = ""
    local_no: int = 0
    section: str = "CLAIMS"

    def render(self) -> str:
        assert self.result in STATUSES, self.result
        if self.result in ("PASSED", "FAILED"):
            assert self.retrieved and self.method != "none", (self.id, self.result)
        else:
            assert self.settle, (self.id, self.result)
        lines = [f'CLAIM {self.id} [{self.prov}] "{self.text}"', f"  METHOD     {self.method}", f"  ACTION     {self.action}",
                 f"  RETRIEVED  {self.retrieved}", f"  RESULT     {self.result}", f"  SETTLE     {self.settle}"]
        if self.method in ("source", "document"):
            lines.append(f"  SOURCE     {self.source}")
        return "\n".join(lines) + "\n"


def render(records: list) -> str:
    return "".join(r.render() for r in records)


class ClaimIdAllocator:
    def __init__(self, rf, prefix="C"):
        self.prefix = prefix
        self.n = 0
        for st in rf.stages():
            if rf.exists(f"{st}/check.md"):
                for c in parse.parse_claims(rf.read(f"{st}/check.md")):
                    m = re.fullmatch(rf"{prefix}(\d+)", c["id"])
                    if m:
                        self.n = max(self.n, int(m.group(1)))
        if rf.exists("review/check-review.md"):
            for c in parse.parse_claims(rf.read("review/check-review.md")):
                m = re.fullmatch(rf"{prefix}(\d+)", c["id"])
                if m:
                    self.n = max(self.n, int(m.group(1)))

    def next(self) -> str:
        self.n += 1
        return f"{self.prefix}{self.n}"


@dataclass
class CheckContext:
    documents_dir: str | None = None
    resolver: object = None
    executor: object = None
    allowed_commands: list = field(default_factory=list)
    now: str = ""
    workdir: str | None = None
    on_execution: object = None


def check_one(raw: parse.RawClaim, ctx: CheckContext) -> dict:
    """Result fields for one raw claim, by its method."""
    if raw.method == "sum":
        result, retrieved, settle = arith.check_sum(raw.text)
        return {"result": result, "retrieved": retrieved, "settle": settle, "action": "recomputed the arithmetic", "source": ""}
    if raw.method == "source":
        return sources.check_source(raw, ctx.resolver or sources.OfflineResolver(), ctx.now)
    if raw.method == "document":
        return documents.check_document(raw, ctx.documents_dir, ctx.now)
    if raw.method == "command":
        return dict(commands.check_command(raw, ctx.executor, ctx.allowed_commands, ctx.workdir, ctx.on_execution), source="")
    if raw.method == "experiment":
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": "run the named experiment through the EXECUTOR (Experiment Engine)",
                "action": "an experiment claim is settled by the Experiment Engine, not by CHECK", "source": ""}
    return {"result": "JUDGEMENT CALL", "retrieved": "", "settle": settle_for_judgement(raw.text), "action": "no method available", "source": ""}


def settle_for_judgement(text: str) -> str:
    m = re.search(r"(?:settle[sd]? (?:by|with)|would settle it:?)\s*(.*)$", text, re.I)
    if m and m.group(1).strip():
        return m.group(1).strip().rstrip(".")
    return "a checkable restatement: a sum, a source, a command, a document, or an experiment"


def run_check(rf, replies: dict, kind: str, ctx: CheckContext, allocator: ClaimIdAllocator, prov_for=None) -> list:
    """replies: seat id -> reply text (stamp lines included). Returns the ClaimRecords in seat order."""
    records = []
    for i, (seat, text) in enumerate(replies.items(), 1):
        body = parse.strip_stamp(text)
        for raw in parse.claims_from_reply(body, kind):
            fields = check_one(raw, ctx)
            prov = prov_for(seat) if prov_for else seat
            rec = ClaimRecord(id=allocator.next(), prov=prov, text=parse.claim_display(raw.text), method=raw.method,
                              action=f"reply {i} ({raw.section} {raw.local_no}): {fields['action']}", retrieved=fields["retrieved"],
                              result=fields["result"], settle=fields["settle"], source=fields.get("source", ""), seat=seat,
                              local_no=raw.local_no, section=raw.section)
            records.append(rec)
    return records


def experiment_records(results: list, allocator: ClaimIdAllocator) -> list:
    """[X-<id>] evidence from executed experiments (DISPATCH 3.5): a KEEP is PASSED evidence for its hypothesis,
    a REVERT is FAILED evidence, INCONCLUSIVE stays INCONCLUSIVE."""
    out = []
    for r in results:
        dec = r["decision"]
        result = {"KEEP": "PASSED", "REVERT": "FAILED"}.get(dec, "INCONCLUSIVE")
        retrieved = (f"baseline {r['metric']} {r['baseline_value']}, result {r.get('result_value')}, repeat {r.get('repeat_value')}, "
                     f"delta {r.get('delta')}, noise {r.get('noise')}, guardrails held: {r.get('guardrails_ok')}")
        out.append(ClaimRecord(id=allocator.next(), prov=f"X-{r['id']}", text=parse.claim_display(r["hypothesis"]), method="experiment",
                               action=f"EXECUTOR ran {r.get('procedure', 'the procedure')} on the mutated copy, twice",
                               retrieved=retrieved if result != "INCONCLUSIVE" else "",
                               result=result, settle="" if result != "INCONCLUSIVE" else "a repeat within budget or a larger delta than the noise",
                               seat="EXECUTOR", section="EXPERIMENT"))
    return out


def review_records(review_md: str, ctx: CheckContext, passed_ids: set) -> str:
    """check-review.md: HITS as H<n>, GAPS as GP<n>, every one [R]; HOLD lines HOLD-ACCEPTED or HOLD-REJECTED (I9)."""
    hits, gaps, holds, _ = parse.review_items(review_md)
    recs = []
    for prefix, items, section in (("H", hits, "HITS"), ("GP", gaps, "GAPS")):
        for n, t in items:
            raw = parse.claim_from_line(n, t, section)
            fields = check_one(raw, ctx)
            recs.append(ClaimRecord(id=f"{prefix}{n}", prov="R", text=parse.claim_display(t), method=raw.method,
                                    action=f"{section} {n}: {fields['action']}", retrieved=fields["retrieved"], result=fields["result"],
                                    settle=fields["settle"], source=fields.get("source", ""), seat="REVIEWER", local_no=n, section=section))
    text = render(recs)
    for n, t in holds:
        cited = {x.upper() for x in re.findall(r"\bC\d+\b", t)}
        ok = not cited or cited <= passed_ids
        text += f"HOLD {n} {'HOLD-ACCEPTED' if ok else 'HOLD-REJECTED'} ({', '.join(sorted(cited)) or 'no claim id cited'}{' PASSED' if ok and cited else ''})\n"
    return text, recs


def counts(records: list) -> dict:
    c = {"claims_total": len(records), "claims_checkable": sum(1 for r in records if r.method != "none"),
         "passed": 0, "failed": 0, "judgement": 0, "not_testable": 0, "blocked": 0, "inconclusive": 0}
    key = {"PASSED": "passed", "FAILED": "failed", "JUDGEMENT CALL": "judgement", "NOT TESTABLE": "not_testable",
           "BLOCKED": "blocked", "INCONCLUSIVE": "inconclusive"}
    for r in records:
        c[key[r.result]] += 1
    return c
