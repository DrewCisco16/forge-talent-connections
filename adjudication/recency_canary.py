"""
recency_canary.py
=================
A known-answer test per seat, run before its output is trusted.

THE FAILURE THIS CATCHES. In a three-run verification exercise on this
project, one run retrieved the correct documentation, found it contradicted
its training priors, and discarded the evidence. Its reasoning trace shows the
sequence plainly: a prior formed before search, real evidence read, then the
conclusion "it's documented as nonexistent" -- a phrase that converts failure
to confirm a prior into a positive finding. It produced the highest confidence
and the best organisation of any run, and it was wrong.

WHY YOUR PANEL IS STRUCTURALLY EXPOSED. Every model identifier, price, and
documentation page this tool touches is from 2026. A seat whose priors predate
its subject faces a conflict between what it retrieved and what it believes,
and reasoning capability does not protect against it -- the failing run had
extended thinking enabled, which is what made the wrong answer coherent.

A seat that finds nothing wrong and a seat that cannot see the present are
indistinguishable without a question whose answer is already known. That is
what a canary is.

WHAT THIS DOES NOT CLAIM. One canary is one data point. A seat that passes has
not been shown to be reliable; it has been shown not to fail this particular
way on this particular question. No rate, frequency, or probability is
asserted anywhere here, because a handful of runs supports none.

THE FLAGGED SEAT STILL RUNS. Its output is collected -- a flagged seat is data
about seat behaviour -- but the flag travels with its claims into the
deliverable, and it contributes to no correlation figure, because a seat that
cannot see the present is not independently sampling the same world as the
others.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

DEFAULT_CANARY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "canaries.json")

PROMPT = """Answer from evidence you can retrieve, not from memory.

{question}

Reply with exactly two lines:
ANSWER: <your answer, or the single word UNKNOWN>
BASIS: <where you got it, or why you could not>

