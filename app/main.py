from hashlib import sha256
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import asyncio

from pydantic import BaseModel

from app.config import settings
from app.candles import chart_catalog, fetch_candles
from app.portals import FIELD_LABELS, LIVE_FEEDS, PORTALS, WEBSITES
from app.secrets_store import filled, load as load_secrets, masked, save, status
from app.connectors.dhan_auth import renew_access, token_from_totp, verify_access
from app.connectors.verify import verify_all
from app.explain import explain_alert
from app.connectors.dhan_fo import fetch_fo
from app.service import service

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title=settings.app_name, version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

GATE_COOKIE = "mc_gate"


def _gate_on() -> bool:
    return bool((settings.board_password or os.getenv("BOARD_PASSWORD") or "").strip())


def _gate_secret() -> str:
    return (settings.board_password or os.getenv("BOARD_PASSWORD") or "").strip()


def _gate_token() -> str:
    return hmac.new(b"marketcommand-gate", _gate_secret().encode(), sha256).hexdigest()


def _authed(request: Request) -> bool:
    if not _gate_on():
        return True
    return hmac.compare_digest(request.cookies.get(GATE_COOKIE) or "", _gate_token())


@app.middleware("http")
async def board_gate(request: Request, call_next):
    if not _gate_on():
        return await call_next(request)
    path = request.url.path
    if path.startswith("/static") or path in {"/login", "/api/health"}:
        return await call_next(request)
    if _authed(request):
        return await call_next(request)
    if path.startswith("/api") or path.startswith("/ws"):
        return HTMLResponse("Sign in required", status_code=401)
    return RedirectResponse("/login", status_code=302)


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(ROOT / "templates" / "index.html")


@app.get("/login")
async def login_page() -> HTMLResponse:
    return HTMLResponse(
        """<!DOCTYPE html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>MarketCommand</title>
<link href="/static/css/app.css?v=news-macro1" rel="stylesheet"/></head>
<body><div class="app" style="display:grid;place-items:center;min-height:100vh">
<form method="post" action="/login" class="card" style="width:min(360px,92vw);padding:24px">
<h1 style="font-size:20px;margin:0 0 8px">MarketCommand</h1>
<p class="text-secondary">This public URL is locked. Enter the board password.</p>
<input name="password" type="password" class="search" style="width:100%;margin:12px 0;padding:10px 12px;border:1px solid #dadce0;border-radius:8px" placeholder="Password" autofocus/>
<button type="submit" class="view-more">Open board</button>
</form></div></body></html>"""
    )


@app.post("/login")
async def login_submit(password: str = Form("")):
    if _gate_on() and hmac.compare_digest(password.strip(), _gate_secret()):
        res = RedirectResponse("/", status_code=302)
        res.set_cookie(GATE_COOKIE, _gate_token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
        return res
    return RedirectResponse("/login", status_code=302)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "app": settings.app_name}


@app.get("/api/dashboard")
async def dashboard() -> dict:
    snap = await service.snapshot()
    return snap.model_dump(mode="json")


@app.get("/api/alerts")
async def alerts() -> dict:
    snap = await service.snapshot()
    return {"alerts": [a.model_dump(mode="json") for a in snap.alerts]}


@app.get("/api/settings")
async def get_settings() -> dict:
    return {
        "portals": PORTALS,
        "labels": FIELD_LABELS,
        "values": masked(),
        "status": status(),
        "filled": filled(),
        "websites": WEBSITES,
        "live_feeds": LIVE_FEEDS,
        "charts": chart_catalog(),
    }


class SettingsIn(BaseModel):
    keys: dict[str, str]


class DhanConnectIn(BaseModel):
    dhan_client_id: str
    dhan_access_token: str


class DhanTotpIn(BaseModel):
    dhan_client_id: str
    pin: str
    totp: str


def _dhan_creds(client_id: str, token: str) -> tuple[str, str]:
    stored = load_secrets()
    if not client_id or client_id == "********":
        client_id = stored.get("dhan_client_id") or ""
    if not token or token == "********":
        token = stored.get("dhan_access_token") or ""
    return client_id, token


@app.post("/api/settings")
async def post_settings(body: SettingsIn) -> dict:
    try:
        save(body.keys)
        service.invalidate()
        return {"ok": True, "status": status(), "values": masked(), "filled": filled(), "message": "Saved on this machine."}
    except Exception as exc:
        return {"ok": False, "error": f"Could not save: {exc.__class__.__name__}: {exc}"}


@app.post("/api/settings/verify")
async def settings_verify() -> dict:
    return await verify_all()


@app.post("/api/dhan/connect")
async def dhan_connect(body: DhanConnectIn) -> dict:
    client_id, token = _dhan_creds(body.dhan_client_id, body.dhan_access_token)
    result = await verify_access(client_id, token)
    if result.get("ok"):
        save({"dhan_client_id": client_id, "dhan_access_token": token})
        service.invalidate()
        result["status"] = status()
        result["values"] = masked()
    return result


@app.post("/api/dhan/renew")
async def dhan_renew(body: DhanConnectIn) -> dict:
    client_id, token = _dhan_creds(body.dhan_client_id, body.dhan_access_token)
    result = await renew_access(client_id, token)
    if result.get("ok") and result.get("access_token"):
        save({"dhan_client_id": client_id, "dhan_access_token": result["access_token"]})
        service.invalidate()
        result["values"] = masked()
        result["status"] = status()
    return result


@app.post("/api/dhan/totp-token")
async def dhan_totp_token(body: DhanTotpIn) -> dict:
    result = await token_from_totp(body.dhan_client_id, body.pin, body.totp)
    if result.get("ok") and result.get("access_token"):
        save({"dhan_client_id": result.get("client_id") or body.dhan_client_id, "dhan_access_token": result["access_token"]})
        service.invalidate()
        result["values"] = masked()
        result["status"] = status()
    return result


class WhyIn(BaseModel):
    id: str


@app.post("/api/alerts/why")
async def alert_why(body: WhyIn) -> dict:
    snap = await service.snapshot()
    alert = next((a for a in snap.alerts if a.id == body.id), None)
    if not alert:
        return {"ok": False, "error": "That alert is no longer on the board."}
    return await explain_alert(alert, snap.news, snap.briefing)


@app.get("/api/fo")
async def fo_page() -> dict:
    return await fetch_fo()


@app.get("/api/candles/{chart_id}")
async def candles(chart_id: str, tf: str = "1d") -> dict:
    return await fetch_candles(chart_id, tf)


@app.get("/api/sources")
async def sources() -> dict:
    return {"websites": WEBSITES, "charts": chart_catalog(), "live_feeds": LIVE_FEEDS}


@app.websocket("/ws/live")
async def live_socket(ws: WebSocket) -> None:
    if _gate_on():
        cookie = ""
        for part in (ws.headers.get("cookie") or "").split(";"):
            if part.strip().startswith(GATE_COOKIE + "="):
                cookie = part.split("=", 1)[-1].strip()
        if not hmac.compare_digest(cookie, _gate_token()):
            await ws.close(code=1008)
            return
    await ws.accept()
    try:
        while True:
            snap = await service.snapshot()
            await ws.send_json(snap.model_dump(mode="json"))
            await asyncio.sleep(settings.refresh_seconds)
    except WebSocketDisconnect:
        return
