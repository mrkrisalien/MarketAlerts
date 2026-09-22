"""Dhan option-chain summaries + NSE participant OI (best effort)."""

from __future__ import annotations

import csv
import io
import time
from datetime import timedelta

import httpx

from app.secrets_store import load
from app.timeutil import now_ist

_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 90

INDEX = [
    {"id": "nifty", "name": "NIFTY 50", "kind": "Index options", "sid": 13, "seg": "IDX_I"},
    {"id": "banknifty", "name": "BANK NIFTY", "kind": "Index options", "sid": 25, "seg": "IDX_I"},
    {"id": "finnifty", "name": "FINNIFTY", "kind": "Index options", "sid": 27, "seg": "IDX_I"},
    {"id": "sensex", "name": "SENSEX", "kind": "Index options", "sid": 51, "seg": "IDX_I"},
]
CASH = [
    {"id": "reliance", "name": "RELIANCE", "kind": "Cash options", "sid": 2885, "seg": "NSE_EQ"},
    {"id": "hdfcbank", "name": "HDFCBANK", "kind": "Cash options", "sid": 1333, "seg": "NSE_EQ"},
    {"id": "infy", "name": "INFY", "kind": "Cash options", "sid": 1594, "seg": "NSE_EQ"},
]


def _headers() -> dict[str, str]:
    s = load()
    return {
        "access-token": s.get("dhan_access_token") or "",
        "client-id": s.get("dhan_client_id") or "",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _summarize(name: str, kind: str, expiry: str, payload: dict) -> dict:
    data = payload.get("data") or payload
    spot = data.get("last_price")
    oc = data.get("oc") or {}
    call_oi = put_oi = call_chg = put_chg = 0.0
    max_ce = max_pe = ("—", 0.0)
    atm_iv = None
    atm_gap = 1e18
    rows = []
    for strike_s, node in oc.items():
        try:
            strike = float(strike_s)
        except ValueError:
            continue
        ce = node.get("ce") or {}
        pe = node.get("pe") or {}
        coi = float(ce.get("oi") or 0)
        poi = float(pe.get("oi") or 0)
        call_oi += coi
        put_oi += poi
        call_chg += float(ce.get("oi") or 0) - float(ce.get("previous_oi") or 0)
        put_chg += float(pe.get("oi") or 0) - float(pe.get("previous_oi") or 0)
        if coi > max_ce[1]:
            max_ce = (strike, coi)
        if poi > max_pe[1]:
            max_pe = (strike, poi)
        if spot is not None and abs(strike - float(spot)) < atm_gap:
            atm_gap = abs(strike - float(spot))
            ivs = [ce.get("implied_volatility"), pe.get("implied_volatility")]
            nums = [float(x) for x in ivs if x not in (None, "")]
            atm_iv = sum(nums) / len(nums) if nums else atm_iv
        if coi or poi:
            rows.append({"strike": strike, "call_oi": coi, "put_oi": poi})
    pcr = (put_oi / call_oi) if call_oi else None
    rows.sort(key=lambda r: r["call_oi"] + r["put_oi"], reverse=True)
    return {
        "name": name,
        "kind": kind,
        "expiry": expiry,
        "spot": spot,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "pcr": round(pcr, 2) if pcr is not None else None,
        "call_oi_chg": call_chg,
        "put_oi_chg": put_chg,
        "max_call": max_ce[0],
        "max_put": max_pe[0],
        "atm_iv": round(atm_iv, 2) if atm_iv is not None else None,
        "top": rows[:8],
        "ok": True,
        "error": None,
    }


async def _one(client: httpx.AsyncClient, spec: dict) -> dict:
    body = {"UnderlyingScrip": spec["sid"], "UnderlyingSeg": spec["seg"]}
    ex = await client.post("https://api.dhan.co/v2/optionchain/expirylist", json=body)
    if ex.status_code >= 400:
        return {**spec, "ok": False, "error": f"Expiry HTTP {ex.status_code}", "kind": spec["kind"], "name": spec["name"]}
    dates = ex.json().get("data") or []
    if not dates:
        return {**spec, "ok": False, "error": "No expiry listed", "kind": spec["kind"], "name": spec["name"]}
    expiry = dates[0]
    ch = await client.post(
        "https://api.dhan.co/v2/optionchain",
        json={**body, "Expiry": expiry},
    )
    if ch.status_code >= 400:
        return {**spec, "ok": False, "error": f"Chain HTTP {ch.status_code}", "expiry": expiry, "kind": spec["kind"], "name": spec["name"]}
    return _summarize(spec["name"], spec["kind"], expiry, ch.json())


async def fetch_fo() -> dict:
    cached = _CACHE.get("fo")
    if cached and time.time() - cached[0] < TTL:
        return cached[1]
    s = load()
    if not (s.get("dhan_access_token") and s.get("dhan_client_id")):
        empty = {
            "ok": False,
            "error": "Connect Dhan (Client ID + Access Token) in Settings to load live option chain OI/PCR.",
            "index": [],
            "cash": [],
            "participants": [],
        }
        return empty
    headers = _headers()
    index, cash = [], []
    specs = INDEX + CASH
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        for i, spec in enumerate(specs):
            rec = await _one(client, spec)
            (index if spec in INDEX else cash).append(rec)
            if i < len(specs) - 1:
                await _sleep()
    out = {
        "ok": any(x.get("ok") for x in index + cash),
        "error": None,
        "index": index,
        "cash": cash,
        "participants": await fetch_participant_oi(),
        "source": "DhanHQ option chain",
        "source_url": "https://dhanhq.co/docs/v2/option-chain/",
    }
    _CACHE["fo"] = (time.time(), out)
    return out


async def _sleep() -> None:
    import asyncio

    await asyncio.sleep(3.05)


async def fetch_participant_oi() -> list[dict]:
    now = now_ist()
    headers = {
        "User-Agent": "Mozilla/5.0 MarketCommand/1.0",
        "Accept": "text/csv,*/*",
        "Referer": "https://www.nseindia.com/",
    }
    async with httpx.AsyncClient(timeout=12.0, headers=headers, follow_redirects=True) as client:
        for i in range(0, 5):
            day = now - timedelta(days=i)
            stamp = day.strftime("%d%m%Y")
            url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{stamp}.csv"
            try:
                r = await client.get(url)
            except Exception:
                continue
            if r.status_code >= 400 or "Client Type" not in r.text[:400] and "client type" not in r.text.lower()[:400]:
                continue
            rows = []
            reader = csv.DictReader(io.StringIO(r.text))
            for row in reader:
                label = (row.get("Client Type") or row.get("ClientType") or next(iter(row.values()), "")).strip()
                if not label or label.lower().startswith("total"):
                    continue
                rows.append(
                    {
                        "client": label,
                        "fut_idx_long": row.get("Future Index Long") or "—",
                        "fut_idx_short": row.get("Future Index Short") or "—",
                        "opt_idx_call_long": row.get("Option Index Call Long") or "—",
                        "opt_idx_put_long": row.get("Option Index Put Long") or "—",
                        "fut_stk_long": row.get("Future Stock Long") or "—",
                        "fut_stk_short": row.get("Future Stock Short") or "—",
                    }
                )
            if rows:
                return [{"as_of": day.strftime("%d %b %Y"), "url": url, "rows": rows[:12]}]
    return []
