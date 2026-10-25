"""Read-only intake of an official economics research RSS feed.

Feed summaries are discovery abstracts, not full papers or validated lessons.
No executable source content, no paid APIs, no policy changes.
"""
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from tools.stage_learning_sources import stage_sources

FEEDS=(("fed-feds","https://www.federalreserve.gov/feeds/feds.xml","www.federalreserve.gov"),)
MAX_FEED_BYTES=1_000_000
def parse_feed(data,*,observed_at,source=FEEDS[0],limit=20):
    if not isinstance(data,bytes) or len(data)>MAX_FEED_BYTES:raise ValueError("feed too large")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():raise ValueError("unsafe XML")
    if type(limit) is not int or not 1<=limit<=50:raise ValueError("invalid limit")
    root=ET.fromstring(data)
    result=[];fail=[]
    for i,item in enumerate(root.findall(".//item")[:limit]):
        try:
            title=(item.findtext("title") or "").strip()
            link=(item.findtext("link") or "").strip()
            date=(item.findtext("pubDate") or "").strip()
            description=unescape(re.sub("<[^>]+>"," ",item.findtext("description") or ""))
            description=re.sub(r"\s+"," ",description).strip()
            host=urlsplit(link)
            if host.scheme!="https" or host.hostname!=source[2]:raise ValueError("source host mismatch")
            if not date:raise ValueError("missing actual publication date")
            published=parsedate_to_datetime(date)
            if published.tzinfo is None:raise ValueError("publication timezone missing")
            if len(description)<50:raise ValueError("short abstract, cannot treat as study")
            result.append({"source_url":link,"published_at":published.isoformat(),
                           "observed_at":observed_at,"title":title,"text":description})
        except (ValueError,TypeError,OverflowError) as ex:
            fail.append({"index":i,"error_type":type(ex).__name__})
    return result,fail
def collect_official_learning(output,*,fetcher=None,observed_at=None):
    observed_at=observed_at or datetime.now(timezone.utc).isoformat()
    if fetcher is None:
        def fetcher(url):
            with urlopen(Request(url,headers={"User-Agent":"EDGE-Learning/0.1"}),timeout=12) as r:
                if r.geturl()!=url:raise ValueError("redirect prohibited")
                data=r.read(MAX_FEED_BYTES+1)
            return data
    docs=[];failure=[]
    for source in FEEDS:
        try:
            incoming,issues=parse_feed(fetcher(source[1]),observed_at=observed_at,source=source)
            docs.extend(incoming)
            failure.extend({"feed":source[0],**x} for x in issues)
        except Exception as ex:
            failure.append({"feed":source[0],"error_type":type(ex).__name__})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    batch=output.with_name("learning_source_batch.json")
    batch.write_text(json.dumps({"schema":"edge.learning.source_batch.v1","documents":docs},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    review=stage_sources(batch,output)
    review["feed_failures"]=failure
    review["collection_status"]="OK" if review["source_count"] and not failure and not review["failures"] else ("PARTIAL" if review["source_count"] else "FAILED")
    output.write_text(json.dumps(review,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return review
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    a=p.parse_args()
    result=collect_official_learning(a.output)
    print(result["collection_status"],result["source_count"])
    if result["collection_status"]=="FAILED":raise SystemExit(1)
