import unittest

from . import helpers  # noqa: F401  (sys.path)
from AGENT import parse


class HeadingTests(unittest.TestCase):
    def test_strict_vs_tolerant(self):
        text = "## CANDIDATES\nA. one\n**CLAIMS**\n1. x (sum: 1 + 1 = 2)\nKNOCKDOWN\nnone\nMISSING\nnone\n"
        secs = parse.sections(text, parse.REPLY_HEADINGS["generate"])
        self.assertEqual(secs["CANDIDATES"], "A. one")
        self.assertIn("1. x", secs["CLAIMS"])
        self.assertEqual(parse.headings_exact(text, parse.REPLY_HEADINGS["generate"]), ["CANDIDATES", "CLAIMS"])

    def test_inline_after_dash_and_list_line_not_swallowed(self):
        text = "KILLS\n- Option 4: dead (source: DOI 10.1/x)\nOPEN\nnone\n"
        secs = parse.sections(text, ["KILLS", "OPEN"])
        self.assertTrue(secs["KILLS"].startswith("- Option 4"))
        self.assertEqual(parse.gate_fields("CLASS        - HYBRID\nKIND         - build\n")["CLASS"], "HYBRID")


class ClaimTests(unittest.TestCase):
    def test_methods(self):
        self.assertEqual(parse.method_of("total is 6 (sum: 5 + 1 = 6)"), "sum")
        self.assertEqual(parse.method_of("documented (source: DOI 10.1000/xyz, \"quote\")"), "source")
        self.assertEqual(parse.method_of("the brief says so (document: brief.md, \"x\")"), "document")
        self.assertEqual(parse.method_of("tests pass (command: `pytest -q`)"), "command")
        self.assertEqual(parse.method_of("common practice (judgement call, no way to check it)"), "none")
        self.assertEqual(parse.method_of("see https://doi.org/10.1/abc for details"), "source")

    def test_claim_fields(self):
        c = parse.claim_from_line(2, 'The lib has strict mode (source: DOI 10.1000/xyz123, "strict mode raises").')
        self.assertEqual((c.doi, c.quote, c.method), ("10.1000/xyz123", "strict mode raises", "source"))
        self.assertEqual(parse.claim_display(c.text), "The lib has strict mode")

    def test_claims_from_operate_reply(self):
        text = "WRONG\n- The figure is 750 (sum: 9000 / 12 = 750).\nMISSING\nnone\nKILLS\nnone\nOPEN\nnone\n"
        cl = parse.claims_from_reply(text, "operate")
        self.assertEqual(len(cl), 1)
        self.assertEqual(cl[0].section, "WRONG")

    def test_options_and_standing(self):
        close = ("OPTIONS\n1. Schema first. Requires C1, C2. Falsified if runtime rises.\n2. Two pass. Requires C2. Falsified if slow.\n"
                 "KILLS\n- Option 2 killed by claim C2 FAILED, EARNED\nOPEN\nnone\nMETRICS\noptions_created=2\n")
        opts = parse.options_from_list_close(close)
        self.assertEqual([o.n for o in opts], [1, 2])
        self.assertEqual(opts[0].required, {"C1", "C2"})
        self.assertEqual(parse.killed_options(close, "LIST"), {2})
        merge = "MERGED\n- x [G1] {C1}\nKILLS\nnone\nDEPRIORITIZED\nnone\nOPEN\nnone\nCONFLICT\nnone\nOPTIONS STANDING\n1. Schema first.\n5. Other.\nMETRICS\na=1 decision_changed=no\n"
        self.assertEqual(parse.options_standing(merge), [1, 5])
        self.assertEqual(parse.metrics_line(merge), {"a": 1, "decision_changed": "no"})

    def test_ready_word_and_candidates(self):
        self.assertTrue(parse.ready_word("READY\n"))
        self.assertTrue(parse.ready_word("READY."))
        self.assertFalse(parse.ready_word("I am READY"))
        cands = parse.lettered_candidates("A. First.\n   MEASURABLE PREDICTIONS: runtime falls\nB. Second.\n   MEASURABLE PREDICTIONS: none\n")
        self.assertEqual(parse.measurable_prediction(cands[0][2]), "runtime falls")
        self.assertEqual(parse.measurable_prediction(cands[1][2]), "")


if __name__ == "__main__":
    unittest.main()
