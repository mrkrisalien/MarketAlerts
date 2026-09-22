"""Yahoo v8 chart API — research fallback, not exchange-official."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.models import Quote
from app.timeutil import IST, now_ist, spark

YAHOO_MAP = {
    "^GSPC": ("S&P 500", "US:SPX", "global", "USD"),
    "^IXIC": ("NASDAQ", "US:NDX", "global", "USD"),
    "^DJI": ("DOW JONES", "US:DJI", "global", "USD"),
    "^FTSE": ("FTSE 100", "UK:FTSE", "global", "GBP"),
    "^GDAXI": ("DAX", "DE:DAX", "global", "EUR"),
    "^N225": ("NIKKEI 225", "JP:N225", "global", "JPY"),
    "^HSI": ("HANG SENG", "HK:HSI", "global", "HKD"),
    "DX-Y.NYB": ("DXY", "FX:DXY", "fx", "USD"),
    "^TNX": ("US 10Y", "RATES:US10Y", "rates", "%"),
    "^NSEI": ("NIFTY 50", "NSE:NIFTY50", "nse", "INR"),
    "^NSEBANK": ("BANKNIFTY", "NSE:BANKNIFTY", "nse", "INR"),
    "^BSESN": ("SENSEX", "BSE:SENSEX", "nse", "INR"),
    "^INDIAVIX": ("INDIA VIX", "NSE:INDIAVIX", "nse", "INR"),
    "NIFTY_FIN_SERVICE.NS": ("FINNIFTY", "NSE:FINNIFTY", "nse", "INR"),
    "BSE-BANK.BO": ("BANKEX", "BSE:BANKEX", "nse", "INR"),
    "USDINR=X": ("USDINR", "FX:USDINR", "fx", "INR"),
    "GC=F": ("GOLD_USD", "CME:GOLD", "mcx", "USD"),
    "SI=F": ("SILVER_USD", "CME:SILVER", "mcx", "USD"),
    "CL=F": ("CRUDE_USD", "CME:CRUDE", "mcx", "USD"),
    "NG=F": ("NATGAS_USD", "CME:NATGAS", "mcx", "USD"),
    "HG=F": ("COPPER_USD", "CME:COPPER", "mcx", "USD"),
    "ALI=F": ("ALU_USD", "CME:ALUMINIUM", "mcx", "USD"),
    "RELIANCE.NS": ("RELIANCE", "NSE:RELIANCE", "nse", "INR"),
    "HDFCBANK.NS": ("HDFCBANK", "NSE:HDFCBANK", "nse", "INR"),
    "TCS.NS": ("TCS", "NSE:TCS", "nse", "INR"),
    "INFY.NS": ("INFY", "NSE:INFY", "nse", "INR"),
    "ICICIBANK.NS": ("ICICIBANK", "NSE:ICICIBANK", "nse", "INR"),
    "SBIN.NS": ("SBIN", "NSE:SBIN", "nse", "INR"),
    "BHARTIARTL.NS": ("BHARTIARTL", "NSE:BHARTIARTL", "nse", "INR"),
    "LT.NS": ("LT", "NSE:LT", "nse", "INR"),
}


FAST_YAHOO = {
    "^NSEI",
    "^NSEBANK",
    "^BSESN",
    "^INDIAVIX",
    "NIFTY_FIN_SERVICE.NS",
    "BSE-BANK.BO",
    "USDINR=X",
    "GC=F",
    "SI=F",
    "CL=F",
    "DX-Y.NYB",
    "^TNX",
    "^GSPC",
}


class YahooConnector:
    name = "Yahoo Finance"
    source_type = "aggregated"

    async def fetch(self, full: bool = False, india: bool = True) -> list[Quote]:
        headers = {"User-Agent": "Mozilla/5.0 MarketCommand/1.0"}
        items = YAHOO_MAP if full else {k: v for k, v in YAHOO_MAP.items() if k in FAST_YAHOO}
        if not india:
            items = {k: v for k, v in items.items() if v[2] not in {"nse", "mcx"}}
        sem = asyncio.Semaphore(8)
        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            async def bound(ysym, meta):
                async with sem:
                    return await self._one(client, ysym, meta)

            results = await asyncio.gather(
                *[bound(ysym, meta) for ysym, meta in items.items()],
                return_exceptions=True,
            )
        quotes = [q for q in results if isinstance(q, Quote)]
        return quotes

    async def _one(self, client: httpx.AsyncClient, ysym: str, meta: tuple) -> Quote | None:
        try:
            name, canonical, market, ccy = meta
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}"
            r = await client.get(url, params={"range": "1d", "interval": "1m"})
            r.raise_for_status()
            result = (r.json().get("chart") or {}).get("result") or []
            if not result:
                return None
            node = result[0]
            meta_n = node.get("meta") or {}
            price = meta_n.get("regularMarketPrice")
            if price is None:
                return None
            prev = meta_n.get("chartPreviousClose") or meta_n.get("previousClose") or price
            chg_abs = float(price) - float(prev)
            chg_pct = (chg_abs / float(prev) * 100) if prev else 0.0
            closes = ((node.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
            sparkline = [float(x) for x in closes if x is not None] or spark(float(price))
            ts_unix = meta_n.get("regularMarketTime")
            as_of = datetime.fromtimestamp(ts_unix, tz=timezone.utc).astimezone(IST) if ts_unix else now_ist()
            highs = ((node.get("indicators") or {}).get("quote") or [{}])[0].get("high") or []
            lows = ((node.get("indicators") or {}).get("quote") or [{}])[0].get("low") or []
            vols = ((node.get("indicators") or {}).get("quote") or [{}])[0].get("volume") or []
            high = max((x for x in highs if x is not None), default=None)
            low = min((x for x in lows if x is not None), default=None)
            volume = sum(x for x in vols if x is not None) or None
            return Quote(
                symbol=name if market in {"global", "fx", "rates"} else meta[0],
                canonical=canonical,
                name=name,
                market=market,  # type: ignore[arg-type]
                ltp=float(price),
                change_pct=chg_pct,
                change_abs=chg_abs,
                currency=ccy,
                high=high,
                low=low,
                volume=volume,
                prev_close=float(prev),
                sparkline=sparkline[-48:],
                source="Yahoo Finance (research live)",
                source_type="aggregated",
                source_url="https://finance.yahoo.com",
                as_of=as_of,
                retrieved_at=now_ist(),
            )
        except Exception:
            return None
