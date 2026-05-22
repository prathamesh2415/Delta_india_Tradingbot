"""Tests for fee calculator."""

from __future__ import annotations

import pytest

from trading_bot.fees.calculator import FeeCalculator


def test_round_trip_fees() -> None:
    calc = FeeCalculator(taker_fee_percent=0.05)
    fees = calc.for_round_trip(100.0, 102.0, 0.01)
    assert fees.entry_fee_usd == pytest.approx(0.0005, rel=1e-3)
    assert fees.exit_fee_usd == pytest.approx(0.00051, rel=1e-3)
    assert fees.total_fee_usd == fees.entry_fee_usd + fees.exit_fee_usd


def test_fee_from_order() -> None:
    calc = FeeCalculator()
    assert calc.fee_from_order({"fee": {"cost": 0.12}}) == 0.12
    assert calc.fee_from_order({}) is None
