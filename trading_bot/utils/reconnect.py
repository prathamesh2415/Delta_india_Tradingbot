"""Retry and reconnect helpers for exchange API calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import ccxt

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE = (
    ccxt.NetworkError,
    ccxt.RequestTimeout,
    ccxt.ExchangeNotAvailable,
    ccxt.DDoSProtection,
    ccxt.RateLimitExceeded,
)


def with_reconnect(
    func: Callable[[], T],
    *,
    max_retries: int = 10,
    base_delay_sec: float = 2.0,
    on_reconnect: Callable[[], None] | None = None,
) -> T:
    """Execute *func* with exponential backoff on transient exchange errors."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return func()
        except RETRYABLE as exc:
            last_error = exc
            delay = base_delay_sec * (2**attempt)
            logger.warning(
                "Transient error (attempt %s/%s): %s. Retrying in %.1fs",
                attempt + 1,
                max_retries,
                exc,
                delay,
            )
            if on_reconnect:
                on_reconnect()
            time.sleep(min(delay, 120.0))
        except ccxt.AuthenticationError:
            raise
        except ccxt.ExchangeError:
            raise
    raise ConnectionError(
        f"Failed after {max_retries} retries: {last_error}"
    ) from last_error
