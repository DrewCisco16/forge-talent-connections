"""SOP v1.2 section 8.1 -- Stage 0, the step that decides whether to build.

    "Do not skip Stage 0 -- it saves the most money."

    1. Write down, in one sentence, the exact task class this tool will handle.
    2. Decide whether that task decomposes or is sequential. Sequential: STOP.
    3. Collect 30 real examples with known-correct answers.
    4. Run ONE strong model on all 30. Score it. This is your BAC baseline.
    5. If baseline > 0.45: STOP. Build one model plus gates. You just saved
       months.

WHY IT MATTERS MORE THAN ANYTHING ELSE HERE. The evidence in SOP 7.1 is that
the average multi-agent system gains NOTHING -- "overall mean multi-agent
improvement across six benchmarks was 0.0%" -- and that above the saturation
threshold it goes negative. The five-seat panel is only justified below it.
Nobody has measured where this task class sits, so nobody can say whether the
panel is worth running at all. This measures it.

WHAT THIS FILE WILL NOT DO, AND THE REFUSAL IS THE POINT.

It will not invent the thirty questions. Ground truth is the operator's own
domain data by definition -- a baseline measured on somebody else's task class
predicts nothing about this one, and SOP 10.1 gives the number: leave-one-
domain-out R-squared of -2.09, which is worse than useless. A fabricated
question set would produce a confident figure that decides whether months of
work continue, resting on nothing. That is the exact failure this whole tool
exists to prevent, committed by the tool's own calibration step.

So it reads a file the operator writes, and refuses to run without one.

NO MODEL EVER JUDGES AN ANSWER. Scoring is mechanical -- a number compared to
a number, a string compared after normalisation, a value checked against a
permitted set. Asking a model whether a model was right reintroduces exactly
the correlated error the baseline exists to measure, and it would be invisible
in the output.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adjudication_orchestrator import CAPABILITY_SATURATION_THRESHOLD, preflight

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_QUESTIONS = 30
"""SOP 8.1 step 3. Not arbitrary: it is the smallest set the manual accepts,
and the interval below shows why fewer cannot settle the gate."""

ANSWER_LINE = re.compile(r"(?mi)^\s*ANSWER\s*[:|]\s*(?P<value>.+?)\s*$")
"""The one line the model must write.

The same contract discipline the panel uses. Grading free prose needs either a
human or a model, and a model grading a model is the correlated-error problem
the baseline exists to measure -- it would make a weak seat look strong in
exactly the cases where both share a blind spot.
"""


class QuestionSetError(ValueError):
    """The question file cannot be used as ground truth."""


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    answer: str
    kind: str = "exact"          # exact | numeric | oneof
    tolerance: str = "0"         # numeric only, absolute, as a decimal string
    accept: tuple[str, ...] = () # oneof only

    def __post_init__(self) -> None:
        if self.kind not in ("exact", "numeric", "oneof"):
            raise QuestionSetError(
                f"{self.id}: kind {self.kind!r} is not exact, numeric or oneof")
        if self.kind == "oneof" and not self.accept:
            raise QuestionSetError(f"{self.id}: oneof needs an accept list")
        if self.kind == "numeric":
            try:
                _number(self.answer)
                Fraction(self.tolerance)
            except (ValueError, ZeroDivisionError) as exc:
                raise QuestionSetError(
                    f"{self.id}: numeric answer or tolerance unreadable") from exc


def _number(text: str) -> Fraction:
    """The first number in a string, exactly. Commas and units are ignored."""
    m = re.search(r"-?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?", text or "")
    if m is None:
        raise ValueError(f"no number in {text!r}")
    return Fraction(m.group(0).replace(",", ""))


def _norm(text: str) -> str:
    """Case, punctuation and spacing folded. NOT meaning -- nothing here reads
    for sense, so a paraphrase scores wrong. That is the honest direction: a
    grader that guesses at intent is a grader nobody can check."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def load_questions(path: str) -> list[Question]:
    """Read the ground-truth set, refusing anything it cannot stand behind."""
    if not os.path.exists(path):
        raise QuestionSetError(
            f"no question set at {path}. SOP 8.1 step 3 asks for thirty real "
            f"examples WITH KNOWN-CORRECT ANSWERS from the task class this "
            f"tool will actually handle. They cannot be generated: a baseline "
            f"measured on another domain predicts nothing about this one "
            f"(SOP 10.1 gives leave-one-domain-out R-squared = -2.09). "
            f"See stage-zero-questions.example.json for the shape.")
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    rows = blob.get("questions", blob) if isinstance(blob, dict) else blob
    if not isinstance(rows, list):
        raise QuestionSetError(f"{path} is not a list of questions")
    out: list[Question] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise QuestionSetError(f"question {i} is not an object")
        if row.get("id", "").startswith("_"):
            continue                       # a comment row
        qid = str(row.get("id") or f"q{i + 1}")
        if qid in seen:
            raise QuestionSetError(f"duplicate question id {qid!r}")
        seen.add(qid)
        for need in ("question", "answer"):
            if not str(row.get(need) or "").strip():
                raise QuestionSetError(f"{qid}: {need} is empty")
        out.append(Question(
            id=qid, question=str(row["question"]).strip(),
            answer=str(row["answer"]).strip(),
            kind=str(row.get("kind") or "exact"),
            tolerance=str(row.get("tolerance") or "0"),
            accept=tuple(str(a) for a in (row.get("accept") or ()))))
    if not out:
        raise QuestionSetError(f"{path} carries no questions")
    return out


