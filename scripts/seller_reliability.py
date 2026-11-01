"""Evidence-based merchant gate, independent of price extraction or discounts."""
import datetime as dt
from urllib.parse import urlsplit
from announcement_history import timestamp

REQUIRED_CHECKS=('LEGAL_IDENTITY','OFFICIAL_DOMAIN','TERMS_AND_RETURNS','RECENT_REPUTATION')
MAX_REVIEW_AGE=dt.timedelta(days=30)


def origin(url):
    try:
        p=urlsplit(url)
        return 'https://'+p.netloc.lower() if p.scheme=='https' and p.hostname and not p.username and not p.password else None
    except (TypeError,ValueError):return None


def review_seller(seller,url,registry,at):
    current=timestamp(at);site=origin(url)
    result={'schema':'edge.seller.reliability.v1','status':'UNVERIFIED','seller':seller,'site_origin':site,
            'reviewed_at':None,'valid_until':None,'eligible_for_economic_use':False,
            'blockers':['SELLER_RELIABILITY_UNVERIFIED']}
    if not isinstance(registry,dict) or registry.get('schema')!='edge.seller.review_registry.v1' or not isinstance(registry.get('reviews'),list):return result
    reviews=[r for r in registry['reviews'] if isinstance(r,dict) and r.get('seller')==seller and origin(r.get('site_origin'))==site and site]
    # Conflicting/duplicate reviews cannot silently grant eligibility.
    if len(reviews)!=1 or current is None:return result
    r=reviews[0];reviewed=timestamp(r.get('reviewed_at'));expires=timestamp(r.get('valid_until'))
    if not reviewed or not expires or reviewed>current or expires<=reviewed or expires>reviewed+MAX_REVIEW_AGE:return result
    result.update(reviewed_at=r['reviewed_at'],valid_until=r['valid_until'])
    if expires<current:
        result.update(status='EXPIRED',blockers=['SELLER_RELIABILITY_REVIEW_EXPIRED']);return result
    checks=r.get('checks',{})
    if not all(isinstance(checks.get(c),dict) and checks[c].get('result')=='PASS'
               and origin(checks[c].get('evidence_url')) and isinstance(checks[c].get('evidence_sha256'),str)
               and len(checks[c]['evidence_sha256'])==64 and all(ch in '0123456789abcdef' for ch in checks[c]['evidence_sha256'])
               for c in REQUIRED_CHECKS):return result
    if r.get('status')!='VERIFIED':return result
    result.update(status='VERIFIED',eligible_for_economic_use=True,blockers=[],checks=checks)
    return result


def purchase_gate(sources,at):
    current=timestamp(at)
    def reviewed(s):
        r=s.get('seller_reliability',{});a=timestamp(r.get('reviewed_at'));b=timestamp(r.get('valid_until'))
        return bool(r.get('schema')=='edge.seller.reliability.v1' and r.get('status')=='VERIFIED'
                    and r.get('eligible_for_economic_use') is True and a and b and current and a<=current<=b
                    and a<b<=a+MAX_REVIEW_AGE and r.get('site_origin')==origin(s.get('source_url')))
    eligible=[s for s in sources if s.get('usable_current_quote') and s.get('availability')=='IN_STOCK' and reviewed(s)]
    blockers=[]
    if not eligible:blockers.append('NO_IN_STOCK_OFFER_FROM_A_REVIEWED_SELLER')
    if any(s.get('usable_current_quote') and not reviewed(s) for s in sources):
        blockers.append('UNVERIFIED_SELLER_OFFERS_EXCLUDED_FROM_ECONOMIC_COMPARISONS')
    return {'status':'BLOCKED' if not eligible else 'SELLER_CHECKS_PASSED_OTHER_REQUIREMENTS_PENDING',
            'seller_eligible_offer_count':len(eligible),'blockers':blockers,
            'buy_signal':False,'purchase_authorized':False,
            'financial_decision':'NOT_ESTABLISHED'}
