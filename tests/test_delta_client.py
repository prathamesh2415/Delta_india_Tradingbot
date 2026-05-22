"""Tests for Delta exchange client (mocked CCXT)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from trading_bot.exchange.delta_client import DeltaExchangeClient, DELTA_INDIA_API


@pytest.fixture
def client() -> DeltaExchangeClient:
    return DeltaExchangeClient("key", "secret", paper_trading=True)


def test_build_exchange_urls(client: DeltaExchangeClient) -> None:
    assert client._exchange.urls["api"]["public"] == DELTA_INDIA_API


def test_fetch_ohlcv_paper(client: DeltaExchangeClient) -> None:
    ohlcv = [
        [1, 100, 101, 99, 100, 10],
        [2, 100, 101, 99, 100, 10],
    ]
    client.resolve_symbol = MagicMock(return_value="BTC/USD:USD")  # type: ignore[method-assign]
    client._call = lambda f: f()  # type: ignore[method-assign]
    client._exchange.fetch_ohlcv = MagicMock(return_value=ohlcv)

    df = client.fetch_ohlcv("BTCUSD", "15m", 2)
    assert len(df) == 2
    assert "close" in df.columns


def test_place_bracket_paper(client: DeltaExchangeClient) -> None:
    client.resolve_symbol = MagicMock(return_value="BTC/USD:USD")  # type: ignore[method-assign]
    order = client.place_bracket_order("BTCUSD", "long", 0.001, 100, 99, 102)
    assert order["paper"] is True


def test_fetch_position_paper(client: DeltaExchangeClient) -> None:
    assert client.fetch_position_size("BTCUSD") == 0.0


def test_fetch_account_equity_fallback(client: DeltaExchangeClient) -> None:
    client.fetch_balance_raw = MagicMock(side_effect=RuntimeError("offline"))  # type: ignore[method-assign]
    assert client.fetch_account_equity(fallback_usd=75.0) == 75.0


def test_fetch_account_equity_live(client: DeltaExchangeClient) -> None:
    client.paper_trading = False
    client.fetch_balance_raw = MagicMock(  # type: ignore[method-assign]
        return_value={"USD": {"total": 200.0, "free": 200.0, "used": 0.0}}
    )
    assert client.fetch_account_equity() == 200.0
