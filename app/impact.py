"""Map news, data, moves, outcomes and geopolitics to an Impact block."""

from __future__ import annotations

from app.models import ImpactAssessment, ImpactLeg, Quote

PLAYBOOKS: list[dict] = [
    {
        "id": "war",
        "trigger": "war",
        "certainty": "uncertain",
        "severity": "high",
        "keys": (
            "war", "missile", "invasion", "airstrike", "air strike", "attack on",
            "conflict", "troops", "blockade", "hormuz", "strait", "sanctions",
            "ukraine", "gaza", "israel", "iran", "taiwan", "hezbollah", "nato",
            "escalation", "military",
        ),
        "headline": "Geopolitical stress → risk-off + energy/gold bid",
        "detail": "Conflict headlines historically lift crude and gold, pressure risk assets (Nifty, BTC). Path is uncertain until de-escalation is confirmed.",
        "legs": [("CRUDE", "up", "supply-risk premium"), ("GOLD", "up", "haven"), ("NIFTY 50", "down", "risk-off"), ("BTC", "down", "risk-off")],
    },
    {
        "id": "peace",
        "trigger": "outcome",
        "certainty": "uncertain",
        "severity": "medium",
        "keys": ("ceasefire", "truce", "peace deal", "de-escalat", "hostilities halt"),
        "headline": "De-escalation → unwind of war premium",
        "detail": "If the headline is real, crude/gold war premium can fade and risk assets can recover. Fake-news risk keeps this uncertain.",
        "legs": [("CRUDE", "down", "premium fade"), ("GOLD", "down", "haven fade"), ("NIFTY 50", "up", "risk-on")],
    },
    {
        "id": "inflation",
        "trigger": "data",
        "certainty": "uncertain",
        "severity": "high",
        "keys": ("cpi", "inflation", "pce", "ppi", "price index"),
        "headline": "Inflation data → USD, gold, BTC, Nifty",
        "detail": "Hot print: DXY/yields ↑ gold/BTC/Nifty offered. Cool print: the reverse. Until the number prints, treat as uncertain.",
        "legs": [("DXY", "watch", "hot ↑ / cool ↓"), ("GOLD", "watch", "hot ↓ / cool ↑"), ("BTC", "watch", "same as gold"), ("NIFTY 50", "watch", "hot pressure")],
    },
    {
        "id": "jobs",
        "trigger": "data",
        "certainty": "uncertain",
        "severity": "high",
        "keys": ("nfp", "nonfarm", "payroll", "unemployment", "jobless", "jobs report"),
        "headline": "Labour data → Fed path → USD and havens",
        "detail": "Strong jobs: DXY ↑ gold/BTC ↓. Weak jobs: rate-cut odds ↑ gold/BTC ↑.",
        "legs": [("DXY", "watch", "strong ↑"), ("US 10Y", "watch", "strong ↑"), ("GOLD", "watch", "strong ↓"), ("BTC", "watch", "strong ↓")],
    },
    {
        "id": "cb",
        "trigger": "event",
        "certainty": "uncertain",
        "severity": "high",
        "keys": ("fomc", "fed ", "federal reserve", "rate hike", "rate cut", "rbi", "mpc", "ecb", "boj"),
        "headline": "Central-bank event → rates, FX, gold, equities",
        "detail": "Hawkish: USD/yields ↑ gold/crypto offered. Dovish: gold/silver/crypto bid; Nifty financials can catch a bid.",
        "legs": [("DXY", "watch", "hawkish ↑"), ("GOLD", "watch", "hawkish ↓"), ("BANKNIFTY", "watch", "dovish +"), ("BTC", "watch", "hawkish ↓")],
    },
    {
        "id": "oil",
        "trigger": "data",
        "certainty": "uncertain",
        "severity": "high",
        "keys": ("crude", "oil inventory", "eia", "opec", "brent", "wti", "petroleum"),
        "headline": "Oil shock → India inflation/CAD and energy tape",
        "detail": "Bullish oil: crude ↑ India import-cost/inflation watch, Nifty mixed (energy + / index drag). Bearish oil is friendlier for India.",
        "legs": [("CRUDE", "watch", "inventory/OPEC"), ("NIFTY 50", "watch", "inflation channel"), ("GOLD", "watch", "sometimes hedges")],
    },
    {
        "id": "flows",
        "trigger": "data",
        "certainty": "certain",
        "severity": "medium",
        "keys": ("fii", "dii", "foreign portfolio", "institutional flow"),
        "headline": "FII/DII flows → Nifty/Banknifty direction",
        "detail": "Persistent FII selling typically pressures Nifty and INR. DII can offset but not always on the day.",
        "legs": [("NIFTY 50", "watch", "FII sell ↓"), ("BANKNIFTY", "watch", "same"), ("DXY", "watch", "INR side")],
    },
    {
        "id": "crypto-reg",
        "trigger": "news",
        "certainty": "uncertain",
        "severity": "medium",
        "keys": ("etf", "sec ", "binance ban", "hack", "liquidation", "stablecoin"),
        "headline": "Crypto-specific news → BTC/ETH first",
        "detail": "Regulatory or flow headlines hit crypto beta first; gold/DXY only if the story is macro.",
        "legs": [("BTC", "watch", "direct"), ("ETH", "watch", "beta")],
    },
    {
        "id": "china",
        "trigger": "data",
        "certainty": "uncertain",
        "severity": "medium",
        "keys": ("china", "pmi", "yuan", "evergrande", "property crisis"),
        "headline": "China data/risk → metals and EM risk",
        "detail": "Weak China: copper/zinc and EM (Nifty) can sag. Stimulus headlines reverse that.",
        "legs": [("COPPER", "watch", "China beta"), ("NIFTY 50", "watch", "EM risk"), ("CRUDE", "watch", "demand")],
    },
]


