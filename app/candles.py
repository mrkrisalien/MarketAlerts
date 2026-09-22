"""OHLC candles for 1D / 1W / 1M / 1Y chart cards."""

from __future__ import annotations

from datetime import timedelta

import httpx

from app.connectors.dhan_scrip import chart_specs
from app.secrets_store import load
from app.timeutil import now_ist

RANGES = {
    "1d": {"yahoo": ("1d", "5m"), "binance": ("15m", 96), "dhan": ("intraday", "5", 1)},
    "1w": {"yahoo": ("5d", "15m"), "binance": ("1h", 168), "dhan": ("intraday", "15", 7)},
    "1m": {"yahoo": ("1mo", "1d"), "binance": ("4h", 180), "dhan": ("intraday", "60", 30)},
    "1y": {"yahoo": ("1y", "1d"), "binance": ("1d", 365), "dhan": ("historical", "D", 365)},
}

CHARTS = {
    "btc": {"title": "Bitcoin (BTC)", "yahoo": None, "binance": "BTCUSDT", "source": "Binance", "source_url": "https://www.binance.com"},
    "eth": {"title": "Ethereum (ETH)", "yahoo": None, "binance": "ETHUSDT", "source": "Binance", "source_url": "https://www.binance.com"},
    "sol": {"title": "Solana (SOL)", "yahoo": None, "binance": "SOLUSDT", "source": "Binance", "source_url": "https://www.binance.com"},
    "xrp": {"title": "XRP", "yahoo": None, "binance": "XRPUSDT", "source": "Binance", "source_url": "https://www.binance.com"},
    "bnb": {"title": "BNB", "yahoo": None, "binance": "BNBUSDT", "source": "Binance", "source_url": "https://www.binance.com"},
    "nifty": {"title": "NIFTY 50", "yahoo": "^NSEI", "binance": None, "source": "Yahoo / NSE", "source_url": "https://www.nseindia.com"},
    "banknifty": {"title": "BANK NIFTY", "yahoo": "^NSEBANK", "binance": None, "source": "Yahoo / NSE", "source_url": "https://www.nseindia.com"},
    "sensex": {"title": "SENSEX", "yahoo": "^BSESN", "binance": None, "source": "Yahoo / BSE", "source_url": "https://www.bseindia.com"},
    "finnifty": {"title": "FINNIFTY", "yahoo": "NIFTY_FIN_SERVICE.NS", "yahoo_alt": "^CNXFIN", "binance": None, "source": "Yahoo / NSE", "source_url": "https://www.nseindia.com"},
    "bankex": {"title": "BANKEX", "yahoo": "BSE-BANK.BO", "yahoo_alt": "^BSEBANK", "binance": None, "source": "Yahoo / BSE", "source_url": "https://www.bseindia.com"},
    "vix": {"title": "INDIA VIX", "yahoo": "^INDIAVIX", "binance": None, "source": "Yahoo / NSE", "source_url": "https://www.nseindia.com"},
    "gold": {"title": "Gold", "yahoo": "GC=F", "binance": None, "source": "Yahoo COMEX", "source_url": "https://www.cmegroup.com"},
    "silver": {"title": "Silver", "yahoo": "SI=F", "binance": None, "source": "Yahoo COMEX", "source_url": "https://www.cmegroup.com"},
    "crude": {"title": "Crude Oil", "yahoo": "CL=F", "binance": None, "source": "Yahoo NYMEX", "source_url": "https://www.eia.gov"},
    "natgas": {"title": "Natural Gas", "yahoo": "NG=F", "binance": None, "source": "Yahoo NYMEX", "source_url": "https://www.cmegroup.com"},
    "copper": {"title": "Copper", "yahoo": "HG=F", "binance": None, "source": "Yahoo COMEX", "source_url": "https://www.cmegroup.com"},
    "aluminium": {"title": "Aluminium", "yahoo": "ALI=F", "binance": None, "source": "Yahoo COMEX", "source_url": "https://www.cmegroup.com"},
    "zinc": {"title": "Zinc", "yahoo": None, "binance": None, "source": "MCX / Dhan", "source_url": "https://www.mcxindia.com/market-data/market-watch"},
}

HEADERS = {"User-Agent": "Mozilla/5.0 MarketCommand/1.0"}


def _pack(t, o, h, l, c) -> dict | None:
    if None in (t, o, h, l, c):
        return None
    return {"time": int(t), "open": float(o), "high": float(h), "low": float(l), "close": float(c)}


