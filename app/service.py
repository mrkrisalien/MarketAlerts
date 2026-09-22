from __future__ import annotations

import asyncio

from app.alerts import evaluate_quotes
from app.calendar import calendar_alerts, fetch_calendar, fetch_news, to_briefing
from app.config import settings
from app.connectors.binance import BinanceConnector
from app.connectors.coingecko import CoinGeckoConnector
from app.connectors.delta import DeltaConnector
from app.connectors.dhan import DhanConnector
from app.connectors.yahoo import YahooConnector
from app.correlations import SEASON_NOTES, evaluate_forward, evaluate_live
from app.impact import classify_move, from_alert
from app.mock_data import mock_quotes
from app.models import Alert, AlertSource, DashboardSnapshot, MacroRow, Quote
from app.regime import classify_regime
from app.secrets_store import flags as connector_flags
from app.timeutil import now_ist, spark

TROY_OZ_G = 31.1034768


def _overlay_extras(base: list[Quote], overlay: list[Quote]) -> list[Quote]:
    extra_by = {q.canonical: q for q in overlay}
    for q in base:
        o = extra_by.get(q.canonical)
        if not o:
            continue
        extra = dict(q.extra or {})
        extra.update(o.extra or {})
        q.extra = extra
        if q.oi is None:
            q.oi = o.oi
        if q.volume is None:
            q.volume = o.volume
    return base


def _merge(base: list[Quote], overlay: list[Quote]) -> list[Quote]:
    by = {q.canonical: q for q in base}
    for q in overlay:
        old = by.get(q.canonical)
        if old:
            extra = dict(old.extra or {})
            extra.update(q.extra or {})
            q.extra = extra
            if not q.sparkline:
                q.sparkline = old.sparkline
            if q.volume is None:
                q.volume = old.volume
            if q.oi is None:
                q.oi = old.oi
        by[q.canonical] = q
    return list(by.values())


def _mcx_from_cme(quotes: list[Quote]) -> list[Quote]:
    by = {q.canonical: q for q in quotes}
    inr = by.get("FX:USDINR")
    fx = float(inr.ltp) if inr else 83.5
    ts = now_ist()

    def convert(src: Quote, canonical: str, symbol: str, name: str, factor: float) -> Quote:
        ltp = src.ltp * fx * factor
        high = (src.high * fx * factor) if src.high else None
        low = (src.low * fx * factor) if src.low else None
        prev = (src.prev_close * fx * factor) if src.prev_close else ltp / (1 + src.change_pct / 100)
        return Quote(
            symbol=symbol,
            canonical=canonical,
            name=name,
            market="mcx",
            ltp=round(ltp, 2),
            change_pct=src.change_pct,
            change_abs=round(ltp - prev, 2),
            currency="INR",
            high=round(high, 2) if high else None,
            low=round(low, 2) if low else None,
            volume=src.volume,
            prev_close=round(prev, 2),
            sparkline=[round(x * fx * factor, 2) for x in (src.sparkline or spark(src.ltp))],
            source=f"{src.source} × USDINR {fx:.2f} (MCX-equivalent, not exchange official)",
            source_type="aggregated",
            source_url=src.source_url,
            as_of=src.as_of,
            retrieved_at=ts,
        )

    gold = by.get("CME:GOLD")
    silver = by.get("CME:SILVER")
    crude = by.get("CME:CRUDE")
    natgas = by.get("CME:NATGAS")
    copper = by.get("CME:COPPER")
    extra: list[Quote] = []
    if gold:
        extra.append(convert(gold, "MCX:GOLD", "GOLD", "Gold (MCX est.)", 10 / TROY_OZ_G))
    if silver:
        extra.append(convert(silver, "MCX:SILVER", "SILVER", "Silver (MCX est.)", 1000 / TROY_OZ_G))
    if crude:
        extra.append(convert(crude, "MCX:CRUDE", "CRUDE", "Crude Oil (MCX est.)", 1.0))
    if natgas:
        extra.append(convert(natgas, "MCX:NATGAS", "NATGAS", "Natural Gas (MCX est.)", 1.0))
    if copper:
        extra.append(convert(copper, "MCX:COPPER", "COPPER", "Copper (MCX est.)", 2.20462))
    return extra


