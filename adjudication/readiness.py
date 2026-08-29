"""How much of this tool is actually established, and by what evidence.

WHY THIS IS NOT A CONFIDENCE THAT THE ANSWERS ARE CORRECT.

The operator asked for a percentage that all answers are correct after five
rounds. That number cannot be computed from a run of this tool, and printing
one would be the exact failure the whole design exists to prevent -- a
confident figure resting on nothing, which a reader acts on.

Three reasons, and none of them is fixable by better code:

1. THE TOOL ELIMINATES; IT DOES NOT VERIFY. An answer survives because
   nothing refuted it. "Nothing refuted it" and "it is true" are different
   facts, and the gap between them is exactly what the packet's caveats
   describe. A survivor with every commitment checked has been shown
   internally consistent, which is not the same as right.

2. A PERCENTAGE NEEDS A DATASET, AN OUTCOME VARIABLE AND A BASE RATE. One run
   of one question has none of the three. Five models agreeing is not a
   sample of five: it is five draws from overlapping training distributions,
   and how overlapping is exactly what this code reports as UNMEASURED.

3. THE QUESTIONS THIS IS FOR HAVE NO KEY. If the true answer were known in
   advance there would be nothing to adjudicate.

WHAT THIS DOES MEASURE is the BUILD: which parts of the machinery have been
shown to work, by what evidence, and which have not. That is a real number,
it is checkable, and it moves as work lands. It is a progress tracker, not a
statement about any answer.

WHAT WOULD PRODUCE A REAL CORRECTNESS FIGURE is at the bottom of this file,
and it is a specific, affordable experiment rather than an aspiration.
"""
from __future__ import annotations

import glob
import json
import os
import re

# Every command below is a literal in this file. Nothing reaches
# them from a run, a prompt, or a seat -- see _suite and _tool_clean.
import subprocess  # nosec B404
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


class Check:
    """One measurable fact about the build, and how it was established."""

    def __init__(self, name: str, weight: int, detail: str,
                 done: bool, evidence: str) -> None:
        self.name, self.weight = name, weight
        self.detail, self.done, self.evidence = detail, done, evidence


def _suite() -> tuple[int, int]:
    """(passed, failed) from an actual run, not from memory."""
    # Literal argv, this interpreter, no shell. Running the suite for real is
    # the point: a readiness report that trusted a remembered result would be
    # the exact thing it exists to stop.
    # NOT -q. This project's addopts already quieten the run, and adding -q
    # on top suppressed the summary line entirely -- so the output had no
    # figures in it and this reported "0 tests" for a suite that had just
    # passed 1,194. A readiness report that cannot read its own evidence is
    # worse than no report, because it is read as evidence.
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=HERE, capture_output=True, text=True, timeout=1800, check=False)
    # THE WHOLE OUTPUT, NOT THE LAST LINE. A warnings summary or a coverage
    # table after the counts left the tail with no figures in it, and this
    # reported "0 tests" for a suite that had just passed -- a readiness
    # report that cannot read its own evidence is worse than none.
    out = proc.stdout or ""
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    return passed, failed


def _tool_clean(cmd: list[str]) -> bool:
    """A gate's own exit code, read from the gate rather than remembered."""
    # cmd comes only from checks() below, where every element is a literal.
    return subprocess.run(cmd, cwd=HERE, capture_output=True,  # nosec B603
                          timeout=900, check=False).returncode == 0


class Round:
    """One round that actually ran against real vendors."""

    def __init__(self, blob: dict) -> None:  # type: ignore[type-arg]
        self.n = int(blob.get("round") or 0)
        self.created = int(blob.get("options_created") or 0)
        self.removed = len(blob.get("options_removed") or [])
        self.challenges = int(blob.get("challenges") or 0)


def _live_runs() -> list[Round]:
    """Every round this panel has actually run against real vendors."""
    out: list[Round] = []
    for path in sorted(glob.glob(os.path.join(HERE, "runs", "*", "status.md"))):
        try:
            with open(path, encoding="utf-8") as fh:
                blob = fh.read().split("```json")[1].split("```")[0]
            out.extend(Round(b) for b in json.loads(blob))
        except (OSError, IndexError, json.JSONDecodeError):
            continue
    return out


def _compliance() -> tuple[int, int]:
    """(seats that wrote a full commitment, seats measured) across live runs."""
    # ROUND ONE AND THE PROBES ONLY. Later rounds do not propose options, so
    # counting their replies put fifteen compliant seats over a denominator of
    # thirty-two and reported a passing panel as failing.
    full = seen = 0
    # THE MOST RECENT RUN OF EACH KIND, not every run ever made. Half the
    # replies on disk predate the PREDICATE contract, so they could not have
    # complied with a contract that did not exist -- counting them put a
    # fully compliant panel at 15/32 and reported a passing check as failing.
    latest: list[str] = []
    for pattern, leaf in ((os.path.join(HERE, "runs", "canary-*"),
                           os.path.join("round-1", "thinker-*.md")),
                          (os.path.join(HERE, "runs", "probe-*"), "seat_*.md")):
        dirs = sorted(glob.glob(pattern))
        if dirs:
            latest.extend(glob.glob(os.path.join(dirs[-1], leaf)))
    for path in latest:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        seen += 1
        if all(re.search(rf"(?mi)^\s*{k}\s*\|", text)
               for k in ("OPTION", "PREDICATE", "FORMULA")):
            full += 1
    return full, seen


