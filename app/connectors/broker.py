"""Placeholders for licensed / broker feeds. Do not scrape NSE/MCX HTML."""

from app.models import Quote


class NseBrokerConnector:
    name = "NSE via broker"
    source_type = "broker"

    async def fetch(self) -> list[Quote]:
        return []


class McxBrokerConnector:
    name = "MCX via broker"
    source_type = "broker"

    async def fetch(self) -> list[Quote]:
        return []
