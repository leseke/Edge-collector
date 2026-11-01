import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from brickshop_offer import parse

URL='https://www.brickshop.eu/lego/lego-icons/lego-11388-venetian-neighbourhood.html'
TARGET=dict(sku='11388',url=URL)
# Minimal structure matching the real 2026-11-01 page, not invented market data.
HTML=f'''<table id="productDetailsTable" data-barcode="5702018069868"><tr><td>
<span itemscope itemtype="http://schema.org/Product">
<meta itemprop="name" content="LEGO 11388 Venetian Neighbourhood"/>
<meta itemprop="sku" content="11388"/><meta itemprop="brand" content="LEGO"/>
<meta itemprop="gtin13" content="5702018069868"/>
<span itemprop="offers" itemscope itemtype="http://schema.org/Offer">
<meta itemprop="price" content="599.99"/><meta itemprop="priceCurrency" content="EUR"/>
<meta itemprop="url" content="{URL}"/>
<link itemprop="availability" href="https://schema.org/OutOfStock"/></span></span>
<h1>LEGO 11388 Venetian Neighbourhood</h1>
<select><option value="EUR" selected>€ 599,99</option></select>
<span>Online status</span><span><a class="modal textNotInStock">COMING SOON!</a>
<span>Available by: 4 November 2026</span></span>
<span>Store</span><a class="modal textNotInStock">Not in stock</a>
</td></tr></table>'''

class BrickshopTests(unittest.TestCase):
    def test_scoped_identity_price_and_coming_soon(self):
        r=parse(HTML.encode(),TARGET)
        self.assertEqual(r['price'],'599.99');self.assertEqual(r['availability'],'COMING_SOON')
        self.assertEqual(r['evidence']['retailer_announced_available_date'],'2026-11-04')
        self.assertFalse(r['evidence']['shipping_to_france_verified'])
        self.assertFalse(r['evidence']['checkout_verified'])

    def test_metadata_and_visible_price_disagreement_rejected(self):
        with self.assertRaises(ValueError):parse(HTML.replace('€ 599,99','€ 499,99').encode(),TARGET)

    def test_stock_disagreement_rejected(self):
        with self.assertRaises(ValueError):parse(HTML.replace('schema.org/OutOfStock','schema.org/InStock').encode(),TARGET)

    def test_heading_brand_barcode_and_sku_are_all_required(self):
        for old,new in [('content="11388"','content="11383"'),('content="LEGO"','content="Other"'),
                        ('data-barcode="5702018069868"','data-barcode="5702018069869"'),
                        ('<h1>LEGO 11388 Venetian Neighbourhood','<h1>LEGO 11383 Other')]:
            with self.assertRaises(ValueError):parse(HTML.replace(old,new).encode(),TARGET)

    def test_recommendation_outside_main_product_cannot_supply_missing_price(self):
        h=HTML.replace('<meta itemprop="price" content="599.99"/>','')
        h+='<meta itemprop="price" content="599.99"/>'
        with self.assertRaises(ValueError):parse(h.encode(),TARGET)

    def test_foreign_currency_and_host_rejected(self):
        with self.assertRaises(ValueError):parse(HTML.replace('content="EUR"','content="USD"').encode(),TARGET)
        with self.assertRaises(ValueError):parse(HTML.encode(),dict(TARGET,url='https://other.example/product'))

    def test_actual_release_requires_both_machine_and_online_status(self):
        h=HTML.replace('schema.org/OutOfStock','schema.org/InStock').replace('COMING SOON!','IN STOCK!')
        self.assertEqual(parse(h.encode(),TARGET)['availability'],'IN_STOCK')
        h=HTML.replace('COMING SOON!','NOT IN STOCK')
        self.assertEqual(parse(h.encode(),TARGET)['availability'],'OUT_OF_STOCK')

    def test_duplicate_main_product_and_unknown_stock_fail_closed(self):
        with self.assertRaises(ValueError):parse((HTML+HTML).encode(),TARGET)
        with self.assertRaises(ValueError):parse(HTML.replace('COMING SOON!','CHECK AVAILABILITY').encode(),TARGET)

if __name__=='__main__':unittest.main()