def _macro(quotes: list[Quote], briefing: list, briefing_status: dict[str, str]) -> list[MacroRow]:
    by = {q.canonical: q for q in quotes}
    dxy = by.get("FX:DXY")
    us10 = by.get("RATES:US10Y")
    inr = by.get("FX:USDINR")
    vix = by.get("NSE:INDIAVIX")
    gold = by.get("MCX:GOLD")
    crude = by.get("MCX:CRUDE")
    btc = by.get("CRYPTO:BTC")

    def chg_of(q: Quote | None) -> str:
        if not q:
            return "—"
        sign = "+" if q.change_pct >= 0 else ""
        return f"{sign}{q.change_pct:.2f}%"

    def when_for(*needles: str) -> str:
        for b in briefing or []:
            blob = (b.title or "").lower()
            if any(n in blob for n in needles):
                return f"{b.status.upper()} · {b.event_time_label}"
        return "See calendar"

    def cal(key: str, label: str, why: str, watch: str, needles: tuple[str, ...]) -> MacroRow:
        st = briefing_status.get(key, "upcoming")
        return MacroRow(
            key=key,
            label=label,
            value=st.upper(),
            change="",
            direction="watch" if st != "released" else "flat",
            status="uncertain" if st in {"upcoming", "live"} else "info",
            why=why,
            watch=watch,
            when=when_for(*needles),
            source="Economic calendar",
        )

    rows = [
        MacroRow(
            key="US10Y",
            label="US 10Y yield",
            value=f"{us10.ltp:.2f}%" if us10 else "—",
            change=chg_of(us10),
            direction="down" if us10 and us10.change_pct < 0 else "up",
            status="info",
            why="Higher real yields compete with gold and crypto. Lower yields usually help duration and havens.",
            watch="Gold, BTC, Nifty financials, USDINR",
            when="Live Treasury/Yahoo",
            source=us10.source if us10 else "Yahoo",
        ),
        MacroRow(
            key="DXY",
            label="US Dollar (DXY)",
            value=f"{dxy.ltp:.2f}" if dxy else "—",
            change=chg_of(dxy),
            direction="down" if dxy and dxy.change_pct < 0 else "up",
            status="info",
            why="A stronger dollar typically pressures gold, EM FX and India-import costs. A weaker dollar is friendlier for metals and risk.",
            watch="Gold, Silver, USDINR, Nifty",
            when="Live",
            source=dxy.source if dxy else "Yahoo",
        ),
        MacroRow(
            key="USDINR",
            label="USD / INR",
            value=f"{inr.ltp:.2f}" if inr else "—",
            change=chg_of(inr),
            direction="down" if inr and inr.change_pct < 0 else "up",
            status="info",
            why="INR weakness raises imported inflation (crude, gold) and can cap FII flows into Nifty.",
            watch="Crude, Gold, Bank Nifty",
            when="Live",
            source=inr.source if inr else "Yahoo",
        ),
        MacroRow(
            key="VIX",
            label="India VIX",
            value=f"{vix.ltp:.1f}" if vix else "—",
            change=chg_of(vix),
            direction="up" if vix and vix.change_pct > 0 else "down",
            status="uncertain" if vix and abs(vix.change_pct) >= 6 else "info",
            why="VIX is the options market's fear gauge. A spike means wider Nifty ranges and richer premiums.",
            watch="Nifty, Bank Nifty, FinNifty",
            when="NSE session",
            source=vix.source if vix else "NSE/Dhan",
        ),
        MacroRow(
            key="GOLD",
            label="Gold (MCX)",
            value=f"₹{gold.ltp:,.0f}" if gold else "—",
            change=chg_of(gold),
            direction="up" if gold and gold.change_pct > 0 else "down",
            status="info",
            why="Gold is the rupee + real-rate + geopolitics sponge. It can rise even when Nifty is calm.",
            watch="USDINR, US 10Y, Silver",
            when="MCX session",
            source=gold.source if gold else "MCX/Dhan",
        ),
        MacroRow(
            key="CRUDE",
            label="Crude (MCX)",
            value=f"₹{crude.ltp:,.0f}" if crude else "—",
            change=chg_of(crude),
            direction="up" if crude and crude.change_pct > 0 else "down",
            status="info",
            why="India imports most of its oil. Higher crude feeds CAD and inflation; lower crude eases the index.",
            watch="Nifty, USDINR, Gold",
            when="MCX / EIA calendar",
            source=crude.source if crude else "MCX/Dhan",
        ),
        MacroRow(
            key="BTC",
            label="Bitcoin",
            value=f"${btc.ltp:,.0f}" if btc else "—",
            change=chg_of(btc),
            direction="up" if btc and btc.change_pct > 0 else "down",
            status="info",
            why="BTC is high-beta global liquidity. Large moves often rhyme with gold and the dollar, not with Nifty 1:1.",
            watch="ETH, Gold, DXY",
            when="24x7",
            source=btc.source if btc else "Binance",
        ),
        cal("nfp", "US Jobs (NFP)", "Strong jobs = Fed stays tighter (USD up, gold/crypto offered). Weak jobs = cut odds up.", "DXY, Gold, BTC", ("nfp", "nonfarm", "payroll", "unemployment")),
        cal("fed", "Fed / FOMC", "Hawkish hold or hike lifts yields and the dollar. Dovish cut/guidance is usually gold and crypto-friendly.", "US 10Y, Gold, Bank Nifty", ("fomc", "fed", "federal funds")),
        cal("cpi", "US CPI", "Hot inflation print typically lifts DXY/yields and hits gold/BTC. Cool print is the reverse.", "DXY, Gold, BTC, Nifty", ("cpi", "inflation")),
        cal("rbi", "RBI / MPC", "RBI path sets INR and banking multiples. Hawkish = USDINR + Bank Nifty watch.", "USDINR, Bank Nifty", ("rbi", "mpc", "repo")),
        cal("eia", "Crude inventories", "A large EIA build can cap oil; a draw supports crude and India's import-cost watch.", "Crude, Nifty energy", ("eia", "inventor", "crude")),
    ]
    return rows


