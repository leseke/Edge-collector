import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from intelligence.market_monitor import SnapshotMonitor, validate_url, visible_text

URL = "https://www.pokemon.cn/tcg"
PAGE_A = b"<html><script>secret</script><body>Pokemon China official trading card news and tournaments publication one.</body></html>"
PAGE_B = b"<html><body>Pokemon China official trading card news and tournaments publication two.</body></html>"

class TestMarketMonitor(unittest.TestCase):
    def test_two_dates_and_change(self):
        with tempfile.TemporaryDirectory() as d:
            pages = iter((PAGE_A, PAGE_B))
            m = SnapshotMonitor(d, lambda url: next(pages))
            t = datetime(2026, 10, 20, tzinfo=timezone.utc)
            a = m.capture(URL, t, allow_network=True)
            b = m.capture(URL, t + timedelta(days=1), allow_network=True)
            self.assertEqual((a['status'], b['status']), ('first_observation', 'changed'))
            self.assertNotEqual(a['sha256'], b['sha256'])
            self.assertEqual(b['previous_sha256'], a['sha256'])
            self.assertEqual(len(m.history(URL)), 2)
            self.assertEqual(b['data_type'], 'page_content_not_sales')
    def test_same_content_not_fabricated_change(self):
        with tempfile.TemporaryDirectory() as d:
            m = SnapshotMonitor(d, lambda url: PAGE_A)
            t = datetime(2026, 10, 20, tzinfo=timezone.utc)
            m.capture(URL, t, True)
            self.assertEqual(m.capture(URL, t + timedelta(days=1), True)['status'], 'unchanged')
    def test_disabled_blocks_before_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            m = SnapshotMonitor(d, lambda _: self.fail('called transport'))
            with self.assertRaises(PermissionError):
                m.capture(URL, datetime.now(timezone.utc))
            self.assertFalse(m.history())
    def test_reject_domain_and_userinfo_and_query(self):
        for u in ('http://www.pokemon.cn/tcg', 'https://evil.example/tcg',
                  'https://www.pokemon.cn.evil.test/tcg', 'https://evil@www.pokemon.cn/tcg',
                  'https://www.pokemon.cn/tcg?token=x'):
            with self.subTest(url=u), self.assertRaises(ValueError):
                validate_url(u)
    def test_reject_empty_and_overlarge(self):
        with self.assertRaises(ValueError):
            visible_text(b'x' * 350001)
        with tempfile.TemporaryDirectory() as d:
            m = SnapshotMonitor(d, lambda _: b'<html></html>')
            with self.assertRaises(ValueError):
                m.capture(URL, datetime.now(timezone.utc), True)
            self.assertEqual(m.history(), [])
    def test_ledger_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            m = SnapshotMonitor(d, lambda _: PAGE_A)
            t = datetime(2026, 10, 20, tzinfo=timezone.utc)
            m.capture(URL, t, True)
            with open(m.ledger, 'rb') as f:
                before = f.read()
            m.capture(URL, t + timedelta(days=1), True)
            with open(m.ledger, 'rb') as f:
                self.assertTrue(f.read().startswith(before))
    def test_no_price_history_claim(self):
        with tempfile.TemporaryDirectory() as d:
            row = SnapshotMonitor(d, lambda _: PAGE_A).capture(URL, datetime.now(timezone.utc), True)
            self.assertNotIn('price', row)
            self.assertNotIn('sold_transaction', row)

if __name__ == '__main__':
    unittest.main()
