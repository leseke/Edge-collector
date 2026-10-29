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

    def test_ambiguous_offers(self):
        with self.assertRaises(ValueError):
            m.parse_offer(self.html() + self.html(), {'sku': '10365'})

    def test_price_event(self):
        events = self.events(self.row(), self.row(price='299.99'))
        self.assertEqual(events[0]['kind'], 'PRICE_CHANGE')
        self.assertFalse(events[0]['buy_signal'])

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


if __name__ == '__main__':
    unittest.main()
