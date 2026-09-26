import os
import tempfile
import unittest

from . import helpers
from AGENT import parse
from AGENT.check import arith, documents, engine, sources
import na_check


class ArithTests(unittest.TestCase):
    def test_pass_fail(self):
        self.assertEqual(arith.check_sum("21600 / 12 = 1800")[0], "PASSED")
        self.assertEqual(arith.check_sum("9000 / 12 = 700")[0], "FAILED")
        self.assertIn("750", arith.check_sum("9000 / 12 = 700")[1])
        self.assertEqual(arith.check_sum("0.1 ^ 5 = 0.00001")[0], "PASSED")
        self.assertEqual(arith.check_sum("1,800 * 12 = 21,600")[0], "PASSED")
        self.assertEqual(arith.check_sum("5 percent of nothing")[0], "NOT TESTABLE")

    def test_whitelist(self):
        with self.assertRaises(Exception):
            arith.evaluate("__import__('os').system('x')")
        with self.assertRaises(Exception):
            arith.evaluate("2 ** 100000")


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.res = sources.FixtureResolver(os.path.join(helpers.FIX, "documents", "dois.json"))

    def check(self, line):
        return sources.check_source(parse.claim_from_line(1, line), self.res, "2026-09-26T22:00")

    def test_mapping(self):
        r = self.check('strict mode exists (source: DOI 10.1000/xyz123, "strict mode raises on malformed input")')
        self.assertEqual(r["result"], "PASSED")
        self.assertIn("support=SUPPORTED grade=A", r["source"].replace("grade=A quote_present=yes support=SUPPORTED", "support=SUPPORTED grade=A"))
        r = self.check("a study shows it (source: DOI 10.9999/notreal.1)")
        self.assertEqual((r["result"], "support=NOT_FOUND" in r["source"]), ("FAILED", True))
        r = self.check('the paper says X (source: DOI 10.1000/xyz123, "words that are not in it")')
        self.assertEqual(r["result"], "INCONCLUSIVE")
        r = self.check("no locator at all (source)")
        self.assertEqual(r["result"], "NOT TESTABLE")
        off = sources.check_source(parse.claim_from_line(1, "x (source: DOI 10.1000/xyz123)"), sources.OfflineResolver(), "t")
        self.assertEqual((off["result"], "support=UNVERIFIED" in off["source"]), ("BLOCKED", True))

    def test_allowed_hosts(self):
        self.assertTrue(sources.host_allowed("https://api.crossref.org/works/x"))
        self.assertTrue(sources.host_allowed("https://www.sba.gov/page"))
        self.assertFalse(sources.host_allowed("https://example.com/page"))


class DocumentTests(unittest.TestCase):
    def test_quote_rules(self):
        d = os.path.join(helpers.FIX, "documents")
        ok = documents.check_document(parse.claim_from_line(1, 'brief says (document: brief.md, "written to rejects.csv")'), d, "t")
        self.assertEqual(ok["result"], "PASSED")
        absent = documents.check_document(parse.claim_from_line(1, 'brief says (document: brief.md, "partial loads are permitted")'), d, "t")
        self.assertEqual((absent["result"], "support=UNSUPPORTED" in absent["source"]), ("INCONCLUSIVE", True))
        noquote = documents.check_document(parse.claim_from_line(1, "brief says so (document: brief.md)"), d, "t")
        self.assertEqual(noquote["result"], "NOT TESTABLE")
        missing = documents.check_document(parse.claim_from_line(1, 'x (document: nothere.md, "q")'), d, "t")
        self.assertEqual(missing["result"], "BLOCKED")
        self.assertIsNone(documents.read_document(d, "../SCHEMA.json"))


class EngineTests(unittest.TestCase):
    def test_records_pass_the_checker_rules_and_ids_continue(self):
        from AGENT.records import Clock, RunFolder
        tmp = tempfile.mkdtemp()
        rf = RunFolder(os.path.join(tmp, "runs", "na-001"), "na-001", Clock("2026-09-26T22:00:00"))
        rf.write_once("stage-01-generate/check.md", 'CLAIM C3 [G1] "x"\n  METHOD     sum\n  ACTION     a\n  RETRIEVED  1 + 1 = 2\n  RESULT     PASSED\n  SETTLE     \n')
        alloc = engine.ClaimIdAllocator(rf)
        self.assertEqual(alloc.next(), "C4")
        ctx = engine.CheckContext(documents_dir=os.path.join(helpers.FIX, "documents"),
                                  resolver=sources.FixtureResolver(os.path.join(helpers.FIX, "documents", "dois.json")), now="t")
        reply = ("STAGE 01 GENERATE SEAT G2 TIME 22:00\nDISPATCH d-1\nCANDIDATES\nA. x\nCLAIMS\n1. Six (sum: 5 + 1 = 6).\n"
                 "2. Common (judgement call, no way to check it).\n3. Strict (source: DOI 10.9999/notreal.1).\nKNOCKDOWN\nnone\nMISSING\nnone\n")
        recs = engine.run_check(rf, {"G2": reply}, "generate", ctx, alloc)
        text = engine.render(recs)
        parsed = na_check.parse_claims(text)
        self.assertEqual([c["result"] for c in parsed], ["PASSED", "JUDGEMENT CALL", "FAILED"])
        for c in parsed:
            if c["result"] in ("PASSED", "FAILED"):
                self.assertTrue(c["retrieved"] and c["method"] != "none")
            else:
                self.assertTrue(c["settle"])
        self.assertTrue(all(na_check.PROV.match("[" + c["prov"] + "]") for c in parsed))
        self.assertEqual([c["id"] for c in parsed], ["C5", "C6", "C7"])


if __name__ == "__main__":
    unittest.main()
