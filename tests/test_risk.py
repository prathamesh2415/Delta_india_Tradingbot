"""Tests for risk management and position sizing."""

from __future__ import annotations

from datetime import date

from trading_bot.risk.manager import RiskManager
from trading_bot.risk.position_sizer import PositionSizer


def test_position_sizer_one_percent() -> None:
    sizer = PositionSizer(account_equity_usd=100, risk_percent=1.0, max_position_size=1.0)
    result = sizer.calculate(entry=100.0, stop_loss=99.0)
    assert result is not None
    assert result.risk_amount_usd == 1.0
    assert result.contracts == 1.0


def test_position_sizer_invalid_sl() -> None:
    sizer = PositionSizer(100, 1.0)
    assert sizer.calculate(100.0, 100.0) is None


def test_position_sizer_max_cap() -> None:
    sizer = PositionSizer(10000, 1.0, max_position_size=0.001)
    result = sizer.calculate(100.0, 90.0)
    assert result is not None
    assert result.contracts == 0.001


def test_risk_manager_session_block() -> None:
    rm = RiskManager(5, 5, 100)
    v = rm.can_open_trade(in_session=False, has_open_position=False)
    assert not v.allowed
    assert "session" in v.reason.lower()


def test_risk_manager_max_trades() -> None:
    rm = RiskManager(5, 2, 100)
    d = date(2025, 1, 1)
    rm.record_trade_result(0, d)
    rm.record_trade_result(0, d)
    v = rm.can_open_trade(True, False, d)
    assert not v.allowed


def test_risk_manager_update_equity() -> None:
    rm = RiskManager(5, 5, 100)
    rm.update_account_equity(250.0)
    assert rm.account_equity_usd == 250.0


def test_risk_manager_max_daily_loss() -> None:
    rm = RiskManager(max_daily_loss_percent=5, max_daily_trades=10, account_equity_usd=100)
    d = date(2025, 1, 2)
    rm.record_trade_result(-6.0, d)
    v = rm.can_open_trade(True, False, d)
    assert not v.allowed
