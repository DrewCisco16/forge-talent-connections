"""
cost_ledger.py
==============
Token accounting and hard spend ceilings.

WHY THIS EXISTS NOW. An unattended trigger -- a watched folder that starts a
run while nobody is at the keyboard -- turns every cost question from
theoretical into structural. A 25-call panel with one uncapped seat and no
ceiling is an open-ended bill running against a machine nobody is watching.
The ceiling is therefore a precondition for the watcher, not a companion
feature.

THE CEILING IS CHECKED BEFORE THE CALL, NEVER AFTER. Checking afterwards means
the call that crossed the limit was already made and already billed. A limit
you can only detect having exceeded is a report, not a limit.

NUMBERS ARE DERIVED OR ABSENT. Cost is computed from token counts the vendor
reported, multiplied by rates the operator entered and dated. Where a vendor
returned no usage block, the tokens are recorded as None and the run's total
is reported as a LOWER BOUND with the number of unmeasured calls stated. An
invented estimate would be worse than no estimate, because it would look like
a measurement.

RATES GO STALE. Every rate carries the date it was verified against the
vendor's pricing page. A rate with no date, or one older than the configured
staleness window, makes the ceiling meaningless -- so the ledger says so
loudly rather than enforcing a limit computed from numbers nobody has checked
this year.
"""
from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from adjudication_orchestrator import BudgetExceeded


class CeilingReached(BudgetExceeded):
    """A call was refused because making it would cross a configured limit.

    Carries which ceiling and by how much, because "aborted on cost" without
    the number is not actionable.
    """

    def __init__(self, which: str, spent: float, limit: float, would_add: float):
        self.which, self.spent, self.limit, self.would_add = (
            which, spent, limit, would_add)
        super().__init__(
            f"{which} ceiling reached: ${spent:.4f} spent, next call adds about "
            f"${would_add:.4f}, limit ${limit:.2f}. Call not made."
        )


@dataclass(frozen=True)
class Rate:
    """Per-million-token prices, with the date they were checked."""
    input_per_mtok: float
    output_per_mtok: float
    verified_on: str | None = None

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1_000_000.0) * self.input_per_mtok + \
               (output_tokens / 1_000_000.0) * self.output_per_mtok

    def is_stale(self, max_age_days: int = 120) -> bool:
        if not self.verified_on:
            return True
        try:
            when = datetime.strptime(self.verified_on, "%Y-%m-%d").date()
        except ValueError:
            return True
        return (date.today() - when).days > max_age_days


@dataclass
class CallCost:
    seat_id: str
    input_tokens: int | None
    output_tokens: int | None
    dollars: float | None
    measured: bool
    pass_id: str | None = None


CHARS_PER_TOKEN = 3.0
"""Conservative characters-per-token for a pre-call bound.

Real tokenisers average nearer 4 for English prose. 3 deliberately
OVER-estimates, because this number exists to refuse a call and an
under-estimate is the one direction that spends money the operator forbade.
"""

HIDDEN_OUTPUT_MULTIPLIER = 5.0
"""Worst-case ratio of billed output to the configured max_tokens cap.

Measured on a live grok-4.6 call: max_tokens was 4096, and the vendor reported
16,748 total tokens against 1,320 input -- roughly 15,400 billed as output,
about 3.8x the cap. Reasoning tokens are generated and billed and are not
bounded by max_tokens, so treating the cap as the worst case under-estimated
the ceiling check by that factor. 5.0 leaves headroom above the one figure
actually observed; it is a bound, not a prediction.
"""


def estimate_input_tokens(prompt: str) -> int:
    """A deliberately high token estimate for a prompt about to be sent.

    The precheck previously assumed a flat 3,000 input tokens regardless of
    the prompt. A 400,000-character prompt was therefore checked as 3,000
    tokens, passed a ceiling it would blow through, and booked its real cost
    only afterwards -- by which point the money was spent.
    """
    return max(1, int(len(prompt or "") / CHARS_PER_TOKEN) + 1)


