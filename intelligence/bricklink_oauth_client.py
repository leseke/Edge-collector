"""BrickLink read-only OAuth 1.0 price guide client.

Credentials are passed at runtime, never logged or persisted. BrickLink may
restrict calls to registered static IPs; no CI live network calls.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from intelligence.bricklink_sold_aggregate import parse_bricklink_sold_priceguide

BASE="https://api.bricklink.com/api/store/v1"
def _enc(s):return quote(str(s),safe="~-._")
def build_signed_request(*,set_no,condition,currency,consumer_key,consumer_secret,token,token_secret,timestamp=None,nonce=None):
    if not isinstance(set_no,str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,40}",set_no):
        raise ValueError("invalid set number")
    if condition not in ("N","U") or currency not in ("EUR","USD","GBP"):raise ValueError("unsupported variant")
    credentials=(consumer_key,consumer_secret,token,token_secret)
    if any(not isinstance(v,str) or not v for v in credentials):raise ValueError("missing runtime credentials")
    stamp=str(int(time.time()) if timestamp is None else timestamp)
    rand=secrets.token_hex(16) if nonce is None else nonce
    if not re.fullmatch(r"[0-9]{9,14}",stamp) or not isinstance(rand,str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}",rand):
        raise ValueError("invalid OAuth freshness parameters")
    url=BASE+"/items/SET/"+_enc(set_no)+"/price"
    params={"guide_type":"sold","new_or_used":condition,"currency_code":currency}
    auth={"oauth_consumer_key":consumer_key,"oauth_token":token,
          "oauth_signature_method":"HMAC-SHA1","oauth_timestamp":stamp,
          "oauth_nonce":rand,"oauth_version":"1.0"}
    query="&".join(f"{_enc(k)}={_enc(v)}" for k,v in sorted(params.items()))
    normalized="&".join(f"{_enc(k)}={_enc(v)}" for k,v in sorted({**params,**auth}.items()))
    base="GET&"+_enc(url)+"&"+_enc(normalized)
    key=_enc(consumer_secret)+"&"+_enc(token_secret)
    sig=base64.b64encode(hmac.new(key.encode(),base.encode(),hashlib.sha1).digest()).decode()
    auth["oauth_signature"]=sig
    header='OAuth realm="", '+", ".join(f'{_enc(k)}="{_enc(v)}"' for k,v in sorted(auth.items()))
    return {"url":url+"?"+query,"headers":{"Authorization":header,"Accept":"application/json","User-Agent":"EDGE-Research/1.0"}}

def fetch_sold_aggregate(*,set_no,condition="N",currency="EUR",observed_at,credentials,transport=None):
    if not isinstance(credentials,dict) or set(credentials)!={"consumer_key","consumer_secret","token","token_secret"}:
        raise ValueError("runtime credential keys required")
    request=build_signed_request(set_no=set_no,condition=condition,currency=currency,**credentials)
    if transport is None:
        def transport(request):
            # Restrict network destination and response size. No redirects.
            from urllib.request import build_opener,HTTPHandler,HTTPSHandler,HTTPRedirectHandler
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs):raise ValueError("redirect denied")
            opener=build_opener(HTTPHandler(),HTTPSHandler(),NoRedirect())
            with opener.open(Request(request["url"],headers=request["headers"]),timeout=12) as resp:
                if resp.status!=200:raise ValueError("HTTP status not successful")
                raw=resp.read(200001)
            if len(raw)>200000:raise ValueError("response too large")
            return json.loads(raw)
    payload=transport(request)
    if not isinstance(payload,dict) or not isinstance(payload.get("meta"),dict) or payload["meta"].get("code") not in (200,"200"):
        raise ValueError("BrickLink API reported failure or malformed envelope")
    output=parse_bricklink_sold_priceguide(payload,set_no=set_no,condition=condition,currency=currency,observed_at=observed_at)
    output["authenticated_request_sent"]=True
    output["provider_response_authenticated_independently"]=False
    return output
