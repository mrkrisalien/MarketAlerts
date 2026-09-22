"""Explicit cross-asset rules. Not an LLM opinion."""

from __future__ import annotations

from app.models import Alert, AlertSource, Quote
from app.timeutil import now_ist

# Live tape: if driver moved, expect these.
LIVE_RULES = [
    {
        "id": "dxy-up",
        "driver": "FX:DXY",
        "dir": "up",
        "pct": 0.25,
        "expect": [("GOLD", "down"), ("SILVER", "down"), ("BTC", "down")],
        "reason": "Stronger USD usually pressures gold, silver and BTC.",
    },
    {
        "id": "dxy-down",
        "driver": "FX:DXY",
        "dir": "down",
        "pct": 0.25,
        "expect": [("GOLD", "up"), ("SILVER", "up"), ("BTC", "up")],
        "reason": "Weaker USD is typically supportive for gold, silver and crypto.",
    },
    {
        "id": "yields-up",
        "driver": "RATES:US10Y",
        "dir": "up",
        "pct": 1.0,
        "expect": [("GOLD", "down"), ("BTC", "down")],
        "reason": "Rising real-rate proxy (US 10Y) competes with non-yielding gold and crypto.",
    },
    {
        "id": "crude-up",
        "driver": "MCX:CRUDE",
        "dir": "up",
        "pct": 1.5,
        "expect": [("NIFTY 50", "down"), ("GOLD", "up")],
        "reason": "Sharp crude rise feeds India inflation/import-cost risk (Nifty pressure) and sometimes gold as a hedge.",
    },
    {
        "id": "crude-down",
        "driver": "MCX:CRUDE",
        "dir": "down",
        "pct": 1.5,
        "expect": [("NIFTY 50", "up")],
        "reason": "Crude decline eases India fuel/CAD pressure — historically friendlier for Nifty.",
    },
    {
        "id": "gold-silver",
        "driver": "MCX:GOLD",
        "dir": "up",
        "pct": 0.8,
        "expect": [("SILVER", "up")],
        "reason": "Gold and silver usually move together; silver often with higher beta.",
    },
    {
        "id": "gold-down-silver",
        "driver": "MCX:GOLD",
        "dir": "down",
        "pct": 0.8,
        "expect": [("SILVER", "down")],
        "reason": "Gold selloff typically drags silver.",
    },
    {
        "id": "vix-up",
        "driver": "NSE:INDIAVIX",
        "dir": "up",
        "pct": 5.0,
        "expect": [("NIFTY 50", "down"), ("BANKNIFTY", "down")],
        "reason": "India VIX expansion = higher expected index volatility; watch Nifty/Banknifty.",
    },
]

# Forward: scheduled event → conditional playbook.
EVENT_PLAYBOOK = [
    {
        "match": ("cpi", "inflation", "pce"),
        "title": "Inflation print window",
        "hot": "If CPI/PCE prints hot → USD ↑ / yields ↑ / Gold ↓ / Silver ↓ / BTC ↓ / Nifty risk-off.",
        "cool": "If CPI/PCE prints cool → USD ↓ / Gold ↑ / BTC ↑ / duration-sensitive Nifty relief.",
        "assets": ["DXY", "GOLD", "SILVER", "BTC", "NIFTY"],
        "season": None,
    },
    {
        "match": ("nfp", "payroll", "nonfarm", "unemployment", "jobless"),
        "title": "US labour data",
        "hot": "Strong jobs → Fed-higher-for-longer pricing → DXY ↑ Gold ↓ BTC ↓.",
        "cool": "Weak jobs → rate-cut odds ↑ → Gold ↑ BTC ↑ DXY ↓.",
        "assets": ["DXY", "GOLD", "BTC", "US 10Y"],
        "season": None,
    },
    {
        "match": ("fomc", "fed", "federal funds", "mpc", "rbi"),
        "title": "Central-bank meeting",
        "hot": "Hawkish hold/hike → USD/INR + yields ↑, gold/crypto usually offered.",
        "cool": "Dovish cut/guidance → gold/silver/crypto bid; Nifty financials can catch a bid.",
        "assets": ["DXY", "GOLD", "NIFTY", "BANKNIFTY", "BTC"],
        "season": None,
    },
    {
        "match": ("crude", "eia", "oil inventories", "petroleum"),
        "title": "Oil inventory / crude event",
        "hot": "Bullish oil surprise → crude ↑ India inflation/import-cost watch → Nifty energy + but index inflation drag.",
        "cool": "Bearish oil surprise → crude ↓ friendlier for India CAD/inflation.",
        "assets": ["CRUDE", "NIFTY", "GOLD"],
        "season": "US driving season (May–Aug) amplifies crude inventory surprises.",
    },
    {
        "match": ("fii", "dii", "foreign"),
        "title": "Institutional flows",
        "hot": "FII selling persistent → Nifty/Banknifty pressure, INR softer, risk-off India.",
        "cool": "FII buying → Nifty breadth improvement; still confirm with DII and VIX.",
        "assets": ["NIFTY", "BANKNIFTY"],
        "season": None,
    },
]

