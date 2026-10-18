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
        self.assertEqual(out["investment_decision"], "CASH")
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
        self.assertEqual(out["investment_decision"], "CASH")
        self.assertEqual(out["candidates"], [])

    def test_invalid_collection_type(self):
        with self.assertRaises(ValueError):
            process({}, "pilot")


if __name__ == "__main__":
    unittest.main()
