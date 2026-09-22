from __future__ import annotations

import httpx

from app.models import Quote
from app.secrets_store import load as load_secrets
from app.config import settings
from app.timeutil import now_ist, spark

COINS = {
    "bitcoin": ("BTC", "CRYPTO:BTC", "Bitcoin"),
    "ethereum": ("ETH", "CRYPTO:ETH", "Ethereum"),
    "solana": ("SOL", "CRYPTO:SOL", "Solana"),
    "ripple": ("XRP", "CRYPTO:XRP", "XRP"),
    "binancecoin": ("BNB", "CRYPTO:BNB", "BNB"),
}


class CoinGeckoConnector:
    name = "CoinGecko"
    source_type = "aggregated"

    async def fetch(self) -> list[Quote]:
        headers = {"accept": "application/json"}
        key = load_secrets().get("coingecko_api_key") or settings.coingecko_api_key
        if key:
            headers["x-cg-demo-api-key"] = key
        ids = ",".join([*COINS, "tether", "usd-coin"])
        url = (
            "https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&ids={ids}&order=market_cap_desc"
            "&sparkline=true&price_change_percentage=24h"
        )
        async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
            r = await client.get(url)
            r.raise_for_status()
            rows = r.json()
            g = await client.get("https://api.coingecko.com/api/v3/global")
            global_payload = g.json() if g.status_code == 200 else {}

        ts = now_ist()
        quotes: list[Quote] = []
        stables = 0.0
        for row in rows:
            if row.get("id") in {"tether", "usd-coin"}:
                stables += float(row.get("market_cap") or 0)
                continue
            meta = COINS.get(row["id"])
            if not meta:
                continue
            symbol, canonical, name = meta
            sparkline = row.get("sparkline_in_7d", {}).get("price") or spark(row["current_price"])
            quotes.append(
                Quote(
                    symbol=symbol,
                    canonical=canonical,
                    name=name,
                    market="crypto",
                    ltp=float(row["current_price"]),
                    change_pct=float(row.get("price_change_percentage_24h") or 0),
                    change_abs=float(row.get("price_change_24h") or 0),
                    currency="USD",
                    high=row.get("high_24h"),
                    low=row.get("low_24h"),
                    volume=row.get("total_volume"),
                    prev_close=float(row["current_price"]) - float(row.get("price_change_24h") or 0),
                    sparkline=[round(x, 4) for x in sparkline[-48:]],
                    source="CoinGecko",
                    source_type="aggregated",
                    source_url="https://www.coingecko.com",
                    as_of=ts,
                    retrieved_at=ts,
                    extra={
                        "market_cap": row.get("market_cap"),
                        "ath": row.get("ath"),
                    },
                )
            )

        data = (global_payload or {}).get("data") or {}
        tracked_mcap = sum(float((q.extra or {}).get("market_cap") or 0) for q in quotes)
        tracked_vol = sum(float(q.volume or 0) for q in quotes)
        total_mcap = float((data.get("total_market_cap") or {}).get("usd") or 0) or tracked_mcap
        btc = next((q for q in quotes if q.symbol == "BTC"), None)
        btc_mcap = float((btc.extra or {}).get("market_cap") or 0) if btc else 0
        btc_d = (data.get("market_cap_percentage") or {}).get("btc")
        eth_d = (data.get("market_cap_percentage") or {}).get("eth")
        if btc_d is None and total_mcap and btc_mcap:
            btc_d = 100.0 * btc_mcap / total_mcap
        quotes.append(
            Quote(
                symbol="TOTALCAP",
                canonical="CRYPTO:TOTALCAP",
                name="Total crypto mcap",
                market="crypto",
                ltp=float(total_mcap or 0),
                change_pct=float(data.get("market_cap_change_percentage_24h_usd") or 0),
                currency="USD",
                volume=float((data.get("total_volume") or {}).get("usd") or tracked_vol or 0) or None,
                source="CoinGecko Global" if data else "CoinGecko markets",
                source_type="aggregated",
                source_url="https://www.coingecko.com/en/charts",
                as_of=ts,
                retrieved_at=ts,
                extra={
                    "btc_dominance": btc_d,
                    "eth_dominance": eth_d,
                    "total_volume": (data.get("total_volume") or {}).get("usd") or tracked_vol,
                    "stablecoin_mcap": stables or None,
                },
            )
        )
        return quotes
