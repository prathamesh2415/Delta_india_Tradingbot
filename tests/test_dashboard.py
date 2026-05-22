"""Tests for dashboard API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trading_bot.config import Settings
from trading_bot.dashboard.server import create_app
from trading_bot.db.repository import TradeRepository


def _settings(tmp_path) -> Settings:
    return Settings(
        delta_api_key="k",
        delta_api_secret="s",
        trading_symbol="BTCUSD",
        timeframe="15m",
        account_equity_fallback=100.0,
        paper_trading=True,
        risk_per_trade_percent=1.0,
        target_rr=2.0,
        ema_length=5,
        signal_window_bars=3,
        max_daily_loss_percent=5.0,
        max_daily_trades=5,
        database_path=str(tmp_path / "dash.db"),
        log_level="INFO",
        log_file=str(tmp_path / "dash.log"),
        telegram_bot_token=None,
        telegram_chat_id=None,
        session_start_utc_hour=0,
        session_end_utc_hour=24,
        filter_buy=True,
        filter_sell=True,
        leverage=1,
        max_position_size=0.002,
        reconnect_max_retries=3,
        reconnect_base_delay_sec=0.01,
        server_host="127.0.0.1",
        server_port=8000,
        dashboard_password=None,
        taker_fee_percent=0.05,
    )


def test_dashboard_summary(tmp_path) -> None:
    settings = _settings(tmp_path)
    repo = TradeRepository(settings.database_path)
    tid = repo.insert_trade("BTCUSD", "long", 100, 99, 102, 0.01, entry_fee_usd=0.05)
    repo.close_trade(tid, 102.0, 0.02, exit_fee_usd=0.05)

    client = TestClient(create_app(settings))
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_fees_usd"] == 0.1
    assert "net_profit_usd" in data
