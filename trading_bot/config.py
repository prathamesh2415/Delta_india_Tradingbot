"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _env_float(key: str, default: float) -> float:
    raw = _env(key)
    return float(raw) if raw else default


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    return int(raw) if raw else default


def _optional_float(key: str) -> float | None:
    raw = _env(key)
    if not raw:
        return None
    return float(raw)


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration."""

    delta_api_key: str
    delta_api_secret: str
    trading_symbol: str
    timeframe: str
    account_equity_fallback: float | None
    paper_trading: bool
    risk_per_trade_percent: float
    target_rr: float
    ema_length: int
    signal_window_bars: int
    max_daily_loss_percent: float
    max_daily_trades: int
    database_path: str
    log_level: str
    log_file: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    session_start_utc_hour: int
    session_end_utc_hour: int
    filter_buy: bool
    filter_sell: bool
    leverage: int
    max_position_size: float
    reconnect_max_retries: int
    reconnect_base_delay_sec: float
    server_host: str
    server_port: int
    dashboard_password: str | None
    taker_fee_percent: float
    maker_fee_percent: float
    gst_percent: float
    contract_size_btc: float
    size_unit: str

    @classmethod
    def from_env(cls) -> Settings:
        api_key = _env("DELTA_API_KEY")
        api_secret = _env("DELTA_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError(
                "DELTA_API_KEY and DELTA_API_SECRET must be set in environment"
            )
        return cls(
            delta_api_key=api_key,
            delta_api_secret=api_secret,
            trading_symbol=_env("TRADING_SYMBOL", "BTCUSD") or "BTCUSD",
            timeframe=_env("TIMEFRAME", "15m") or "15m",
            account_equity_fallback=_optional_float("ACCOUNT_EQUITY_USD"),
            paper_trading=_env_bool("PAPER_TRADING", True),
            risk_per_trade_percent=_env_float("RISK_PER_TRADE_PERCENT", 1.0),
            target_rr=_env_float("TARGET_RR", 2.0),
            ema_length=_env_int("EMA_LENGTH", 5),
            signal_window_bars=_env_int("SIGNAL_WINDOW_BARS", 3),
            max_daily_loss_percent=_env_float("MAX_DAILY_LOSS_PERCENT", 5.0),
            max_daily_trades=_env_int("MAX_DAILY_TRADES", 5),
            database_path=_env("DATABASE_PATH", "trading_data.db") or "trading_data.db",
            log_level=_env("LOG_LEVEL", "INFO") or "INFO",
            log_file=_env("LOG_FILE", "logs/trading.log") or "logs/trading.log",
            telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
            session_start_utc_hour=_env_int("SESSION_START_UTC_HOUR", 13),
            session_end_utc_hour=_env_int("SESSION_END_UTC_HOUR", 21),
            filter_buy=_env_bool("FILTER_BUY", True),
            filter_sell=_env_bool("FILTER_SELL", True),
            leverage=_env_int("LEVERAGE", 1),
            max_position_size=_env_float("MAX_POSITION_SIZE", 0.002),
            reconnect_max_retries=_env_int("RECONNECT_MAX_RETRIES", 10),
            reconnect_base_delay_sec=_env_float("RECONNECT_BASE_DELAY_SEC", 2.0),
            server_host=_env("SERVER_HOST", "127.0.0.1") or "127.0.0.1",
            server_port=_env_int("SERVER_PORT", 8000),
            dashboard_password=_env("DASHBOARD_PASSWORD") or _env("WEBHOOK_SECRET"),
            taker_fee_percent=_env_float("TAKER_FEE_PERCENT", 0.05),
            maker_fee_percent=_env_float("MAKER_FEE_PERCENT", 0.02),
            gst_percent=_env_float("GST_PERCENT", 18.0),
            contract_size_btc=_env_float("CONTRACT_SIZE_BTC", 0.001),
            size_unit=(_env("SIZE_UNIT", "btc") or "btc").lower(),
        )

    def ensure_paths(self) -> None:
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
