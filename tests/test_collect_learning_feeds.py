import tempfile
import unittest
from pathlib import Path
from tools.collect_learning_feeds import parse_feed,collect_official_learning

DATE="2026-10-25T08:00:00Z"
FEED=b"""<?xml version="1.0"?><rss><channel><item><title>Economics and liquidity research</title><link>https://www.federalreserve.gov/econres/feds/some-paper.htm</link><pubDate>Sat, 24 Oct 2026 08:00:00 GMT</pubDate><description>This finance research explores pricing, markets and liquidity, with methodology and a detailed discussion of evidence and limitations in a research context.</description></item></channel></rss>"""
class FeedTests(unittest.TestCase):
 def test_official_feed_becomes_unreviewed_research(self):
  with tempfile.TemporaryDirectory() as d:
   result=collect_official_learning(Path(d)/"review.json",fetcher=lambda _:FEED,observed_at=DATE)
   self.assertEqual(result["source_count"],1)
   self.assertEqual(result["collection_status"],"OK")
   self.assertEqual(result["lessons_adopted"],0)
   self.assertFalse(result["learning_applied"])
 def test_reject_untrusted_links(self):
  modified=FEED.replace(b"https://www.federalreserve.gov/econres/",b"https://example.org/econres/")
  docs,fail=parse_feed(modified,observed_at=DATE)
  self.assertEqual(len(docs),0)
  self.assertEqual(len(fail),1)
 def test_future_dates_not_inferred(self):
  modified=FEED.replace(b"24 Oct 2026",b"26 Oct 2026")
  with tempfile.TemporaryDirectory() as d:
   result=collect_official_learning(Path(d)/"review.json",fetcher=lambda _:modified,observed_at=DATE)
   self.assertEqual(result["source_count"],0)
   self.assertEqual(result["collection_status"],"FAILED")
 def test_xml_entities_blocked(self):
  with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><rss/>',observed_at=DATE)
 def test_feed_size_is_hard_limit(self):
  with self.assertRaises(ValueError):parse_feed(b"A"*1000001,observed_at=DATE)
if __name__=="__main__":unittest.main()
