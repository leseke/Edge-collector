import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('commercial', Path(__file__).parents[1] / 'scripts/commercial_history.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CommercialTests(unittest.TestCase):
    def html(self, **updates):
        offer = {'@type': 'Offer', 'price': '349.99', 'priceCurrency': 'EUR', 'availability': 'https://schema.org/InStock'}
        offer.update(updates)
        return ('<script type="application/ld+json">' + json.dumps({'@type': 'Product', 'sku': '10365', 'offers': offer}) + '</script>').encode()

    def row(self, **updates):
        row = dict(id='lego', product_id='lego_10365', seller='LEGO', url='https://www.lego.com/product',
                   status='OK', currency='EUR', price='349.99', availability='IN_STOCK',
                   observed_at='2026-10-29T10:00:00+00:00', body_sha256='abc')
        row.update(updates)
        return row

    def events(self, old, new):
        return m.compare({'observed_at': '2026-10-29T12:00:00+00:00', 'observations': [new]},
                         [{'observed_at': '2026-10-29T10:00:00+00:00', 'observations': [old]}])

    def test_offer(self):
        self.assertEqual(m.parse_offer(self.html(), {'sku': '10365'})['price'], '349.99')

    def test_identity(self):
        with self.assertRaises(ValueError):
            m.parse_offer(self.html(), {'sku': '1036'})

    def test_invalid_prices(self):
        for price in ('NaN', 'Infinity', '-1', '0', 'bad'):
            with self.assertRaises(ValueError):
                m.parse_offer(self.html(price=price), {'sku': '10365'})

    def test_wrong_currency(self):
        with self.assertRaises(ValueError):
            m.parse_offer(self.html(priceCurrency='USD'), {'sku': '10365'})

    def test_wrong_seller(self):
        with self.assertRaises(ValueError):
            m.parse_offer(self.html(seller={'name': 'Marketplace seller'}),
                          {'sku': '10365', 'expected_offer_seller': 'LDLC'})

    def test_right_seller(self):
        row = m.parse_offer(self.html(seller={'name': 'LDLC'}),
                            {'sku': '10365', 'expected_offer_seller': 'LDLC'})
        self.assertEqual(row['price'], '349.99')

    def test_seller_change_is_new_scope(self):
        self.assertEqual(self.events(self.row(), self.row(price='299.99', seller='Other')), [])

    def test_comparison_unchanged_is_available(self):
        row = self.row()
        report = m.comparison_report({'observed_at': '2026-10-29T12:00:00+00:00', 'observations': [row]},
                                     [{'observed_at': '2026-10-29T10:00:00+00:00', 'observations': [row]}])
        self.assertTrue(report['observations'][0]['comparison_available'])
        self.assertEqual(report['observations'][0]['price_change_pct'], '0')

    def test_failed_comparison(self):
        report = m.comparison_report({'observed_at': '2026-10-29', 'observations': [self.row(status='FAILED')]}, [])
        self.assertEqual(report['observations'][0]['reason'], 'CURRENT_COLLECTION_FAILED')

    def test_comparison_baseline(self):
        report = m.comparison_report({'observed_at': '2026-10-29', 'observations': [self.row()]}, [])
        self.assertEqual(report['observations'][0]['reason'], 'BASELINE_ONLY')

    def test_failure_gap_uses_previous_success(self):
        history = [{'observed_at': '2026-10-29T10:00:00+00:00', 'observations': [self.row()]},
                   {'observed_at': '2026-10-29T11:00:00+00:00', 'observations': [self.row(status='FAILED')]}]
        events = m.compare({'observed_at': '2026-10-29T12:00:00+00:00', 'observations': [self.row(price='299.99')]}, history)
        self.assertEqual(events[0]['previous_snapshot_at'], '2026-10-29T10:00:00+00:00')

    def test_ambiguous_offers(self):
        with self.assertRaises(ValueError):
            m.parse_offer(self.html() + self.html(), {'sku': '10365'})

    def test_price_event(self):
        events = self.events(self.row(), self.row(price='299.99'))
        self.assertEqual(events[0]['kind'], 'PRICE_CHANGE')
        self.assertFalse(events[0]['buy_signal'])

    def test_indicative_price_event(self):
        events = self.events(self.row(price_kind='AGGREGATED_INDICATIVE_LOW'),
                             self.row(price='99.99', price_kind='AGGREGATED_INDICATIVE_LOW'))
        self.assertEqual(events[0]['kind'], 'INDICATIVE_PRICE_CHANGE')

    def test_metric_scope(self):
        self.assertEqual(self.events(self.row(price_kind='ASKING_PRICE'),
                                    self.row(price='99.99', price_kind='AGGREGATED_INDICATIVE_LOW')), [])

    def test_restock(self):
        self.assertEqual(self.events(self.row(availability='OUT_OF_STOCK'), self.row())[0]['kind'], 'RESTOCK_OBSERVED')

    def test_failure_not_stockout(self):
        self.assertEqual(self.events(self.row(), self.row(status='FAILED', availability='UNKNOWN')), [])

    def test_unknown_not_restock(self):
        self.assertEqual(self.events(self.row(availability='UNKNOWN'), self.row()), [])

    def test_baseline_empty(self):
        self.assertEqual(m.compare({'observed_at': '2026-10-29', 'observations': [self.row()]}, []), [])

    def test_unchanged(self):
        self.assertEqual(self.events(self.row(), self.row()), [])

    def test_changed_scope(self):
        self.assertEqual(self.events(self.row(), self.row(url='https://other.example')), [])



class TransportTests(unittest.TestCase):
    def test_transport_timeout_gets_one_bounded_retry(self):
        from unittest.mock import patch, MagicMock
        response=MagicMock();response.status=200;response.url='https://example.com/p'
        response.read.return_value=b'real body'
        response.__enter__.return_value=response
        row={}
        with patch.object(m,'urlopen',side_effect=[TimeoutError('timed out'),response]) as opened:
            self.assertEqual(m.read_response(m.Request(response.url),row),b'real body')
        self.assertEqual([c.kwargs['timeout'] for c in opened.call_args_list],[25,15])
        self.assertEqual([a['status'] for a in row['request_attempts']],['FAILED','OK'])
        self.assertEqual(row['observed_at'],row['request_attempts'][1]['finished_at'])

    def test_http_403_is_not_retried(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        with patch.object(m,'urlopen',side_effect=HTTPError('https://example.com',403,'Forbidden',None,None)) as opened:
            with self.assertRaises(HTTPError):m.read_response(m.Request('https://example.com'),{})
        self.assertEqual(opened.call_count,1)

    def test_retry_stops_after_second_timeout(self):
        from unittest.mock import patch
        with patch.object(m,'urlopen',side_effect=TimeoutError('timed out')) as opened:
            with self.assertRaises(TimeoutError):m.read_response(m.Request('https://example.com'),{})
        self.assertEqual(opened.call_count,2)


if __name__ == '__main__':
    unittest.main()
