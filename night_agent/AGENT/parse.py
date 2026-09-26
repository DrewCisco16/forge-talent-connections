"""Tolerant readers of model replies and Dispatch files. Nothing here mutates a reply.

Two heading matchers: the tolerant one (markdown marks, double spaces) is what the
runtime reads with; the strict one is na_check's own regex, so a reply that would fail
the checker counts as a missing heading and is retried (DISPATCH 2.4).
"""
import os
import re
import sys
from dataclasses import dataclass, field

from . import PKG

sys.path.insert(0, os.path.join(PKG, "TESTS"))
import na_check  # noqa: E402  (pure regexes and parsers; its rep() is never called here)

REPLY_HEADINGS = na_check.REPLY_HEADINGS
DELIV_SECTIONS = na_check.DELIV_SECTIONS
STAMP = na_check.STAMP
CLAIM = na_check.CLAIM
PROV = na_check.PROV
CIDS = na_check.CIDS
parse_claims = na_check.parse_claims
kills_entries = na_check.kills_entries

GATE_HEADINGS = ["CLASS", "CLASS BASIS", "KIND", "SUCCESS", "CONSTRAINTS", "GROUND TRUTH", "OBJECTIVES", "BUDGET", "PROFILE"]
LIST_CLOSE = ["OPTIONS", "KILLS", "OPEN", "METRICS"]
MERGE_CLOSE = ["MERGED", "KILLS", "DEPRIORITIZED", "OPEN", "CONFLICT", "OPTIONS STANDING", "METRICS"]
PROPOSAL_HEADINGS = ["ID", "HYPOTHESIS", "PRIMARY CHANGE", "EXPECTED EFFECT", "GUARDRAIL RISK", "PROCEDURE", "COST", "DECISION RULE"]
CANDIDATE_LABELS = ["APPROACH", "ASSUMPTIONS", "REQUIRED CLAIMS", "FALSIFICATION CONDITIONS", "EXPECTED UPSIDE",
                    "FAILURE MODES", "MEASURABLE PREDICTIONS", "DISTINGUISHING EXPERIMENT"]
METHODS = ("sum", "source", "command", "document", "experiment", "none")

NUMBERED = re.compile(r"^\s*(\d+)[\.\)]\s+(.*)$")
LETTERED = re.compile(r"^\s*([A-Z])[\.\)]\s+(.*)$")


def _heading_re(name, strict):
    if strict:
        return re.compile(rf"^{re.escape(name)}\b", re.M)
    return re.compile(rf"^[ \t]*(?:#{{1,6}}[ \t]*|\*\*[ \t]*)?{re.escape(name)}\b\**[ \t]*(?:[-:][ \t]*(.*))?$", re.M)


def headings_exact(text: str, names: list) -> list:
    """Headings the checker would call missing (na_check.check_headings rule)."""
    return [h for h in names if _heading_re(h, True).search(text) is None]


def sections(text: str, names: list) -> dict:
    """Body of each named section, tolerant of markdown marks and same-line content after '-' or ':'.

    A section runs to the next named heading. Unknown upper-case lines do not end a section, so a
    reply that adds its own sub-headings still parses; the checker's stricter view is applied by
    headings_exact and the pre-save validators.
    """
    found = []
    for name in names:
        for m in _heading_re(name, False).finditer(text):
            found.append((m.start(), m.end(), name, m.group(1) or ""))
    found.sort()
    out = {}
    for i, (start, end, name, inline) in enumerate(found):
        if name in out:
            continue
        stop = found[i + 1][0] if i + 1 < len(found) else len(text)
        body = text[end:stop]
        out[name] = (inline.strip() + "\n" + body).strip("\n") if inline.strip() else body.strip("\n")
    return out


def list_lines(body: str) -> list:
    """Lines the checker treats as claim or kill lines: '-', '*', or numbered."""
    return [l.strip() for l in body.splitlines() if l.strip().startswith(("-", "*")) or NUMBERED.match(l)]


def numbered_items(body: str) -> list:
    items = []
    for l in body.splitlines():
        m = NUMBERED.match(l)
        if m:
            items.append([int(m.group(1)), m.group(2).strip()])
        elif items and l.strip() and (l.startswith((" ", "\t")) or not re.match(r"^[A-Z][A-Z \-]{3,}\s*$", l.strip())):
            items[-1][1] += " " + l.strip()
    return [(n, t) for n, t in items]


