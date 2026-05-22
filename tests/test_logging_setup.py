"""Tests for logging setup."""

from __future__ import annotations

import logging

from trading_bot.utils.logging_setup import setup_logging


def test_setup_logging(tmp_path) -> None:
    log_file = tmp_path / "logs" / "bot.log"
    logger = setup_logging("DEBUG", str(log_file))
    assert logger.name == "trading_bot"
    assert log_file.exists()
    logger.debug("test message")
    assert "test message" in log_file.read_text(encoding="utf-8")
    root = logging.getLogger()
    assert len(root.handlers) >= 2
