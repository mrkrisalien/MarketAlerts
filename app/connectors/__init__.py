from __future__ import annotations

from typing import Protocol

from app.models import Quote


class MarketConnector(Protocol):
    name: str
    source_type: str

    async def fetch(self) -> list[Quote]:
        ...
