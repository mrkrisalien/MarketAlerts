"""Official DhanHQ auth helpers. Cannot mint API key/secret — Dhan only issues those on web.dhan.co."""

from __future__ import annotations

import httpx

PROFILE = "https://api.dhan.co/v2/profile"
RENEW = "https://api.dhan.co/v2/RenewToken"
GEN_TOKEN = "https://auth.dhan.co/app/generateAccessToken"


def _headers(token: str, client_id: str = "") -> dict[str, str]:
    h = {
        "access-token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if client_id:
        h["client-id"] = client_id
        h["dhanClientId"] = client_id
    return h


async def verify_access(client_id: str, token: str) -> dict:
    if not token.strip() or not client_id.strip():
        return {"ok": False, "error": "Paste Dhan client ID and access token first."}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.get(PROFILE, headers=_headers(token.strip(), client_id.strip()))
    body = {}
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:400]}
    if r.status_code >= 400:
        msg = body.get("errorMessage") or body.get("message") or body.get("remarks") or r.reason_phrase
        return {"ok": False, "error": f"Dhan rejected the token ({r.status_code}): {msg}", "detail": body}
    got_id = str(body.get("dhanClientId") or "")
    if got_id and got_id != client_id.strip():
        return {
            "ok": False,
            "error": f"Token belongs to client {got_id}, not {client_id.strip()}.",
            "profile": body,
        }
    return {
        "ok": True,
        "message": "Access token is valid. NSE/MCX quotes on this board use Client ID + Access Token only — API key and secret are not required.",
        "profile": body,
        "needs_api_key": False,
        "api_key_url": "https://web.dhan.co",
        "api_key_steps": [
            "Log in at web.dhan.co",
            "My Profile → Access DhanHQ APIs (or Get Trading & Data APIs)",
            "Toggle from Access Token to API Key",
            "Enter app name + redirect URL, then Generate API Key",
        ],
    }


async def renew_access(client_id: str, token: str) -> dict:
    if not token.strip() or not client_id.strip():
        return {"ok": False, "error": "Need a still-valid access token to renew."}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.get(RENEW, headers=_headers(token.strip(), client_id.strip()))
    try:
        body = r.json()
    except Exception:
        return {"ok": False, "error": f"Renew failed ({r.status_code})."}
    new_token = body.get("accessToken") or body.get("access_token")
    if r.status_code >= 400 or not new_token:
        msg = body.get("errorMessage") or body.get("message") or body
        return {"ok": False, "error": f"Could not renew: {msg}"}
    return {"ok": True, "access_token": new_token, "profile": body, "message": "New 24h access token from Dhan."}


async def token_from_totp(client_id: str, pin: str, totp: str) -> dict:
    """Official Dhan generateAccessToken — needs TOTP enabled on the Dhan account. Returns access token, not API key."""
    if not (client_id.strip() and pin.strip() and totp.strip()):
        return {"ok": False, "error": "Need client ID, 6-digit Dhan PIN, and current TOTP."}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.post(
            GEN_TOKEN,
            params={"dhanClientId": client_id.strip(), "pin": pin.strip(), "totp": totp.strip()},
        )
    try:
        body = r.json()
    except Exception:
        return {"ok": False, "error": f"Dhan auth failed ({r.status_code})."}
    token = body.get("accessToken")
    if not token:
        msg = body.get("errorMessage") or body.get("message") or body
        return {"ok": False, "error": f"Could not mint access token: {msg}"}
    return {
        "ok": True,
        "access_token": token,
        "client_id": body.get("dhanClientId") or client_id.strip(),
        "profile": body,
        "message": "Dhan issued a 24h access token. API key/secret still only come from Dhan Web.",
    }
