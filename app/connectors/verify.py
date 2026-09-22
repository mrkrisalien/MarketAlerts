"""Ping saved integrations without exposing secrets."""

from __future__ import annotations

import httpx

from app.connectors.dhan_auth import verify_access
from app.secrets_store import load, status


async def verify_all() -> dict:
    d = load()
    cards = status()
    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Dhan
        if d.get("dhan_client_id") and d.get("dhan_access_token"):
            results["dhan"] = await verify_access(d["dhan_client_id"], d["dhan_access_token"])
        else:
            results["dhan"] = {"ok": False, "error": "Save Client ID and Access Token first."}

        # Delta public
        try:
            r = await client.get("https://api.india.delta.exchange/v2/tickers")
            results["delta"] = {"ok": r.status_code == 200, "message": "Public tickers reachable." if r.status_code == 200 else r.reason_phrase}
        except Exception as exc:
            results["delta"] = {"ok": False, "error": str(exc)}

        # CoinGecko
        try:
            headers = {"accept": "application/json"}
            if d.get("coingecko_api_key"):
                headers["x-cg-demo-api-key"] = d["coingecko_api_key"]
            r = await client.get("https://api.coingecko.com/api/v3/ping", headers=headers)
            results["coingecko"] = {
                "ok": r.status_code == 200,
                "message": "CoinGecko reachable." if r.status_code == 200 else f"HTTP {r.status_code}",
            }
        except Exception as exc:
            results["coingecko"] = {"ok": False, "error": str(exc)}

        # NewsAPI optional
        if d.get("newsapi_key"):
            try:
                r = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"country": "us", "pageSize": 1, "apiKey": d["newsapi_key"]},
                )
                results["news"] = {"ok": r.status_code == 200, "message": "NewsAPI key accepted." if r.status_code == 200 else f"HTTP {r.status_code}"}
            except Exception as exc:
                results["news"] = {"ok": False, "error": str(exc)}
        else:
            results["news"] = {"ok": True, "message": "Using BBC/CoinDesk RSS. NewsAPI not required."}

        if d.get("deepseek_api_key"):
            try:
                r = await client.get(
                    "https://api.deepseek.com/models",
                    headers={"Authorization": f"Bearer {d['deepseek_api_key']}"},
                )
                results["deepseek"] = {
                    "ok": r.status_code == 200,
                    "message": "DeepSeek key accepted." if r.status_code == 200 else f"HTTP {r.status_code}",
                }
            except Exception as exc:
                results["deepseek"] = {"ok": False, "error": str(exc)}
        else:
            results["deepseek"] = {"ok": True, "message": "Optional. WHY? still works with local text."}

        results["firstock"] = {
            "ok": bool(d.get("firstock_jkey")),
            "message": "jKey saved." if d.get("firstock_jkey") else "No Firstock jKey saved yet.",
        }
        results["shark"] = {
            "ok": bool(d.get("shark_api_key") and d.get("shark_base_url")),
            "message": "Shark URL + key saved." if (d.get("shark_api_key") and d.get("shark_base_url")) else "Optional — skipped.",
        }
        results["tradingview"] = {"ok": True, "message": "No key required."}

    for pid, card in cards.items():
        if pid in results:
            results[pid]["label"] = card.get("label")
            if results[pid].get("ok") is False and card.get("ok") and pid != "dhan":
                pass
    return {"ok": all(v.get("ok") for k, v in results.items() if k in {"dhan", "delta"}), "accounts": results, "status": cards}