def lettered_candidates(body: str) -> list:
    """[(letter, first line, {LABEL: text})] for CANDIDATES sections."""
    out = []
    cur = None
    for l in body.splitlines():
        m = LETTERED.match(l)
        if m:
            cur = [m.group(1), m.group(2).strip(), {}]
            out.append(cur)
            continue
        if cur is None:
            continue
        s = l.strip()
        lm = re.match(r"^(" + "|".join(re.escape(x) for x in CANDIDATE_LABELS) + r")\s*[:\-]?\s*(.*)$", s)
        if lm:
            cur[2][lm.group(1)] = lm.group(2).strip()
        elif s and cur[2]:
            last = list(cur[2].keys())[-1]
            cur[2][last] += " " + s
        elif s:
            cur[1] += " " + s
    return [(a, b, c) for a, b, c in out]


@dataclass
class RawClaim:
    local_no: int
    text: str
    method: str = "none"
    quote: str = ""
    doi: str = ""
    url: str = ""
    document: str = ""
    expression: str = ""
    section: str = "CLAIMS"


DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"')\]>,;]+)")
URL_RE = re.compile(r"https?://[^\s\"')\]>]+")
DOC_RE = re.compile(r"\b([\w\-]+\.(?:md|csv|txt|pdf|json|py))\b")
QUOTE_RE = re.compile(r"[\"“]([^\"”]{4,})[\"”]")
PAREN_RE = re.compile(r"\(([^()]*)\)")


def method_of(text: str) -> str:
    """The check method a claim line names (P2: sum, source, command, document, experiment, judgement call)."""
    hint = ""
    for p in PAREN_RE.findall(text):
        pl = p.lower()
        if any(k in pl for k in ("sum", "source", "command", "document", "experiment", "judgement", "judgment", "arithmetic", "doi", "cite", "run ")):
            hint = pl
            break
    low = hint or text.lower()
    if "judgement" in low or "judgment" in low or "no way to check" in low:
        return "none"
    if hint:
        for k, m in (("sum", "sum"), ("arithmetic", "sum"), ("source", "source"), ("doi", "source"), ("cite", "source"),
                     ("command", "command"), ("run ", "command"), ("document", "document"), ("experiment", "experiment")):
            if k in hint:
                return m
    if DOI_RE.search(text) or URL_RE.search(text):
        return "source"
    if DOC_RE.search(text) and "run" not in low:
        return "document"
    if re.search(r"\d\s*[+\-*/^x×]\s*\d.*=\s*-?\d", text):
        return "sum"
    if re.search(r"`[^`]+`|\bpytest\b|\bpython3?\s", text):
        return "command"
    return "none"


def claim_from_line(no: int, text: str, section="CLAIMS") -> RawClaim:
    c = RawClaim(local_no=no, text=text.strip(), section=section)
    c.method = method_of(text)
    m = DOI_RE.search(text)
    if m:
        c.doi = m.group(1).rstrip(".")
    m = URL_RE.search(text)
    if m:
        c.url = m.group(0).rstrip(".,)")
    m = QUOTE_RE.search(text)
    if m:
        c.quote = m.group(1).strip()
    m = DOC_RE.search(text)
    if m and c.method in ("document", "none"):
        c.document = m.group(1)
    return c


def claims_from_reply(text: str, kind: str) -> list:
    """Checkable statements a reply makes. generate/direct: the CLAIMS list; operate: WRONG and KILLS lines;
    review: HITS and GAPS lines."""
    out = []
    if kind in ("generate", "direct"):
        body = sections(text, REPLY_HEADINGS[kind]).get("CLAIMS", "")
        for n, t in numbered_items(body):
            out.append(claim_from_line(n, t, "CLAIMS"))
    elif kind == "operate":
        secs = sections(text, REPLY_HEADINGS["operate"])
        n = 0
        for name in ("WRONG", "KILLS"):
            for l in list_lines(secs.get(name, "")):
                t = re.sub(r"^(\d+[\.\)]|[-*])\s*", "", l).strip()
                if t.lower() in ("none", "none found", "none."):
                    continue
                n += 1
                out.append(claim_from_line(n, t, name))
    elif kind == "review":
        secs = sections(text, REPLY_HEADINGS["review"])
        for name in ("HITS", "GAPS"):
            for n, t in numbered_items(secs.get(name, "")):
                out.append(claim_from_line(n, t, name))
    return out


