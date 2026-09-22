"""Resolve Dhan security IDs from the official scrip master (cached)."""

from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path

import httpx

from app.timeutil import now_ist

MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "dhan_scrip.json"
TTL = 6 * 3600
CACHE_VER = 2

# Stable index IDs (IDX_I). VIX was wrongly mapped to 51 (SENSEX) before.
INDEX_IDS = {
    "13": ("NIFTY 50", "NSE:NIFTY50", "nse", "INDEX"),
    "25": ("BANKNIFTY", "NSE:BANKNIFTY", "nse", "INDEX"),
    "27": ("FINNIFTY", "NSE:FINNIFTY", "nse", "INDEX"),
    "21": ("INDIA VIX", "NSE:INDIAVIX", "nse", "INDEX"),
    "51": ("SENSEX", "BSE:SENSEX", "nse", "INDEX"),
    "69": ("BANKEX", "BSE:BANKEX", "nse", "INDEX"),
    "442": ("MIDCPNIFTY", "NSE:NIFTYMIDCAP", "nse", "INDEX"),
}

EQUITY_IDS = {
    "2885": ("RELIANCE", "NSE:RELIANCE", "nse", "EQUITY"),
    "1333": ("HDFCBANK", "NSE:HDFCBANK", "nse", "EQUITY"),
    "11536": ("TCS", "NSE:TCS", "nse", "EQUITY"),
    "1594": ("INFY", "NSE:INFY", "nse", "EQUITY"),
    "4963": ("ICICIBANK", "NSE:ICICIBANK", "nse", "EQUITY"),
    "3045": ("SBIN", "NSE:SBIN", "nse", "EQUITY"),
}

MCX_UNDERLYINGS = {
    "GOLD": ("GOLD", "MCX:GOLD", "mcx"),
    "SILVER": ("SILVER", "MCX:SILVER", "mcx"),
    "CRUDEOIL": ("CRUDE", "MCX:CRUDE", "mcx"),
    "NATURALGAS": ("NATGAS", "MCX:NATGAS", "mcx"),
    "COPPER": ("COPPER", "MCX:COPPER", "mcx"),
    "ALUMINIUM": ("ALUMINIUM", "MCX:ALUMINIUM", "mcx"),
    "ZINC": ("ZINC", "MCX:ZINC", "mcx"),
}


def _load_cache() -> dict | None:
    if not CACHE.exists():
        return None
    try:
        raw = json.loads(CACHE.read_text(encoding="utf-8"))
        if time.time() - raw.get("ts", 0) < TTL and raw.get("ver") == CACHE_VER:
            return raw
    except Exception:
        return None
    return None


def _save_cache(payload: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(payload), encoding="utf-8")


def _nearest_mcx(text: str) -> dict[str, dict]:
    today = now_ist().date().isoformat()
    best: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if (row.get("SEM_INSTRUMENT_NAME") or "") != "FUTCOM":
            continue
        if (row.get("SEM_EXM_EXCH_ID") or "") != "MCX":
            continue
        trade = (row.get("SEM_TRADING_SYMBOL") or "").split("-")[0].upper()
        if trade not in MCX_UNDERLYINGS:
            continue
        expiry = (row.get("SEM_EXPIRY_DATE") or "")[:10]
        if expiry < today:
            continue
        prev = best.get(trade)
        if not prev or expiry < prev["expiry"]:
            best[trade] = {
                "sid": str(row.get("SEM_SMST_SECURITY_ID")),
                "expiry": expiry,
                "symbol": trade,
            }
    return best


def quote_universe() -> dict[str, dict[str, tuple]]:
    """exchangeSegment -> {securityId: (symbol, canonical, market, instrument)}"""
    cached = _load_cache()
    mcx = (cached or {}).get("mcx") or {}
    if not cached:
        try:
            r = httpx.get(MASTER_URL, timeout=60.0, headers={"User-Agent": "MarketCommand/1.0"})
            r.raise_for_status()
            mcx_raw = _nearest_mcx(r.text)
            mcx = mcx_raw
            _save_cache({"ts": time.time(), "ver": CACHE_VER, "mcx": mcx})
        except Exception:
            mcx = {}

    out: dict[str, dict[str, tuple]] = {
        "IDX_I": {sid: meta for sid, meta in INDEX_IDS.items()},
        "NSE_EQ": {sid: meta for sid, meta in EQUITY_IDS.items()},
        "MCX_COMM": {},
    }
    for trade, rec in mcx.items():
        symbol, canonical, market = MCX_UNDERLYINGS[trade]
        out["MCX_COMM"][rec["sid"]] = (symbol, canonical, market, "FUTCOM")
    return {k: v for k, v in out.items() if v}


def chart_specs() -> dict[str, dict]:
    """chart_id -> Dhan candle request fields."""
    uni = quote_universe()
    by_canon = {}
    for seg, items in uni.items():
        for sid, meta in items.items():
            symbol, canonical, market, instrument = meta
            by_canon[canonical] = {
                "securityId": sid,
                "exchangeSegment": seg,
                "instrument": instrument,
            }
    return {
        "nifty": {**by_canon.get("NSE:NIFTY50", {}), "title": "NIFTY 50"},
        "banknifty": {**by_canon.get("NSE:BANKNIFTY", {}), "title": "BANK NIFTY"},
        "finnifty": {**by_canon.get("NSE:FINNIFTY", {}), "title": "FINNIFTY"},
        "vix": {**by_canon.get("NSE:INDIAVIX", {}), "title": "INDIA VIX"},
        "sensex": {**by_canon.get("BSE:SENSEX", {}), "title": "SENSEX"},
        "bankex": {**by_canon.get("BSE:BANKEX", {}), "title": "BANKEX"},
        "gold": {**by_canon.get("MCX:GOLD", {}), "title": "Gold"},
        "silver": {**by_canon.get("MCX:SILVER", {}), "title": "Silver"},
        "crude": {**by_canon.get("MCX:CRUDE", {}), "title": "Crude Oil"},
        "natgas": {**by_canon.get("MCX:NATGAS", {}), "title": "Natural Gas"},
        "copper": {**by_canon.get("MCX:COPPER", {}), "title": "Copper"},
        "aluminium": {**by_canon.get("MCX:ALUMINIUM", {}), "title": "Aluminium"},
        "zinc": {**by_canon.get("MCX:ZINC", {}), "title": "Zinc"},
    }
