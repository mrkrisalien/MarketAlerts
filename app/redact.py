"""Strip secrets and raw broker payloads before they leave the server."""

from __future__ import annotations

from typing import Any

DROP = {
    "access_token",
    "accesstoken",
    "refresh_token",
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "token",
    "jkey",
    "pin",
    "totp",
    "password",
    "authorization",
    "profile",
    "detail",
    "raw",
    "dhan_access_token",
    "dhan_api_key",
    "dhan_api_secret",
    "firstock_api_key",
    "firstock_jkey",
    "delta_api_key",
    "delta_api_secret",
    "shark_api_key",
    "shark_api_secret",
    "coingecko_api_key",
    "newsapi_key",
    "deepseek_api_key",
    "board_password",
}


def _drop_key(name: str) -> bool:
    n = name.lower().replace("-", "_")
    if n in DROP:
        return True
    return n.endswith(("_secret", "_token", "_password", "_jkey", "_api_key"))


def scrub(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if _drop_key(str(k)):
                continue
            out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    return obj


def dhan_public(result: dict) -> dict:
    return {
        "ok": bool(result.get("ok")),
        "message": result.get("message"),
        "error": result.get("error") if isinstance(result.get("error"), str) else None,
        "needs_api_key": result.get("needs_api_key"),
        "api_key_url": result.get("api_key_url"),
        "api_key_steps": result.get("api_key_steps"),
    }
