import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import announcement_history as m

SOURCE = dict(id='brickset', adapter='rss', role='SPECIALIST_MEDIA', article_host='brickset.com')
TARGETS = [dict(product_id='lego_10365', sku='10365')]


def rss(title='LEGO 10365 revealed', link='https://brickset.com/article/1'):
    return f'<rss><channel><item><title>{title}</title><link>{link}</link><pubDate>Thu, 29 Oct 2026 12:00:00 +0000</pubDate></item></channel></rss>'.encode()


class AnnouncementTests(unittest.TestCase):
    def test_rss_identity_stable_on_title_change(self):
        a, b = m.parse(rss(), SOURCE)[0], m.parse(rss('Updated LEGO 10365'), SOURCE)[0]
        self.assertEqual(a['id'], b['id'])
        self.assertNotEqual(a['content_sha256'], b['content_sha256'])

    def test_wrong_host_rejected(self):
        with self.assertRaises(ValueError):
            m.parse(rss(link='https://elsewhere.example/1'), SOURCE)

    def test_invalid_xml_rejected(self):
        with self.assertRaises(ValueError):
            m.parse(b'<html>captcha</html>', SOURCE)

    def test_dtd_rejected(self):
        with self.assertRaises(ValueError):
            m.parse(b'<!DOCTYPE rss><rss><channel/></rss>', SOURCE)

    def test_naive_timestamp_unknown(self):
        self.assertIsNone(m.timestamp('2026-10-29T12:00:00'))

    def test_baseline_not_new_alert(self):
        row = m.register(m.parse(rss(), SOURCE), [], '2026-10-29T13:00:00+00:00', False, TARGETS)[0]
        self.assertTrue(row['imported_baseline'])
        self.assertFalse(row['new_since_previous_capture'])
        self.assertEqual(row['product_ids'], ['lego_10365'])

    def test_repeat_preserves_first_seen(self):
        old = m.register(m.parse(rss(), SOURCE), [], '2026-10-29T13:00:00+00:00', False, TARGETS)
        rows = m.register(m.parse(rss(), SOURCE), [{'publications': old}], '2026-10-30T13:00:00+00:00', True, TARGETS)
        self.assertEqual(rows[0]['first_observed_at'], old[0]['first_observed_at'])
        self.assertFalse(rows[0]['new_since_previous_capture'])

    def test_exact_sku_avoids_substring(self):
        rows = m.register(m.parse(rss('LEGO 103650'), SOURCE), [], '2026-10-29T13:00:00+00:00', False, TARGETS)
        self.assertEqual(rows[0]['product_ids'], [])

    def test_lego_card(self):
        raw = b'<a class="c-card c-card--article" href="/en-us/aboutus/news/2026/test"><time datetime="2026-10-29T12:00:00Z"></time><h2>LEGO 10365</h2><p>Launch</p></a>'
        rows = m.parse(raw, dict(id='lego', adapter='lego_newsroom', role='MANUFACTURER', article_host='lego.com'))
        self.assertEqual(rows[0]['source_role'], 'MANUFACTURER')

    def measurements(self, times):
        event = m.register(m.parse(rss(), SOURCE), [], '2026-10-29T13:00:00+00:00', False, TARGETS)[0]
        rows = [dict(id='retail', product_id='lego_10365', url='https://retailer.example/1', seller='Retailer',
                     currency='EUR', price_kind='ASKING_PRICE', status='OK', observed_at=time,
                     price=price, availability='IN_STOCK', body_sha256='hash') for time, price in times]
        return m.reactions([event], [{'observations': rows}])['measurements'][0]

    def test_no_baseline_no_invented_return(self):
        result = self.measurements([('2026-10-30T12:00:00+00:00', '120')])
        self.assertEqual(result['status'], 'NO_PRE_EVENT_BASELINE')
        self.assertNotIn('asking_price_change_pct', result['windows'][0])

    def test_24h_window(self):
        result = self.measurements([('2026-10-29T11:00:00+00:00', '100'), ('2026-10-30T13:00:00+00:00', '120')])
        self.assertEqual(result['windows'][0]['status'], 'MEASURED')
        self.assertEqual(result['windows'][0]['asking_price_change_pct'], '20.0')
        self.assertFalse(result['causality_proven'])

    def test_early_observation_not_24h_result(self):
        result = self.measurements([('2026-10-29T11:00:00+00:00', '100'), ('2026-10-29T13:00:00+00:00', '120')])
        self.assertEqual(result['windows'][0]['status'], 'AWAITING_OBSERVATION')

    def test_stale_baseline_excluded(self):
        result = self.measurements([('2026-10-27T11:00:00+00:00', '100'), ('2026-10-30T13:00:00+00:00', '120')])
        self.assertEqual(result['status'], 'NO_PRE_EVENT_BASELINE')

    def test_missed_window(self):
        result = self.measurements([('2026-10-29T11:00:00+00:00', '100'), ('2026-10-31T13:00:00+00:00', '120')])
        self.assertEqual(result['windows'][0]['status'], 'MISSING_WINDOW_OBSERVATION')

    def test_future_publication_is_not_reaction(self):
        event = m.register(m.parse(rss(), SOURCE), [], '2026-10-29T11:00:00+00:00', False, TARGETS)[0]
        self.assertTrue(event['future_dated'])
        self.assertEqual(m.reactions([event], [])['measurements'][0]['status'], 'INVALID_PUBLICATION_TIME')


if __name__ == '__main__':
    unittest.main()