def _sentiment(quotes: list[Quote], alerts: list[Alert]) -> dict:
    def pick(*canons: str) -> list[Quote]:
        by = {q.canonical: q for q in quotes}
        return [by[c] for c in canons if c in by]

    def pack(mid: str, title: str, items: list[Quote], kpis: list[str], note: str, vix_penalty: float = 0.0) -> dict:
        if items:
            avg = sum(q.change_pct for q in items) / len(items)
            n_up = sum(1 for q in items if q.change_pct > 0.05)
            n_down = sum(1 for q in items if q.change_pct < -0.05)
            breadth = ((n_up - n_down) / len(items)) * 12
            score = int(round(50 + avg * 10 + breadth - vix_penalty))
        else:
            avg, score = 0.0, 50
        score = max(8, min(92, score))
        if score >= 58:
            label = "Risk-On"
        elif score <= 42:
            label = "Cautious"
        else:
            label = "Neutral"
        return {
            "id": mid,
            "title": title,
            "score": score,
            "label": label,
            "avg_change": round(avg, 2),
            "kpis": [k for k in kpis if k],
            "note": note,
        }

    crypto = [q for q in quotes if q.canonical in {"CRYPTO:BTC", "CRYPTO:ETH", "CRYPTO:SOL", "CRYPTO:XRP", "CRYPTO:BNB"}]
    nse = pick("NSE:NIFTY50", "NSE:BANKNIFTY", "NSE:FINNIFTY", "BSE:SENSEX", "BSE:BANKEX")
    vix = next((q for q in quotes if q.canonical == "NSE:INDIAVIX"), None)
    vix_pen = 0.0
    if vix and vix.change_pct > 4:
        vix_pen = min(18.0, vix.change_pct)

    def pct(q: Quote | None, name: str) -> str:
        if not q:
            return ""
        sign = "+" if q.change_pct >= 0 else ""
        return f"{name} {sign}{q.change_pct:.2f}%"

    by = {q.canonical: q for q in quotes}
    btc = by.get("CRYPTO:BTC")
    eth = by.get("CRYPTO:ETH")
    cap = next((q for q in quotes if q.canonical == "CRYPTO:TOTALCAP"), None)
    btc_d = (cap.extra or {}).get("btc_dominance") if cap else None

    return {
        "markets": [
            pack(
                "crypto",
                "Crypto",
                crypto[:8],
                [
                    pct(btc, "BTC"),
                    pct(eth, "ETH"),
                    f"BTC.D {float(btc_d):.1f}%" if btc_d else "",
                ],
                "BTC still sets crypto beta. Large coin moves here are live prints, not forecasts.",
            ),
            pack(
                "nse",
                "NSE / India",
                nse,
                [
                    pct(by.get("NSE:NIFTY50"), "Nifty"),
                    pct(by.get("NSE:BANKNIFTY"), "Bank Nifty"),
                    f"India VIX {vix.ltp:.1f}" if vix else "",
                ],
                "VIX up usually means caution for Nifty/Bank Nifty even if the index is green.",
                vix_penalty=vix_pen,
            ),
            pack(
                "mcx",
                "MCX",
                pick("MCX:GOLD", "MCX:SILVER", "MCX:CRUDE", "MCX:NATGAS"),
                [
                    pct(by.get("MCX:GOLD"), "Gold"),
                    pct(by.get("MCX:SILVER"), "Silver"),
                    pct(by.get("MCX:CRUDE"), "Crude"),
                ],
                "Gold, energy and base metals can split. A gold bid is not the same as a crude bid.",
            ),
        ]
    }