def _challenges_seen() -> int:
    """CHALLENGE lines in live replies, counted from the replies themselves.

    Not from status.md: the challenge count only became durable after the run
    that produced the first one, so the file has no trace of it. The replies
    are the primary evidence and they are on disk either way.
    """
    return sum(
        len(re.findall(r"(?mi)^\s*CHALLENGE\s*\|", open(f, encoding="utf-8").read()))
        for f in glob.glob(os.path.join(HERE, "runs", "canary-*", "round-*",
                                        "thinker-*.md")))


def _corroborated_removals() -> int:
    """Removals that happened because seats AGREED, counted from the record.

    HARDCODED FALSE UNTIL NOW, so this check could never flip however many
    runs happened -- a tracker with a square that cannot be ticked reports
    progress that has been made as progress still owed.

    The ruling detail carries the phrase when corroboration decided it, and
    status.md carries the rulings, so the fact is on disk rather than in
    anyone's memory.
    """
    n = 0
    for path in glob.glob(os.path.join(HERE, "runs", "*", "status.md")):
        try:
            with open(path, encoding="utf-8") as fh:
                blob = fh.read().split("```json")[1].split("```")[0]
            for rnd in json.loads(blob):
                for ruling in rnd.get("rulings") or []:
                    if (ruling.get("status") == "fail"
                            and "agreed by" in (ruling.get("detail") or "")):
                        n += 1
        except (OSError, IndexError, json.JSONDecodeError):
            continue
    return n


def checks() -> list[Check]:
    rounds = _live_runs()
    eliminated = sum(r.removed for r in rounds)
    challenged = sum(r.challenges for r in rounds)
    deepest = max((r.n for r in rounds), default=0)
    created = sum(r.created for r in rounds)
    full, seen = _compliance()
    seen_ch = _challenges_seen()
    corroborated = _corroborated_removals()
    passed, failed = _suite()

    return [
        Check("offline suite", 15,
              f"{passed} tests, {failed} failing",
              failed == 0 and passed > 0, "pytest, run just now"),
        Check("static gates", 5, "ruff, mypy, bandit",
              _tool_clean([".venv/bin/ruff", "check", "."])
              and _tool_clean([".venv/bin/mypy"])
              and _tool_clean([".venv/bin/bandit", "-q", "-c",
                               "pyproject.toml", "-r", "."]),
              "each tool's own exit code"),
        Check("seats write the contract", 20,
              f"{full}/{seen} live replies carried a full commitment",
              seen > 0 and full == seen,
              "the most recent live run of each kind"),
        Check("round one proposes and self-checks", 15,
              "options parsed, commitments recomputed, merge completes",
              created > 0,
              "live canary"),
        Check("an option is removed on its own arithmetic", 15,
              f"{eliminated} removed across all live rounds",
              eliminated > 0, "live canary"),
        Check("later rounds reach the answers", 15,
              f"{seen_ch} challenge line(s) written live, "
              f"{challenged} recorded in status",
              seen_ch > 0, "the round-two replies themselves"),
        Check("a corroborated dispute removes an option", 10,
              f"{corroborated} live removal(s) carrying 'agreed by N seats'",
              corroborated > 0,
              "the ruling detail recorded in status.md"),
        Check("all five rounds run", 5,
              f"deepest round reached live: {deepest}",
              deepest >= 5, "live run"),
    ]


def main() -> int:
    got = checks()
    earned = sum(c.weight for c in got if c.done)
    total = sum(c.weight for c in got)
    print("=" * 72)
    print("BUILD READINESS -- how much of the machinery is established")
    print("=" * 72)
    for c in got:
        mark = "OK  " if c.done else "  --"
        print(f"  [{mark}] {c.weight:>3}%  {c.name}")
        print(f"            {c.detail}")
        print(f"            evidence: {c.evidence}")
    print("-" * 72)
    print(f"  {earned}% of {total}% established by evidence on disk")
    print()
    print("  THIS IS NOT A CONFIDENCE THAT ANY ANSWER IS CORRECT.")
    print("  It says how much of the machinery has been shown to work.")
    print()
    print("=" * 72)
    print("ANSWER CORRECTNESS: NOT MEASURED, AND NOT MEASURABLE FROM A RUN")
    print("=" * 72)
    print("""
  This tool removes answers that are demonstrably wrong. It does not show
  that a survivor is right, and a percentage saying otherwise would be
  invented. A survivor with every commitment checked has been shown
  internally consistent -- its own numbers add up -- which is a real fact and
  a smaller one than correctness.

  WHAT WOULD PRODUCE A REAL FIGURE, and it is one experiment:

    Put N questions to the panel whose true answers are already known and
    were not in the prompt. Run all five rounds on each. Count how often the
    answer that survived was the right one. That is an accuracy rate with a
    confidence interval, and it is the only honest route to a percentage.

    N drives the interval. Roughly, to claim better than 95% accuracy with a
    95% interval that excludes 90%, you need on the order of a few hundred
    questions -- not five, and not fifty. At a five-round run each, that is
    the real cost of the number being asked for, and it should be known
    before it is committed to.

    validation_harness.py already does exactly this against SYNTHETIC seats,
    and its own docstring says what is missing: "that requires wiring
    BlindedSeatRunner to actual seat callables and re-running against defects
    seeded in real work."

  Until that runs, the honest report on any single answer is the one the
  packet already prints: what was checked, what was refuted, and what nobody
  could check.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