SEASON_NOTES = [
    "India festive demand (Sep–Nov): gold/silver jewellery demand can cushion dips.",
    "US summer driving season (May–Aug): crude more sensitive to EIA draws.",
    "Monsoon window: agri/rural Nifty pockets; not a gold driver by itself.",
]


def _moved(q: Quote, direction: str, pct: float) -> bool:
    if direction == "up":
        return q.change_pct >= pct
    return q.change_pct <= -pct


def evaluate_live(quotes: list[Quote]) -> tuple[list[dict], list[Alert]]:
    by = {q.canonical: q for q in quotes}
    rows = []
    alerts: list[Alert] = []
    ts = now_ist()
    for rule in LIVE_RULES:
        q = by.get(rule["driver"])
        if not q or not _moved(q, rule["dir"], rule["pct"]):
            continue
        arrow = "↑" if rule["dir"] == "up" else "↓"
        expected = [{"asset": a, "direction": d} for a, d in rule["expect"]]
        rows.append(
            {
                "id": rule["id"],
                "kind": "live",
                "driver": q.symbol,
                "driver_move": f"{arrow} {q.change_pct:+.2f}%",
                "reason": rule["reason"],
                "expected": expected,
            }
        )
        related = [a for a, _ in rule["expect"]]
        alerts.append(
            Alert(
                id=f"corr-{rule['id']}",
                tone="uncertain",
                severity="medium",
                category="REGIME",
                title=f"{q.symbol} {arrow} — related tape may follow",
                detail=rule["reason"],
                asset=q.symbol,
                market="cross",
                detected_at=ts,
                importance="medium",
                confidence="medium",
                related_assets=related,
                highlight_symbol=q.symbol,
                sources=[AlertSource(source=q.source, source_type=q.source_type)],
                why={
                    "primary": rule["reason"],
                    "secondary": "This is a historical tendency, not a guarantee.",
                    "technical": f"Driver {q.canonical} exceeded {rule['pct']}% {rule['dir']}",
                    "confidence": "medium",
                },
            )
        )
    return rows, alerts


def evaluate_forward(briefing: list) -> tuple[list[dict], list[Alert]]:
    rows = []
    alerts: list[Alert] = []
    ts = now_ist()
    for item in briefing:
        if getattr(item, "status", "") not in {"upcoming", "live"}:
            continue
        title = (item.title or "").lower()
        for book in EVENT_PLAYBOOK:
            if not any(k in title for k in book["match"]):
                continue
            rows.append(
                {
                    "id": f"fwd-{book['title']}",
                    "kind": "forward",
                    "driver": item.title,
                    "driver_move": item.event_time_label,
                    "reason": book["hot"],
                    "alt": book["cool"],
                    "season": book["season"],
                    "expected": [{"asset": a, "direction": "watch"} for a in book["assets"]],
                }
            )
            alerts.append(
                Alert(
                    id=f"fwd-{item.event_at}-{book['title'][:18]}" if item.event_at else f"fwd-{book['title']}",
                    tone="info",
                    severity="high" if item.status == "live" else "medium",
                    category="MACRO",
                    title=f"FUTURE: {book['title']} · {item.countdown or item.event_time_label}",
                    detail=book["hot"] + " Alternative: " + book["cool"],
                    asset="MACRO",
                    market="macro",
                    detected_at=ts,
                    event_time=item.event_at,
                    importance=item.importance,
                    confidence="medium",
                    related_assets=book["assets"],
                    sources=item.sources,
                    why={
                        "primary": book["hot"],
                        "secondary": book["cool"],
                        "technical": "Scheduled event playbook vs IST clock",
                        "confidence": "medium",
                        "season": book["season"] or "No strong seasonal overlay",
                    },
                )
            )
            break
    return rows, alerts
