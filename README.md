# MarketCommand (MarketAlerts)

A **market command center** for India + crypto: live prices, rule-based alerts, F&O context, macro tape, and news with impact mapping. Times are **IST**.

It is a **read-only desk**. It does not place orders. You still trade in Dhan, Delta, or your own terminal.

## What you get

| Area | What it shows |
| --- | --- |
| Dashboard | Pulse, alerts, BTC / Nifty / Gold charts, lists, briefing, news, sentiment, impact |
| Charts | In-app candles (1D / 1W / 1M / 1Y) grouped **Crypto · NSE · MCX** |
| Crypto | Top 5 coins + **structure** (BTC.D, mcap, volume, stables, Delta funding/OI) |
| India / F&O | Indices, watchlist, Dhan option chain PCR and heavy strikes |
| MCX | Gold, silver, crude, natgas, copper, aluminium, zinc |
| Global | US/EU/Asia indices + **macro tape** (level, change, why it matters, what to watch) |
| News | Click a story for summary + impact; categories **Geopolitics / Global / Crypto** |
| Settings | Paste broker/API keys on this machine only (`data/secrets.json`) |

Alerts and **WHY?** fire from **explicit rules** (price %, VIX, calendar, headline classifiers, DXY/crude/gold playbooks). Color is used when a rule fires, not because a print is green.

## Stack

- Python 3.11+ · FastAPI · Uvicorn
- Bootstrap 5 + Lightweight Charts
- Live refresh over WebSocket (`/ws/live`)

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

Open [http://127.0.0.1:8050](http://127.0.0.1:8050).

Optional `.env`:

```
BOARD_PASSWORD=          # lock the board before any public URL
REFRESH_SECONDS=8
ENABLE_LIVE_BINANCE=true
ENABLE_LIVE_CRYPTO=true
ENABLE_LIVE_YAHOO=true
COINGECKO_API_KEY=       # demo key reduces CoinGecko 429s
```

Keys you paste in **Settings** are stored in `data/secrets.json` (gitignored). Never commit that file.

## Data sources (honest labels)

| Market | Live path (free or with your account) | Fallback |
| --- | --- | --- |
| Crypto LTP | Binance public ticker | CoinGecko |
| Crypto structure | CoinGecko markets/global | Sum of BTC/ETH/SOL/XRP/BNB |
| Crypto funding / OI | Delta India **public** tickers | Note on the Structure card |
| NSE / BSE / MCX / F&O | **DhanHQ** (Client ID + 24h access token) | Seed/mock until connected |
| US indices, DXY, 10Y | Yahoo Finance (often delayed) | Last good snapshot |
| News | BBC / Guardian / CoinDesk RSS | Empty list |
| Calendar | Public economic calendar | Empty briefing |
| WHY? | Local plain English | Optional DeepSeek key |

**NSE/MCX official realtime is licensed.** This app does not scrape NSE/MCX. India tape is meant to come from a **broker API you already have** (Dhan first, Firstock as alternate). Yahoo/CME-converted metals are research, not MCX official.

### Dhan (India live)

1. Open [web.dhan.co](https://web.dhan.co) → Access DhanHQ APIs.
2. Copy **Client ID** and **Access Token** (token lasts about 24 hours).
3. Settings → DhanHQ → Save → Connect.

API key/secret are created only on Dhan Web if you need them; the board’s quote path mainly needs client id + token.

### Optional keys

- **CoinGecko Demo** — structure (dominance, total mcap, USDT+USDC).
- **DeepSeek** — richer WHY? text. Without it, WHY? still explains the rule in simple English.
- **NewsAPI** — optional; RSS already runs.
- **Delta key** — not required for public tickers.

## Using it as a trade setup

1. **What Matters Today** — if CPI / Fed / RBI / EIA is live or imminent, wait for the clock.
2. **Macro tape** — 10Y, DXY, USDINR, VIX, crude are drivers; Nifty/Gold/BTC follow.
3. Trade only when an **alert** fires. Tap **WHY?** (trigger + impact + related names).
4. Check **If this moves → watch that** (e.g. DXY up → gold/BTC offered; VIX jump → index caution).
5. Pick the venue: **F&O** for indices, **MCX charts** for metals/energy, **Crypto structure** (funding, BTC.D) for coins.
6. Write bias / invalidation, then **execute in the broker**. Flatten or recheck if a war/CPI/VIX alert appears while you are in.

This is context, not a signal service.

## Phone / public URL

The PC at `127.0.0.1` is local only.

**Same-day phone access (PC must stay on):**

```powershell
winget install --id Cloudflare.cloudflared -e
cloudflared tunnel --url http://127.0.0.1:8050
```

Set `BOARD_PASSWORD` in `.env` first, then restart Uvicorn. Open the `https://….trycloudflare.com` link on the phone and sign in.

The free quick-tunnel URL **changes** every time you start `cloudflared`. The PC off = link dead.

**24/7 with the PC off:** deploy the included `Dockerfile` / `render.yaml` (e.g. Render). Set `BOARD_PASSWORD`. Free hosts sleep and may drop `secrets.json`; paste Dhan again after wake.

## Project layout

```
app/                 FastAPI app, connectors, alerts, impact
app/connectors/      Binance, CoinGecko, Delta, Dhan, Yahoo
static/              CSS, JS, category graphics
templates/index.html Single-page board
data/secrets.json    Local keys (not in git)
Dockerfile           Production image (PORT from the host)
```

Health check: `GET /api/health`.

## License

Use and modify for your own desk. Broker and exchange terms still apply to any keys you connect.