def _india_structure() -> dict:
    return {
        "fii": None,
        "dii": None,
        "advances": None,
        "declines": None,
        "new_highs": None,
        "new_lows": None,
        "fo_note": "Open the F&O page for live index and cash option OI/PCR from Dhan.",
    }


def _crypto_structure(quotes: list[Quote]) -> dict:
    by = {q.canonical: q for q in quotes}
    cap = by.get("CRYPTO:TOTALCAP")
    extra = dict(cap.extra or {}) if cap else {}
    coins = [q for q in quotes if q.market == "crypto" and q.symbol not in {"TOTALCAP"}]
    tracked_mcap = sum(float((q.extra or {}).get("market_cap") or 0) for q in coins)
    tracked_vol = sum(float(q.volume or 0) for q in coins)
    btc = by.get("CRYPTO:BTC")
    btc_mcap = float((btc.extra or {}).get("market_cap") or 0) if btc else 0
    total_mcap = float(cap.ltp) if cap and cap.ltp else tracked_mcap or None
    total_volume = extra.get("total_volume") or tracked_vol or None
    btc_d = extra.get("btc_dominance")
    if btc_d is None and total_mcap and btc_mcap:
        btc_d = 100.0 * btc_mcap / total_mcap
    eth_d = extra.get("eth_dominance")
    stables = extra.get("stablecoin_mcap")
    funding = extra.get("funding")
    if funding is None:
        fund_vals = [(q.extra or {}).get("funding") for q in coins if (q.extra or {}).get("funding") not in (None, "")]
        if fund_vals:
            try:
                rate = float(fund_vals[0])
                funding = f"{rate * 100:.4f}% 8h (Delta BTC/ETH)"
            except (TypeError, ValueError):
                funding = str(fund_vals[0])
    oi = next((q.oi for q in coins if q.oi), None)
    return {
        "btc_dominance": btc_d,
        "eth_dominance": eth_d,
        "total_mcap": total_mcap,
        "total_volume": total_volume,
        "stablecoin_mcap": stables,
        "funding": funding or "Delta funding when the India ticker is up",
        "open_interest": oi,
        "tracked_mcap": tracked_mcap or None,
        "note": "Dominance and mcap from CoinGecko global when the feed answers; otherwise summed from BTC/ETH/SOL/XRP/BNB.",
    }


