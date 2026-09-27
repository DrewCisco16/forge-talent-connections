"""Packets: the PROMPTS files filled by Dispatch, scanned for neutrality and data-boundary breaches
(spec 16), hashed for the dispatch record (spec 7)."""
import hashlib
import os
import re
from dataclasses import dataclass, field

from . import PKG

PROMPTS = os.path.join(PKG, "PROMPTS")
MODEL_NAMES = ("Sol", "Gemini", "Grok", "Magistral", "Fable", "Astra", "GPT", "Claude", "Mistral")
NEUTRALITY_WORDS = ("winner", "the best option", "recommended option", "final verdict", "previous final", "strongest seat")
FALSIFIABILITY_LINE = ("At least half your claims must be checkable by a sum, a source, a command, a document, "
                       "or an experiment. Rewrite them so they can be wrong.")
PLACEHOLDER = re.compile(r"<[^<>]*>", re.S)
LABEL = re.compile(r"^([A-Z][A-Z /]*?)\s{2,}")


class PacketError(Exception):
    pass


def prompt_text(name: str) -> str:
    with open(os.path.join(PROMPTS, name), encoding="utf-8") as f:
        return f.read()


def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


@dataclass
class Packet:
    text: str
    prompt_hash: str = ""
    snapshot_hash: str = ""
    kind: str = ""
    narrowed: bool = False
    neutrality: list = field(default_factory=list)

    def __post_init__(self):
        if not self.prompt_hash:
            self.prompt_hash = sha(self.text)


def _indent(value: str, col: int) -> str:
    """A one-line value sits on the label line; a multi-line value starts on the next line at column one so
    CLAIM records, REPLY blocks and headings inside it keep their line starts (the seats and the fake closer parse them)."""
    lines = (value or "").rstrip("\n").split("\n")
    if len(lines) == 1:
        return lines[0]
    return "\n" + "\n".join(lines)


def fill(template: str, values: dict, literal: dict | None = None) -> str:
    """Replace every <placeholder> whose line starts with a label in values. Placeholders spanning two
    lines are replaced whole. A placeholder with no value raises PacketError: nothing leaves half filled."""
    literal = literal or {}
    out = []
    pos = 0
    for m in PLACEHOLDER.finditer(template):
        ph = m.group(0)
        line_start = template.rfind("\n", 0, m.start()) + 1
        line = template[line_start:m.start()]
        lm = LABEL.match(line + "  ")
        label = lm.group(1).strip() if lm else None
        if ph in literal:
            rep = literal[ph]
        elif label in values:
            rep = _indent(str(values[label]), m.start() - line_start)
        elif label is None:
            rep = ph  # prose such as {C<n>} or <hh:mm>: template text, not a placeholder
        else:
            raise PacketError(f"unfilled placeholder {ph[:50]!r} (label {label!r})")
        out.append(template[pos:m.start()])
        out.append(rep)
        pos = m.end()
    out.append(template[pos:])
    text = "".join(out)
    if PLACEHOLDER.search(text):
        # a value that itself contains angle brackets is data, not a placeholder; only template ones matter
        pass
    return text


def neutrality_hits(text: str) -> list:
    low = text.lower()
    return [w for w in NEUTRALITY_WORDS if w in low]


def payload_hits(text: str) -> list:
    hits = []
    if re.search(r"(?m)(^|[\s\"'(])(/home/|/root/|/Users/|[A-Za-z]:\\)", text):
        hits.append("absolute path")
    if re.search(r"\b[0-9a-f]{64}\b", text):
        hits.append("sha256 hash")
    for w in ("quota", "telemetry"):
        if re.search(rf"\b{w}\b", text, re.I):
            hits.append(w)
    return hits


def narrow(text: str) -> str:
    """Remove what PAYLOAD_AUTHORIZATION forbids by default (spec 16): paths and hashes become placeholders."""
    text = re.sub(r"(/home/|/root/|/Users/|[A-Za-z]:\\)[^\s\"')]*", "<path withheld>", text)
    text = re.sub(r"\b[0-9a-f]{64}\b", "<hash withheld>", text)
    return text


def strip_attribution(text: str, seat_ids: list) -> str:
    """Review package and closer inputs carry no model names and no seat ids (spec 4.6, 16)."""
    for name in MODEL_NAMES:
        text = re.sub(rf"\b{name}\b", "a model", text)
    for i, sid in enumerate(sorted(s for s in seat_ids if s.startswith("G")), 1):
        text = re.sub(rf"\[{sid}\]", f"[{i}]", text)
        text = re.sub(rf"\b{sid}\b", f"reply {i}", text)
    return text


def snapshot_hash(merged: str, options: str, open_: str) -> str:
    return sha("MERGED\n" + merged + "\nOPTIONS STANDING\n" + options + "\nOPEN\n" + open_)


