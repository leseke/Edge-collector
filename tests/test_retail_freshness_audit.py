import tempfile
import unittest
from pathlib import Path
from intelligence.retail_radar import normalize_offer
from intelligence.retail_observation_history import append_retail_observation
from intelligence.retail_freshness_audit import audit_retail_freshness

def row(at,seller="Seller",state="IN_STOCK"):
 return normalize_offer(source_id="shop",source_domain="example.org",
   listing_url="https://example.org/item",actual_seller=seller,
   product_key="lego-10365",vertical="LEGO",offer_state=state,
   observed_at=at,price_eur="149.00")

class FreshnessAuditTests(unittest.TestCase):
 def test_stale_claim_not_stock(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"observations.jsonl"
   append_retail_observation(p,row("2026-10-25T12:00:00Z"))
   r=audit_retail_freshness(p,as_of="2026-10-28T12:00:00Z")
   self.assertEqual(r["stale_offers"],1)
   self.assertEqual(r["offers"][0]["offer_state"],"UNKNOWN_STALE")
   self.assertFalse(r["offers"][0]["stock_verified"])
 def test_fresh_claim_remains_unverified(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"observations.jsonl"
   append_retail_observation(p,row("2026-10-28T10:00:00Z"))
   r=audit_retail_freshness(p,as_of="2026-10-28T12:00:00Z")
   self.assertEqual(r["stale_offers"],0)
   self.assertEqual(r["offers"][0]["freshness"],"RECENT_SOURCE_CLAIM")
   self.assertFalse(r["offers"][0]["source_authenticated"])
 def test_future_rows_not_visible(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"observations.jsonl"
   append_retail_observation(p,row("2026-10-28T14:00:00Z"))
   r=audit_retail_freshness(p,as_of="2026-10-28T12:00:00Z")
   self.assertEqual(r["tracked_offers"],0)
   self.assertEqual(r["future_records_excluded"],1)
 def test_seller_variants_isolated(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"observations.jsonl"
   append_retail_observation(p,row("2026-10-28T10:00:00Z"))
   append_retail_observation(p,row("2026-10-28T11:00:00Z",seller="Other"))
   r=audit_retail_freshness(p,as_of="2026-10-28T12:00:00Z")
   self.assertEqual(r["tracked_offers"],2)
 def test_invalid_limit_denied(self):
  with self.assertRaises(ValueError):
   audit_retail_freshness("absent.jsonl",as_of="2026-10-28T12:00:00Z",stale_after_hours=0)
if __name__=="__main__":unittest.main()
