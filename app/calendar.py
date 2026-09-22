"""Economic calendar with exact timestamps, classified vs IST now."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from xml.etree import ElementTree

import httpx

from app.models import Alert, AlertSource, BriefingItem, NewsItem
from app.impact import classify_text
from app.timeutil import IST, now_ist

def _strip_html(raw: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()


def _rss_summary(node) -> str:
    encoded = node.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    raw = ""
    if encoded is not None and (encoded.text or "").strip():
        raw = encoded.text
    else:
        raw = node.findtext("description") or ""
    text = _strip_html(raw)
    if len(text) > 900:
        return text[:880].rsplit(" ", 1)[0] + "…"
    return text


def _rss_image(node) -> str | None:
    for tag in (
        "{http://search.yahoo.com/mrss/}thumbnail",
        "{http://search.yahoo.com/mrss/}content",
    ):
        el = node.find(tag)
        if el is None:
            continue
        url = el.attrib.get("url") or el.attrib.get("href")
        if url:
            return url
    enc = node.find("enclosure")
    if enc is not None:
        url = enc.attrib.get("url")
        typ = enc.attrib.get("type") or ""
        if url and (typ.startswith("image") or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))):
            return url
    return None


WATCH = (
    "cpi",
    "ppi",
    "nfp",
    "nonfarm",
    "payroll",
    "unemployment",
    "fomc",
    "fed interest",
    "federal funds",
    "gdp",
    "retail sales",
    "crude",
    "oil inventories",
    "eia",
    "rbi",
    "repo rate",
    "india cpi",
    "pmi",
    "core pce",
    "jobless",
    "treasury",
)

IMPACT_MAP = {"High": "high", "Medium": "medium", "Low": "low", "Holiday": "low"}


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST)
    except ValueError:
        return None


def _status(event_at: datetime, now: datetime) -> str:
    if now < event_at - timedelta(minutes=2):
        return "upcoming"
    if event_at - timedelta(minutes=2) <= now <= event_at + timedelta(minutes=45):
        return "live"
    return "released"


def _countdown(event_at: datetime, now: datetime) -> str:
    delta = event_at - now
    secs = int(delta.total_seconds())
    if secs >= 0:
        hours, rem = divmod(secs, 3600)
        mins = rem // 60
        if hours >= 24:
            days = hours // 24
            return f"in {days}d {hours % 24}h"
        if hours:
            return f"in {hours}h {mins:02d}m"
        return f"in {mins}m"
    ago = -secs
    if ago < 3600:
        return f"{ago // 60}m ago"
    if ago < 86400:
        return f"{ago // 3600}h ago"
    return f"{ago // 86400}d ago"


def _relevant(title: str, country: str) -> bool:
    blob = f"{country} {title}".lower()
    return any(k in blob for k in WATCH) or country in {"USD", "INR", "CNY", "United States", "India", "China"}


def _impact_from_title(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("cpi", "nfp", "nonfarm", "fomc", "fed", "rbi", "gdp")):
        return "high"
    if any(k in t for k in ("ppi", "pmi", "eia", "crude", "unemployment", "pce")):
        return "medium"
    return "medium"


def _assets(title: str) -> list[str]:
    t = title.lower()
    if "crude" in t or "oil" in t or "eia" in t:
        return ["CRUDE", "NIFTY"]
    if "rbi" in t or "india" in t:
        return ["NIFTY", "BANKNIFTY"]
    if any(k in t for k in ("cpi", "ppi", "fed", "fomc", "nfp", "payroll", "pce")):
        return ["DXY", "GOLD", "BTC"]
    if "pmi" in t or "china" in t:
        return ["COPPER", "NIFTY"]
    return ["DXY"]


def fallback_calendar(now: datetime) -> list[dict]:
    """Known high-impact slots if the live calendar feed is down."""
    # US releases: 08:30 ET = 18:00 IST (EDT) or 19:00 IST (EST). Sep = IST = ET+9.5 → 18:00 IST.
    base = [
        ("US CPI (BLS)", datetime(2026, 9, 11, 18, 0, tzinfo=IST), "high", "BLS"),
        ("US PPI (BLS)", datetime(2026, 9, 12, 18, 0, tzinfo=IST), "medium", "BLS"),
        ("EIA Crude oil inventories", datetime(2026, 9, 17, 20, 0, tzinfo=IST), "medium", "EIA"),
        ("US Initial jobless claims", datetime(2026, 9, 18, 18, 30, tzinfo=IST), "medium", "DOL"),
        ("FOMC rate decision", datetime(2026, 9, 17, 2, 0, tzinfo=IST), "high", "Federal Reserve"),
        ("RBI MPC minutes / commentary", datetime(2026, 9, 19, 12, 0, tzinfo=IST), "medium", "RBI"),
        ("US Existing home sales", datetime(2026, 9, 19, 19, 0, tzinfo=IST), "low", "NAR"),
        ("China industrial production", datetime(2026, 9, 15, 7, 0, tzinfo=IST), "medium", "NBS"),
    ]
    # Roll weekly EIA to this week's Wednesday 20:00 IST if the hardcoded date is stale
    wed = now.date() + timedelta(days=(2 - now.weekday()) % 7)
    eia = datetime(wed.year, wed.month, wed.day, 20, 0, tzinfo=IST)
    out = []
    for title, when, importance, src in base:
        if "EIA Crude" in title:
            when = eia
        out.append(
            {
                "title": title,
                "event_at": when,
                "importance": importance,
                "country": "US" if src != "RBI" else "IN",
                "actual": None,
                "forecast": None,
                "previous": None,
                "source": src,
            }
        )
    return out


async def fetch_calendar() -> list[dict]:
    now = now_ist()
    rows: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "MarketCommand/1.0"}) as client:
            r = await client.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
            r.raise_for_status()
            payload = r.json()
        for item in payload:
            title = str(item.get("title") or item.get("event") or "")
            country = str(item.get("country") or item.get("currency") or "")
            if not title:
                continue
            dt = _parse_dt(str(item.get("date") or item.get("datetime") or ""))
            if not dt:
                continue
            impact_raw = str(item.get("impact") or "")
            impact = IMPACT_MAP.get(impact_raw, _impact_from_title(title))
            watched = _relevant(title, country)
            if impact_raw != "High" and not watched and not (country in {"USD", "INR"} and impact_raw == "Medium"):
                continue
            rows.append(
                {
                    "title": title,
                    "event_at": dt,
                    "importance": impact,
                    "country": country,
                    "actual": item.get("actual"),
                    "forecast": item.get("forecast"),
                    "previous": item.get("previous"),
                    "source": "Forex Factory calendar",
                }
            )
    except Exception:
        rows = fallback_calendar(now)

    if not rows:
        rows = fallback_calendar(now)

    rows.sort(key=lambda x: x["event_at"])
    return rows


def to_briefing(rows: list[dict], now: datetime | None = None) -> list[BriefingItem]:
    now = now or now_ist()
    upcoming = [r for r in rows if r["event_at"] >= now]
    recent = [r for r in rows if now - timedelta(hours=8) <= r["event_at"] < now]
    pick = recent[-3:] + upcoming[:10]
    if not pick:
        pick = rows[-8:]
    items = []
    for i, row in enumerate(pick, start=1):
        when: datetime = row["event_at"]
        status = _status(when, now)
        actual = row.get("actual")
        extra = ""
        if actual not in (None, "", " "):
            extra = f" Actual: {actual}."
            if row.get("forecast"):
                extra += f" Forecast: {row['forecast']}."
        impact = {
            "upcoming": "Scheduled print — watch listed assets at the exact time.",
            "live": "Release window is OPEN. Tape may reprice now.",
            "released": "Print is out. Check whether assets finished reacting." + extra,
        }[status]
        label = when.strftime("%d %b %Y, %H:%M IST")
        items.append(
            BriefingItem(
                rank=i,
                title=row["title"],
                impact=impact,
                assets=_assets(row["title"]),
                importance=row["importance"],  # type: ignore[arg-type]
                event_time_label=f"{label} · {status.upper()} · {_countdown(when, now)}",
                event_at=when,
                status=status,  # type: ignore[arg-type]
                countdown=_countdown(when, now),
                sources=[
                    AlertSource(
                        source=str(row.get("source") or "Calendar"),
                        source_type="primary" if row.get("source") in {"BLS", "EIA", "RBI", "Federal Reserve"} else "aggregated",
                    )
                ],
                impact_card=classify_text(
                    row["title"],
                    trigger_hint="data" if status != "upcoming" else "event",
                    actual=str(actual) if actual not in (None, "", " ") else None,
                ),
            )
        )
    return items


def calendar_alerts(rows: list[dict], now: datetime | None = None) -> list[Alert]:
    now = now or now_ist()
    alerts = []
    for row in rows:
        when: datetime = row["event_at"]
        status = _status(when, now)
        if status == "upcoming" and timedelta(0) <= when - now <= timedelta(minutes=45):
            tone = "uncertain"
            title = f"{row['title']} at {when.strftime('%H:%M IST')}"
        elif status == "live":
            tone = "uncertain"
            title = f"LIVE: {row['title']}"
        else:
            continue
        alerts.append(
            Alert(
                id=f"cal-{when.strftime('%Y%m%d%H%M')}-{row['title'][:24]}",
                tone=tone,  # type: ignore[arg-type]
                severity="high" if row["importance"] == "high" else "medium",
                category="MACRO",
                title=title,
                detail=f"{when.strftime('%d %b %Y, %H:%M IST')} · {status}",
                asset="MACRO",
                market="macro",
                detected_at=now,
                event_time=when,
                importance=row["importance"],  # type: ignore[arg-type]
                confidence="high",
                related_assets=_assets(row["title"]),
                sources=[AlertSource(source=str(row.get("source") or "Calendar"), source_type="aggregated")],
                why={
                    "primary": "Scheduled macro release with a fixed timestamp.",
                    "secondary": f"Relevant assets: {', '.join(_assets(row['title']))}.",
                    "technical": "Calendar clock vs IST now",
                    "confidence": "high",
                },
            )
        )
    return alerts[:6]


async def fetch_news() -> list[NewsItem]:
    now = now_ist()
    feeds = [
        ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC", "Global"),
        ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World", "Geopolitics"),
        ("https://feeds.bbci.co.uk/news/world/europe/rss.xml", "BBC Europe", "Geopolitics"),
        ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk", "Crypto"),
        ("https://www.theguardian.com/world/rss", "Guardian World", "Geopolitics"),
    ]
    items: list[NewsItem] = []
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers={"User-Agent": "MarketCommand/1.0"}) as client:
            for url, name, market in feeds:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    root = ElementTree.fromstring(r.content)
                except Exception:
                    continue
                for node in root.findall(".//item")[:8]:
                    title = _strip_html(node.findtext("title") or "")
                    link = (node.findtext("link") or "").strip()
                    pub = node.findtext("pubDate") or ""
                    age = ""
                    try:
                        pdt = parsedate_to_datetime(pub).astimezone(IST)
                        mins = int((now - pdt).total_seconds() // 60)
                        if mins < 1:
                            age = "just now"
                        elif mins < 60:
                            age = f"{mins} min ago"
                        elif mins < 1440:
                            age = f"{mins // 60}h ago"
                        else:
                            age = pdt.strftime("%d %b %H:%M IST")
                    except Exception:
                        age = pub
                    blob = f"{title} {_rss_summary(node)}".lower()
                    tag = market
                    if any(k in blob for k in ("bitcoin", "ethereum", "crypto", "token", "blockchain")):
                        tag = "Crypto"
                    elif any(k in blob for k in ("war", "military", "missile", "nato", "ukraine", "gaza", "israel", "china", "taiwan", "russia")):
                        tag = "Geopolitics"
                    if title:
                        items.append(
                            NewsItem(
                                title=title,
                                source=name,
                                age=age,
                                market=tag,
                                url=link or None,
                                image=_rss_image(node),
                                summary=_rss_summary(node),
                                impact_card=classify_text(title, trigger_hint="news"),
                            )
                        )
    except Exception:
        items = []
    seen = set()
    unique: list[NewsItem] = []
    for n in items:
        key = n.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(n)
    return unique[:24]
