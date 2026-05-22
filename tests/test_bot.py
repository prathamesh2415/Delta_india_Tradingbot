"""Tests for trading bot orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from trading_bot.bot import TradingBot
from trading_bot.config import Settings


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
        database_path=str(tmp_path / "bot.db"),
        log_level="INFO",
        log_file=str(tmp_path / "bot.log"),
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


@patch(
    "trading_bot.exchange.delta_client.DeltaExchangeClient.fetch_account_equity",
    return_value=100.0,
)
def test_run_once_no_signal(mock_equity, tmp_path) -> None:
    bot = TradingBot(_settings(tmp_path))
    df = pd.DataFrame(
        {
            "timestamp": list(range(50)),
            "open": [100.0] * 50,
            "high": [101.0] * 50,
            "low": [99.0] * 50,
            "close": [100.0] * 50,
            "volume": [1.0] * 50,
        }
    )
    bot.exchange.fetch_ohlcv = MagicMock(return_value=df)  # type: ignore[method-assign]
    bot.exchange.fetch_ticker_price = MagicMock(return_value=100.0)  # type: ignore[method-assign]
    bot.run_once()
    assert bot.repository.get_open_trades() == []


@patch(
    "trading_bot.exchange.delta_client.DeltaExchangeClient.fetch_account_equity",
    return_value=100.0,
)
@patch("trading_bot.bot.is_london_ny_session", return_value=True)
def test_run_once_blocked_by_position(mock_session, mock_equity, tmp_path) -> None:
    bot = TradingBot(_settings(tmp_path))
    bot.repository.insert_trade("BTCUSD", "long", 100, 99, 102, 0.001)
    bot._active_trade_id = 1
    df = pd.DataFrame(
        {
            "timestamp": list(range(50)),
            "open": [100.0] * 50,
            "high": [101.0] * 50,
            "low": [99.0] * 50,
            "close": [100.0] * 50,
            "volume": [1.0] * 50,
        }
    )
    bot.exchange.fetch_ohlcv = MagicMock(return_value=df)  # type: ignore[method-assign]
    bot.exchange.fetch_ticker_price = MagicMock(return_value=100.0)  # type: ignore[method-assign]
    bot.run_once()
    assert len(bot.repository.get_open_trades()) == 1
