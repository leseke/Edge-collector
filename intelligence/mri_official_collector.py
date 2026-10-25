"""MRI-004: narrow free public-source polling, research-only, fail-closed.

Only two fixed official news pages, no untrusted URLs, no API keys or paid calls.
Publication date is NOT inferred; observation is the real UTC fetch time.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = (
    ("pokemon-official", "https://www.pokemon.com/fr/actualites/decouvrez-tous-les-produits-du-jcc-pokemon-qui-sortiront-en-octobre-2026", "Pokémon", "Pokémon TCG", "publication"),
    ("lego-official", "https://www.lego.com/en-us/aboutus/newsroom", "LEGO", "LEGO", "newsroom_update"),
)
MAX_BYTES = 250000
class Extract(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden=0; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style"): self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
    def handle_data(self,data):
        if not self.hidden and data.strip():self.parts.append(data.strip())

def observe(source, html, observed_at):
    sid,url,actor,subject,action=source
    if not isinstance(html,str) or len(html.encode("utf-8"))>MAX_BYTES:raise ValueError("invalid page")
    p=Extract();p.feed(html)
    summary=re.sub(r"\s+"," "," ".join(p.parts))[:900]
    if len(summary)<20:raise ValueError("insufficient public text")
    digest=hashlib.sha256(summary.encode("utf-8")).hexdigest()[:20]
    return {"id":f"{sid}:{digest}","subject":subject,"actor":actor,"action":action,
      "occurred_at":observed_at,"observed_at":observed_at,"source_url":url,
      "summary":summary}

def collect(output, fetcher=None, now=None):
    from intelligence.mri_observation_ingest import create_research_digest
    now=now or datetime.now(timezone.utc).isoformat()
    if fetcher is None:
        def fetcher(url):
            req=Request(url,headers={"User-Agent":"EDGE-MRI-research/0.1 (public official newsroom)"})
            with urlopen(req,timeout=12) as response:
                if response.geturl()!=url:raise ValueError("redirected URL not accepted")
                data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES:raise ValueError("response too large")
            return data.decode("utf-8",errors="replace")
    observations=[];failures=[]
    for source in SOURCES:
        try:
            observations.append(observe(source,fetcher(source[1]),now))
        except Exception as exc:
            failures.append({"source_id":source[0],"state":"FAILED","error_type":type(exc).__name__})
    digest=create_research_digest(observations)
    digest["source_failures"]=failures
    digest["collection_status"]="OK" if observations and not failures else ("PARTIAL" if observations else "FAILED")
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(digest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return digest

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True)
    args=parser.parse_args()
    d=collect(args.output)
    print(d["collection_status"],d["count"])
    if not d["count"]:raise SystemExit(1)
