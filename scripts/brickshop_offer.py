"""Read BRICKshop's scoped microdata and corroborate it with visible EUR/stock."""
import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlsplit

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def clean(value):
    return ' '.join(value.split())

class ProductPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.products=[];self.barcodes=[];self.names=[];self.eur=[]
        self.online=[];self.main_text=[];self.wait_online=False

    def handle_starttag(self,tag,attrs):
        a=dict(attrs);parent=self.stack[-1] if self.stack else {}
        state=dict(parent,tag=tag)
        if tag=='table' and a.get('id')=='productDetailsTable':
            state['main']=True;self.barcodes.append(a.get('data-barcode'))
        if state.get('main'):
            kind=a.get('itemtype','').rsplit('/',1)[-1] if 'itemscope' in a else None
            if kind=='Product':
                node={'offers':[]};self.products.append(node);state['product']=node;state.pop('offer',None)
            elif kind=='Offer' and state.get('product') is not None:
                node={};state['product']['offers'].append(node);state['offer']=node
            prop=a.get('itemprop');value=a.get('content',a.get('href'))
            node=state.get('offer',state.get('product'))
            if prop and value is not None and node is not None and kind is None:
                node.setdefault(prop,[]).append(value)
            if tag=='h1':
                chunks=[];self.names.append(chunks);state['name_chunks']=chunks
            if tag=='option' and a.get('value')=='EUR' and 'selected' in a:
                chunks=[];self.eur.append(chunks);state['eur_chunks']=chunks
            if tag=='a' and self.wait_online and {'textInStock','textNotInStock'}&set(a.get('class','').split()):
                chunks=[];self.online.append(chunks);state['online_chunks']=chunks;self.wait_online=False
        if tag not in VOID:self.stack.append(state)

    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag:
                del self.stack[i:];break

    def handle_data(self,data):
        if not self.stack or not self.stack[-1].get('main'):return
        state=self.stack[-1];self.main_text.append(data)
        if clean(data)=='Online status':self.wait_online=True
        for key in ('name_chunks','eur_chunks','online_chunks'):
            if key in state:state[key].append(data)


def one(node,key):
    values=set(node.get(key,[]))
    if len(values)!=1:raise ValueError('Missing or ambiguous product field: '+key)
    return next(iter(values))


def parse(raw,target):
    url=urlsplit(target['url'])
    if url.scheme!='https' or url.hostname!='www.brickshop.eu':raise ValueError('Unexpected retailer host')
    page=ProductPage();page.feed(raw.decode('utf-8'))
    if len(page.products)!=1 or len(page.barcodes)!=1 or len(page.names)!=1:
        raise ValueError('Expected one main product')
    product=page.products[0];name=one(product,'name');sku=one(product,'sku');brand=one(product,'brand')
    gtin=one(product,'gtin13')
    if sku!=target['sku'] or brand.upper()!='LEGO' or not re.fullmatch(r'\d{13}',gtin) or page.barcodes[0]!=gtin:
        raise ValueError('Retail product identity not corroborated')
    if clean(''.join(page.names[0]))!=name or not re.search(r'\bLEGO\b',name,re.I) or not re.search(r'(?<!\d)'+re.escape(sku)+r'(?!\d)',name):
        raise ValueError('Main heading disagrees with product identity')
    if len(product['offers'])!=1:raise ValueError('Expected one product offer')
    offer=product['offers'][0];price=one(offer,'price');currency=one(offer,'priceCurrency')
    if one(offer,'url')!=target['url'] or currency!='EUR':raise ValueError('Unexpected offer URL or currency')
    try:
        amount=Decimal(price)
        if not amount.is_finite() or amount<=0:raise ValueError('Invalid price')
        visible={Decimal(clean(''.join(v)).replace('€','').strip().replace('.','').replace(',','.')) for v in page.eur}
    except InvalidOperation:raise ValueError('Invalid visible EUR price')
    if visible!={amount}:raise ValueError('Visible price disagrees with product microdata')
    if len(page.online)!=1:raise ValueError('Missing or ambiguous online availability')
    stock=clean(''.join(page.online[0])).upper().rstrip('!');machine=one(offer,'availability').rsplit('/',1)[-1]
    states={'COMING SOON':('COMING_SOON','OutOfStock'),'IN STOCK':('IN_STOCK','InStock'),
            'NOT IN STOCK':('OUT_OF_STOCK','OutOfStock')}
    if stock not in states or states[stock][1]!=machine:raise ValueError('Uncorroborated online availability')
    dates=set(re.findall(r'Available by:\s*(\d{1,2} [A-Za-z]+ \d{4})',clean(' '.join(page.main_text))))
    release=dt.datetime.strptime(next(iter(dates)),'%d %B %Y').date().isoformat() if len(dates)==1 else None
    return {'price':str(amount),'currency':'EUR','availability':states[stock][0],'product_name':name,
            'evidence':{'product':{'name':name,'sku':sku,'brand':brand,'gtin13':gtin},
                        'offer':{k:one(offer,k) for k in ('price','priceCurrency','url','availability')},
                        'visible_online_status':stock,'retailer_announced_available_date':release,
                        'shipping_to_france_verified':False,'checkout_verified':False,'seller_reliability_reviewed':False}}