def _calendar_macro_keys(rows: list[dict]) -> dict[str, str]:
    now = now_ist()
    keys = {}
    for row in rows:
        title = row["title"].lower()
        when = row["event_at"]
        if now < when:
            st = "upcoming"
        elif (now - when).total_seconds() < 2700:
            st = "live"
        else:
            st = "released"
        if "cpi" in title:
            keys["cpi"] = st
        if "nonfarm" in title or "nfp" in title or "payroll" in title:
            keys["nfp"] = st
        if "fomc" in title or "federal funds" in title or "fed interest" in title:
            keys["fed"] = st
        if "rbi" in title:
            keys["rbi"] = st
        if "crude" in title or "oil inventories" in title or "eia" in title:
            keys["eia"] = st
    return keys


def _tape(q: Quote, now, lag: float) -> str:
    mins = now.hour * 60 + now.minute
    weekday = now.weekday() < 5
    if q.market == "nse":
        open_sess = weekday and (9 * 60 + 15) <= mins <= (15 * 60 + 30)
        if not open_sess:
            return "closed"
        return "live" if lag < 90 else "delayed"
    if q.market == "crypto":
        return "live" if lag < 45 else "delayed"
    if q.market == "mcx":
        return "live" if lag < 180 else "delayed"
    return "live" if lag < 120 else ("closed" if lag > 3600 else "delayed")


