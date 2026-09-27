"""A total spend cap for one night, on the SDK's client-side cost estimates.

Dispatch charges every model call it observes (handshakes, sends, EXECUTOR sessions) and checks before the next
one. The check is estimate-based: the next call is expected to cost what the most expensive call of its kind
cost so far, so the total can overshoot the cap by at most one per-call cap (2 USD for a send, 5 USD for an
EXECUTOR session by default). A cap of None means no total cap, which is the fake-seat and CI behaviour.
"""
from .errors import NightStop


class Budget:
    def __init__(self, cap_usd: float | None, spent: float = 0.0):
        self.cap = float(cap_usd) if cap_usd else None
        self.spent = float(spent or 0.0)
        self.calls = 0
        self.max_seen = {"send": 0.0, "exec": 0.0}

    def expected(self, kind: str = "send") -> float:
        return self.max_seen.get(kind, 0.0)

    def check(self, kind: str, what: str):
        """Raise NightStop BUDGET when the running total plus the expected next call would pass the cap."""
        if self.cap is None:
            return
        if self.spent + self.expected(kind) > self.cap:
            raise NightStop("BUDGET", f"total cost estimate {self.spent:.4f} USD plus an expected {self.expected(kind):.4f} USD for "
                                      f"{what} would pass the cap of {self.cap:.2f} USD")

    def charge(self, cost_usd, kind: str = "send") -> float:
        c = float(cost_usd or 0.0)
        self.spent += c
        self.calls += 1
        if c > self.max_seen.get(kind, 0.0):
            self.max_seen[kind] = c
        return self.spent

    def projected_over(self, calls_ahead: int) -> bool:
        """SELECT's stop test: would calls_ahead more sends at the expected cost pass the cap?"""
        if self.cap is None:
            return False
        return self.spent + self.expected("send") * calls_ahead > self.cap
