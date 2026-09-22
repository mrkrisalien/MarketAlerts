from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def spark(base: float, n: int = 24, drift: float = 0.0, vol: float = 0.012) -> list[float]:
    """Deterministic-looking path from a seed price (not a forecast)."""
    values = []
    px = base
    for i in range(n):
        wave = ((i % 7) - 3) * vol * 0.35
        px = px * (1 + drift / n + wave * 0.15)
        values.append(round(px, 4))
    values[-1] = base
    return values
