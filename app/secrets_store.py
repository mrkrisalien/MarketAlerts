"""Save broker keys locally and report connection status per Settings card."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "secrets.json"
_lock = Lock()

KEYS = [
    "dhan_client_id",
    "dhan_access_token",
    "dhan_api_key",
    "dhan_api_secret",
    "firstock_user_id",
    "firstock_vendor_code",
    "firstock_api_key",
    "firstock_jkey",
    "delta_api_key",
    "delta_api_secret",
    "shark_base_url",
    "shark_api_key",
    "shark_api_secret",
    "coingecko_api_key",
    "newsapi_key",
    "deepseek_api_key",
]

MASKED = set(KEYS)


def _empty() -> dict[str, str]:
    return {k: "" for k in KEYS}


def load() -> dict[str, str]:
    data = _empty()
    if PATH.exists():
        try:
            raw = json.loads(PATH.read_text(encoding="utf-8"))
            for k in KEYS:
                if isinstance(raw.get(k), str):
                    data[k] = raw[k]
        except Exception:
            pass
    return data


def save(updates: dict[str, str]) -> dict[str, str]:
    with _lock:
        data = load()
        for k in KEYS:
            if k not in updates or updates[k] is None:
                continue
            val = str(updates[k]).strip()
            if val in {"", "********", "••••••••"}:
                continue
            data[k] = val
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def masked() -> dict[str, str]:
    """Never send stored credentials to the browser."""
    return {k: "" for k in KEYS}


def filled() -> dict[str, bool]:
    d = load()
    return {k: bool(v) for k, v in d.items()}


def flags() -> dict[str, bool]:
    return {k: bool(v.get("ok")) for k, v in status().items()}


def status() -> dict[str, dict]:
    """Keys must match Settings portal ids."""
    d = load()
    dhan_ok = bool(d.get("dhan_access_token") and d.get("dhan_client_id"))
    dhan_partial = bool(d.get("dhan_api_key") and d.get("dhan_api_secret")) and not dhan_ok
    return {
        "dhan": {
            "ok": dhan_ok,
            "label": "Connected" if dhan_ok else ("Saved API key — still need access token" if dhan_partial else "Not connected"),
        },
        "firstock": {
            "ok": bool(d.get("firstock_jkey")),
            "label": "Connected" if d.get("firstock_jkey") else "Not connected",
        },
        "delta": {"ok": True, "label": "Public feed ready"},
        "shark": {
            "ok": bool(d.get("shark_api_key") and d.get("shark_base_url")),
            "label": "Connected" if (d.get("shark_api_key") and d.get("shark_base_url")) else "Optional — not set",
        },
        "coingecko": {
            "ok": bool(d.get("coingecko_api_key")),
            "label": "Connected" if d.get("coingecko_api_key") else "Optional — not set",
        },
        "tradingview": {"ok": True, "label": "No key required"},
        "news": {
            "ok": True,
            "label": "NewsAPI connected" if d.get("newsapi_key") else "RSS active (NewsAPI optional)",
        },
        "deepseek": {
            "ok": bool(d.get("deepseek_api_key")),
            "label": "Connected" if d.get("deepseek_api_key") else "Optional — WHY? uses local text until a key is saved",
        },
    }
