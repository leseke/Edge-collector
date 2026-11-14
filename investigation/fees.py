"""Calculs financiers deterministes et auditables (aucun appel externe)."""
import json
import math
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "fee_profiles.json")


def load_fee_profiles(path=_DEFAULT_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["profiles"]


def net_resale(sale_price, profile):
    """Montant encaisse net apres commission, paiement, frais fixes,
    expedition et emballage."""
    pct = (profile["commission_pct"] + profile["payment_pct"]) / 100.0
    return sale_price * (1 - pct) - profile["fixed_fee_eur"] - profile["shipping_out_eur"] - profile["packaging_eur"]


def annualize(roi, days):
    """Rendement annualise compose. None si non defini."""
    if roi is None or days is None or days <= 0 or roi <= -1:
        return None
    return (1 + roi) ** (365.0 / days) - 1


def economics(buy_price, buy_shipping, sale_price, profile, holding_days):
    if buy_price is None or sale_price is None:
        return None
    cost = buy_price + (buy_shipping or 0)
    if cost <= 0:
        return None
    net = net_resale(sale_price, profile)
    profit = net - cost
    roi = profit / cost
    ann = annualize(roi, holding_days)
    return {
        "buy_total_eur": round(cost, 2),
        "sale_price_eur": round(sale_price, 2),
        "net_resale_eur": round(net, 2),
        "fees_eur": round(sale_price - net, 2),
        "net_profit_eur": round(profit, 2),
        "net_roi_pct": round(roi * 100, 1),
        "holding_days": holding_days,
        "annualized_pct": round(ann * 100, 1) if ann is not None and math.isfinite(ann) else None,
    }
