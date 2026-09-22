from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Market = Literal["crypto", "nse", "mcx", "global", "fx", "rates", "macro"]
SourceType = Literal["primary", "broker", "aggregated", "news", "mock"]
Severity = Literal["high", "medium", "low", "info"]
AlertCategory = Literal["PRICE", "VOLUME", "VOLATILITY", "OI", "MACRO", "NEWS", "REGIME"]
Tone = Literal["neutral", "positive", "negative", "uncertain", "info"]


class Quote(BaseModel):
    symbol: str
    canonical: str
    name: str
    market: Market
    ltp: float
    change_pct: float
    change_abs: float = 0.0
    currency: str = "USD"
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    oi: float | None = None
    prev_close: float | None = None
    sparkline: list[float] = Field(default_factory=list)
    volatility: Literal["low", "normal", "elevated"] = "normal"
    source: str
    source_type: SourceType
    source_url: str | None = None
    as_of: datetime
    retrieved_at: datetime
    extra: dict[str, Any] = Field(default_factory=dict)


class ImpactLeg(BaseModel):
    asset: str
    direction: Literal["up", "down", "watch"] = "watch"
    note: str = ""


class ImpactAssessment(BaseModel):
    trigger: Literal["news", "data", "move", "outcome", "war", "event"]
    certainty: Literal["certain", "uncertain"]
    severity: Severity = "medium"
    headline: str
    detail: str = ""
    legs: list[ImpactLeg] = Field(default_factory=list)
    source_title: str = ""


class AlertSource(BaseModel):
    source: str
    source_type: SourceType
    original_url: str | None = None
    published_time: datetime | None = None


class Alert(BaseModel):
    id: str
    tone: Tone
    severity: Severity
    category: AlertCategory
    title: str
    detail: str
    asset: str
    market: Market | Literal["cross"]
    detected_at: datetime
    event_time: datetime | None = None
    importance: Severity = "medium"
    confidence: Literal["high", "medium", "low"] = "medium"
    related_assets: list[str] = Field(default_factory=list)
    sources: list[AlertSource] = Field(default_factory=list)
    highlight_symbol: str | None = None
    why: dict[str, Any] = Field(default_factory=dict)
    impact: ImpactAssessment | None = None


class BriefingItem(BaseModel):
    rank: int
    title: str
    impact: str
    assets: list[str]
    importance: Severity
    event_time_label: str
    event_at: datetime | None = None
    status: Literal["upcoming", "live", "released"] = "upcoming"
    countdown: str = ""
    sources: list[AlertSource] = Field(default_factory=list)
    impact_card: ImpactAssessment | None = None


class NewsItem(BaseModel):
    title: str
    source: str
    age: str
    market: str
    url: str | None = None
    image: str | None = None
    summary: str = ""
    impact_card: ImpactAssessment | None = None


class MacroRow(BaseModel):
    key: str
    label: str
    value: str
    direction: Literal["up", "down", "flat", "watch", "ok"]
    status: Tone = "neutral"
    note: str = ""
    change: str = ""
    why: str = ""
    watch: str = ""
    when: str = ""
    source: str = ""


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    timezone: str
    live: bool
    global_risk: str
    liquidity: str
    alert_count: int
    regime: str
    pulse: list[Quote]
    alerts: list[Alert]
    india: list[Quote]
    crypto: list[Quote]
    mcx: list[Quote]
    global_markets: list[Quote]
    watchlist: list[Quote]
    crypto_structure: dict[str, Any]
    india_structure: dict[str, Any]
    macro: list[MacroRow]
    briefing: list[BriefingItem]
    news: list[NewsItem]
    sentiment: dict[str, Any]
    sources_used: list[dict[str, str]]
    chart_series: dict[str, list[float]]
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    season_notes: list[str] = Field(default_factory=list)
    connector_status: dict[str, bool] = Field(default_factory=dict)
    impact_board: list[ImpactAssessment] = Field(default_factory=list)
