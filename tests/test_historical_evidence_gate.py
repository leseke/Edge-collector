import unittest
from intelligence.historical_evidence_gate import classify_source, qualify_case

CUT="2022-09-21T23:59:59+08:00"
BASE={"source_id":"pokemon2022","url":"https://www.pokemon.cn/tcg/product/16380.html",
      "published_at":"2022-09-21T00:00:00+08:00",
      "retrieved_at":"2026-10-22T12:00:00Z","role":"pre_signal",
      "support":"publisher_date_only"}
class HistoricalEvidenceGateTests(unittest.TestCase):
    def test_publisher_date_alone_is_not_capture(self):
        self.assertEqual(classify_source(BASE,CUT)["reason"],"NO_CONTEMPORANEOUS_CAPTURE")
    def test_later_publication_rejected(self):
        item={**BASE,"published_at":"2022-09-28T00:00:00+08:00"}
        self.assertEqual(classify_source(item,CUT)["reason"],"PUBLISHED_AFTER_CUTOFF")
    def test_later_capture_rejected(self):
        item={**BASE,"support":"contemporaneous_archive","captured_at":"2026-10-22T12:00:00Z","capture_url":"https://example.org/capture"}
        self.assertEqual(classify_source(item,CUT)["reason"],"CAPTURE_AFTER_CUTOFF")
    def test_capture_requires_provenance(self):
        item={**BASE,"support":"contemporaneous_archive","captured_at":"2022-09-21T16:00:00+08:00"}
        self.assertEqual(classify_source(item,CUT)["reason"],"MISSING_CAPTURE_PROVENANCE")
    def test_valid_capture(self):
        item={**BASE,"support":"first_party_capture_log","captured_at":"2022-09-21T16:00:00+08:00","capture_url":"https://example.org/verifiable-log"}
        self.assertTrue(classify_source(item,CUT)["eligible"])
    def test_future_capture_not_masqueraded(self):
        item={**BASE,"support":"contemporaneous_archive","captured_at":"2022-09-22T00:00:00+08:00","capture_url":"https://example.org/capture"}
        self.assertFalse(classify_source(item,CUT)["eligible"])
    def test_no_ready_claim_without_capture(self):
        self.assertFalse(qualify_case({"case_id":"pk","cutoff":CUT,"sources":[BASE]})["replay_ready"])
    def test_no_financial_signal(self):
        r=qualify_case({"case_id":"pk","cutoff":CUT,"sources":[BASE]})
        self.assertEqual(r["financial_signal"],"NOT_EVALUATED")
    def test_duplicate_source_rejected(self):
        with self.assertRaises(ValueError):
            qualify_case({"case_id":"pk","cutoff":CUT,"sources":[BASE,BASE]})
if __name__ == "__main__": unittest.main()