def make(kind: str, name: str, values: dict, literal: dict | None = None, snapshot=("", "", "")) -> Packet:
    text = fill(prompt_text(name), values, literal)
    narrowed = False
    if kind not in ("P7",) and payload_hits(text):
        text = narrow(text)
        narrowed = True
    p = Packet(text=text, kind=kind, narrowed=narrowed, neutrality=neutrality_hits(text),
               snapshot_hash=snapshot_hash(*snapshot))
    return p


# ---- one builder per prompt
def build_p0() -> Packet:
    return Packet(text=prompt_text("P0_handshake.md"), kind="P0")


def build_p1(ask: str, class_line: str, seats_summary: str, docs_summary: str) -> Packet:
    return make("P1", "P1_gate.md", {"THE ASK": ask.strip(), "OPERATOR CLASS": class_line, "SEATS AVAILABLE": seats_summary,
                                     "PROJECT DOCUMENTS": docs_summary})


def build_p2(ask: str, kind: str, constraints: str, ruled_out: str, recency: str) -> Packet:
    return make("P2", "P2_generate.md", {"THE ASK": ask.strip(), "KIND OF ASK": kind, "MUST BE TRUE": constraints,
                                         "ALREADY RULED OUT": ruled_out, "RECENCY": recency})


def build_p3(merged: str, options_standing: str, open_: str, lens: str) -> Packet:
    return make("P3", "P3_operate.md", {"WORKING ANSWER": merged, "OPTIONS STANDING": options_standing, "STILL OPEN": open_,
                                        "YOUR LENS": lens}, snapshot=(merged, options_standing, open_))


def build_p4(mode: str, replies: list, check_md: str, options_standing: str) -> Packet:
    labelled = "\n".join(f"REPLY {i}\n{r.strip()}\n" for i, r in enumerate(replies, 1))
    return make("P4", "P4_close.md", {"MODE": mode, "REVIEWER REPLIES": labelled, "CHECK RESULTS": check_md.strip(),
                                      "OPTIONS STANDING": options_standing if mode == "MERGE" else "not applicable in LIST mode"},
                snapshot=("", options_standing, ""))


def build_p5(merged: str, claims: str, options_standing: str, open_: str, conflict: str, experiments: str) -> Packet:
    return make("P5", "P5_review.md", {"THE CONCLUSION": merged, "ITS CLAIMS": claims, "OPTIONS STANDING": options_standing,
                                       "STILL OPEN": open_, "CONFLICT": conflict, "EXPERIMENTS": experiments},
                snapshot=(merged, options_standing, open_))


def build_p6(mode: str, ask: str, class_kind: str, success: str, constraints: str, merged: str, options_standing: str,
             open_: str, conflict: str, kills_all: str, review: str, review_check: str, experiments: str, metrics: str,
             flags: str, classification: str) -> Packet:
    literal = {"<if the ask touches law, tax, patents, medicine, or compliance>":
               "(only if the ask touches law, tax, patents, medicine, or compliance)"}
    return make("P6", "P6_final.md", {"MODE": mode, "THE ASK": ask.strip(), "CLASS / KIND": class_kind, "SUCCESS CRITERIA": success,
                                      "HARD CONSTRAINTS": constraints, "WORKING ANSWER": merged, "OPTIONS STANDING": options_standing,
                                      "STILL OPEN": open_, "CONFLICT": conflict, "ALL KILLS": kills_all, "REVIEW": review,
                                      "REVIEW CHECK": review_check, "EXPERIMENTS": experiments, "METRICS": metrics, "FLAGS": flags,
                                      "CLASSIFICATION": classification}, literal, snapshot=(merged, options_standing, open_))


def build_p7(sections_1_2: str, section_3: str, documents: str) -> Packet:
    p = make("P7", "P7_verify.md", {"THE RESULT": sections_1_2, "ITS CLAIMS": section_3})
    if documents:
        p.text = p.text.rstrip("\n") + "\n\nDOCUMENTS IN THIS PROJECT\n" + documents.rstrip("\n") + "\n"
        p.prompt_hash = sha(p.text)
    return p


def build_p8(ask: str, objective: str, guardrails: str, constraints: str, baseline: str, log: str, artifact: str) -> Packet:
    return make("P8", "P8_experiment.md", {"THE ASK": ask.strip(), "OBJECTIVE": objective, "GUARDRAILS": guardrails,
                                           "HARD CONSTRAINTS": constraints, "BASELINE": baseline, "EXPERIMENT LOG": log,
                                           "ARTIFACT": artifact})


def build_p9(ask: str, constraints: str, recency: str) -> Packet:
    return make("P9", "P9_direct.md", {"THE ASK": ask.strip(), "MUST BE TRUE": constraints, "RECENCY": recency})


def reprompt(packet: Packet, line: str) -> Packet:
    """The one re-prompt DISPATCH allows: the same packet with the rule that was missed appended."""
    return Packet(text=packet.text.rstrip("\n") + "\n\n" + line + "\n", kind=packet.kind, snapshot_hash=packet.snapshot_hash,
                  narrowed=packet.narrowed, neutrality=packet.neutrality)


def system_prompt() -> str:
    return prompt_text("S0_system.md")
