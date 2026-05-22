"""Tests for reconnect helper."""

from __future__ import annotations

import ccxt
import pytest

from trading_bot.utils.reconnect import with_reconnect


def test_success_first_try() -> None:
    assert with_reconnect(lambda: 42, max_retries=3) == 42


def test_retries_then_success() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ccxt.NetworkError("timeout")
        return "ok"

    result = with_reconnect(flaky, max_retries=5, base_delay_sec=0.01)
    assert result == "ok"
    assert calls["n"] == 2


def test_auth_error_not_retried() -> None:
    def fail() -> None:
        raise ccxt.AuthenticationError("bad key")

    with pytest.raises(ccxt.AuthenticationError):
        with_reconnect(fail, max_retries=3, base_delay_sec=0.01)


def test_exhausted_retries() -> None:
    def always_fail() -> None:
        raise ccxt.NetworkError("down")

    with pytest.raises(ConnectionError):
        with_reconnect(always_fail, max_retries=2, base_delay_sec=0.01)
