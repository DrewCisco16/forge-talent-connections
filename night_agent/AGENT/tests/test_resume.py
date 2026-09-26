"""B10: kill the run after the second CLOSE, resume from status.json, and no written file changes."""
import hashlib
import os
import unittest

from . import helpers


def hashes(run):
    out = {}
    for root, _, files in os.walk(run):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, run)
            if rel == "status.json" or rel.endswith(".jsonl"):
                continue  # the one overwritable file and the append-only records
            out[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


class ResumeTests(unittest.TestCase):
    def test_resume_rewrites_nothing(self):
        root = helpers.tmp_root()
        r = helpers.run_night(root, extra=["--stop-after", "stage-02-fmea/close.md"])
        self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
        run = os.path.join(root, "runs", "na-001")
        before = hashes(run)
        self.assertIn("stage-02-fmea/close.md", before)
        self.assertNotIn("final/DELIVERABLE.md", before)
        r2 = helpers.resume_night(root)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        after = hashes(run)
        for rel, h in before.items():
            self.assertEqual(after[rel], h, f"{rel} was rewritten on resume")
        self.assertIn("final/DELIVERABLE_ASSEMBLED.md", after)
        self.assertEqual(helpers.na_check(run), (0, []))
        log = helpers.jsonl(os.path.join(run, "log.jsonl"))
        self.assertTrue(all(l["result"] == "ALLOW" for l in log if l["action"] == "guard"))


if __name__ == "__main__":
    unittest.main()
