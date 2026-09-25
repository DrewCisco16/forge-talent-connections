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

sys.path.insert(0, HERE)
from adjudication_orchestrator import undecorate_marker_line  # noqa: E402


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


def _flatten(text: str) -> str:
    """A reply with its list and emphasis decoration stripped, line by line.

    The counters below anchor on the start of a line, and a model writing a
    line it thinks of as data puts a bullet, a number or a pair of asterisks
    in front of it. Same undecorator the engine uses, so what this tracker
    counts is what a real run would actually get.
    """
    return "\n".join(undecorate_marker_line(ln) for ln in text.splitlines())


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
    # THE FULL RUN COUNTS, AND IT IS THE BEST EVIDENCE THERE IS. This looked
    # only at canaries and probes, so a completed five-round run -- the one
    # that exercises the contract under the real prompt lengths, with personas
    # assigned and a working answer in front of the seats -- contributed
    # nothing to the compliance figure.
    for pattern, leaf in ((os.path.join(HERE, "runs", "full-*"),
                           os.path.join("round-1", "thinker-*.md")),
                          (os.path.join(HERE, "runs", "canary-*"),
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
        # READ THE WAY THE ENGINE READS IT. This matched only a line that
        # STARTS with the keyword, and a model writes "- OPTION | ..." or
        # "**PREDICATE | ...**". This module's own history is two rounds of
        # the same error -- a fully compliant panel counted at 15 of 32, a
        # passing check reported as failing -- and this is the third: a seat
        # that followed the contract exactly and used bullets counted as
        # having ignored it, on a tracker whose whole purpose is to say what
        # has been established.
        flat = _flatten(text)
        if all(re.search(rf"(?mi)^\s*{k}\s*\|", flat)
               for k in ("OPTION", "PREDICATE", "FORMULA")):
            full += 1
    return full, seen


def _challenges_seen() -> int:
    """CHALLENGE lines in live replies, counted from the replies themselves.

    Not from status.md: the challenge count only became durable after the run
    that produced the first one, so the file has no trace of it. The replies
    are the primary evidence and they are on disk either way.
    """
    total = 0
    for pattern in ("canary-*", "full-*"):
        for f in glob.glob(os.path.join(HERE, "runs", pattern, "round-*",
                                        "thinker-*.md")):
            with open(f, encoding="utf-8") as fh:
                total += len(re.findall(r"(?mi)^\s*CHALLENGE\s*\|",
                                        _flatten(fh.read())))
    return total


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


def _calibration_pass_is_inert() -> tuple[bool, str]:
    """SOP 2.3: the fifth pass calibrates and CANNOT RULE ANYTHING OUT.

    Read from the two engines rather than from memory, and read from BOTH,
    because the defect this replaces was the two disagreeing: the orchestrator
    had `Pass(eliminative=False)` from the start and the live engine ran
    `eliminate()` on round five like any other round.
    """
    from adjudication_orchestrator import DEFAULT_PASSES
    from night_loop import ROUNDS, thinker_prompt
    live = [r.eliminates for r in ROUNDS]
    other = [p.eliminative for p in DEFAULT_PASSES]
    prompt = thinker_prompt(ROUNDS[4], "x", "working")
    agree = live == other == [True, True, True, True, False]
    honest = "CAN REMOVE AN ANSWER" not in prompt and "REMOVES NOTHING" in prompt
    return agree and honest, (
        f"both engines: {sum(live)}/5 eliminative"
        + ("" if agree else "  -- THE TWO ENGINES DISAGREE")
        + ("" if honest else "  -- the prompt still asks seats to remove"))


def _stop_rule_reaches_a_live_run() -> tuple[bool, str]:
    """SOP 6.3 and 9.3, applied to the engine that spends money.

    Every estimator existed and was tested; none was reachable from
    `night_loop`, so a packet could report a survivor while the manual's own
    stop rule said DO NOT COMMIT and nothing on the page said so.
    """
    import inspect

    import convergence
    from night_loop import write_verifier_packet
    src = inspect.getsource(write_verifier_packet)
    wired = "render_convergence" in src or "analyse" in src
    has = all(hasattr(convergence, n)
              for n in ("analyse", "render", "divergence", "detections_by_seat"))
    return wired and has, (
        "the packet carries the residual, the singleton fraction, the "
        "per-pass divergence and the holes"
        if wired and has else "the live engine still cannot reach them")


def _holes_name_their_remedy() -> tuple[bool, str]:
    """SOP 9.3: "a hole you cannot act on is a disclaimer"."""
    import convergence
    from night_loop import RoundResult

    r = RoundResult(1, "r", eliminative=True)
    r.options_observed = True
    r.options_alive = ["a", "b"]
    r.options_unexamined = ["b"]
    r.thinkers_failed = {"seat_3": "timeout"}
    c = convergence.analyse([r], escalations_pending=1)
    named = [h for h in c.holes if h.remedy.strip()]
    return bool(c.holes) and len(named) == len(c.holes), (
        f"{len(named)}/{len(c.holes)} holes name what would close them")


def _the_queue_can_be_worked() -> tuple[bool, str]:
    """SOP 9.1 steps 7-8, and SOP 10 makes it a do-not-build condition.

    Measured by REPLAYING the most recent full run rather than by importing
    the module: a queue surface that cannot read a real run is not a queue
    surface, and every earlier gap in this project was a thing that existed
    and could not be reached from the engine that spends money.
    """
    runs = sorted(glob.glob(os.path.join(HERE, "runs", "full-*")))
    if not runs:
        return False, "no full run on disk to work a queue from"
    try:
        import judgment_queue as JQ
        from run_adjudication import _default_gates
        # THE OFFLINE GATES, NOT NONE. With no gates nothing is ever settled,
        # so every claim reads as open and this reported 143 where the run
        # itself had 136 -- a readiness figure describing a run that did not
        # happen. Not night_gates() either: those reach Crossref and doi.org,
        # and a readiness report that needs the network cannot be trusted to
        # run when the network is what is broken.
        rep = JQ.replay(runs[-1], gates=_default_gates())
        items = JQ.open_items(rep)
        # EVERY ITEM MARKED TRUE. This is a PIPELINE TEST, not a measurement:
        # nobody has decided these claims, and the rho it produces describes a
        # panel in which every open claim happened to be correct. It proves
        # the path from a worked queue to a correlation exists, which is the
        # thing that was missing. It is not evidence about these seats.
        folded = JQ.fold(rep, {c.id: True for c in items})
    except Exception as exc:                      # noqa: BLE001
        return False, f"replaying {os.path.basename(runs[-1])} failed: {exc}"
    return bool(items) and folded.rho is not None, (
        f"{len(items)} open item(s) in {os.path.basename(runs[-1])}; the path "
        f"from a worked queue to rho runs end to end "
        f"(pipeline test on placeholder decisions, NOT a measured rho -- "
        f"nobody has decided these {len(items)} claims)")


def _the_accuracy_experiment_is_reachable() -> tuple[bool, str]:
    """SOP 8.4's seeded-truth run: built, wired, and refusing to spend blind.

    A BUILD CHECK, NOT A RESULT. Whether the panel is accurate is a
    measurement nobody has taken; whether the thing that would take it exists
    and works is a fact about the build, and it is the fact that was missing.
    Every gap in this project has been a capability that existed and could not
    be reached, so reachability is what this tests: the scorer decides the
    three outcomes correctly and the runner refuses to spend without an
    explicit confirmation.
    """
    try:
        import accuracy as AC
        from stage_zero import Question
        q = Question(id="q", question="which?", answer="alpha")
        cases = [
            (["alpha"], AC.RESOLVED_CORRECT),
            (["beta"], AC.RESOLVED_WRONG),
            ([], AC.NOT_RESOLVED),
            (["alpha", "beta"], AC.NOT_RESOLVED),   # a tie is never broken
        ]
        wrong = [f"{s}->{AC.judge(s, q)[0]}" for s, want in cases
                 if AC.judge(s, q)[0] != want]
        guarded = AC.CONFIRM != "yes"
    except Exception as exc:                          # noqa: BLE001
        return False, f"accuracy.py is not usable: {exc}"
    return not wrong and guarded, (
        "the seeded-truth run is wired and refuses to spend unconfirmed; "
        "UNRUN -- it needs the operator's questions"
        if not wrong and guarded
        else f"scorer disagreed on {wrong}" if wrong
        else "it would spend without confirmation")


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
    calib_ok, calib_detail = _calibration_pass_is_inert()
    stop_ok, stop_detail = _stop_rule_reaches_a_live_run()
    holes_ok, holes_detail = _holes_name_their_remedy()
    queue_ok, queue_detail = _the_queue_can_be_worked()
    acc_ok, acc_detail = _the_accuracy_experiment_is_reachable()

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
        # -- SOP v1.2 conformance, added after a full audit of the manual
        # against the engine that actually spends money. These were scope
        # from the first day; they were simply never measured here, and a
        # tracker that omits a specified behaviour reports a build as more
        # finished than it is.
        Check("the calibration pass cannot eliminate", 8,
              calib_detail, calib_ok, "SOP 2.3, read from both engines"),
        Check("the manual's stop rule reaches a live run", 7,
              stop_detail, stop_ok, "SOP 6.2, 6.3, 6.5, 9.1 steps 9-11"),
        Check("every hole names what would close it", 5,
              holes_detail, holes_ok, "SOP 9.3, computed from a real hole set"),
        Check("the judgment queue can be worked", 10,
              queue_detail, queue_ok,
              "SOP 9.1 steps 7-8, by replaying the most recent full run"),
        Check("the accuracy experiment is built and wired", 10,
              acc_detail, acc_ok,
              "SOP 8.4, by scoring the three outcomes it must distinguish"),
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
    # NORMALISED, because the weights are not guaranteed to sum to 100 and
    # were not: adding the three SOP-conformance checks took the total to 120
    # and this printed "120% of 120%", which reads as a broken meter rather
    # than a finished build. The weights say how much each check MATTERS
    # relative to the others; the percentage is their share.
    pct = (100.0 * earned / total) if total else 0.0
    print(f"  {pct:.0f}% established by evidence on disk "
          f"({earned} of {total} weighted points)")
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

    THE EXPERIMENT IS NOW BUILT AND UNRUN, which is a different state from
    the one this section described for months. accuracy.py puts each question
    to the whole five-round panel and scores the SURVIVOR against the key,
    reusing stage_zero's question set so one file measures both the panel and
    the single model it has to beat. What it still needs is the questions,
    and those are the operator's -- see stage_zero.py for why they cannot be
    generated.

    It reports THREE outcomes, not two: resolved-correct, resolved-wrong, and
    NOT RESOLVED. The third is what the only real five-round run produced --
    twelve answers standing, none chosen -- and it is neither a right answer
    nor a wrong one. An accuracy figure that folded it into either would
    misdescribe the instrument.

    validation_harness.py remains SYNTHETIC and remains useful for exactly
    what it claims: exercising the machinery against known ground truth. It
    is not this.

  Until accuracy.py runs, the honest report on any single answer is the one
  the packet already prints: what was checked, what was refuted, and what nobody
  could check.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
