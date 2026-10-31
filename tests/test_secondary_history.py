import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import secondary_history as m


def card(title='LEGO 40889 Build Paint Play sealed', price='EUR 39.50', extra=''):
    return ('<ul><li class="s-card"><a href="https://www.ebay.ie/itm/198752609812?tracking=1">'
            '<div class="s-card__title"><span>' + title + '</span></div></a>'
            '<span class="s-card__price">' + price + '</span>'
            '<div>+EUR 12.00 postage from Italy</div>' + extra + '</li></ul>').encode()


class SecondaryTests(unittest.TestCase):
    def test_card_is_asking_price_not_sale(self):
        row = m.parse_cards(card(), '40889')[0]
        self.assertEqual(row['asking_price_eur'], '39.50')
        self.assertFalse(row['completed_sale_verified'])
        self.assertFalse(row['individual_listing_verified'])
        self.assertEqual(row['url'], 'https://www.ebay.ie/itm/198752609812')

    def test_search_shipping_not_french_delivery(self):
        row = m.parse_cards(card(), '40889')[0]
        self.assertEqual(row['displayed_shipping_eur'], '12.00')
        self.assertFalse(row['france_delivery_verified'])
        self.assertIsNone(row['delivered_price_fr_eur'])

    def test_wrong_brand_and_reference(self):
        self.assertEqual(m.parse_cards(card('Car part 40889'), '40889'), [])
        self.assertEqual(m.parse_cards(card('LEGO 408890'), '40889'), [])

    def test_mixed_bundle_excluded(self):
        row = m.parse_cards(card('LEGO 11388 + 40898 bundle sealed'), '11388')[0]
        self.assertIn('BUNDLE_OR_MULTIPLE_REFERENCES', row['exclusions'])

    def test_incomplete_set_excluded(self):
        row = m.parse_cards(card('LEGO 40889 box only'), '40889')[0]
        self.assertIn('INCOMPLETE_OR_ACCESSORY', row['exclusions'])

    def test_multilingual_display_case_excluded(self):
        row = m.parse_cards(card('TECA IN PLEXIGLASS ACRILICO SHOWCASE PER SET LEGO 11388'), '11388')[0]
        self.assertIn('INCOMPLETE_OR_ACCESSORY', row['exclusions'])

    def test_minifigure_is_not_complete_parent_set(self):
        row = m.parse_cards(card('LEGO Icons Venetian Glassblower Minifigure Set 11388 PREORDER'), '11388')[0]
        self.assertIn('MINIFIGURE_COMPONENT_NOT_COMPLETE_SET', row['exclusions'])

    def test_piano_element_is_not_complete_parent_set(self):
        row = m.parse_cards(card('LEGO New 3D Printed Piano Element Set 11388'), '11388')[0]
        self.assertIn('INDIVIDUAL_ELEMENT_NOT_COMPLETE_SET', row['exclusions'])

    def test_presale_not_stock(self):
        row = m.parse_cards(card('LEGO 40889 PRESALE'), '40889')[0]
        self.assertEqual(row['fulfilment'], 'PRESALE_CLAIM')

    def test_multiple_prices_not_arbitrarily_selected(self):
        self.assertEqual(m.parse_cards(card(price='EUR 30.00 to EUR 39.50'), '40889'), [])

    def test_wrong_currency_not_converted(self):
        self.assertEqual(m.parse_cards(card(price='$39.50'), '40889'), [])

    def test_captcha_is_failure_not_empty_market(self):
        with self.assertRaises(ValueError):
            m.parse_cards(b'<html>captcha</html>', '40889')



if __name__ == '__main__':
    unittest.main()
