"""The total spend cap (AGENT/budget.py) and the live start-up check (run_night.startup_problem)."""
import json
import os
import unittest

from . import helpers
from AGENT import selection
from AGENT.budget import Budget
from AGENT.config import RunConfig
from AGENT.errors import NightStop
from AGENT.run_night import startup_problem
from .test_selection_records_packets import state


class BudgetUnitTests(unittest.TestCase):
    def test_no_cap_never_stops(self):
        b = Budget(None)
        b.charge(50.0)
        b.check("send", "x")
        self.assertFalse(b.projected_over(1000))

    def test_expected_is_the_most_expensive_call_of_that_kind(self):
        b = Budget(1.0)
        b.check("send", "first call")          # nothing seen yet: nothing expected, so the first call is never blocked
        b.charge(0.4, "send")
        b.charge(0.1, "send")
        self.assertEqual(b.expected("send"), 0.4)
        self.assertEqual(b.expected("exec"), 0.0)
        b.check("send", "third call")          # 0.5 + 0.4 = 0.9 <= 1.0
        b.charge(0.2, "send")
        with self.assertRaises(NightStop) as cm:
            b.check("send", "fourth call")     # 0.7 + 0.4 > 1.0
        self.assertEqual(cm.exception.reason, "BUDGET")
        self.assertIn("0.7000", cm.exception.note)

    def test_select_stop_test_projects_the_tail(self):
        b = Budget(3.0)
        b.charge(0.5, "send")   # expected 0.5 per send; one operator (4 + 1) plus tail 4 = 9 sends = 4.5 > 3.0 - 0.5
        self.assertEqual(selection.stop_test(state(budget=b)), "BUDGET")
        self.assertIsNone(selection.stop_test(state(budget=Budget(100.0))))
        self.assertIsNone(selection.stop_test(state(budget=None)))


class StartupTests(unittest.TestCase):
    def cfg(self, **kw):
        return RunConfig(root="/tmp/x", **kw)

    def test_fake_always_starts(self):
        self.assertIsNone(startup_problem(self.cfg(seats_mode="fake"), has_key=False, has_sdk=False))

    def test_live_key_route_needs_the_key(self):
        p = startup_problem(self.cfg(seats_mode="live", auth="key"), has_key=False, has_sdk=True)
        self.assertIn("ANTHROPIC_API_KEY", p)
        self.assertIn("--auth cli", p)
        self.assertIsNone(startup_problem(self.cfg(seats_mode="live", auth="key"), has_key=True, has_sdk=True))

    def test_live_cli_route_needs_no_key_but_needs_the_sdk(self):
        self.assertIsNone(startup_problem(self.cfg(seats_mode="live", auth="cli"), has_key=False, has_sdk=True))
        self.assertIn("claude-agent-sdk", startup_problem(self.cfg(seats_mode="live", auth="cli"), has_key=False, has_sdk=False))


class FakeBudgetNightTests(unittest.TestCase):
    def test_direct_night_stops_with_budget_and_still_conforms(self):
        # 7 handshakes, the gate and the DIRECT send at 0.1 each = 0.9; FINAL brings 1.0; VERIFY would pass the cap
        root = helpers.tmp_root()
        r = helpers.run_night(root, ask="ask_direct.md", sandbox=False, extra=["--fake-cost-usd", "0.1", "--budget-usd", "1.0"])
        run = os.path.join(root, "runs", "na-001")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        note = open(os.path.join(run, "NOTE.md")).read()
        self.assertTrue(note.startswith("STOP_REASON BUDGET"), note)
        self.assertIn("cap of 1.00 USD", note)
        st = json.load(open(os.path.join(run, "status.json")))
        self.assertEqual(st["stop_reason"], "BUDGET")
        self.assertAlmostEqual(st["cost_usd_estimate"], 1.0, places=6)
        self.assertEqual(helpers.na_check(run), (0, []))
        reg = json.load(open(os.path.join(run, "registry.json")))
        self.assertTrue(all(s["auth"] == "none" for s in reg["seats"]))

    def test_cap_not_reached_reports_the_estimate_in_the_ledger(self):
        root = helpers.tmp_root()
        r = helpers.run_night(root, ask="ask_direct.md", sandbox=False, extra=["--fake-cost-usd", "0.01", "--budget-usd", "50"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        led = json.load(open(os.path.join(root, "runs", "na-001", "ledger.json")))
        self.assertGreater(led["cost_usd_estimate"], 0.1)
        self.assertLess(led["cost_usd_estimate"], 0.2)


if __name__ == "__main__":
    unittest.main()
