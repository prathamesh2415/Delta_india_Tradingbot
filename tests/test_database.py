"""Tests for SQLite trade repository."""

from __future__ import annotations

import pytest

from trading_bot.db.repository import TradeRepository


def test_insert_and_close_trade(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "t.db"))
    tid = repo.insert_trade(
        "BTCUSD", "long", 100.0, 99.0, 102.0, 0.001, order_id="o1"
    )
    assert tid == 1
    open_trades = repo.get_open_trades("BTCUSD")
    assert len(open_trades) == 1
    repo.close_trade(tid, 102.0, 0.002, exit_fee_usd=0.0001)
    assert len(repo.get_open_trades()) == 0
    assert repo.total_realized_pnl() == pytest.approx(0.0019, rel=1e-2)


def test_fee_statistics(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "fees.db"))
    tid = repo.insert_trade("BTCUSD", "long", 100, 99, 102, 0.01, entry_fee_usd=0.01)
    repo.close_trade(tid, 102.0, 0.02, exit_fee_usd=0.01)
    stats = repo.get_fee_statistics()
    assert stats["total_fees"] == pytest.approx(0.02, rel=1e-2)
    assert stats["net_profit"] == pytest.approx(0.0, rel=1e-2)


def test_pnl_snapshot(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "t2.db"))
    repo.record_pnl_snapshot(100.0, 0.5, 1.0)
    repo.record_pnl_snapshot(101.0, 0.0, 1.5)
    assert repo.total_realized_pnl() == 0.0


def test_trade_history(tmp_path) -> None:
    repo = TradeRepository(str(tmp_path / "t3.db"))
    repo.insert_trade("BTCUSD", "short", 50, 51, 48, 0.01)
    repo.insert_trade("BTCUSD", "long", 50, 49, 52, 0.01)
    history = repo.get_trade_history()
    assert len(history) == 2
