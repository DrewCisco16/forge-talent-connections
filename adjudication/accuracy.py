"""Does the panel get the right answer? The only experiment that can say.

THE QUESTION THIS FILE EXISTS FOR, asked from the first day: what is the
confidence that the answers surviving five rounds are correct?

Every other number in this repo refuses to answer it, and correctly.
readiness.py measures the BUILD. convergence.py measures whether the yields
decayed. judgment_queue.py measures whether the seats fail together. None of
them says whether a survivor is TRUE, because none of them can: the tool
eliminates, and "nothing refuted it" is a different fact from "it is right".

There is exactly one way to close that gap, and SOP 8.4 names it -- plant
known answers, run the panel, count how often it landed on them:

    Put N questions to the panel whose true answers are already known and
    were not in the prompt. Run all five rounds on each. Count how often the
    answer that survived was the right one.

This is that. It reuses stage_zero's question format, so ONE question set
measures both the single-model baseline and the panel, which is what makes
them comparable -- and comparing them is the whole point. SOP 7.1: "overall
mean multi-agent improvement across six benchmarks was 0.0%". If the panel
does not beat one model on your own questions, that is the finding.

THREE OUTCOMES PER QUESTION, NOT TWO.

    RESOLVED CORRECT   one answer survived and it was the right one
    RESOLVED WRONG     one answer survived and it was not
    NOT RESOLVED       nothing survived, or several did

The third is not a failure to score, it is a result, and folding it into
either of the others would misreport the instrument. SOP 9.3 is explicit that
the tool will not break a tie: "If two survive, the run reports two and does
not break the tie." So a panel that leaves twelve answers standing has not
been 0% accurate and has not been 100% accurate -- it has RESOLVED NOTHING,
and that is the number an operator most needs, because it is the one the last
five-round run actually produced.

WHAT IT COSTS, STATED BEFORE ANYTHING ELSE. One question is one full
five-round run. The measured cost of a five-round run on this panel is $4.96
and the planned bound is $16.82. Thirty questions is therefore on the order of
$150 measured, $500 bounded. That is real money and it is the price of the
number, so nothing here starts without ACCURACY_CONFIRM=yes in the
environment -- a ceiling alone is too easy to pass by accident.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stage_zero import (
    MIN_QUESTIONS,
    Question,
    QuestionSetError,
    load_questions,
    score,
    wilson,
)

HERE = os.path.dirname(os.path.abspath(__file__))

RESOLVED_CORRECT = "resolved-correct"
RESOLVED_WRONG = "resolved-wrong"
NOT_RESOLVED = "not-resolved"


@dataclass
class Outcome:
    """One question, put to the whole panel."""

    question_id: str
    result: str
    survivors: list[str] = field(default_factory=list)
    note: str = ""
    dollars: float = 0.0


def judge(survivors: list[str], q: Question) -> tuple[str, str]:
    """(outcome, note) for one question's surviving answers.

    THE TIE IS NOT BROKEN HERE, and it must not be. SOP 9.3: "Supply claims
    that distinguish them, or accept the set as the honest result. The tool
    will not break the tie." Picking the survivor that happens to match the
    key would measure this scorer's generosity rather than the panel's
    accuracy, and it would do it in the direction that flatters the panel.
    """
    if not survivors:
        return NOT_RESOLVED, "every answer was refuted; nothing survived"
    if len(survivors) > 1:
        matched = [s for s in survivors if score(s, q) is True]
        return NOT_RESOLVED, (
            f"{len(survivors)} answers survived and nothing separated them"
            + (f" ({len(matched)} of them would have scored correct, which is "
               f"not the same as the panel choosing one)" if matched else ""))
    only = survivors[0]
    return (RESOLVED_CORRECT if score(only, q) is True else RESOLVED_WRONG,
            f"survivor: {only!r}")


@dataclass
class Accuracy:
    """What the panel scored across the whole question set."""

    outcomes: list[Outcome] = field(default_factory=list)
    baseline: dict[str, Any] | None = None
    """The Stage 0 figure for the SAME questions, if it is on disk. Without it
    the panel's rate is a number with nothing to compare against, and SOP 7.1's
    finding is precisely about the comparison."""

    @property
    def n(self) -> int:
        return len(self.outcomes)

    @property
    def resolved(self) -> int:
        return sum(1 for o in self.outcomes if o.result != NOT_RESOLVED)

    @property
    def correct(self) -> int:
        return sum(1 for o in self.outcomes if o.result == RESOLVED_CORRECT)

    @property
    def dollars(self) -> float:
        return sum(o.dollars for o in self.outcomes)

    @property
    def resolution_rate(self) -> float:
        return self.resolved / self.n if self.n else 0.0

    @property
    def accuracy(self) -> float:
        """Correct among RESOLVED. Undefined when nothing resolved."""
        return self.correct / self.resolved if self.resolved else 0.0

    @property
    def end_to_end(self) -> float:
        """Correct among ALL questions asked.

        The number an operator actually lives with: a panel that is right
        every time it commits, and commits twice in thirty, has an accuracy of
        1.00 and an end-to-end rate of 0.067. Reporting only the first would
        be true and profoundly misleading.
        """
        return self.correct / self.n if self.n else 0.0


def render(a: Accuracy) -> list[str]:
    out = ["=" * 72,
           "PANEL ACCURACY -- was the surviving answer the right one?",
           "=" * 72,
           f"  questions put to the panel:  {a.n}",
           f"  resolved to ONE answer:      {a.resolved}"
           f"   ({a.resolution_rate:.0%})",
           f"  and that answer was right:   {a.correct}",
           f"  spent:                       ${a.dollars:.2f}",
           ""]
    if not a.n:
        return [*out, "  Nothing was measured.", ""]
    if not a.resolved:
        out += ["  ACCURACY: UNDEFINED, and that is the result.",
                "",
                "  The panel resolved NOTHING to a single answer, so there was",
                "  never a survivor to be right or wrong about. This is not a",
                "  score of zero -- a score of zero would mean it committed and",
                "  was wrong. It did not commit.",
                "",
                "  SOP 9.3 forbids breaking the tie, so this is the tool",
                "  behaving as specified. Whether that is USEFUL is the",
                "  question, and this number is the answer to it.", ""]
    else:
        lo, hi = wilson(a.correct, a.resolved)
        elo, ehi = wilson(a.correct, a.n)
        out += [f"  ACCURACY WHEN IT RESOLVES:  {a.accuracy:.3f}"
                f"   95% CI [{lo:.3f}, {hi:.3f}]",
                f"  END-TO-END (of all asked):  {a.end_to_end:.3f}"
                f"   95% CI [{elo:.3f}, {ehi:.3f}]",
                "",
                "  READ BOTH. The first is how often it is right when it",
                "  commits; the second is how often you get a right answer for",
                "  asking. A panel right every time it commits, committing",
                "  twice in thirty, scores 1.000 and 0.067.", ""]
    if a.n < MIN_QUESTIONS:
        out += [f"  THIN: {a.n} question(s) against the {MIN_QUESTIONS} SOP 8.1",
                "  step 3 asks for. The intervals above say what that costs.",
                ""]
    if a.baseline:
        b = a.baseline
        out += ["  AGAINST ONE MODEL ON THE SAME QUESTIONS (Stage 0):",
                f"    one model:  {b.get('rate', 0.0):.3f}"
                f"   [{b.get('low', 0.0):.3f}, {b.get('high', 0.0):.3f}]",
                f"    the panel:  {a.end_to_end:.3f}   end-to-end",
                ""]
        gap = a.end_to_end - float(b.get("rate") or 0.0)
        if gap > 0:
            out.append(f"    The panel is ahead by {gap:.3f} on these "
                       f"questions.")
        else:
            out.append(f"    The panel is BEHIND one model by {abs(gap):.3f}. "
                       f"SOP 7.1 found")
            out.append("    exactly this across six benchmarks: mean "
                       "multi-agent gain 0.0%.")
        out += ["    Compare the INTERVALS, not the points -- if they overlap,",
                "    this does not separate them.", ""]
    else:
        out += ["  NO STAGE 0 BASELINE ON DISK for comparison. The panel's",
                "  number alone cannot say whether five seats beat one; run",
                "  stage_zero.py on the SAME question set first.", ""]

    wrong = [o for o in a.outcomes if o.result == RESOLVED_WRONG]
    if wrong:
        out += ["  COMMITTED AND WRONG -- read every one of these:"]
        out += [f"    - {o.question_id}: {o.note}" for o in wrong[:15]]
        out.append("")
    return out


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

QUESTIONS = os.environ.get(
    "ACCURACY_QUESTIONS", os.path.join(HERE, "stage-zero-questions.json"))
PER_QUESTION_CEILING = float(os.environ.get("ACCURACY_PER_QUESTION", "17.00"))
TOTAL_CEILING = float(os.environ.get("ACCURACY_TOTAL", "60.00"))
"""A SECOND, OUTER BOUND. The per-run ceiling stops one question overspending;
nothing stopped thirty questions each stopping just under it. Two limits
because the failure modes are different: one is a runaway call, the other is
a long afternoon."""
CONFIRM = os.environ.get("ACCURACY_CONFIRM", "").strip().lower()
LIMIT = int(os.environ.get("ACCURACY_LIMIT", "0"))
"""Run only the first N questions. For a two-question smoke test before
committing to the whole set."""


def _survivors(results: Sequence[object]) -> list[str]:
    """The answers still standing at the end, as TEXT.

    Read from the last round that actually observed the option set. A round
    whose closer failed never reaches the bookkeeping, and reading its empty
    default as "nothing survived" would score a transport failure as the panel
    refuting every answer.
    """
    observed = [r for r in results if getattr(r, "options_observed", False)]
    if not observed:
        return []
    last = observed[-1]
    texts = getattr(last, "option_text", {}) or {}
    return [texts.get(oid, oid) for oid in getattr(last, "options_alive", [])]


def main() -> int:
    if CONFIRM != "yes":
        print("ACCURACY_CONFIRM is not set to yes.\n\n"
              "  This runs the FULL FIVE-ROUND PANEL once per question. The\n"
              "  measured cost of one five-round run on this panel is $4.96\n"
              f"  and the planned bound is $16.82, so the {MIN_QUESTIONS} "
              "questions SOP 8.1\n"
              "  asks for is on the order of $150 measured and $500 bounded.\n\n"
              "  That is the price of the accuracy figure, and it should be\n"
              "  paid deliberately rather than by running a script. Set\n"
              "  ACCURACY_CONFIRM=yes when you mean it.\n\n"
              "  ACCURACY_LIMIT=2 runs two questions first, for about $10.")
        return 2
    try:
        questions = load_questions(QUESTIONS)
    except (QuestionSetError, json.JSONDecodeError) as exc:
        print(f"question set unusable:\n\n  {exc}")
        return 2
    if LIMIT:
        questions = questions[:LIMIT]

    from cost_ledger import operator_ledger, rates_from_config
    from night_loop import RunTooExpensive, live_night

    with open(os.path.join(HERE, "rates.json"), encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))

    baseline = None
    for path in sorted(glob.glob(
            os.path.join(HERE, "runs", "stage0-*", "baseline.json")))[-1:]:
        with open(path, encoding="utf-8") as fh:
            baseline = json.load(fh)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_root = os.path.join(HERE, "runs", f"accuracy-{stamp}")
    os.makedirs(out_root, exist_ok=True)
    print(f"  {len(questions)} question(s), one five-round run each")
    print(f"  per-question ceiling ${PER_QUESTION_CEILING:.2f}, "
          f"total ceiling ${TOTAL_CEILING:.2f}")
    print(f"  output: {out_root}")

    acc = Accuracy(baseline=baseline)
    for i, q in enumerate(questions, 1):
        if acc.dollars >= TOTAL_CEILING:
            print(f"\n  TOTAL CEILING REACHED at ${acc.dollars:.2f}. "
                  f"Stopping with {i - 1} of {len(questions)} done.")
            break
        print(f"\n  [{i}/{len(questions)}] {q.id}")
        ledger = operator_ledger(rates, per_run=PER_QUESTION_CEILING)
        run_dir = os.path.join(out_root, q.id)
        try:
            results = live_night(
                q.question, os.path.join(HERE, "profiles.json"), run_dir,
                ledger=ledger,
                on_event=lambda m: print(f"      {m}", flush=True))
        except RunTooExpensive as exc:
            acc.outcomes.append(Outcome(q.id, NOT_RESOLVED,
                                        note=f"refused before spending: {exc}"))
            continue
        except Exception as exc:                       # noqa: BLE001
            # One question failing must not lose the questions already paid
            # for. Recorded as NOT RESOLVED with the reason, never as wrong.
            acc.outcomes.append(Outcome(
                q.id, NOT_RESOLVED, note=f"run failed: {type(exc).__name__}: {exc}",
                dollars=float(getattr(ledger, "spent", 0.0))))
            print(f"      FAILED: {exc}")
            continue
        survivors = _survivors(results)
        result, note = judge(survivors, q)
        spent = float(getattr(ledger, "spent", 0.0))
        acc.outcomes.append(Outcome(q.id, result, survivors, note, spent))
        print(f"      {result}  ${spent:.2f}  {note[:110]}")

    lines = render(acc)
    print()
    print("\n".join(lines))
    with open(os.path.join(out_root, "accuracy.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# Panel accuracy\n\n```\n" + "\n".join(lines) + "\n```\n")
    with open(os.path.join(out_root, "accuracy.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n": acc.n, "resolved": acc.resolved,
                    "correct": acc.correct, "dollars": acc.dollars,
                    "resolution_rate": acc.resolution_rate,
                    "accuracy": acc.accuracy, "end_to_end": acc.end_to_end,
                    "baseline": acc.baseline,
                    "outcomes": [vars(o) for o in acc.outcomes]}, fh, indent=2)
    print(f"  written to {out_root}")
    return 0 if acc.resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
