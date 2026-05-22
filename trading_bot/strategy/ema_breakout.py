"""
5 EMA Breakout strategy (Power of Stocks / StockYogi Pine logic).

Signal candle -> breakout within N bars -> entry at signal level, SL at opposite extreme.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class SignalState:
    """Stored signal candle from Pine var state."""

    signal_high: float
    signal_low: float
    signal_index: int
    is_buy_signal: bool
    is_sell_signal: bool


@dataclass
class TradeSetup:
    """Executable trade parameters."""

    side: Literal["long", "short"]
    entry: float
    stop_loss: float
    take_profit: float
    signal_index: int
    bar_index: int


class EmaBreakoutStrategy:
    """5 EMA breakout with configurable risk-reward."""

    def __init__(
        self,
        ema_length: int = 5,
        target_rr: float = 2.0,
        signal_window_bars: int = 3,
        filter_buy: bool = True,
        filter_sell: bool = True,
    ) -> None:
        self.ema_length = ema_length
        self.target_rr = target_rr
        self.signal_window_bars = signal_window_bars
        self.filter_buy = filter_buy
        self.filter_sell = filter_sell
        self._state: SignalState | None = None

    @staticmethod
    def compute_ema(closes: pd.Series, length: int) -> pd.Series:
        return closes.ewm(span=length, adjust=False).mean()

    def reset_state(self) -> None:
        self._state = None

    def update_bar(
        self,
        bar_index: int,
        high: float,
        low: float,
        close: float,
        ema: float,
        in_block_zone: bool = False,
    ) -> TradeSetup | None:
        """
        Process one closed candle and return a trade setup if triggered.

        Mirrors Pine logic bar-by-bar.
        """
        new_buy = close < ema and high < ema
        new_sell = close > ema and low > ema

        if new_buy:
            self._state = SignalState(
                signal_high=high,
                signal_low=low,
                signal_index=bar_index,
                is_buy_signal=True,
                is_sell_signal=False,
            )
        elif new_sell:
            self._state = SignalState(
                signal_high=high,
                signal_low=low,
                signal_index=bar_index,
                is_buy_signal=False,
                is_sell_signal=True,
            )

        if self._state is None:
            return None

        state = self._state
        within_window = (
            bar_index > state.signal_index
            and bar_index <= state.signal_index + self.signal_window_bars
        )

        buy_trigger = (
            state.is_buy_signal
            and within_window
            and high > state.signal_high
            and not in_block_zone
        )
        sell_trigger = (
            state.is_sell_signal
            and within_window
            and low < state.signal_low
            and not in_block_zone
        )

        if buy_trigger and self.filter_buy:
            entry = state.signal_high
            sl = state.signal_low
            risk = entry - sl
            if risk <= 0:
                return None
            target = entry + risk * self.target_rr
            self._state = None
            return TradeSetup(
                side="long",
                entry=entry,
                stop_loss=sl,
                take_profit=target,
                signal_index=state.signal_index,
                bar_index=bar_index,
            )

        if sell_trigger and self.filter_sell:
            entry = state.signal_low
            sl = state.signal_high
            risk = sl - entry
            if risk <= 0:
                return None
            target = entry - risk * self.target_rr
            self._state = None
            return TradeSetup(
                side="short",
                entry=entry,
                stop_loss=sl,
                take_profit=target,
                signal_index=state.signal_index,
                bar_index=bar_index,
            )

        return None

    def evaluate_dataframe(self, df: pd.DataFrame) -> list[TradeSetup]:
        """
        Run strategy on OHLCV dataframe with columns: open, high, low, close.

        Uses only closed bars; last row is treated as the forming bar (excluded).
        """
        if len(df) < self.ema_length + 2:
            return []

        work = df.copy()
        work["ema"] = self.compute_ema(work["close"], self.ema_length)
        self.reset_state()
        setups: list[TradeSetup] = []

        for i in range(self.ema_length, len(work) - 1):
            row = work.iloc[i]
            setup = self.update_bar(
                bar_index=i,
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                ema=float(row["ema"]),
            )
            if setup:
                setups.append(setup)

        return setups

    def latest_signal_on_closed_bars(self, df: pd.DataFrame) -> TradeSetup | None:
        """Evaluate all closed bars and return trigger on the most recent if any."""
        if len(df) < self.ema_length + 3:
            return None

        work = df.copy()
        work["ema"] = self.compute_ema(work["close"], self.ema_length)
        self.reset_state()
        last_setup: TradeSetup | None = None

        for i in range(self.ema_length, len(work) - 1):
            row = work.iloc[i]
            setup = self.update_bar(
                bar_index=i,
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                ema=float(row["ema"]),
            )
            if setup:
                last_setup = setup

        return last_setup
