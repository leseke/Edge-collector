import unittest

from discovery.engine import process


class DiscoveryTests(unittest.TestCase):
    def observation(self, **overrides):
        obj = {
            "source": "example_market",
            "source_url": "https://example.com/listing/1",
            "observed_at": "2026-10-18T09:00:00+00:00",
            "name": "Demo collectible",
            "external_id": "listing-1",
            "price_eur": 35,
        }
        obj.update(overrides)
        return obj

    def test_candidate_never_allocates(self):
        out = process([self.observation()], "pilot", "2026-10-18T09:00:00Z")
        # Contrat revise (V2) : un lot de candidats n'est pas une posture CASH.
        self.assertEqual(out["investment_decision"], "NOT_EVALUATED")
        self.assertEqual(out["allocation_eur"], 0)
        self.assertEqual(out["candidates"][0]["allocation_eur"], [0, 0])
        self.assertEqual(out["candidates"][0]["decision"], "NO_DATA")
        self.assertEqual(out["candidates"][0]["evidence_type"], "ASKING_PRICE")

    def test_deduplicate_by_source_and_external_id(self):
        out = process([self.observation(), self.observation(price_eur=25)], "pilot")
        self.assertEqual((out["summary"]["candidates"], out["summary"]["duplicates"]), (1, 1))

    def test_invalid_records_fail_closed(self):
        bad = [self.observation(price_eur=-1), self.observation(source_url="http://bad.example"),
               self.observation(observed_at="2026-10-18"), {"name": "incomplete"}, "bad"]
        out = process(bad, "pilot")
        self.assertEqual(out["summary"]["rejected"], 5)
        self.assertEqual(out["status"], "ALL_REJECTED")
        self.assertNotEqual(out["investment_decision"], "CASH")
        self.assertEqual(out["candidates"], [])

    def test_evidence_type_preserved_and_validated(self):
        out = process([self.observation(evidence_type="SOLD"),
                       self.observation(external_id="2", evidence_type="RUMOR")], "pilot")
        self.assertEqual(out["candidates"][0]["evidence_type"], "SOLD")
        self.assertEqual(out["rejected"][0]["reason"], "invalid:evidence_type")

    def test_used_and_non_product_rejected(self):
        out = process([self.observation(name="LEGO 75639 occasion"),
                       self.observation(external_id="2", name="Notice LEGO 75639")], "pilot")
        self.assertEqual([r["reason"] for r in out["rejected"]],
                         ["rejected:used_condition", "rejected:identity"])

    def test_foreign_currency_requires_fx(self):
        out = process([self.observation(currency_src="USD")], "pilot")
        self.assertEqual(out["rejected"][0]["reason"], "invalid:currency_without_fx")

    def test_empty_input_is_no_data(self):
        self.assertEqual(process([], "pilot")["status"], "NO_DATA")

    def test_invalid_collection_type(self):
        with self.assertRaises(ValueError):
            process({}, "pilot")


if __name__ == "__main__":
    unittest.main()
