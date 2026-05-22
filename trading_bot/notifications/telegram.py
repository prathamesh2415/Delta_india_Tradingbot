"""Telegram alert notifications."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send trade and system alerts via Telegram Bot API."""

    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            logger.debug("Telegram disabled; message: %s", message)
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error("Telegram send failed: %s", exc)
            return False

    def trade_opened(
        self,
        symbol: str,
        side: str,
        entry: float,
        sl: float,
        tp: float,
        size: float,
    ) -> None:
        self.send(
            f"<b>Trade Opened</b>\n"
            f"{symbol} {side.upper()}\n"
            f"Entry: {entry:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nSize: {size}"
        )

    def trade_closed(self, symbol: str, pnl: float, reason: str) -> None:
        emoji = "✅" if pnl >= 0 else "❌"
        self.send(
            f"<b>Trade Closed</b> {emoji}\n"
            f"{symbol}\nP&L: ${pnl:.2f}\nReason: {reason}"
        )

    def alert(self, title: str, detail: str) -> None:
        self.send(f"<b>{title}</b>\n{detail}")

    def error(self, context: str, error: str) -> None:
        self.send(f"<b>Error</b>\n{context}\n<code>{error}</code>")
