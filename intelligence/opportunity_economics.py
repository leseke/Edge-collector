"""Scenario arithmetic only; never a BUY recommendation or estimated probability."""
from decimal import Decimal, InvalidOperation

def money(value):
    if isinstance(value,bool) or not isinstance(value,(int,float,str,Decimal)):
        raise ValueError("invalid monetary input")
    try: d=Decimal(str(value))
    except InvalidOperation: raise ValueError("invalid monetary input")
    if not d.is_finite() or d<0:raise ValueError("non-finite or negative money")
    return d

def evaluate_scenario(*, buy_price, shipping_in, sell_price, platform_fee, shipping_out, taxes, other_costs, sold_evidence_count=None):
    fields={k:money(v) for k,v in locals().items() if k not in {"sold_evidence_count"}}
    if sold_evidence_count is not None and (type(sold_evidence_count) is not int or sold_evidence_count<0):
        raise ValueError("invalid sold evidence count")
    cost=fields["buy_price"]+fields["shipping_in"]+fields["platform_fee"]+fields["shipping_out"]+fields["taxes"]+fields["other_costs"]
    pnl=fields["sell_price"]-cost
    invested=fields["buy_price"]+fields["shipping_in"]
    roi=(pnl/invested*100) if invested else None
    return {"schema":"edge.opportunity.scenario.v1",
            "net_profit_eur":str(pnl.quantize(Decimal("0.01"))),
            "net_roi_pct":str(roi.quantize(Decimal("0.01"))) if roi is not None else None,
            "sold_evidence_count":sold_evidence_count,
            "liquidity_status":"UNKNOWN" if sold_evidence_count is None else "UNVALIDATED",
            "sell_price_basis":"USER_SCENARIO_NOT_OBSERVED",
            "status":"SCENARIO_ONLY",
            "decision":"NOT_EVALUATED",
            "execution_authorized":False}
