"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(level: str, log_file: str) -> logging.Logger:
    """Configure root logger with console and file handlers."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return logging.getLogger("trading_bot")
