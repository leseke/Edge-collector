"""Real SQLite regression for the read-only Leboncoin offers feed.

Synthetic data only; this test never accesses Outlook or remote D1.
"""
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SQL="""WITH ranked AS (
  SELECT o.listing_id,o.observed_at,o.source_url,o.title,
    o.price_cents,o.location,m.search_name,m.advertised_count,
    m.extracted_count,COUNT(*) OVER (PARTITION BY o.listing_id) AS alert_hits,
    ROW_NUMBER() OVER (
      PARTITION BY o.listing_id
      ORDER BY o.observed_at DESC,o.message_id DESC
    ) AS rn
  FROM lbc_listing_observations o
  JOIN lbc_alert_messages m ON m.message_id=o.message_id
)
SELECT listing_id,observed_at,source_url,title,price_cents,location,
  search_name,advertised_count,extracted_count,alert_hits,
  first_observed_at,first_price_cents
FROM ranked WHERE rn=1 ORDER BY observed_at DESC,listing_id DESC LIMIT 50"""

class OffersViewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript((ROOT/"migrations"/"003_leboncoin_outlook.sql").read_text(encoding="utf-8"))
    def tearDown(self):
        self.db.close()
    def add(self,message_id,listing_id,price,received,advertised,extracted):
        self.db.execute("""INSERT INTO lbc_alert_messages
          (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
          VALUES (?,?,?,?,?,?,?)""",(message_id,received,"Pokémon 30 ans",advertised,extracted,
          int(advertised>extracted),received))
        self.db.execute("""INSERT INTO lbc_listing_observations
          (message_id,listing_id,observed_at,source_url,title,price_cents,currency,
           location,category_hint,price_kind,availability,evidence)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",(message_id,listing_id,received,
          "https://www.leboncoin.fr/vi/"+listing_id.split(":")[1]+".htm",
          "Carte Pokémon",price,"EUR","Paris","Pokémon 30 ans","LISTING",
          "UNVERIFIED","EMAIL_EXCERPT"))
    def test_same_listing_in_two_emails_is_one_card_with_history_count(self):
        self.add("m1","leboncoin:3313155234",15000,"2026-11-19T05:21:31Z",990,1)
        self.add("m2","leboncoin:3313155234",14000,"2026-11-20T05:11:45Z",1286,1)
        self.db.commit()
        rows=self.db.execute(SQL).fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],"leboncoin:3313155234")
        self.assertEqual(rows[0][4],14000)
        self.assertEqual(rows[0][7],1286)
        self.assertEqual(rows[0][9],2)
        self.assertEqual(rows[0][10],"2026-11-19T05:21:31Z")
        self.assertEqual(rows[0][11],15000)
    def test_distinct_listings_do_not_collapse(self):
        self.add("m1","leboncoin:3313155234",15000,"2026-11-19T05:21:31Z",990,1)
        self.add("m2","leboncoin:3313155235",20000,"2026-11-20T05:11:45Z",1286,1)
        self.db.commit()
        rows=self.db.execute(SQL).fetchall()
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0][0],"leboncoin:3313155235")
        self.assertTrue(all(r[9]==1 for r in rows))
    def test_empty_ledger_is_not_a_synthetic_offer(self):
        self.assertEqual(self.db.execute(SQL).fetchall(),[])

if __name__=="__main__":
    unittest.main()
