"""MRI evidence segmentation with full coverage and source offsets.

No summarization, network access, model calls, or silent truncation.
"""
import hashlib
from intelligence.mri_official_collector import extract_visible_text, MAX_BYTES

def segment_page(source_id, source_url, html, max_chars=1600):
    if not isinstance(html,str) or len(html.encode("utf-8"))>MAX_BYTES:
        raise ValueError("oversized or invalid source")
    if not isinstance(max_chars,int) or max_chars<256 or max_chars>10000:
        raise ValueError("invalid chunk size")
    text=extract_visible_text(html)
    if len(text)<20:raise ValueError("insufficient source")
    digest=hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks=[]
    for start in range(0,len(text),max_chars):
        end=min(start+max_chars,len(text))
        part=text[start:end]
        chunks.append({"index":len(chunks),"start":start,"end":end,
                       "sha256":hashlib.sha256(part.encode("utf-8")).hexdigest(),
                       "text":part})
    assert "".join(c["text"] for c in chunks)==text
    return {"schema":"edge.mri.evidence_segments.v1","source_id":source_id,
            "source_url":source_url,"source_sha256":digest,
            "total_characters":len(text),"complete":True,"segments":chunks}
