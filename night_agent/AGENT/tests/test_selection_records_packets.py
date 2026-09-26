import json
import os
import tempfile
import unittest

from . import helpers  # noqa: F401
from AGENT import packets, selection
from AGENT.records import Clock, RunFolder, WriteOnceViolation, sha_text


def state(**kw):
    base = dict(class_="HYBRID", kind="build", profile="adaptive", options_standing=[1, 2], open_lines=["- C4 judgement call: settle by survey"],
                stage_metrics=[], ops_run=[], ready_generators=4, executor_ready=True, sends_used=10, max_calls=100, tail_sends=4,
                max_operators=4, measurable_options=2, now_hhmm="23:00")
    base.update(kw)
    return selection.NightState(**base)


class SelectionTests(unittest.TestCase):
    def test_stop_tests_in_order(self):
        self.assertEqual(selection.stop_test(state(usable_seats=1)), "CREW")
        self.assertEqual(selection.stop_test(state(hard_stop="22:00")), "HARD_STOP")
        self.assertEqual(selection.stop_test(state(max_calls=15)), "BUDGET")
        self.assertEqual(selection.stop_test(state(options_standing=[])), "NONE_STANDING")
        self.assertEqual(selection.stop_test(state(options_standing=[1], open_lines=["- C4 judgement call"])), "SUFFICIENT")
        self.assertIsNone(selection.stop_test(state(options_standing=[1], open_lines=["- C6 blocked: rerun the command"])))
        dry = [{"earned_kills": 0, "passed": 0, "decision_changed": "no"}] * 2
        self.assertEqual(selection.stop_test(state(stage_metrics=dry)), "MARGINAL")
        self.assertEqual(selection.stop_test(state(ops_run=["EXPERIMENT", "FMEA", "IDOV", "BAYES"])), "EXHAUSTED")
        self.assertIsNone(selection.stop_test(state()))

    def test_operator_table(self):
        self.assertEqual(selection.select_operator(state())[0], "EXPERIMENT")
        self.assertEqual(selection.select_operator(state(executor_ready=False))[0], "FMEA")
        self.assertEqual(selection.select_operator(state(class_="DELIBERATION", ops_run=["FMEA"]))[0], "IDOV")
        self.assertEqual(selection.select_operator(state(class_="DELIBERATION", kind="answer", ops_run=["FMEA"]))[0], "BAYES")
        self.assertEqual(selection.select_operator(state(class_="DELIBERATION", kind="answer", ops_run=["FMEA", "BAYES"]))[0], "TRIZ")
        self.assertIsNone(selection.select_operator(state(class_="DELIBERATION", kind="answer", options_standing=[1], open_lines=["settle with x"], ops_run=["FMEA"])))
        fixed = state(profile="v10-fixed", ops_run=["FMEA", "IDOV"])
        self.assertEqual(selection.select_operator(fixed)[0], "TRIZ")


class RecordsTests(unittest.TestCase):
    def test_write_once_hash_and_append(self):
        tmp = tempfile.mkdtemp()
        rf = RunFolder(os.path.join(tmp, "na-001"), "na-001", Clock("2026-09-26T22:00:00"))
        sha = rf.write_once("stage-01-generate/x.md", "hello\r\nworld\n", stage="GENERATE")
        raw = open(rf.path("stage-01-generate/x.md"), "rb").read()
        self.assertEqual(raw, b"hello\r\nworld\n")
        self.assertEqual(sha, sha_text("hello\r\nworld\n"))
        with self.assertRaises(WriteOnceViolation):
            rf.write_once("stage-01-generate/x.md", "again")
        rf.status(stage="X", step="y", next="z", last_complete="stage-01-generate/x.md")
        rf.status(stage="Y")
        st = json.load(open(rf.path("status.json")))
        self.assertEqual((st["stage"], st["last_complete"], st["run"]), ("Y", "stage-01-generate/x.md", "na-001"))
        with self.assertRaises(ValueError):
            rf.status(last_complete="missing.md")
        rf.append_jsonl("dispatch.jsonl", {"a": 1})
        rf.append_jsonl("dispatch.jsonl", {"a": 2})
        self.assertEqual([x["a"] for x in rf.read_jsonl("dispatch.jsonl")], [1, 2])
        log = rf.read_jsonl("log.jsonl")
        self.assertEqual(log[0]["file"], "stage-01-generate/x.md")
        self.assertEqual(log[0]["sha256"], sha)
        with self.assertRaises(ValueError):
            rf.path("../escape")


class PacketTests(unittest.TestCase):
    def test_every_prompt_fills_and_unlabelled_angle_text_is_kept(self):
        p2 = packets.build_p2("the ask", "build", "none given", "nothing", "none given")
        self.assertNotIn("<paste", p2.text)
        self.assertIn("one of several reviewers", p2.text)
        p6 = packets.build_p6("EVIDENCE", "ask", "HYBRID / build", "s", "c", "- m [G1] {C1}", "1. o", "none", "none", "KILLS\nnone", "NO REVIEW", "none", "none", "{}", "none", "KEEP_FOR_DEVELOPMENT")
        self.assertIn("{C<n>}", p6.text)
        self.assertIn("CLASSIFICATION    KEEP_FOR_DEVELOPMENT", p6.text)
        p4 = packets.build_p4("MERGE", ["CANDIDATES\nA. x\n", "CANDIDATES\nB. y\n"], 'CLAIM C1 [G1] "x"\n  RESULT     PASSED\n', "1. o")
        self.assertIn("\nREPLY 1\n", p4.text)
        self.assertIn('\nCLAIM C1 [G1] "x"\n', p4.text)  # multi-line values keep their line starts
        with self.assertRaises(packets.PacketError):
            packets.fill("LABEL  <missing>\n", {})

    def test_scans(self):
        self.assertEqual(packets.neutrality_hits("The winner is option 1"), ["winner"])
        self.assertEqual(packets.neutrality_hits(packets.prompt_text("P3_operate.md")), [])
        self.assertIn("absolute path", packets.payload_hits("see /home/user/x.md"))
        self.assertIn("sha256 hash", packets.payload_hits("a" * 64))
        self.assertNotIn("/home/user", packets.narrow("see /home/user/x.md now"))
        s = packets.strip_attribution("Claude said so [G2] and Fable agreed; seat G1 too", ["G1", "G2", "CLOSER"])
        self.assertNotIn("Claude", s)
        self.assertIn("[2]", s)
        self.assertEqual(packets.reprompt(packets.build_p0(), "extra").text.rstrip().endswith("extra"), True)


if __name__ == "__main__":
    unittest.main()