async def _yahoo(client: httpx.AsyncClient, symbol: str, tf: str) -> list[dict]:
    rng, interval = RANGES[tf]["yahoo"]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = await client.get(url, params={"range": rng, "interval": interval})
    r.raise_for_status()
    result = (r.json().get("chart") or {}).get("result") or []
    if not result:
        return []
    node = result[0]
    ts = node.get("timestamp") or []
    q = ((node.get("indicators") or {}).get("quote") or [{}])[0]
    out = []
    for i, t in enumerate(ts):
        bar = _pack(
            t,
            (q.get("open") or [None] * len(ts))[i] if i < len(q.get("open") or []) else None,
            (q.get("high") or [None] * len(ts))[i] if i < len(q.get("high") or []) else None,
            (q.get("low") or [None] * len(ts))[i] if i < len(q.get("low") or []) else None,
            (q.get("close") or [None] * len(ts))[i] if i < len(q.get("close") or []) else None,
        )
        if bar:
            out.append(bar)
    return out


async def _binance(client: httpx.AsyncClient, symbol: str, tf: str) -> list[dict]:
    interval, limit = RANGES[tf]["binance"]
    r = await client.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    r.raise_for_status()
    out = []
    for row in r.json():
        bar = _pack(int(row[0]) // 1000, row[1], row[2], row[3], row[4])
        if bar:
            out.append(bar)
    return out


async def _dhan_candles(client: httpx.AsyncClient, spec: dict, tf: str) -> list[dict]:
    token = load().get("dhan_access_token") or ""
    client_id = load().get("dhan_client_id") or ""
    sid = spec.get("securityId")
    if not token or not sid:
        return []
    kind, interval, days = RANGES[tf]["dhan"]
    now = now_ist()
    start = now - timedelta(days=days)
    headers = {
        "access-token": token,
        "client-id": client_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if kind == "intraday":
        url = "https://api.dhan.co/v2/charts/intraday"
        body = {
            "securityId": str(sid),
            "exchangeSegment": spec["exchangeSegment"],
            "instrument": spec["instrument"],
            "interval": str(interval),
            "oi": False,
            "fromDate": start.strftime("%Y-%m-%d 09:00:00"),
            "toDate": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        url = "https://api.dhan.co/v2/charts/historical"
        body = {
            "securityId": str(sid),
            "exchangeSegment": spec["exchangeSegment"],
            "instrument": spec["instrument"],
            "expiryCode": 0,
            "oi": False,
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate": now.strftime("%Y-%m-%d"),
        }
    r = await client.post(url, headers=headers, json=body)
    r.raise_for_status()
    payload = r.json()
    opens, highs, lows, closes, ts = payload.get("open") or [], payload.get("high") or [], payload.get("low") or [], payload.get("close") or [], payload.get("timestamp") or []
    out = []
    for i, t in enumerate(ts):
        bar = _pack(
            t,
            opens[i] if i < len(opens) else None,
            highs[i] if i < len(highs) else None,
            lows[i] if i < len(lows) else None,
            closes[i] if i < len(closes) else None,
        )
        if bar:
            out.append(bar)
    return out


async def fetch_candles(chart_id: str, tf: str = "1d") -> dict:
    spec = CHARTS.get(chart_id)
    if not spec:
        return {"id": chart_id, "candles": [], "error": "unknown chart"}
    tf = tf if tf in RANGES else "1d"
    dhan_spec = chart_specs().get(chart_id) or {}
    async with httpx.AsyncClient(timeout=14.0, headers=HEADERS) as client:
        try:
            if spec["binance"]:
                candles = await _binance(client, spec["binance"], tf)
                source, source_url = spec["source"], spec["source_url"]
            else:
                candles = []
                source, source_url = spec["source"], spec["source_url"]
                if dhan_spec.get("securityId") and load().get("dhan_access_token"):
                    try:
                        candles = await _dhan_candles(client, dhan_spec, tf)
                        if candles:
                            source, source_url = "DhanHQ live", "https://dhanhq.co/docs/v2/historical-data/"
                    except Exception:
                        candles = []
                if not candles and spec.get("yahoo"):
                    candles = await _yahoo(client, spec["yahoo"], tf)
                    if not candles and spec.get("yahoo_alt"):
                        candles = await _yahoo(client, spec["yahoo_alt"], tf)
                    source, source_url = spec["source"], spec["source_url"]
        except Exception as exc:
            return {
                "id": chart_id,
                "title": spec["title"],
                "tf": tf,
                "candles": [],
                "source": spec["source"],
                "source_url": spec["source_url"],
                "error": exc.__class__.__name__,
            }
    return {
        "id": chart_id,
        "title": spec["title"],
        "tf": tf,
        "candles": candles,
        "source": source,
        "source_url": source_url,
        "error": None,
    }


def chart_catalog() -> list[dict]:
    return [{"id": k, "title": v["title"], "source": v["source"], "source_url": v["source_url"]} for k, v in CHARTS.items()]
