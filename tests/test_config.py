"""Tests for configuration loading."""

from __future__ import annotations

import pytest

from trading_bot.config import Settings


def test_settings_from_env() -> None:
    s = Settings.from_env()
    assert s.delta_api_key == "test_key"
    assert s.delta_api_secret == "test_secret"
    assert s.paper_trading is True
    assert s.target_rr == 2.0
    assert s.risk_per_trade_percent == 1.0
    assert s.account_equity_fallback is None


def test_settings_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DELTA_API_KEY", raising=False)
    monkeypatch.delenv("DELTA_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="DELTA_API_KEY"):
        Settings.from_env()


def test_ensure_paths(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = str(tmp_path / "sub" / "logs" / "bot.log")
    db = str(tmp_path / "data" / "trades.db")
    monkeypatch.setenv("LOG_FILE", log)
    monkeypatch.setenv("DATABASE_PATH", db)
    s = Settings.from_env()
    s.ensure_paths()
    assert (tmp_path / "sub" / "logs").is_dir()
