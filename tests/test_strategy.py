"""Tests for 5 EMA breakout strategy."""

from __future__ import annotations

import pandas as pd

from trading_bot.strategy.ema_breakout import EmaBreakoutStrategy


def test_compute_ema(trending_ohlcv: pd.DataFrame) -> None:
    ema = EmaBreakoutStrategy.compute_ema(trending_ohlcv["close"], 5)
    assert len(ema) == len(trending_ohlcv)
    assert ema.iloc[-1] > ema.iloc[0]


def test_buy_signal_update_bar() -> None:
    strategy = EmaBreakoutStrategy(ema_length=5, target_rr=2.0)
    strategy.update_bar(0, 96.0, 94.0, 95.0, 100.0)
    setup = strategy.update_bar(1, 98.0, 94.5, 97.0, 100.0)
    assert setup is not None
    assert setup.side == "long"
    assert setup.entry == 96.0
    assert setup.stop_loss == 94.0
    assert setup.take_profit == setup.entry + (setup.entry - setup.stop_loss) * 2.0


def test_sell_signal_update_bar() -> None:
    strategy = EmaBreakoutStrategy()
    strategy.update_bar(0, 106.0, 105.0, 105.5, 100.0)
    setup = strategy.update_bar(1, 105.5, 104.0, 104.5, 100.0)
    assert setup is not None
    assert setup.side == "short"
    assert setup.entry == 105.0
    assert setup.stop_loss == 106.0


def test_no_signal_when_risk_zero() -> None:
    strategy = EmaBreakoutStrategy()
    strategy.update_bar(0, 100.0, 100.0, 99.0, 101.0)
    setup = strategy.update_bar(1, 101.0, 99.0, 100.0, 101.0)
    assert setup is None


def test_block_zone_prevents_entry() -> None:
    strategy = EmaBreakoutStrategy()
    strategy.update_bar(0, 96.0, 94.0, 95.0, 100.0)
    setup = strategy.update_bar(1, 98.0, 94.5, 97.0, 100.0, in_block_zone=True)
    assert setup is None


def test_evaluate_dataframe(sample_ohlcv: pd.DataFrame) -> None:
    strategy = EmaBreakoutStrategy(ema_length=3, target_rr=2.0)
    setups = strategy.evaluate_dataframe(sample_ohlcv)
    assert isinstance(setups, list)


def test_reset_state() -> None:
    strategy = EmaBreakoutStrategy()
    strategy.update_bar(0, 96.0, 94.0, 95.0, 100.0)
    strategy.reset_state()
    setup = strategy.update_bar(5, 200.0, 199.0, 199.5, 100.0)
    assert setup is None
