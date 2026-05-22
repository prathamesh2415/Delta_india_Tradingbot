"""Tests for balance parsing."""

from __future__ import annotations

from trading_bot.exchange.balance import parse_wallet_equity


def test_parse_usd_total() -> None:
    balance = {"USD": {"total": 127.5, "free": 120.0, "used": 7.5}}
    assert parse_wallet_equity(balance) == 127.5


def test_parse_usdt_and_inr() -> None:
    balance = {
        "USDT": {"total": 50.0},
        "INR": {"total": 8000.0},
    }
    assert parse_wallet_equity(balance) == 8000.0


def test_parse_delta_info() -> None:
    balance = {"info": {"result": {"available_balance": "42.25"}}}
    assert parse_wallet_equity(balance) == 42.25


def test_empty_returns_zero() -> None:
    assert parse_wallet_equity({}) == 0.0


def test_parse_free_plus_used() -> None:
    balance = {"USD": {"total": 0, "free": 80.0, "used": 20.0}}
    assert parse_wallet_equity(balance) == 100.0


def test_parse_totals_and_free_maps() -> None:
    balance = {
        "total": {"USDT": 25.0},
        "free": {"USD": 10.0},
    }
    assert parse_wallet_equity(balance) == 25.0


def test_parse_delta_info_list() -> None:
    balance = {"info": {"result": [{"wallet_balance": "15.5"}]}}
    assert parse_wallet_equity(balance) == 15.5


def test_invalid_values_return_zero() -> None:
    balance = {"USD": {"total": "not-a-number"}}
    assert parse_wallet_equity(balance) == 0.0