def extract_answer(reply: str) -> str | None:
    """The LAST ANSWER line. A model that reasons aloud and then answers has
    its conclusion at the end; taking the first would grade a worked step."""
    found = ANSWER_LINE.findall(reply or "")
    return found[-1].strip() if found else None


def score(given: str | None, q: Question) -> bool | None:
    """True, False, or None when the model wrote no ANSWER line at all.

    None is NOT wrong. A model that did not answer in the required shape has
    not been shown to lack the knowledge, and counting it against the model
    understates the baseline -- which biases the 0.45 gate toward building the
    ensemble, the expensive direction.
    """
    if given is None:
        return None
    if q.kind == "numeric":
        try:
            return abs(_number(given) - _number(q.answer)) <= Fraction(q.tolerance)
        except (ValueError, ZeroDivisionError):
            return False
    if q.kind == "oneof":
        return _norm(given) in {_norm(a) for a in q.accept}
    return _norm(given) == _norm(q.answer)


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion.

    NOT the textbook normal approximation, which misbehaves badly near 0 and 1
    and at small n -- and small n is the whole situation here. Wilson is the
    standard correction and it stays inside [0, 1].
    """
    if n <= 0:
        return (0.0, 1.0)
    p = correct / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class Baseline:
    """What one strong model scored, and what it settles."""

    n: int
    correct: int
    wrong: int
    unanswered: int
    low: float
    high: float
    misses: list[str] = field(default_factory=list)

    @property
    def scored(self) -> int:
        return self.correct + self.wrong

    @property
    def rate(self) -> float:
        return self.correct / self.scored if self.scored else 0.0

    @property
    def verdict(self) -> str:
        """The 0.45 gate, applied to the INTERVAL rather than the point.

        A point estimate of 0.47 from thirty questions has an interval running
        from roughly 0.30 to 0.65, which contains the threshold -- so it does
        not decide anything, and reading the point as though it did is how a
        coin flip becomes a months-long build. When the interval straddles the
        threshold the honest answer is that the question is still open.
        """
        t = CAPABILITY_SATURATION_THRESHOLD
        if self.scored < MIN_QUESTIONS:
            return "INSUFFICIENT"
        if self.low > t:
            return "DO NOT BUILD THE ENSEMBLE"
        if self.high <= t:
            return "ENSEMBLE JUSTIFIED"
        return "INCONCLUSIVE"


def measure(questions: Sequence[Question],
            ask_model: Callable[[str], str],
            on_event: Callable[[str], None] | None = None) -> Baseline:
    """Run ONE model over the set and score it. `ask_model(prompt) -> text`."""
    emit = on_event or (lambda _m: None)
    correct = wrong = unanswered = 0
    misses: list[str] = []
    for i, q in enumerate(questions, 1):
        prompt = (
            f"{q.question}\n\n"
            f"Work it out however you like. End your reply with one line, "
            f"exactly:\n\nANSWER: <your answer and nothing else>\n")
        try:
            reply = ask_model(prompt)
        except Exception as exc:                     # noqa: BLE001
            # A transport failure is not a wrong answer, and scoring it as one
            # would understate the baseline and bias the gate toward building.
            unanswered += 1
            emit(f"  {i}/{len(questions)} {q.id}: CALL FAILED -- {exc}")
            continue
        got = extract_answer(reply)
        verdict = score(got, q)
        if verdict is None:
            unanswered += 1
            emit(f"  {i}/{len(questions)} {q.id}: no ANSWER line")
        elif verdict:
            correct += 1
            emit(f"  {i}/{len(questions)} {q.id}: correct")
        else:
            wrong += 1
            misses.append(f"{q.id}: said {got!r}, answer is {q.answer!r}")
            emit(f"  {i}/{len(questions)} {q.id}: WRONG -- said {got!r}")
    low, high = wilson(correct, correct + wrong)
    return Baseline(len(questions), correct, wrong, unanswered, low, high,
                    misses)


def render(b: Baseline, task_class: str, decomposes: bool) -> list[str]:
    t = CAPABILITY_SATURATION_THRESHOLD
    out = [
        "=" * 72,
        "STAGE 0 -- should this tool be built at all?  (SOP 8.1)",
        "=" * 72,
        f"  task class:   {task_class}",
        f"  decomposes:   {'yes' if decomposes else 'NO -- see below'}",
        "",
        f"  questions:    {b.n}",
        f"  correct:      {b.correct}",
        f"  wrong:        {b.wrong}",
        f"  unanswered:   {b.unanswered}  (not counted either way)",
        "",
    ]
    if b.scored:
        out += [f"  BASELINE:     {b.rate:.3f}   "
                f"95% interval [{b.low:.3f}, {b.high:.3f}]",
                f"  threshold:    {t}"]
    else:
        out.append("  BASELINE:     NOT MEASURED -- nothing was scored")
    out += ["", f"  VERDICT: {b.verdict}", ""]
    if not decomposes:
        out += ["  SOP 10: a strictly sequential task measured -70%. Use one",
                "  model and one pass. Do not build this.", ""]
    elif b.verdict == "DO NOT BUILD THE ENSEMBLE":
        out += [f"  One model already clears {t} on this task class, with the",
                "  whole interval above it. SOP 8.1 step 5: build ONE model",
                "  plus deterministic gates. The gate layer in this repo --",
                "  arithmetic, citation resolution, DOI field matching, the",
                "  audit chain -- is the part worth keeping, and it does not",
                "  need five seats.", ""]
    elif b.verdict == "ENSEMBLE JUSTIFIED":
        out += ["  The whole interval sits below saturation and the task",
                "  decomposes. This is the regime where SOP 7.1's evidence",
                "  permits a gain. Run the panel.", ""]
    elif b.verdict == "INCONCLUSIVE":
        out += [f"  The interval CONTAINS {t}, so this does not decide. A",
                "  point estimate here is a coin flip dressed as a number.",
                "  More questions narrow it; nothing else does.", ""]
    else:
        out += [f"  Fewer than {MIN_QUESTIONS} questions were scored, which is",
                "  the floor SOP 8.1 step 3 sets. The interval below that is",
                "  too wide to separate anything.", ""]
    if b.misses:
        out += ["  What it got wrong -- read these before trusting the number:"]
        out += [f"    - {m}" for m in b.misses[:15]]
        if len(b.misses) > 15:
            out.append(f"    ... and {len(b.misses) - 15} more")
        out.append("")
    if b.scored >= MIN_QUESTIONS and decomposes:
        v = preflight(b.rate, decomposes)
        # PREFLIGHT DECIDES ON THE POINT ESTIMATE; THIS SECTION DECIDES ON
        # THE INTERVAL. When the interval does not settle the gate, preflight
        # still returns a firm answer -- and printing that under "agrees"
        # hands the reader a decision the evidence does not support. It was
        # doing exactly that: a baseline of 0.567 with an interval straddling
        # 0.45 came out INCONCLUSIVE above and "preflight() agrees: ... Run
        # one seat plus deterministic gates" below it.
        if b.verdict in ("INCONCLUSIVE", "INSUFFICIENT"):
            out += ["  preflight() reads the POINT estimate on its own, and on "
                    "that alone it says:",
                    f"    {v.reason}",
                    "  THE INTERVAL ABOVE DOES NOT SUPPORT THAT, either way. "
                    "The point is where",
                    "  the estimate happens to sit; the interval is what the "
                    "evidence can carry.", ""]
        elif v.run_ensemble == (b.verdict == "ENSEMBLE JUSTIFIED"):
            out += ["  preflight() agrees:", f"    {v.reason}", ""]
        else:
            out += ["  preflight() reads the POINT estimate differently, and "
                    "the interval above is the stricter reading:",
                    f"    {v.reason}", ""]
    return out


# ---------------------------------------------------------------------------
# the command
# ---------------------------------------------------------------------------

QUESTIONS = os.environ.get(
    "STAGE0_QUESTIONS", os.path.join(HERE, "stage-zero-questions.json"))
SEAT = os.environ.get("STAGE0_SEAT", "seat_1")
CEILING = float(os.environ.get("STAGE0_CEILING", "6.00"))
CAP = int(os.environ.get("STAGE0_CAP", "4096"))
TASK_CLASS = os.environ.get("STAGE0_TASK_CLASS", "").strip()
DECOMPOSES = os.environ.get("STAGE0_DECOMPOSES", "").strip().lower()


def main() -> int:
    if not TASK_CLASS:
        print("STAGE0_TASK_CLASS is not set.\n\n"
              "  SOP 8.1 step 1: write down, in ONE SENTENCE, the exact task\n"
              "  class this tool will handle. It is step one because a\n"
              "  baseline is only meaningful for a named task class -- and\n"
              "  because a tool whose job cannot be said in a sentence is not\n"
              "  ready to be measured.\n\n"
              '  e.g. STAGE0_TASK_CLASS="choosing between capital allocation\n'
              '        options from a written brief"')
        return 2
    if DECOMPOSES not in ("yes", "no"):
        print("STAGE0_DECOMPOSES must be yes or no.\n\n"
              "  SOP 8.1 step 2, and it can end the exercise on its own: a\n"
              "  strictly sequential task measured -70%. Kim et al. found\n"
              "  DECOMPOSABILITY, not difficulty, decides whether coordination\n"
              "  is viable at all.")
        return 2
    decomposes = DECOMPOSES == "yes"

    try:
        questions = load_questions(QUESTIONS)
    except (QuestionSetError, json.JSONDecodeError) as exc:
        print(f"question set unusable:\n\n  {exc}")
        return 2
    print(f"  {len(questions)} question(s) from {QUESTIONS}")
    if len(questions) < MIN_QUESTIONS:
        print(f"  NOTE: SOP 8.1 asks for {MIN_QUESTIONS}. Fewer will run, and "
              f"the interval will say what it could not settle.")

    if not decomposes:
        # Step 2 ends it before a single call. Measuring a baseline for a task
        # the manual already refuses is spending money to confirm a stop.
        print("\n".join(render(Baseline(len(questions), 0, 0, 0, 0.0, 1.0),
                               TASK_CLASS, decomposes=False)))
        return 1

    import json as _json

    from cost_ledger import CostLedger, rates_from_config
    from run_adjudication import live_seats, load_env_file
    print(load_env_file())
    with open(os.path.join(HERE, "rates.json"), encoding="utf-8") as fh:
        rates = rates_from_config(_json.load(fh))
    # No day_state_path: a calibration measurement must not consume the
    # operator's daily budget for adjudication runs.
    ledger = CostLedger(rates=rates, per_run=CEILING)
    seats = live_seats(os.path.join(HERE, "profiles.json"), ledger=ledger)
    if SEAT not in seats:
        print(f"  no seat {SEAT!r}; have {sorted(seats)}")
        return 2
    seat = seats[SEAT]
    if hasattr(seat, "max_tokens"):
        seat.max_tokens = CAP
    if hasattr(seat, "set_pass"):
        seat.set_pass("stage-0")
    print(f"  ONE seat: {SEAT}, cap {CAP}, ceiling ${CEILING:.2f}, "
          f"{len(questions)} calls")

    t0 = time.time()
    b = measure(questions, seat, on_event=lambda m: print(m, flush=True))
    print(f"\n  wall clock: {time.time() - t0:.0f}s")
    print("\n".join(ledger.render()))

    lines = render(b, TASK_CLASS, decomposes)
    print()
    print("\n".join(lines))

    out = os.path.join(HERE, "runs", f"stage0-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "stage-0.md"), "w", encoding="utf-8") as fh:
        fh.write("# Stage 0\n\n```\n" + "\n".join(lines) + "\n```\n")
    with open(os.path.join(out, "baseline.json"), "w", encoding="utf-8") as fh:
        _json.dump({"task_class": TASK_CLASS, "decomposes": decomposes,
                    "seat": SEAT, "n": b.n, "correct": b.correct,
                    "wrong": b.wrong, "unanswered": b.unanswered,
                    "rate": b.rate, "low": b.low, "high": b.high,
                    "verdict": b.verdict, "misses": b.misses}, fh, indent=2)
    print(f"  written to {out}")
    return 0 if b.verdict in ("ENSEMBLE JUSTIFIED",
                              "DO NOT BUILD THE ENSEMBLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