def claim_display(text: str) -> str:
    """Claim text as it goes inside the CLAIM record quotes: one line, no double quotes."""
    t = re.sub(r"\s*\((?:[^()]*(?:sum|source|command|document|experiment|judgement|judgment)[^()]*)\)\s*", " ", text, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip().rstrip(".").strip()
    return t.replace('"', "'")


@dataclass
class Option:
    n: int
    name: str
    text: str
    required: set = field(default_factory=set)
    falsification: str = ""
    prediction: str = ""


def options_from_list_close(close_md: str) -> list:
    body = sections(close_md, LIST_CLOSE).get("OPTIONS", "")
    opts = []
    for n, t in numbered_items(body):
        req = {x.upper() for x in re.findall(r"\bC\d+\b", t)}
        req |= {"C" + x for x in re.findall(r"\bclaims?\s+(\d+)\b", t, re.I)}
        name = re.split(r"(?<=[a-z0-9\)])\.\s", t, 1)[0].strip()
        fm = re.search(r"[Ff]alsif\w*\s*(?:if|when|conditions?:?)\s*(.*)$", t)
        opts.append(Option(n=n, name=name, text=t, required=req, falsification=(fm.group(1) if fm else "")))
    return opts


def options_standing(close_md: str) -> list:
    body = sections(close_md, MERGE_CLOSE).get("OPTIONS STANDING", "")
    return [n for n, _ in numbered_items(body)]


def options_standing_lines(close_md: str) -> list:
    body = sections(close_md, MERGE_CLOSE).get("OPTIONS STANDING", "")
    return [l for l in body.splitlines() if NUMBERED.match(l)]


def killed_options(close_md: str, mode: str) -> set:
    body = sections(close_md, MERGE_CLOSE if mode == "MERGE" else LIST_CLOSE).get("KILLS", "")
    out = set()
    for l in list_lines(body):
        for n in re.findall(r"\b[Oo]ption\s+(\d+)\b", l):
            out.add(int(n))
    return out


def section_text(close_md: str, name: str, names=None) -> str:
    return sections(close_md, names or MERGE_CLOSE).get(name, "")


def metrics_line(close_md: str) -> dict:
    body = sections(close_md, MERGE_CLOSE).get("METRICS", "")
    out = {}
    for k, v in re.findall(r"([a-z_]+)\s*=\s*([A-Za-z0-9\.\-]+)", body):
        try:
            out[k] = int(v) if re.fullmatch(r"-?\d+", v) else (float(v) if re.fullmatch(r"-?\d+\.\d+", v) else v)
        except ValueError:
            out[k] = v
    return out


def gate_fields(gate_md: str) -> dict:
    secs = sections(gate_md, GATE_HEADINGS)
    return {k: v.strip() for k, v in secs.items()}


def review_items(review_md: str):
    secs = sections(review_md, REPLY_HEADINGS["review"])
    return (numbered_items(secs.get("HITS", "")), numbered_items(secs.get("GAPS", "")),
            numbered_items(secs.get("HOLDS", "")), secs.get("OPEN", ""))


def verifier_items(verifier_md: str) -> dict:
    secs = sections(verifier_md, REPLY_HEADINGS["verifier"])
    out = {}
    for k, v in secs.items():
        items = [l for l in v.splitlines() if re.match(r"^\s*(\d+[\.\)]|[-*])\s*\S", l) and l.strip().lower() not in ("- none", "* none")]
        out[k] = items
    return out


def proposal_fields(md: str) -> dict:
    return {k: v.strip() for k, v in sections(md, PROPOSAL_HEADINGS).items()}


def deliverable_sections(md: str) -> dict:
    return sections(md, DELIV_SECTIONS + ["13 VERIFY BEFORE RELYING", "14 PRIVATE DOCUMENT VERIFICATION"])


def classification_words(md: str) -> list:
    return re.findall(r"\b(KEEP_FOR_DEVELOPMENT|REVERT|PARTIAL_REPORT)\b", md)


def strip_stamp(text: str) -> str:
    lines = text.split("\n")
    if lines and STAMP.match(lines[0]):
        lines = lines[1:]
        if lines and lines[0].startswith("DISPATCH "):
            lines = lines[1:]
    return "\n".join(lines)


def ready_word(text: str) -> bool:
    """P0: only the word READY is usable (spec 7); trailing whitespace or a full stop is tolerated."""
    return text.strip().rstrip(".!") == "READY"


def measurable_prediction(candidate_labels: dict) -> str:
    p = candidate_labels.get("MEASURABLE PREDICTIONS", "").strip()
    return "" if p.lower() in ("", "none", "none.") else p
