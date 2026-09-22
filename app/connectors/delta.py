"""Delta India public tickers — no key required for LTP/funding."""

from __future__ import annotations

import httpx

from app.models import Quote
from app.timeutil import now_ist, spark

WANT = {
    "BTCUSD": ("BTC", "CRYPTO:BTC", "Bitcoin"),
    "ETHUSD": ("ETH", "CRYPTO:ETH", "Ethereum"),
    "SOLUSD": ("SOL", "CRYPTO:SOL", "Solana"),
}


class DeltaConnector:
    name = "Delta Exchange India"
    source_type = "primary"

    async def fetch(self) -> list[Quote]:
        url = "https://api.india.delta.exchange/v2/tickers"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            payload = r.json()
        rows = payload.get("result") or payload.get("tickers") or []
        ts = now_ist()
        quotes: list[Quote] = []
        for row in rows:
            sym = str(row.get("symbol") or "")
            meta = WANT.get(sym)
            if not meta:
                continue
            symbol, canonical, name = meta
            mark = row.get("mark_price") or row.get("close") or row.get("spot_price")
            if mark is None:
                continue
            chg = float(row.get("mark_change_24h") or row.get("price_change_percent_24h") or 0)
            quotes.append(
                Quote(
                    symbol=symbol,
                    canonical=canonical,
                    name=name,
                    market="crypto",
                    ltp=float(mark),
                    change_pct=chg,
                    currency="USD",
                    volume=row.get("turnover_usd") or row.get("volume"),
                    oi=row.get("oi_value_usd") or row.get("oi"),
                    sparkline=spark(float(mark)),
                    source="Delta Exchange India tickers",
                    source_type="primary",
                    source_url="https://docs.delta.exchange/",
                    as_of=ts,
                    retrieved_at=ts,
                    extra={"funding": row.get("funding_rate"), "product": sym},
                )
            )
        return quotes
