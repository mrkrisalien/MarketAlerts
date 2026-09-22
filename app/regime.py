from app.models import Quote


def classify_regime(quotes: list[Quote]) -> tuple[str, str, str]:
    """Measurable regime labels. Not an LLM opinion."""
    by = {q.canonical: q for q in quotes}
    dxy = by.get("FX:DXY")
    us10y = by.get("RATES:US10Y")
    vix = by.get("NSE:INDIAVIX")
    btc = by.get("CRYPTO:BTC")
    nifty = by.get("NSE:NIFTY50")

    risk_score = 0
    if dxy and dxy.change_pct > 0.25:
        risk_score += 1
    if us10y and us10y.change_abs > 0:
        risk_score += 1
    if vix and vix.change_pct > 4:
        risk_score += 1
    if btc and btc.change_pct < -2:
        risk_score += 1
    if nifty and nifty.change_pct < -0.8:
        risk_score += 1

    if risk_score >= 3:
        return "ELEVATED", "WATCH", "Risk-Off"
    if risk_score == 2:
        return "WATCH", "WATCH", "Mixed"
    return "NORMAL", "NORMAL", "Risk-On" if (btc and btc.change_pct > 0 and nifty and nifty.change_pct >= 0) else "Neutral"
