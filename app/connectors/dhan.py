"""DhanHQ v2 live NSE/MCX quotes. Requires access token from Settings."""

from __future__ import annotations

from datetime import datetime

import httpx

from app.connectors.dhan_scrip import quote_universe
from app.models import Quote
from app.secrets_store import load
from app.timeutil import IST, now_ist, spark


def _as_of(row: dict, fallback):
    raw = row.get("last_trade_time") or row.get("ltt")
    if not raw or str(raw).startswith("01/01/1980"):
        return fallback
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
        try:
            return datetime.strptime(str(raw)[:19], fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return fallback


class DhanConnector:
    name = "DhanHQ"
    source_type = "broker"

    async def fetch(self) -> list[Quote]:
        secrets = load()
        token = secrets.get("dhan_access_token") or ""
        client_id = secrets.get("dhan_client_id") or ""
        if not token or not client_id:
            return []
        universe = quote_universe()
        body = {seg: [int(i) for i in ids] for seg, ids in universe.items() if ids}
        if not body:
            return []
        headers = {
            "access-token": token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post("https://api.dhan.co/v2/marketfeed/quote", headers=headers, json=body)
            if r.status_code >= 400:
                r = await client.post("https://api.dhan.co/v2/marketfeed/ohlc", headers=headers, json=body)
            r.raise_for_status()
            payload = r.json()
        data = payload.get("data") or payload
        ts = now_ist()
        quotes: list[Quote] = []
        if not isinstance(data, dict):
            return quotes
        for seg, instruments in data.items():
            mapping = universe.get(seg, {})
            if not isinstance(instruments, dict):
                continue
            for sid, row in instruments.items():
                meta = mapping.get(str(sid))
                if not meta or not isinstance(row, dict):
                    continue
                symbol, canonical, market, _inst = meta
                ohlc = row.get("ohlc") if isinstance(row.get("ohlc"), dict) else {}
                ltp = row.get("last_price") or row.get("LTP") or row.get("ltp")
                if ltp is None:
                    continue
                close = ohlc.get("close") or row.get("close") or row.get("prev_close") or ltp
                high = ohlc.get("high") or row.get("high")
                low = ohlc.get("low") or row.get("low")
                chg = (float(ltp) - float(close)) / float(close) * 100 if close else 0
                quotes.append(
                    Quote(
                        symbol=symbol,
                        canonical=canonical,
                        name=symbol,
                        market=market,  # type: ignore[arg-type]
                        ltp=float(ltp),
                        change_pct=chg,
                        change_abs=float(ltp) - float(close or ltp),
                        currency="INR",
                        high=float(high) if high else None,
                        low=float(low) if low else None,
                        oi=row.get("oi") or row.get("OI"),
                        volume=row.get("volume"),
                        prev_close=float(close) if close else None,
                        sparkline=spark(float(ltp)),
                        source="DhanHQ live quote",
                        source_type="broker",
                        source_url="https://dhanhq.co/docs/v2/market-quote/",
                        as_of=_as_of(row, ts),
                        retrieved_at=ts,
                        extra={"tape": "live", "dhan_sid": str(sid), "segment": seg},
                    )
                )
        return quotes