If you cannot retrieve anything, answer UNKNOWN. UNKNOWN is a correct and
useful reply. Asserting that something does not exist is NOT the same as
failing to confirm it, and no document says a thing is nonexistent."""


@dataclass(frozen=True)
class Canary:
    id: str
    question: str
    expect_substring: str
    """Case-folded substring that must appear in a correct ANSWER line."""
    why: str = ""


@dataclass
class CanaryResult:
    seat_id: str
    canary_id: str
    verdict: str          # PASS | PRIOR_OVERRIDE | UNKNOWN | ERROR
    answer: str = ""
    detail: str = ""

    @property
    def usable(self) -> bool:
        """UNKNOWN is not a pass, but it is not the failure this looks for.

        A seat that says it could not retrieve is behaving honestly and is
        merely under-informed. A seat that asserts the fact does not exist has
        converted a failure to confirm into a positive finding, which is the
        mechanism that produces confident wrong answers.
        """
        return self.verdict in ("PASS", "UNKNOWN")


def load_canaries(path: str = DEFAULT_CANARY_FILE) -> list[Canary]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    items = raw.get("canaries") if isinstance(raw, dict) else raw
    return [Canary(c["id"], c["question"], c["expect_substring"].casefold(),
                   c.get("why", ""))
            for c in (items or []) if c.get("id") and c.get("question")]


_DENIAL = ("does not exist", "doesn't exist", "nonexistent", "non-existent",
           "is not a real", "no such model", "not a real model",
           "is fictional", "made up", "i could not find any evidence that it "
           "exists")


def judge(reply: str, canary: Canary) -> CanaryResult:
    """Classify one reply. No model is asked to judge another."""
    answer = ""
    for line in (reply or "").splitlines():
        if line.strip().upper().startswith("ANSWER:"):
            answer = line.split(":", 1)[1].strip()
            break
    low = (answer or reply or "").casefold()

    # DENIAL IS CHECKED FIRST, and the order is load-bearing. A reply reading
    # "gpt-5.6-sol does not exist" contains the expected substring, so a
    # match-first canary scores the denial as a PASS -- blind to the exact
    # failure it was built to catch. Found by feeding it the real Run 3
    # wording.
    if any(d in low for d in _DENIAL):
        return CanaryResult(
            "", canary.id, "PRIOR_OVERRIDE", answer,
            "asserted the fact does not exist. No document states that a "
            "thing is nonexistent; this converts a failure to confirm into a "
            "positive finding.")
    if canary.expect_substring and canary.expect_substring in low:
        return CanaryResult("", canary.id, "PASS", answer,
                            "reported the documented fact")
    if "unknown" in low:
        return CanaryResult("", canary.id, "UNKNOWN", answer,
                            "could not retrieve, and said so -- honest, and "
                            "not the failure this test looks for")
    return CanaryResult("", canary.id, "UNKNOWN", answer,
                        "answer did not match and made no denial")


def run_canaries(seats: Mapping[str, Callable[[str], str]],
                 canaries: list[Canary]) -> dict[str, list[CanaryResult]]:
    """One call per seat per canary. Costs what one short call costs."""
    out: dict[str, list[CanaryResult]] = {}
    for seat_id, fn in seats.items():
        results: list[CanaryResult] = []
        for canary in canaries:
            try:
                reply = fn(PROMPT.format(question=canary.question))
            except Exception as exc:  # noqa: BLE001 - a dead seat is not a flag
                results.append(CanaryResult(seat_id, canary.id, "ERROR", "",
                                            f"{type(exc).__name__}: {exc}"))
                continue
            r = judge(reply, canary)
            results.append(CanaryResult(seat_id, canary.id, r.verdict,
                                        r.answer, r.detail))
        out[seat_id] = results
    return out


def flagged_seats(results: Mapping[str, list[CanaryResult]]) -> list[str]:
    return sorted(s for s, rs in results.items()
                  if any(r.verdict == "PRIOR_OVERRIDE" for r in rs))


def render(results: Mapping[str, list[CanaryResult]]) -> list[str]:
    out = ["-" * 72, "RECENCY CANARY -- can each seat see the present?", "-" * 72]
    if not results:
        out.append("  no canaries configured; no seat was tested")
        return out
    for seat_id, rs in sorted(results.items()):
        for r in rs:
            mark = "FLAG" if r.verdict == "PRIOR_OVERRIDE" else "    "
            out.append(f"  {mark} {seat_id:<10} {r.canary_id:<22} "
                       f"{r.verdict:<15} {r.detail[:44]}")
    flagged = flagged_seats(results)
    out.append("")
    if flagged:
        out.append(f"  PRIOR_OVERRIDE: {', '.join(flagged)}")
        out.append("  These seats asserted a documented fact does not exist.")
        out.append("  Their output is still collected, and it carries the flag.")
        out.append("  They contribute to no correlation figure.")
    else:
        out.append("  No seat asserted a documented fact does not exist.")
        out.append("  That is one data point per seat, not a reliability rating.")
    return out


def write_example_canaries(path: str = DEFAULT_CANARY_FILE) -> str:
    """Never overwrites. The questions must be ones YOU can verify today."""
    if os.path.exists(path):
        return path
    payload = {
        "_README": [
            "A canary is a question whose answer you have personally checked",
            "on a retrievable page, and which postdates common training",
            "cutoffs. Both halves matter: an old fact tests nothing, and a",
            "fact you have not checked yourself makes the canary the thing",
            "being tested.",
            "",
            "expect_substring is matched case-folded against the seat's",
            "ANSWER line. Keep it short and unambiguous.",
            "",
            "Re-verify these on the vendor pages before you rely on them.",
            "They are examples, not verified fixtures.",
        ],
        "canaries": [
            {"id": "openai-flagship-2026",
             "question": "What is the exact API model identifier of OpenAI's "
                         "current flagship reasoning model, as listed on their "
                         "own model page today?",
             "expect_substring": "gpt-5.6-sol",
             "why": "A 2026 identifier. A seat whose priors predate it tends "
                    "to report it as nonexistent rather than as unconfirmed."},
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path
