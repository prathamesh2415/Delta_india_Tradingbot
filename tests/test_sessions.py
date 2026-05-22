"""Tests for session filtering."""

from __future__ import annotations

from datetime import datetime, timezone

from trading_bot.utils.sessions import is_london_ny_session


def test_inside_session() -> None:
    dt = datetime(2025, 5, 22, 15, 0, tzinfo=timezone.utc)
    assert is_london_ny_session(dt, 13, 21) is True


def test_outside_session() -> None:
    dt = datetime(2025, 5, 22, 8, 0, tzinfo=timezone.utc)
    assert is_london_ny_session(dt, 13, 21) is False


def test_boundary_start() -> None:
    dt = datetime(2025, 5, 22, 13, 0, tzinfo=timezone.utc)
    assert is_london_ny_session(dt, 13, 21) is True


def test_boundary_end() -> None:
    dt = datetime(2025, 5, 22, 21, 0, tzinfo=timezone.utc)
    assert is_london_ny_session(dt, 13, 21) is False
