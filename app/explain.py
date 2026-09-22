"""Simple-language WHY text. DeepSeek when a key is saved; otherwise local."""

from __future__ import annotations

import time

import httpx

from app.models import Alert, BriefingItem, NewsItem
from app.secrets_store import load

_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 20 * 60


def _local_plain(alert: Alert, news: list[NewsItem], briefing: list[BriefingItem]) -> str:
    w = alert.why or {}
    trigger = (w.get("trigger") or w.get("primary") or alert.detail or alert.title).strip()
    impact = (w.get("impact") or w.get("secondary") or "").strip()
    blob = f"{alert.title} {alert.detail} {alert.asset} {(alert.market or '')}".lower()
    hits = []
    for n in news[:12]:
        t = (n.title or "").lower()
        keys = [alert.asset.lower(), "war", "oil", "gold", "fed", "rbi", "bitcoin", "crypto", "inflation", "crude"]
        if any(k and k in t for k in keys) or any(k in blob and k in t for k in ("btc", "eth", "nifty", "gold", "crude", "vix")):
            hits.append(n.title)
    for b in briefing[:6]:
        if b.status in {"live", "released"} and any(a.lower() in blob for a in (b.assets or []) if a):
            hits.append(b.title)
    parts = [trigger]
    if hits:
        parts.append("Related tape/news: " + hits[0] + ".")
    if impact:
        parts.append(impact)
    if alert.impact and alert.impact.detail and alert.impact.detail not in parts[-1]:
        parts.append(alert.impact.detail)
    text = " ".join(p for p in parts if p)
    return text[:700]


async def explain_alert(alert: Alert, news: list[NewsItem], briefing: list[BriefingItem]) -> dict:
    key = f"{alert.id}:{alert.title[:40]}"
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < TTL:
        return hit[1]

    headlines = [n.title for n in news[:8]]
    events = [f"{b.title} ({b.status} {b.event_time_label})" for b in briefing[:6]]
    local = _local_plain(alert, news, briefing)
    out = {
        "ok": True,
        "plain": local,
        "source": "local",
        "headlines": headlines[:4],
        "model": None,
    }

    api_key = (load().get("deepseek_api_key") or "").strip()
    if api_key:
        prompt = (
            "Explain this market alert in 4 short, simple sentences for a retail trader in India. "
            "No jargon. No buy/sell advice. Say what happened, why the board flagged it, "
            "what news/event/war/data might be connected if listed, and what it can affect.\n\n"
            f"Alert: {alert.title}\nDetail: {alert.detail}\nAsset: {alert.asset}\n"
            f"Market: {alert.market}\nRule: {alert.why}\nImpact: {alert.impact}\n"
            f"Headlines: {headlines}\nCalendar: {events}\n"
        )
        try:
            async with httpx.AsyncClient(timeout=18.0) as client:
                r = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "temperature": 0.2,
                        "max_tokens": 280,
                        "messages": [
                            {"role": "system", "content": "You write plain English market explainers. Never give trade orders."},
                            {"role": "user", "content": prompt},
                        ],
                    },
                )
            if r.status_code < 400:
                text = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                if text:
                    out["plain"] = text
                    out["source"] = "deepseek"
                    out["model"] = "deepseek-chat"
            else:
                out["plain"] = local + " (DeepSeek did not answer; showing the board's own reason.)"
        except Exception:
            out["plain"] = local + " (DeepSeek unreachable; showing the board's own reason.)"

    _CACHE[key] = (now, out)
    return out
