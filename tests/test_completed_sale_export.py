import hashlib
import unittest
from intelligence.completed_sale_export import validate_completed_sale_export
B=b"Official transaction export sample fixture bytes, not a real receipt"
P=dict(provider="AUTHORIZED_MARKETPLACE_EXPORT",transaction_id="sale-1234",product_key="pokemon-sealed-fr",
record_type="COMPLETED_SALE",price_eur="140.00",sold_at="2026-10-24T10:00:00Z",
observed_at="2026-10-25T10:00:00Z",source_url="https://example.org/export/1234",
snapshot_bytes=B,expected_sha256=hashlib.sha256(B).hexdigest())
class CompletedSaleExportTests(unittest.TestCase):
 def test_valid_format_is_not_verified_sale(self):
  r=validate_completed_sale_export(**P)
  self.assertTrue(r["export_consistent"])
  self.assertFalse(r["eligible_for_learning"])
  self.assertFalse(r["provider_authenticated"])
 def test_asking_price_denied(self):
  with self.assertRaises(ValueError):validate_completed_sale_export(**{**P,"record_type":"ASK"})
 def test_tampered_snapshot_denied(self):
  with self.assertRaises(ValueError):validate_completed_sale_export(**{**P,"snapshot_bytes":B+b"!"})
 def test_future_sale_denied(self):
  with self.assertRaises(ValueError):validate_completed_sale_export(**{**P,"sold_at":"2026-10-26T10:00:00Z"})
 def test_bad_price_denied(self):
  with self.assertRaises(ValueError):validate_completed_sale_export(**{**P,"price_eur":"NaN"})
if __name__=="__main__":unittest.main()
