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
        if not self.day_state_path or not os.path.exists(self.day_state_path):
            return 0.0
        try:
            with open(self.day_state_path, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:  # noqa: BLE001 - unreadable state is not spend
            return 0.0
        return float(blob.get(date.today().isoformat(), 0.0))

    # -- enforcement -------------------------------------------------------
    def stale_rates(self) -> list[str]:
        return [s for s, r in self.rates.items()
                if r.is_stale(self.max_rate_age_days)]

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
        tmp = self.day_state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, indent=2)
        os.replace(tmp, self.day_state_path)

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


def rates_from_config(raw: Mapping[str, Mapping[str, object]]) -> dict[str, Rate]:
    """Build rates from a {seat_id: {input, output, verified_on}} mapping."""
    out: dict[str, Rate] = {}
    for seat, cfg in raw.items():
        if seat.startswith("_"):
            continue
        out[seat] = Rate(
            input_per_mtok=float(cfg.get("input_per_mtok", 0.0) or 0.0),
            output_per_mtok=float(cfg.get("output_per_mtok", 0.0) or 0.0),
            verified_on=(str(cfg["verified_on"]) if cfg.get("verified_on") else None),
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
        return int(cur) if isinstance(cur, (int, float)) else None

    return walk(input_path), walk(output_path)
