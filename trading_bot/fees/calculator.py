"""Trading fee estimation (Delta taker/maker rates)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeFees:
    entry_fee_usd: float
    exit_fee_usd: float
    total_fee_usd: float
    notional_entry_usd: float
    notional_exit_usd: float


class FeeCalculator:
    """
    Estimate per-trade fees from notional × fee rate.

    Delta India perpetuals: ~0.05% taker (configurable via TAKER_FEE_PERCENT).
    """

    def __init__(self, taker_fee_percent: float = 0.05) -> None:
        self.rate = taker_fee_percent / 100.0

    def leg_fee(self, price: float, size: float) -> float:
        notional = abs(price * size)
        return notional * self.rate

    def entry_fee(self, entry_price: float, size: float) -> float:
        return self.leg_fee(entry_price, size)

    def exit_fee(self, exit_price: float, size: float) -> float:
        return self.leg_fee(exit_price, size)

    def for_round_trip(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
    ) -> TradeFees:
        notional_entry = abs(entry_price * size)
        notional_exit = abs(exit_price * size)
        entry_fee = notional_entry * self.rate
        exit_fee = notional_exit * self.rate
        return TradeFees(
            entry_fee_usd=entry_fee,
            exit_fee_usd=exit_fee,
            total_fee_usd=entry_fee + exit_fee,
            notional_entry_usd=notional_entry,
            notional_exit_usd=notional_exit,
        )

    @staticmethod
    def fee_from_order(order: dict) -> float | None:
        """Extract fee from CCXT order if exchange returned it."""
        fee = order.get("fee")
        if isinstance(fee, dict) and fee.get("cost") is not None:
            return float(fee["cost"])
        if order.get("fees"):
            total = 0.0
            for f in order["fees"]:
                if isinstance(f, dict) and f.get("cost"):
                    total += float(f["cost"])
            if total > 0:
                return total
        return None