def classify_text(text: str, *, trigger_hint: str | None = None, actual: str | None = None) -> ImpactAssessment | None:
    blob = (text or "").lower()
    if not blob.strip():
        return None
    for book in PLAYBOOKS:
        if any(k in blob for k in book["keys"]):
            certainty = book["certainty"]
            if actual not in (None, "", " "):
                certainty = "certain"
            if trigger_hint:
                trigger = trigger_hint
            else:
                trigger = book["trigger"]
            return ImpactAssessment(
                trigger=trigger,  # type: ignore[arg-type]
                certainty=certainty,  # type: ignore[arg-type]
                severity=book["severity"],  # type: ignore[arg-type]
                headline=book["headline"],
                detail=book["detail"],
                legs=[ImpactLeg(asset=a, direction=d, note=n) for a, d, n in book["legs"]],  # type: ignore[arg-type]
                source_title=text[:140],
            )
    return None


def classify_move(q: Quote) -> ImpactAssessment | None:
    if abs(q.change_pct) < 1.2:
        return None
    direction = "up" if q.change_pct > 0 else "down"
    mapping = {
        "MCX:CRUDE": classify_text("crude oil " + direction, trigger_hint="move"),
        "MCX:GOLD": classify_text("gold " + ("haven" if direction == "up" else "gold selloff"), trigger_hint="move"),
        "FX:DXY": classify_text("dollar " + direction, trigger_hint="move"),
        "NSE:INDIAVIX": classify_text("volatility spike nifty", trigger_hint="move"),
        "CRYPTO:BTC": classify_text("bitcoin etf liquidation", trigger_hint="move") if abs(q.change_pct) >= 3 else None,
    }
    card = mapping.get(q.canonical)
    if not card:
        return ImpactAssessment(
            trigger="move",
            certainty="certain",
            severity="medium" if abs(q.change_pct) < 2.5 else "high",
            headline=f"{q.symbol} {q.change_pct:+.2f}% → watch related tape",
            detail="Price already printed. Impact is the move itself; related assets may lag.",
            legs=[ImpactLeg(asset=q.symbol, direction=direction, note="already moved")],  # type: ignore[arg-type]
            source_title=q.symbol,
        )
    card.trigger = "move"
    card.certainty = "certain"
    card.source_title = f"{q.symbol} {q.change_pct:+.2f}%"
    return card


def from_alert(title: str, detail: str, related: list[str], *, trigger: str = "event") -> ImpactAssessment:
    card = classify_text(f"{title} {detail}", trigger_hint=trigger)
    if card:
        if related and not card.legs:
            card.legs = [ImpactLeg(asset=a, direction="watch") for a in related]
        card.source_title = title
        return card
    return ImpactAssessment(
        trigger=trigger,  # type: ignore[arg-type]
        certainty="uncertain" if trigger in {"event", "war", "news"} else "certain",
        severity="medium",
        headline=title or "Price/event impact",
        detail=detail or "The print already happened. Related assets listed below can lag, reverse, or ignore the move.",
        legs=[ImpactLeg(asset=a, direction="watch") for a in related[:6]],
        source_title=title,
    )
