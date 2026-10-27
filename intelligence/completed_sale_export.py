"""Adapter for licensed/authorized completed-sale exports; no scraping or network.

This validates a provider receipt against the captured bytes and exact identity.
Provider authenticity and settlement remain unverified without independent audit.
"""
import hashlib
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
from intelligence.prediction_journal import _dt

def validate_completed_sale_export(*,provider,transaction_id,product_key,record_type,price_eur,
                                   sold_at,observed_at,source_url,snapshot_bytes,expected_sha256):
    if provider not in ("AUTHORIZED_MARKETPLACE_EXPORT","MERCHANT_SETTLEMENT_EXPORT"):
        raise ValueError("unsupported provider class")
    if record_type!="COMPLETED_SALE":raise ValueError("not a completed-sale record")
    if not isinstance(transaction_id,str) or not 4<=len(transaction_id)<=180:
        raise ValueError("transaction identity required")
    if not isinstance(product_key,str) or not product_key.strip():raise ValueError("exact product identity required")
    url=urlsplit(source_url)
    if url.scheme!="https" or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError("invalid evidence URL")
    if _dt(sold_at)>_dt(observed_at):raise ValueError("sale after observation")
    if not isinstance(snapshot_bytes,bytes) or not 20<=len(snapshot_bytes)<=200000:
        raise ValueError("invalid source evidence size")
    actual=hashlib.sha256(snapshot_bytes).hexdigest()
    if expected_sha256!=actual:raise ValueError("source bytes do not match")
    try:price=Decimal(str(price_eur))
    except (TypeError,ValueError,InvalidOperation):raise ValueError("invalid price")
    if not price.is_finite() or not 0<price<Decimal("1000000000"):raise ValueError("invalid price")
    return {"schema":"edge.learning.completed_sale_export.v1","provider_class":provider,
            "transaction_id":transaction_id,"product_key":product_key,"price_eur":str(price),
            "sold_at":sold_at,"observed_at":observed_at,"source_url":source_url,
            "source_sha256":actual,"record_type":"COMPLETED_SALE",
            "export_consistent":True,"provider_authenticated":False,
            "settlement_independently_verified":False,"eligible_for_learning":False,
            "purchase_authorized":False}
