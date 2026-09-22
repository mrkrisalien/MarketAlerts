"""Canonical symbol map so every feed collapses to one identity."""

from __future__ import annotations

ALIASES: dict[str, str] = {
    "BTC": "CRYPTO:BTC",
    "BITCOIN": "CRYPTO:BTC",
    "BTCUSDT": "CRYPTO:BTC",
    "ETH": "CRYPTO:ETH",
    "ETHEREUM": "CRYPTO:ETH",
    "SOL": "CRYPTO:SOL",
    "XRP": "CRYPTO:XRP",
    "BNB": "CRYPTO:BNB",
    "NIFTY": "NSE:NIFTY50",
    "NIFTY50": "NSE:NIFTY50",
    "NIFTY 50": "NSE:NIFTY50",
    "BANKNIFTY": "NSE:BANKNIFTY",
    "BANK NIFTY": "NSE:BANKNIFTY",
    "SENSEX": "BSE:SENSEX",
    "FINNIFTY": "NSE:FINNIFTY",
    "MIDCAP": "NSE:NIFTYMIDCAP",
    "INDIA VIX": "NSE:INDIAVIX",
    "INDIAVIX": "NSE:INDIAVIX",
    "GOLD": "MCX:GOLD",
    "SILVER": "MCX:SILVER",
    "CRUDE": "MCX:CRUDE",
    "CRUDE OIL": "MCX:CRUDE",
    "NATURAL GAS": "MCX:NATGAS",
    "NATGAS": "MCX:NATGAS",
    "COPPER": "MCX:COPPER",
    "ALUMINIUM": "MCX:ALUMINIUM",
    "ZINC": "MCX:ZINC",
    "DXY": "FX:DXY",
    "US10Y": "RATES:US10Y",
    "US 10Y": "RATES:US10Y",
}


def canonical(symbol: str) -> str:
    key = symbol.strip().upper()
    return ALIASES.get(key, key)
