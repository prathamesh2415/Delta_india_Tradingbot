"""Tests for P&L tracker."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trading_bot.db.repository import TradeRepository
from trading_bot.monitoring.pnl_tracker import PnLTracker


def test_snapshot_with_open_long(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "pnl.db"))
    repo.insert_trade("BTCUSD", "long", 100.0, 99.0, 102.0, 0.01)

    exchange = MagicMock()
    exchange.fetch_ticker_price.return_value = 101.0

    tracker = PnLTracker(repo, exchange)
    snap = tracker.snapshot("BTCUSD", wallet_balance_usd=100.0)
    assert snap.unrealized_pnl == pytest.approx(0.01)
    assert snap.wallet_balance_usd == 100.0
    assert snap.open_positions == 1
    assert "Balance" in tracker.format_status(snap)


def test_snapshot_no_open(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "pnl2.db"))
    exchange = MagicMock()
    exchange.fetch_ticker_price.return_value = 100.0
    exchange.fetch_account_equity = MagicMock(return_value=100.0)  # type: ignore[method-assign]
    tracker = PnLTracker(repo, exchange)
    snap = tracker.snapshot("BTCUSD")
    assert snap.unrealized_pnl == 0.0
    assert snap.open_positions == 0
