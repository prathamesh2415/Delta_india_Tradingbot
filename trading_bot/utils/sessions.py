"""Trading session filters (London–New York overlap in UTC)."""

from __future__ import annotations

from datetime import datetime, timezone


def is_london_ny_session(
    dt: datetime | None = None,
    start_hour: int = 13,
    end_hour: int = 21,
) -> bool:
    """
    Return True if UTC time falls within the London–NY overlap window.

    Default 13:00–21:00 UTC covers London afternoon through NY close.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    hour = dt.hour
    if start_hour <= end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour
