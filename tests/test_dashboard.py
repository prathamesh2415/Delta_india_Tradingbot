"""Tests for dashboard API."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

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
        maker_fee_percent=0.02,
        gst_percent=18.0,
        contract_size_btc=0.001,
        size_unit="btc",
    )


def test_dashboard_summary(tmp_path) -> None:
    settings = _settings(tmp_path)
    repo = TradeRepository(settings.database_path)
    tid = repo.insert_trade(
        "BTCUSD", "long", 100, 99, 102, 0.01,
        entry_fee_usd=0.059, entry_trading_fee_usd=0.05, entry_gst_usd=0.009,
        entry_notional_usd=1.0,
    )
    repo.close_trade(
        tid, 102.0, 0.02, exit_fee_usd=0.059,
        exit_trading_fee_usd=0.05, exit_gst_usd=0.009, exit_notional_usd=1.02,
    )

    with patch(
        "trading_bot.dashboard.server.DeltaExchangeClient.fetch_account_equity",
        return_value=100.0,
    ):
        client = TestClient(create_app(settings))
        r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_fees_usd"] == 0.12
    assert data["live_balance_usd"] == 100.0
    assert "net_profit_usd" in data


def test_dashboard_trades_and_equity_history(tmp_path) -> None:
    settings = _settings(tmp_path)
    repo = TradeRepository(settings.database_path)
    repo.insert_trade("BTCUSD", "long", 100, 99, 102, 0.01)
    repo.record_pnl_snapshot(100.0, 0.0, 1.0)

    with patch(
        "trading_bot.dashboard.server.DeltaExchangeClient.fetch_account_equity",
        return_value=100.0,
    ):
        client = TestClient(create_app(settings))
        trades = client.get("/api/trades")
        history = client.get("/api/equity-history")

    assert trades.status_code == 200
    assert len(trades.json()["trades"]) == 1
    assert history.status_code == 200
    assert len(history.json()["snapshots"]) == 1


def test_dashboard_password_required(tmp_path) -> None:
    settings = replace(_settings(tmp_path), dashboard_password="secret")
    client = TestClient(create_app(settings))
    assert client.get("/api/summary").status_code == 401
    assert client.get("/api/summary", params={"password": "secret"}).status_code == 200
