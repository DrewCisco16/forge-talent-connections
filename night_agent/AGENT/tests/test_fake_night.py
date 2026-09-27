"""A full fake HYBRID night and a full fake DIRECT night pass the package's own checker, every guard call is
ALLOW, and G-11 ran before every non-registry dispatch."""
import json
import os
import unittest

from . import helpers


class FakeNightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = helpers.tmp_root()
        cls.r = helpers.run_night(cls.root)
        cls.run_dir = os.path.join(cls.root, "runs", "na-001")

    def test_exit_and_checker(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        rc, fails = helpers.na_check(self.run_dir)
        self.assertEqual((rc, fails), (0, []))

    def test_guards_all_allow_and_g11_before_every_send(self):
        log = helpers.jsonl(os.path.join(self.run_dir, "log.jsonl"))
        guards = [l for l in log if l["action"] == "guard"]
        self.assertTrue(guards)
        self.assertTrue(all(g["result"] == "ALLOW" for g in guards), [g for g in guards if g["result"] != "ALLOW"])
        sends = [g for g in guards if g["stage"] == "SEND"]
        dispatches = [d for d in helpers.jsonl(os.path.join(self.run_dir, "dispatch.jsonl")) if d["stage_id"] != "registry"]
        self.assertEqual(len(sends), len(dispatches))
        for stage in ("GATE", "GENERATE", "CHECK", "CLOSE", "OPERATE", "REVIEW", "FINAL", "VERIFY", "BASELINE", "DECIDE"):
            self.assertTrue(any(g["stage"] == stage for g in guards), stage)

    def test_shape(self):
        led = json.load(open(os.path.join(self.run_dir, "ledger.json")))
        self.assertEqual(led["class"], "HYBRID")
        self.assertIn("EXPERIMENT", led["stages"])
        self.assertEqual(led["classification"], "KEEP_FOR_DEVELOPMENT")
        self.assertGreaterEqual(led["earned_kills"], 2)
        xlog = helpers.jsonl(os.path.join(self.run_dir, "experiments", "log.jsonl"))
        self.assertEqual([x["decision"] for x in xlog], ["KEEP", "REVERT"])
        caps = helpers.jsonl(os.path.join(self.run_dir, "capture.jsonl"))
        self.assertTrue(all(c["completion_signal_observed"] for c in caps))
        self.assertTrue(os.path.exists(os.path.join(self.run_dir, "stage-01-generate", "packet.md")))
        self.assertTrue(os.path.exists(os.path.join(self.run_dir, "executions.jsonl")))
        reg = json.load(open(os.path.join(self.run_dir, "registry.json")))
        self.assertTrue(all(s["url"].startswith("fake://fake/") and s["runtime"] == "fake" for s in reg["seats"]))
        self.assertTrue(os.path.exists(os.path.join(self.root, "architecture", "runs.jsonl")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "architecture", "model-capability-ledger.jsonl")))
        d = open(os.path.join(self.run_dir, "final", "DELIVERABLE.md")).read()
        self.assertEqual(d.count("KEEP_FOR_DEVELOPMENT"), 1)
        self.assertNotIn("REVERT", d)


class FakeDirectTests(unittest.TestCase):
    def test_direct(self):
        root = helpers.tmp_root()
        r = helpers.run_night(root, ask="ask_direct.md", sandbox=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        run = os.path.join(root, "runs", "na-001")
        self.assertEqual(helpers.na_check(run), (0, []))
        self.assertEqual(sorted(os.listdir(os.path.join(run, "stage-01-direct"))), ["check.md", "packet.md", "seat-G1.md"])
        led = json.load(open(os.path.join(run, "ledger.json")))
        self.assertIn("NO_OUTSIDE_REVIEW", led["flags"])
        self.assertEqual(led["class"], "DIRECT")
        self.assertTrue(os.path.exists(os.path.join(run, "final", "verifier.md")))


if __name__ == "__main__":
    unittest.main()
