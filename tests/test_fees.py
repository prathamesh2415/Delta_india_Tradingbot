"""Tests for Delta fee calculator (official formula)."""

from __future__ import annotations

import pytest

from trading_bot.fees.calculator import FeeCalculator


def test_notional_btc_qty() -> None:
    """300 contracts × 0.001 BTC @ 90000 = $27000 notional (Delta doc example)."""
    calc = FeeCalculator(
        taker_fee_percent=0.05,
        gst_percent=18.0,
        contract_size_btc=0.001,
        size_unit="contracts",
    )
    leg = calc.leg_fee(90_000.0, 300.0, order_role="taker")
    assert leg.notional_usd == pytest.approx(27_000.0)
    assert leg.trading_fee_usd == pytest.approx(13.5, rel=1e-3)
    assert leg.gst_usd == pytest.approx(2.43, rel=1e-2)
    assert leg.total_fee_usd == pytest.approx(15.93, rel=1e-2)


def test_maker_fee_lower() -> None:
    calc = FeeCalculator(taker_fee_percent=0.05, maker_fee_percent=0.02, gst_percent=18.0)
    taker = calc.leg_fee(90_000.0, 0.3, "taker")
    maker = calc.leg_fee(90_000.0, 0.3, "maker")
    assert maker.trading_fee_usd < taker.trading_fee_usd


def test_round_trip_with_gst() -> None:
    calc = FeeCalculator(taker_fee_percent=0.05, gst_percent=18.0)
    fees = calc.for_round_trip(100.0, 102.0, 0.01)
    assert fees.entry.trading_fee_usd == pytest.approx(0.0005, rel=1e-3)
    assert fees.entry.gst_usd == pytest.approx(0.00009, rel=1e-2)
    assert fees.total_fee_usd == fees.entry.total_fee_usd + fees.exit.total_fee_usd


def test_gross_pnl_long() -> None:
    calc = FeeCalculator()
    pnl = calc.gross_pnl_usd("long", 100.0, 102.0, 0.01)
    assert pnl == pytest.approx(0.02)


def test_fee_from_order() -> None:
    calc = FeeCalculator()
    assert calc.fee_from_order({"fee": {"cost": 0.12}}) == 0.12
    assert calc.fee_from_order({}) is None
