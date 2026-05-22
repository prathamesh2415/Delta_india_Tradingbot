"""Tests for Telegram notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from trading_bot.notifications.telegram import TelegramNotifier


def test_disabled_when_no_token() -> None:
    n = TelegramNotifier(None, None)
    assert n.send("hello") is False


@patch("trading_bot.notifications.telegram.requests.post")
def test_send_success(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    n = TelegramNotifier("token", "123")
    assert n.send("test message") is True


@patch("trading_bot.notifications.telegram.requests.post")
def test_trade_opened(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    n = TelegramNotifier("token", "123")
    n.trade_opened("BTCUSD", "long", 100, 99, 102, 0.001)
    mock_post.assert_called_once()
