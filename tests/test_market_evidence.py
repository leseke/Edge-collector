import unittest
from intelligence.market_evidence import market_snapshot
P={"category":"TCG","brand":"Pokémon","reference":"SV-001","edition":"Normal","language":"FR","region":"France","condition":"NEW","sealed":True}
def row(id,kind,price,product=P):
 return {"observation_id":id,"product":product,"kind":kind,"price_eur":price,"quantity":1,
 "observed_at":"2026-10-25T08:00:00Z","source_url":"https://example.org/market",
 "source_record_id":id}
class MarketEvidenceTests(unittest.TestCase):
 def test_sold_never_mixed_with_ask(self):
  d=market_snapshot([row("a","SOLD",80),row("b","SOLD",100),row("c","ASK",300)],"2026-10-25T10:00:00Z")
  self.assertEqual(d["sold_median_eur"],"90")
  self.assertEqual(d["asking_median_eur"],"300")
  self.assertEqual(d["liquidity_status"],"NOT_ESTIMABLE")
  self.assertFalse(d["execution_authorized"])
 def test_no_sales_means_no_sales_median(self):
  self.assertIsNone(market_snapshot([row("a","ASK",300)],"2026-10-25T10:00:00Z")["sold_median_eur"])
 def test_unknown_product_rejected(self):
  with self.assertRaises(ValueError):market_snapshot([row("a","SOLD",100,{**P,"edition":"unknown"})],"2026-10-25T10:00:00Z")
 def test_different_languages_not_merged(self):
  with self.assertRaises(ValueError):market_snapshot([row("a","SOLD",100),row("b","SOLD",110,{**P,"language":"EN"})],"2026-10-25T10:00:00Z")
 def test_future_data_excluded(self):
  self.assertEqual(market_snapshot([row("a","SOLD",100)],"2026-10-24T10:00:00Z")["sold_records"],0)
 def test_duplicate_market_record_rejected(self):
  x=row("a","SOLD",100);y={**x,"observation_id":"b"}
  with self.assertRaises(ValueError):market_snapshot([x,y],"2026-10-25T10:00:00Z")
 def test_reject_bool_and_nan(self):
  for val in (True,float("nan")):
   with self.assertRaises(ValueError):market_snapshot([row("a","SOLD",val)],"2026-10-25T10:00:00Z")
if __name__=="__main__":unittest.main()
