from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.models import Quote
from app.timeutil import IST, now_ist

PAIRS = {
    "BTCUSDT": ("BTC", "CRYPTO:BTC", "Bitcoin"),
    "ETHUSDT": ("ETH", "CRYPTO:ETH", "Ethereum"),
    "SOLUSDT": ("SOL", "CRYPTO:SOL", "Solana"),
    "XRPUSDT": ("XRP", "CRYPTO:XRP", "XRP"),
    "BNBUSDT": ("BNB", "CRYPTO:BNB", "BNB"),
}


class BinanceConnector:
    name = "Binance"
    source_type = "primary"

    async def fetch(self) -> list[Quote]:
        symbols = "[" + ",".join(f'"{s}"' for s in PAIRS) + "]"
        url = "https://api.binance.com/api/v3/ticker/24hr"
        ts = now_ist()
        quotes: list[Quote] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params={"symbols": symbols})
            r.raise_for_status()
            rows = r.json()

            for row in rows:
                if row.get("symbol") not in PAIRS:
                    continue
                meta = PAIRS[row["symbol"]]
                symbol, canonical, name = meta
                last = float(row["lastPrice"])
                close_ms = row.get("closeTime")
                as_of = datetime.fromtimestamp(int(close_ms) / 1000, tz=timezone.utc).astimezone(IST) if close_ms else ts
                quotes.append(
                    Quote(
                        symbol=symbol,
                        canonical=canonical,
                        name=name,
                        market="crypto",
                        ltp=last,
                        change_pct=float(row["priceChangePercent"]),
                        change_abs=float(row["priceChange"]),
                        currency="USD",
                        high=float(row["highPrice"]),
                        low=float(row["lowPrice"]),
                        volume=float(row["quoteVolume"]),
                        prev_close=float(row["prevClosePrice"]),
                        sparkline=[last],
                        source="Binance 24h ticker",
                        source_type="primary",
                        source_url="https://www.binance.com",
                        as_of=as_of,
                        retrieved_at=ts,
                    )
                )
        return list(quotes)