class MarketService:
    def __init__(self) -> None:
        self._cache: DashboardSnapshot | None = None
        self._lock = asyncio.Lock()
        self._sparks: dict[str, list[float]] = {}
        self._slow_at = None
        self._full_yahoo_at = None
        self._news: list = []
        self._calendar: list = []
        self._gecko: list[Quote] = []
        self._delta: list[Quote] = []
        self._yahoo_full: list[Quote] = []

    def _roll_sparks(self, quotes: list[Quote]) -> None:
        now = now_ist()
        for q in quotes:
            prev = self._sparks.get(q.canonical) or []
            incoming = q.sparkline or []
            if len(incoming) >= 8 and incoming != spark(q.ltp):
                series = incoming[-48:]
            else:
                series = prev[-47:] if prev else []
            if not series or abs(series[-1] - q.ltp) > 1e-9:
                series = (series + [q.ltp])[-48:]
            self._sparks[q.canonical] = series
            q.sparkline = series
            lag = max(0.0, (now - q.as_of).total_seconds())
            extra = dict(q.extra or {})
            extra["lag_seconds"] = int(lag)
            extra["tape"] = _tape(q, now, lag)
            q.extra = extra

    async def snapshot(self, force: bool = False) -> DashboardSnapshot:
        async with self._lock:
            if (
                not force
                and self._cache
                and (now_ist() - self._cache.generated_at).total_seconds() < settings.refresh_seconds
            ):
                return self._cache
            self._cache = await self._build()
            return self._cache

    def invalidate(self) -> None:
        self._cache = None

    async def _safe(self, coro, label: str, sources: list) -> list:
        try:
            data = await coro
            sources.append({"name": label, "type": "live"})
            return data
        except Exception as exc:
            sources.append({"name": label, "type": f"failed:{exc.__class__.__name__}"})
            return []

    async def _build(self) -> DashboardSnapshot:
        quotes = mock_quotes()
        sources_used = [{"name": "Internal seed (overwritten by live feeds)", "type": "mock"}]
        live = False
        now = now_ist()
        slow_stale = self._slow_at is None or (now - self._slow_at).total_seconds() > 90
        full_yahoo = self._full_yahoo_at is None or (now - self._full_yahoo_at).total_seconds() > 20

        tasks = {}
        if settings.enable_live_binance:
            tasks["binance"] = self._safe(BinanceConnector().fetch(), "Binance", sources_used)
        if settings.enable_live_yahoo:
            tasks["yahoo"] = self._safe(YahooConnector().fetch(full=full_yahoo), "Yahoo Finance", sources_used)
        tasks["dhan"] = self._safe(DhanConnector().fetch(), "DhanHQ", sources_used)
        if slow_stale:
            if settings.enable_live_crypto:
                tasks["gecko"] = self._safe(CoinGeckoConnector().fetch(), "CoinGecko", sources_used)
            tasks["delta"] = self._safe(DeltaConnector().fetch(), "Delta Exchange", sources_used)
            tasks["calendar"] = self._safe(fetch_calendar(), "Economic calendar", sources_used)
            tasks["news"] = self._safe(fetch_news(), "News RSS", sources_used)

        keys = list(tasks)
        results = await asyncio.gather(*[tasks[k] for k in keys])
        fetched = dict(zip(keys, results))

        if "gecko" in fetched:
            self._gecko = fetched["gecko"] or []
        if "delta" in fetched:
            self._delta = fetched["delta"] or []
        if "calendar" in fetched:
            self._calendar = fetched["calendar"] or []
        if "news" in fetched:
            self._news = fetched["news"] or []
        if slow_stale:
            self._slow_at = now
        if fetched.get("yahoo") and full_yahoo:
            self._yahoo_full = fetched["yahoo"]
            self._full_yahoo_at = now

        if self._gecko:
            quotes = _merge(quotes, self._gecko)
            live = True
        if fetched.get("binance"):
            quotes = _merge(quotes, fetched["binance"])
            live = True
        if self._delta:
            quotes = _overlay_extras(quotes, self._delta)
        yahoo_q = fetched.get("yahoo") or []
        dhan_q = fetched.get("dhan") or []
        if yahoo_q:
            if not full_yahoo and self._yahoo_full:
                quotes = _merge(quotes, self._yahoo_full)
            quotes = _merge(quotes, yahoo_q)
            if not dhan_q:
                quotes = _merge(quotes, _mcx_from_cme(quotes))
            live = True
        elif self._yahoo_full and not dhan_q:
            quotes = _merge(quotes, self._yahoo_full)
            quotes = _merge(quotes, _mcx_from_cme(quotes))
            live = True
        if dhan_q:
            if yahoo_q or self._yahoo_full:
                keep = [q for q in quotes if q.market in {"global", "fx", "rates", "crypto"}]
                quotes = keep
                if yahoo_q:
                    quotes = _merge(quotes, [q for q in yahoo_q if q.market in {"global", "fx", "rates"}])
                elif self._yahoo_full:
                    quotes = _merge(quotes, [q for q in self._yahoo_full if q.market in {"global", "fx", "rates"}])
            quotes = _merge(quotes, dhan_q)
            live = True

        self._roll_sparks(quotes)

        calendar_rows = self._calendar or []
        news = self._news or []
        briefing = to_briefing(calendar_rows) if calendar_rows else []

        for q in quotes:
            if not q.sparkline:
                q.sparkline = spark(q.ltp)

        live_corr, live_corr_alerts = evaluate_live(quotes)
        fwd_corr, fwd_corr_alerts = evaluate_forward(briefing)
        alerts = evaluate_quotes(quotes) + calendar_alerts(calendar_rows) + live_corr_alerts + fwd_corr_alerts
        for n in news:
            card = n.impact_card
            if card and card.trigger in {"war", "outcome"} and card.severity == "high":
                alerts.insert(
                    0,
                    Alert(
                        id=f"news-{n.title[:28]}",
                        tone="uncertain",
                        severity="high",
                        category="NEWS",
                        title=n.title,
                        detail=card.headline,
                        asset="MARKET",
                        market="cross",
                        detected_at=now_ist(),
                        importance="high",
                        confidence="low" if card.certainty == "uncertain" else "medium",
                        related_assets=[leg.asset for leg in card.legs],
                        sources=[AlertSource(source=n.source, source_type="news", original_url=n.url)],
                        impact=card,
                        why={
                            "primary": card.headline,
                            "trigger": "This NEWS rule fired because the headline matched a war/geopolitics classifier.",
                            "secondary": card.detail,
                            "technical": "Headline classifier (war/outcome)",
                            "impact": card.detail,
                            "confidence": card.certainty,
                        },
                    ),
                )
        for a in alerts:
            if a.impact is None:
                related = list(dict.fromkeys([a.asset, *(a.related_assets or [])]))
                trig = "move" if a.category in {"PRICE", "VOLATILITY"} else "event"
                a.impact = from_alert(a.title, a.detail, related, trigger=trig)
        seen = set()
        deduped: list[Alert] = []
        for a in alerts:
            if a.id in seen:
                continue
            seen.add(a.id)
            deduped.append(a)
        alerts = deduped[:14]

        board = []
        seen_h = set()
        for card in [n.impact_card for n in news] + [b.impact_card for b in briefing] + [a.impact for a in alerts]:
            if not card:
                continue
            key = card.headline
            if key in seen_h:
                continue
            seen_h.add(key)
            board.append(card)
        for q in quotes:
            mv = classify_move(q)
            if mv and mv.headline not in seen_h:
                seen_h.add(mv.headline)
                board.append(mv)
        board = board[:8]

        risk, liq, regime = classify_regime(quotes)
        by = {q.canonical: q for q in quotes}
        pulse_order = [
            "CRYPTO:BTC",
            "CRYPTO:ETH",
            "NSE:NIFTY50",
            "NSE:BANKNIFTY",
            "NSE:FINNIFTY",
            "BSE:SENSEX",
            "BSE:BANKEX",
            "NSE:INDIAVIX",
            "MCX:GOLD",
            "MCX:SILVER",
            "MCX:CRUDE",
            "FX:DXY",
            "RATES:US10Y",
        ]
        pulse = [by[k] for k in pulse_order if k in by]
        snapshot = DashboardSnapshot(
            generated_at=now_ist(),
            timezone=settings.timezone,
            live=live,
            global_risk=risk,
            liquidity=liq,
            alert_count=len(alerts),
            regime=regime,
            pulse=pulse,
            alerts=alerts,
            india=[
                by[k]
                for k in [
                    "NSE:NIFTY50",
                    "NSE:BANKNIFTY",
                    "BSE:SENSEX",
                    "NSE:FINNIFTY",
                    "NSE:NIFTYMIDCAP",
                    "NSE:INDIAVIX",
                    "BSE:BANKEX",
                ]
                if k in by
            ],
            crypto=[q for q in quotes if q.market == "crypto" and q.symbol not in {"TOTALCAP"}],
            mcx=[
                by[k]
                for k in ["MCX:GOLD", "MCX:SILVER", "MCX:CRUDE", "MCX:NATGAS", "MCX:COPPER", "MCX:ALUMINIUM", "MCX:ZINC"]
                if k in by
            ],
            global_markets=[q for q in quotes if q.market == "global"],
            watchlist=[
                by[k]
                for k in [
                    "NSE:RELIANCE",
                    "NSE:HDFCBANK",
                    "NSE:TCS",
                    "NSE:INFY",
                    "NSE:ICICIBANK",
                    "NSE:SBIN",
                ]
                if k in by
            ],
            crypto_structure=_crypto_structure(quotes),
            india_structure=_india_structure(),
            macro=_macro(quotes, briefing, _calendar_macro_keys(calendar_rows)),
            briefing=briefing,
            news=news,
            sentiment=_sentiment(quotes, alerts),
            sources_used=sources_used,
            chart_series={
                "BTC": (by.get("CRYPTO:BTC").sparkline if by.get("CRYPTO:BTC") else []),
                "NIFTY": (by.get("NSE:NIFTY50").sparkline if by.get("NSE:NIFTY50") else []),
                "GOLD": (by.get("MCX:GOLD").sparkline if by.get("MCX:GOLD") else []),
            },
            correlations=live_corr + fwd_corr,
            season_notes=SEASON_NOTES,
            connector_status=connector_flags(),
            impact_board=board,
        )
        return snapshot


service = MarketService()
