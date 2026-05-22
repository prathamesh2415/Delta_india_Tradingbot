"""
Delta Exchange India client via CCXT.

Authenticates with DELTA_API_KEY and DELTA_API_SECRET from environment.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt
import pandas as pd

from trading_bot.exchange.balance import parse_wallet_equity
from trading_bot.utils.reconnect import with_reconnect

logger = logging.getLogger(__name__)

DELTA_INDIA_API = "https://api.india.delta.exchange"


class DeltaExchangeClient:
    """CCXT wrapper for Delta Exchange with reconnect logic."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        paper_trading: bool = False,
        equity_fallback_usd: float | None = None,
        max_retries: int = 10,
        base_delay_sec: float = 2.0,
    ) -> None:
        self.paper_trading = paper_trading
        self.equity_fallback_usd = equity_fallback_usd
        self.max_retries = max_retries
        self.base_delay_sec = base_delay_sec
        self._exchange = self._build_exchange(api_key, api_secret)
        self._last_equity_usd: float | None = None

    def _build_exchange(self, api_key: str, api_secret: str) -> ccxt.delta:
        exchange = ccxt.delta(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "future"},
            }
        )
        exchange.urls["api"] = {
            "public": DELTA_INDIA_API,
            "private": DELTA_INDIA_API,
        }
        return exchange

    def reconnect(self) -> None:
        """Re-initialize exchange connection."""
        logger.info("Reconnecting Delta Exchange client")
        keys = self._exchange.apiKey, self._exchange.secret
        self._exchange = self._build_exchange(keys[0], keys[1])

    def _call(self, func: Any) -> Any:
        return with_reconnect(
            func,
            max_retries=self.max_retries,
            base_delay_sec=self.base_delay_sec,
            on_reconnect=self.reconnect,
        )

    def load_markets(self) -> dict[str, Any]:
        return self._call(lambda: self._exchange.load_markets())

    def resolve_symbol(self, symbol: str) -> str:
        """Map BTCUSD / BTCUSDT to CCXT unified symbol."""
        markets = self.load_markets()
        candidates = [
            symbol,
            f"{symbol}:USD",
            f"{symbol}/USD:USD",
            "BTC/USD:USD",
            "BTC/USDT:USDT",
        ]
        for c in candidates:
            if c in markets:
                return c
        for mid, m in markets.items():
            base = m.get("base", "")
            if symbol.replace("USDT", "").replace("USD", "") in base.upper():
                if m.get("swap") or m.get("future"):
                    return mid
        raise ValueError(f"Symbol not found on Delta: {symbol}")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 100,
    ) -> pd.DataFrame:
        unified = self.resolve_symbol(symbol)
        raw = self._call(
            lambda: self._exchange.fetch_ohlcv(unified, timeframe, limit=limit)
        )
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def fetch_balance_raw(self) -> dict[str, Any]:
        """Fetch full balance payload from Delta (swap + spot attempts)."""
        errors: list[str] = []
        for params in ({"type": "swap"}, {"type": "future"}, {}):
            try:
                balance = self._call(
                    lambda p=params: self._exchange.fetch_balance(p)
                )
                if balance:
                    return balance
            except ccxt.ExchangeError as exc:
                errors.append(str(exc))
        balance = self._call(lambda: self._exchange.fetch_balance())
        return balance

    def fetch_account_equity(
        self,
        fallback_usd: float | None = None,
    ) -> float:
        """
        Live wallet equity from Delta for position sizing and risk limits.

        Uses the last successful reading if the API call fails temporarily.
        Paper mode still fetches the real balance when API keys are valid.
        """
        fallback = fallback_usd if fallback_usd is not None else self.equity_fallback_usd

        try:
            balance = self.fetch_balance_raw()
            equity = parse_wallet_equity(balance)
            if equity > 0:
                self._last_equity_usd = equity
                logger.info("Live account equity: $%.2f", equity)
                return equity
            logger.warning("Balance API returned zero equity; raw keys: %s", list(balance.keys()))
        except Exception as exc:
            logger.error("Failed to fetch account balance: %s", exc)

        if self._last_equity_usd and self._last_equity_usd > 0:
            logger.warning(
                "Using cached equity $%.2f (API fetch failed)",
                self._last_equity_usd,
            )
            return self._last_equity_usd

        if fallback and fallback > 0:
            logger.warning(
                "Using ACCOUNT_EQUITY_USD fallback $%.2f — set live keys for real balance",
                fallback,
            )
            return fallback

        raise RuntimeError(
            "Could not read account balance from Delta. "
            "Check API keys, IP whitelist, and trading permissions."
        )

    def fetch_balance_usd(self) -> float:
        """Alias for account equity (backward compatible)."""
        return self.fetch_account_equity()

    def fetch_ticker_price(self, symbol: str) -> float:
        unified = self.resolve_symbol(symbol)
        ticker = self._call(lambda: self._exchange.fetch_ticker(unified))
        return float(ticker["last"])

    def fetch_position_size(self, symbol: str) -> float:
        if self.paper_trading:
            return 0.0
        unified = self.resolve_symbol(symbol)
        positions = self._call(lambda: self._exchange.fetch_positions([unified]))
        for pos in positions:
            contracts = float(pos.get("contracts") or pos.get("size") or 0)
            if contracts != 0:
                return contracts
        return 0.0

    def place_bracket_order(
        self,
        symbol: str,
        side: str,
        size: float,
        entry: float,
        stop_loss: float,
        take_profit: float,
    ) -> dict[str, Any]:
        """
        Place entry with stop-loss and take-profit.

        Paper mode logs only; live mode sends market/limit + reduce-only exits.
        """
        unified = self.resolve_symbol(symbol)
        order_side = "buy" if side == "long" else "sell"

        if self.paper_trading:
            logger.info(
                "[PAPER] %s %s size=%s entry=%s sl=%s tp=%s",
                order_side,
                unified,
                size,
                entry,
                stop_loss,
                take_profit,
            )
            return {
                "id": f"paper_{order_side}_{symbol}",
                "symbol": unified,
                "side": side,
                "size": size,
                "paper": True,
            }

        entry_order = self._call(
            lambda: self._exchange.create_order(
                unified,
                "market",
                order_side,
                size,
            )
        )
        exit_side = "sell" if side == "long" else "buy"
        try:
            self._call(
                lambda: self._exchange.create_order(
                    unified,
                    "stop_market",
                    exit_side,
                    size,
                    None,
                    {"stopPrice": stop_loss, "reduceOnly": True},
                )
            )
            self._call(
                lambda: self._exchange.create_order(
                    unified,
                    "take_profit_market",
                    exit_side,
                    size,
                    None,
                    {"stopPrice": take_profit, "reduceOnly": True},
                )
            )
        except ccxt.ExchangeError as exc:
            logger.error("Bracket exit placement failed: %s", exc)

        return entry_order

    def close_position(self, symbol: str) -> dict[str, Any] | None:
        size = self.fetch_position_size(symbol)
        if size == 0:
            return None
        unified = self.resolve_symbol(symbol)
        side = "sell" if size > 0 else "buy"
        close_size = abs(size)
        if self.paper_trading:
            logger.info("[PAPER] Close %s %s", side, close_size)
            return {"id": "paper_close", "paper": True}
        return self._call(
            lambda: self._exchange.create_order(
                unified, "market", side, close_size, None, {"reduceOnly": True}
            )
        )
