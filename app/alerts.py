"""Threshold alert engine. Color is used only when a rule fires."""

from __future__ import annotations

from app.models import Alert, AlertSource, Quote, Tone
from app.timeutil import now_ist


DEFAULT_RULES = {
    "price_breakout": {"CRYPTO:BTC": 80000.0, "NSE:NIFTY50": 25000.0, "MCX:GOLD": 75000.0},
    "abs_pct": {
        "CRYPTO:BTC": 2.5,
        "CRYPTO:ETH": 3.0,
        "CRYPTO:SOL": 5.0,
        "CRYPTO:XRP": 5.0,
        "CRYPTO:BNB": 4.0,
        "MCX:CRUDE": 2.0,
        "MCX:GOLD": 1.2,
        "NSE:NIFTY50": 1.0,
        "NSE:BANKNIFTY": 1.2,
        "FX:DXY": 0.6,
        "default": 2.0,
    },
    "vix_pct": 6.0,
}


def _tone_for_move(change_pct: float, bullish_is_good: bool = True) -> Tone:
    up = change_pct > 0
    if bullish_is_good:
        return "positive" if up else "negative"
    return "negative" if up else "positive"


def evaluate_quotes(quotes: list[Quote], rules: dict | None = None) -> list[Alert]:
    rules = rules or DEFAULT_RULES
    by_canon = {q.canonical: q for q in quotes}
    alerts: list[Alert] = []
    ts = now_ist()

    for q in quotes:
        breakout = rules["price_breakout"].get(q.canonical)
        if breakout and q.ltp >= breakout:
            alerts.append(
                Alert(
                    id=f"px-break-{q.canonical}",
                    tone="positive" if q.market == "crypto" else "info",
                    severity="high",
                    category="PRICE",
                    title=f"{q.symbol} crossed above {breakout:,.0f}",
                    detail=f"Price alert · {q.ltp:,.2f} {q.currency}",
                    asset=q.symbol,
                    market=q.market,
                    detected_at=ts,
                    importance="high",
                    confidence="high" if q.source_type != "mock" else "medium",
                    highlight_symbol=q.symbol,
                    sources=[AlertSource(source=q.source, source_type=q.source_type, original_url=q.source_url)],
                    why={
                        "primary": f"{q.symbol} last {q.ltp:,.2f} {q.currency} is at or above the {breakout:,.0f} breakout level.",
                        "trigger": f"This PRICE rule fires when {q.symbol} last traded price ≥ {breakout:,.0f}. Last print {q.ltp:,.2f} {q.currency} from {q.source}.",
                        "secondary": "A breakout is a level event, not a guarantee of follow-through. Check volume and related assets.",
                        "technical": f"price_breakout[{q.canonical}] = {breakout:g}",
                        "impact": "Listed risk assets can lag or fade if the break is not accepted.",
                        "confidence": "high",
                    },
                )
            )

        thresh = rules["abs_pct"].get(q.canonical, rules["abs_pct"]["default"])
        if abs(q.change_pct) >= thresh:
            alerts.append(
                Alert(
                    id=f"px-move-{q.canonical}",
                    tone=_tone_for_move(q.change_pct, bullish_is_good=q.market != "fx"),
                    severity="high" if abs(q.change_pct) >= thresh * 1.5 else "medium",
                    category="PRICE",
                    title=f"{q.name} moved {q.change_pct:+.2f}%",
                    detail="Percentage-move rule fired",
                    asset=q.symbol,
                    market=q.market,
                    detected_at=ts,
                    importance="high",
                    confidence="high",
                    highlight_symbol=q.symbol,
                    related_assets=[],
                    sources=[AlertSource(source=q.source, source_type=q.source_type, original_url=q.source_url)],
                    why={
                        "primary": f"{q.symbol} moved {q.change_pct:+.2f}% vs a {thresh:g}% absolute-move threshold.",
                        "trigger": f"This PRICE rule fires when |day change| ≥ {thresh:g}%. Tape: {q.change_pct:+.2f}% on {q.source}.",
                        "secondary": "A large day move can be news, positioning, or a gap. Confirm with the Impact block before treating it as a regime shift.",
                        "technical": f"abs_pct[{q.canonical}] = {thresh:g}%",
                        "impact": "Related contracts/indices often catch up with a delay.",
                        "confidence": "high",
                    },
                )
            )

        if q.canonical == "NSE:INDIAVIX" and abs(q.change_pct) >= rules["vix_pct"]:
            alerts.append(
                Alert(
                    id="vol-india-vix",
                    tone="uncertain",
                    severity="high",
                    category="VOLATILITY",
                    title=f"NIFTY India VIX {q.change_pct:+.1f}%",
                    detail="Volatility alert",
                    asset="INDIA VIX",
                    market="nse",
                    detected_at=ts,
                    importance="high",
                    confidence="high",
                    highlight_symbol="NIFTY 50",
                    sources=[AlertSource(source=q.source, source_type=q.source_type)],
                    why={
                        "primary": f"India VIX is {q.ltp:.2f}, a {q.change_pct:+.1f}% move vs the {rules['vix_pct']:g}% volatility rule.",
                        "trigger": f"This VOLATILITY rule fires when |India VIX day change| ≥ {rules['vix_pct']:g}%.",
                        "secondary": "Higher VIX usually means wider Nifty/Bank Nifty ranges and more expensive options.",
                        "technical": "vix_pct rule on NSE:INDIAVIX",
                        "impact": "Treat Nifty, Bank Nifty, FinNifty and Bankex as higher-risk until VIX cools.",
                        "confidence": "high",
                    },
                )
            )

    btc = by_canon.get("CRYPTO:BTC")
    gold = by_canon.get("MCX:GOLD")
    dxy = by_canon.get("FX:DXY")
    crude = by_canon.get("MCX:CRUDE")
    nifty = by_canon.get("NSE:NIFTY50")
    if btc and gold and dxy and crude and nifty:
        risk_off_like = btc.change_pct > 2 and gold.change_pct > 1 and dxy.change_pct < -0.4 and crude.change_pct > 1.5
        if risk_off_like or (
            btc.change_pct > 3 and gold.change_pct > 1 and dxy.change_pct < -0.5
        ):
            alerts.insert(
                0,
                Alert(
                    id="regime-cross-asset",
                    tone="negative",
                    severity="high",
                    category="REGIME",
                    title="Risk regime changed",
                    detail="Cross-asset move: crypto, gold, dollar and crude moved together.",
                    asset="MARKET",
                    market="cross",
                    detected_at=ts,
                    importance="high",
                    confidence="medium",
                    related_assets=["BTC", "GOLD", "DXY", "CRUDE", "NIFTY"],
                    sources=[
                        AlertSource(source=btc.source, source_type=btc.source_type),
                        AlertSource(source=gold.source, source_type=gold.source_type),
                        AlertSource(source=dxy.source, source_type=dxy.source_type),
                    ],
                    why={
                        "primary": "Several risk/haven assets breached move thresholds in the same window.",
                        "secondary": "Potentially relevant to crypto, gold, Indian equities and INR.",
                        "technical": "Explicit cross-asset coincidence rule, not an LLM opinion.",
                        "confidence": "medium",
                    },
                ),
            )

    # Deduplicate by id, keep first (regime first)
    seen = set()
    unique = []
    for a in alerts:
        if a.id in seen:
            continue
        seen.add(a.id)
        unique.append(a)
    return unique[:12]