@dataclass
class CostLedger:
    """Running spend for one run, enforced against three ceilings."""

    rates: Mapping[str, Rate]
    per_run: float | None = None
    per_stage: float | None = None
    per_day: float | None = None
    day_state_path: str | None = None
    max_rate_age_days: int = 120

    calls: list[CallCost] = field(default_factory=list)
    _stage_spent: dict[str, float] = field(default_factory=dict)

    # -- totals ------------------------------------------------------------
    @property
    def spent(self) -> float:
        return sum(c.dollars or 0.0 for c in self.calls)

    @property
    def unmeasured_calls(self) -> int:
        """Calls whose vendor returned no usage block. The total is a lower
        bound by exactly this many calls' worth of unknown tokens."""
        return sum(1 for c in self.calls if not c.measured)

    def stage_spent(self, pass_id: str) -> float:
        return self._stage_spent.get(pass_id, 0.0)

    def day_spent(self) -> float:
        """Today's spend from the shared state file.

        An UNREADABLE file raises rather than returning 0.0. It previously
        returned zero, which handed a fresh full day's budget to anyone whose
        state file was corrupt -- and a corrupt file is exactly what a crashed
        or concurrent writer leaves behind. "I cannot tell what has been spent
        today" and "nothing has been spent today" are opposite facts, and only
        one of them is a reason to authorise more calls.

        A MISSING file is still zero: nothing has run yet, which is a state we
        can actually establish.
        """
        if not self.day_state_path or not os.path.exists(self.day_state_path):
            return 0.0
        try:
            with open(self.day_state_path, encoding="utf-8") as fh:
                blob = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CeilingReached(
                f"daily spend state at {self.day_state_path} is unreadable "
                f"({type(exc).__name__}). Refusing to spend: an unreadable "
                f"ledger is not an empty one, and treating it as empty grants "
                f"a whole fresh day's budget on a corrupt file",
                0.0, self.per_day or 0.0, 0.0,
            ) from None
        if not isinstance(blob, dict):
            raise CeilingReached(
                f"daily spend state at {self.day_state_path} is not an object",
                0.0, self.per_day or 0.0, 0.0)
        today = blob.get(date.today().isoformat(), 0.0)
        if isinstance(today, bool) or not isinstance(today, (int, float)) \
                or not math.isfinite(float(today)) or float(today) < 0:
            raise CeilingReached(
                f"daily spend state at {self.day_state_path} holds "
                f"{today!r} for today, which is not a spend figure",
                0.0, self.per_day or 0.0, 0.0)
        return float(today)

    # -- enforcement -------------------------------------------------------
    def stale_rates(self) -> list[str]:
        """Seats whose price cannot bound anything: unverified, expired, or
        zero. A zero price means every call is free and the ceiling is
        decorative, so it belongs here however recently it was 'verified'."""
        return [s for s, r in self.rates.items()
                if r.is_stale(self.max_rate_age_days)
                or r.input_per_mtok <= 0 or r.output_per_mtok <= 0]

    def check_before_call(self, seat_id: str, est_input: int, est_output: int,
                          pass_id: str | None = None) -> None:
        """Refuse a call that would cross any ceiling. Raises CeilingReached.

        The estimate uses the seat's configured cap for output, which is the
        worst case the call can produce. Estimating with anything smaller
        would let the last call of a run cross the limit it was checked
        against.
        """
        rate = self.rates.get(seat_id)
        if rate is None:
            # No rate means no ability to enforce a limit on this seat. Fail
            # closed: an unpriced seat under a ceiling is an unbounded seat.
            raise CeilingReached(f"no rate configured for {seat_id}",
                                 self.spent, 0.0, 0.0)
        would_add = rate.cost(est_input, est_output)

        if self.per_run is not None and self.spent + would_add > self.per_run:
            raise CeilingReached("per-run", self.spent, self.per_run, would_add)
        if self.per_stage is not None and pass_id is not None:
            s = self.stage_spent(pass_id)
            if s + would_add > self.per_stage:
                raise CeilingReached(f"per-stage ({pass_id})", s,
                                     self.per_stage, would_add)
        if self.per_day is not None:
            d = self.day_spent() + self.spent
            if d + would_add > self.per_day:
                raise CeilingReached("per-day", d, self.per_day, would_add)

    def record(self, seat_id: str, input_tokens: int | None,
               output_tokens: int | None, pass_id: str | None = None) -> CallCost:
        """Book a completed call. Unmeasured calls cost 0.0 and are counted."""
        rate = self.rates.get(seat_id)
        measured = (input_tokens is not None and output_tokens is not None
                    and rate is not None)
        dollars = rate.cost(input_tokens or 0, output_tokens or 0) \
            if measured and rate else None
        cc = CallCost(seat_id, input_tokens, output_tokens, dollars,
                      measured, pass_id)
        self.calls.append(cc)
        if pass_id is not None and dollars:
            self._stage_spent[pass_id] = self._stage_spent.get(pass_id, 0.0) + dollars
        return cc

    def persist_day(self) -> None:
        if not self.day_state_path:
            return
        blob: dict[str, float] = {}
        if os.path.exists(self.day_state_path):
            try:
                with open(self.day_state_path, encoding="utf-8") as fh:
                    blob = json.load(fh)
            except Exception:  # noqa: BLE001
                blob = {}
        today = date.today().isoformat()
        blob[today] = float(blob.get(today, 0.0)) + self.spent
        # A UNIQUE temporary name per writer. Two processes sharing
        # "<path>.tmp" raced: one os.replace moved the file out from under the
        # other, which then raised FileNotFoundError, and one day's spend was
        # lost -- silently raising the next run's available budget.
        tmp = f"{self.day_state_path}.{os.getpid()}.{id(self)}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(blob, fh, indent=2)
            os.replace(tmp, self.day_state_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # -- reporting ---------------------------------------------------------
    def render(self) -> list[str]:
        out = ["-" * 72, "COST", "-" * 72]
        if not self.calls:
            out.append("  no billable call was made")
            return out
        by_seat: dict[str, tuple[int, int, float, int]] = {}
        for c in self.calls:
            n, i, d, u = by_seat.get(c.seat_id, (0, 0, 0.0, 0))
            by_seat[c.seat_id] = (n + 1, i + (c.input_tokens or 0) + (c.output_tokens or 0),
                                  d + (c.dollars or 0.0), u + (0 if c.measured else 1))
        for seat, (n, toks, d, unmeasured) in sorted(by_seat.items()):
            note = f"  ({unmeasured} call(s) reported no usage)" if unmeasured else ""
            out.append(f"  {seat:<14} {n:>3} call(s)  {toks:>8} tokens  ${d:.4f}{note}")
        bound = "LOWER BOUND" if self.unmeasured_calls else "total"
        out.append(f"  {bound:<14} ${self.spent:.4f}")
        if self.unmeasured_calls:
            out.append(f"  {self.unmeasured_calls} call(s) returned no usage block, so the "
                       f"figure above is a floor, not the bill.")
        stale = self.stale_rates()
        if stale:
            out.append("")
            out.append(f"  RATES UNVERIFIED OR STALE for: {', '.join(sorted(stale))}")
            out.append("  A ceiling computed from unchecked rates does not bound anything.")
            out.append("  Re-check the vendor pricing pages and stamp verified_on.")
        return out


def _finite_positive(v: object) -> float | None:
    """A usable price, or None. bool and non-finite are never usable.

    A rate of 0.0 means every call is free, so no ceiling can ever be crossed
    and the limit is decorative. Previously a malformed price became 0.0 while
    KEEPING its verified_on date, so stale_rates() reported nothing wrong and
    an unbounded seat looked correctly configured.
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    if not math.isfinite(f) or f <= 0.0:
        return None
    return f


def _as_float(v: object) -> float:
    """A price from untyped JSON. Anything unreadable is 0.0, which makes
    the rate stale-by-absence rather than a silent wrong number."""
    return float(v) if isinstance(v, (int, float)) else 0.0


def rates_from_config(raw: Mapping[str, Mapping[str, object]]) -> dict[str, Rate]:
    """Build rates from a mapping of seat id to price.

    Each entry takes input_per_mtok, output_per_mtok, and verified_on -- the
    full field names, matching rates.json. An earlier version of this line
    said "input, output", which no code has ever read: a config written to
    that description produces a rate of $0.00 per million tokens on both
    sides, and a seat priced at zero can never cross a ceiling.

    That failure is caught rather than silent, but only indirectly: a zero
    rate carries no verified_on it can justify, so the seat lands in
    stale_rates() and the report says the ceiling does not bound anything.
    Keys prefixed with an underscore are treated as comments and skipped,
    which is how rates.json carries _vendor and _source alongside the prices.
    """
    out: dict[str, Rate] = {}
    for seat, cfg in raw.items():
        if seat.startswith("_"):
            continue
        cin = _finite_positive(cfg.get("input_per_mtok"))
        cout = _finite_positive(cfg.get("output_per_mtok"))
        # An unusable price drops the verification date with it. Keeping the
        # date on a zero rate was the failure: stale_rates() saw a
        # recently-verified entry and reported nothing, while the seat it
        # priced could never cross a ceiling.
        usable = cin is not None and cout is not None
        out[seat] = Rate(
            input_per_mtok=cin or 0.0,
            output_per_mtok=cout or 0.0,
            verified_on=(str(cfg["verified_on"])
                         if usable and cfg.get("verified_on") else None),
        )
    return out


def usage_from_payload(payload: Mapping[str, object],
                       input_path: Sequence[object] | None,
                       output_path: Sequence[object] | None) -> tuple[int | None, int | None]:
    """Pull token counts out of a vendor reply using configured paths.

    Declarative for the same reason the response text path is declarative:
    every vendor puts usage somewhere slightly different, and hard-coding
    five shapes into the adapter is how the adapter ends up knowing about
    vendors again.
    """
    def walk(path: Sequence[object] | None) -> int | None:
        if not path:
            return None
        cur: object = payload
        for step in path:
            if isinstance(step, int):
                if not isinstance(cur, list) or not -len(cur) <= step < len(cur):
                    return None
                cur = cur[step]
            else:
                if not isinstance(cur, dict) or step not in cur:
                    return None
                cur = cur[step]
        # STRICT. bool is a subclass of int, so `true` was read as 1 token.
        # A negative count produced negative spend, and a fractional one was
        # silently truncated. Every one of those is a vendor payload we do not
        # understand, and a figure we do not understand must be reported as
        # UNMEASURED -- which makes the total an explicit lower bound -- not
        # coerced into a number that looks measured.
        if isinstance(cur, bool) or not isinstance(cur, (int, float)):
            return None
        if isinstance(cur, float) and not cur.is_integer():
            return None
        return int(cur) if cur >= 0 else None

    tin, tout = walk(input_path), walk(output_path)

    # REASONING TOKENS ARE BILLED AND DO NOT APPEAR IN THE OUTPUT FIELD.
    #
    # Measured live on grok-4.6 with a real pass-1 prompt:
    #   prompt_tokens 1320, completion_tokens 2433, total_tokens 16748
    # About 13,000 tokens were generated, billed, and invisible to the
    # configured output path. Reading the output field alone under-counted
    # billable output by roughly 4.5x, so every ceiling in this ledger was
    # being enforced against a fraction of the real spend -- the failure mode
    # a ceiling exists to prevent, wearing the ceiling's own green light.
    #
    # The vendor's own total is the authority on what it charged for. Where a
    # total is present and exceeds input + output, the difference is real
    # generation and belongs in the output figure. Where no total is reported
    # (Anthropic folds thinking tokens into output_tokens already), nothing
    # changes.
    #
    # The total is found as a SIBLING of the input field rather than under a
    # hard-coded "usage" key, because hard-coding a vendor's container name in
    # here is the exact thing the paths above exist to avoid: Anthropic uses
    # usage.input_tokens, Gemini uses usageMetadata.promptTokenCount, and a
    # literal "usage" would silently do nothing for one of them while looking
    # like it worked.
    total = _sibling_total(payload, input_path)
    if total is not None and tin is not None and tout is not None:
        if total < tin + tout:
            # The vendor's own arithmetic does not close. We cannot tell which
            # figure is wrong, so we report none of them: an unmeasured call
            # makes the run total an explicit LOWER BOUND, which is honest,
            # where a reconciled-from-contradictory-inputs number is not.
            return None, None
        if total > tin + tout:
            tout = total - tin
    return tin, tout


TOTAL_FIELD_NAMES = ("total_tokens", "totalTokenCount", "total_token_count")
"""Names a vendor may give the all-in token count, checked as siblings of the
input-token field. Not a vendor list -- a list of spellings of one idea."""


def _sibling_total(payload: Mapping[str, object],
                   input_path: Sequence[object] | None) -> int | None:
    """The all-in token count sitting alongside the input-token count.

    Returns None when the vendor reports no total. None means "not reported",
    never "zero": treating a missing total as zero would make the reconcile
    above subtract its way to a negative output count.
    """
    if not input_path or len(input_path) < 2:
        return None
    cur: object = payload
    for step in input_path[:-1]:
        if isinstance(step, int):
            if not isinstance(cur, list) or not -len(cur) <= step < len(cur):
                return None
            cur = cur[step]
        else:
            if not isinstance(cur, dict) or step not in cur:
                return None
            cur = cur[step]
    if not isinstance(cur, dict):
        return None
    for name in TOTAL_FIELD_NAMES:
        v = cur.get(name)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return int(v)
    return None
