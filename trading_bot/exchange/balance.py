"""Parse Delta / CCXT balance responses into tradable equity (USD)."""

from __future__ import annotations

from typing import Any

# Currencies Delta India may report for collateral / wallet
_EQUITY_CURRENCIES = ("USD", "USDT", "INR", "USDC")


def _float_or_zero(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _currency_entry(balance: dict[str, Any], currency: str) -> dict[str, Any]:
    entry = balance.get(currency)
    if isinstance(entry, dict):
        return entry
    return {}


def parse_wallet_equity(balance: dict[str, Any]) -> float:
    """
    Extract best estimate of account equity available for risk sizing.

    Prefers ``total``, then ``free`` + ``used``, per currency.
    """
    candidates: list[float] = []

    for currency in _EQUITY_CURRENCIES:
        entry = _currency_entry(balance, currency)
        total = _float_or_zero(entry.get("total"))
        free = _float_or_zero(entry.get("free"))
        used = _float_or_zero(entry.get("used"))
        if total > 0:
            candidates.append(total)
        elif free > 0 or used > 0:
            candidates.append(free + used)

    totals = balance.get("total")
    if isinstance(totals, dict):
        for currency in _EQUITY_CURRENCIES:
            val = _float_or_zero(totals.get(currency))
            if val > 0:
                candidates.append(val)

    free_map = balance.get("free")
    if isinstance(free_map, dict):
        for currency in _EQUITY_CURRENCIES:
            val = _float_or_zero(free_map.get(currency))
            if val > 0:
                candidates.append(val)

    info = balance.get("info")
    if isinstance(info, dict):
        candidates.extend(_parse_delta_info(info))

    if not candidates:
        return 0.0
    return max(candidates)


def _parse_delta_info(info: dict[str, Any]) -> list[float]:
    """Read common Delta wallet / margin fields from raw API payload."""
    found: list[float] = []
    keys = (
        "available_balance",
        "balance",
        "equity",
        "wallet_balance",
        "total_equity",
        "total_balance",
        "margin_balance",
        "available_margin",
    )
    for key in keys:
        val = info.get(key)
        if val is not None:
            f = _float_or_zero(val)
            if f > 0:
                found.append(f)

    result = info.get("result")
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val is not None:
                f = _float_or_zero(val)
                if f > 0:
                    found.append(f)
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                found.extend(_parse_delta_info(item))

    return found
