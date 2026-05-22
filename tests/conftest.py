"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DELTA_API_KEY", "test_key")
    monkeypatch.setenv("DELTA_API_SECRET", "test_secret")
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "test.log"))


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Synthetic OHLCV with a clear buy signal + breakout pattern."""
    data = {
        "timestamp": list(range(20)),
        "open": [100.0] * 20,
        "high": [101.0] * 20,
        "low": [99.0] * 20,
        "close": [100.0] * 20,
        "volume": [1.0] * 20,
    }
    df = pd.DataFrame(data)
    # Signal bar: close and high below EMA proxy
    df.loc[10, "close"] = 95.0
    df.loc[10, "high"] = 96.0
    df.loc[10, "low"] = 94.0
    # Breakout bar
    df.loc[11, "high"] = 98.0
    df.loc[11, "close"] = 97.0
    df.loc[11, "low"] = 94.5
    return df


@pytest.fixture
def trending_ohlcv() -> pd.DataFrame:
    """Uptrending prices for EMA tests."""
    closes = [100 + i * 0.5 for i in range(30)]
    return pd.DataFrame(
        {
            "timestamp": list(range(30)),
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1.0] * 30,
        }
    )
