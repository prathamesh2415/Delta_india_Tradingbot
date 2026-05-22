"""
Delta Exchange futures fees (India).

Official formula:
  Notional Size = Spot Price × Qty (BTC)
  Trading fee = Notional × Taker% (0.05%) or Maker% (0.02%) per leg
  GST = 18% on trading fee

Reference: https://www.delta.exchange/support/solutions/articles/80001177864
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

OrderRole = Literal["taker", "maker"]


@dataclass(frozen=True)
class LegFeeBreakdown:
    """Fees for one open or close leg."""

    spot_price: float
    qty_btc: float
    notional_usd: float
    trading_fee_usd: float
    gst_usd: float
    total_fee_usd: float
    order_role: OrderRole
    fee_rate_percent: float


@dataclass(frozen=True)
class TradeFees:
    entry: LegFeeBreakdown
    exit: LegFeeBreakdown
    entry_fee_usd: float
    exit_fee_usd: float
    total_fee_usd: float
    total_trading_fee_usd: float
    total_gst_usd: float
    notional_entry_usd: float
    notional_exit_usd: float


class FeeCalculator:
    """
    Delta BTCUSD perpetual futures fee model.

    - 1 contract = 0.001 BTC (configurable CONTRACT_SIZE_BTC)
    - ``size`` in trades can be BTC qty or contract count (SIZE_UNIT)
    """

    def __init__(
        self,
        taker_fee_percent: float = 0.05,
        maker_fee_percent: float = 0.02,
        gst_percent: float = 18.0,
        contract_size_btc: float = 0.001,
        size_unit: Literal["btc", "contracts"] = "btc",
    ) -> None:
        self.taker_rate = taker_fee_percent / 100.0
        self.maker_rate = maker_fee_percent / 100.0
        self.gst_rate = gst_percent / 100.0
        self.contract_size_btc = contract_size_btc
        self.size_unit = size_unit

    def qty_btc(self, size: float) -> float:
        """Convert stored size to BTC quantity for notional / PnL."""
        if self.size_unit == "contracts":
            return abs(size) * self.contract_size_btc
        return abs(size)

    def notional_usd(self, spot_price: float, size: float) -> float:
        """Notional Size = Spot Price × Qty (BTC)."""
        return abs(spot_price) * self.qty_btc(size)

    def leg_fee(
        self,
        spot_price: float,
        size: float,
        order_role: OrderRole = "taker",
    ) -> LegFeeBreakdown:
        notional = self.notional_usd(spot_price, size)
        rate = self.taker_rate if order_role == "taker" else self.maker_rate
        fee_pct = rate * 100.0
        trading_fee = notional * rate
        gst = trading_fee * self.gst_rate
        return LegFeeBreakdown(
            spot_price=spot_price,
            qty_btc=self.qty_btc(size),
            notional_usd=notional,
            trading_fee_usd=trading_fee,
            gst_usd=gst,
            total_fee_usd=trading_fee + gst,
            order_role=order_role,
            fee_rate_percent=fee_pct,
        )

    def entry_fee(
        self,
        entry_price: float,
        size: float,
        order_role: OrderRole = "taker",
    ) -> LegFeeBreakdown:
        return self.leg_fee(entry_price, size, order_role)

    def exit_fee(
        self,
        exit_price: float,
        size: float,
        order_role: OrderRole = "taker",
    ) -> LegFeeBreakdown:
        return self.leg_fee(exit_price, size, order_role)

    def for_round_trip(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
        entry_role: OrderRole = "taker",
        exit_role: OrderRole = "taker",
    ) -> TradeFees:
        entry = self.entry_fee(entry_price, size, entry_role)
        exit_leg = self.exit_fee(exit_price, size, exit_role)
        return TradeFees(
            entry=entry,
            exit=exit_leg,
            entry_fee_usd=entry.total_fee_usd,
            exit_fee_usd=exit_leg.total_fee_usd,
            total_fee_usd=entry.total_fee_usd + exit_leg.total_fee_usd,
            total_trading_fee_usd=entry.trading_fee_usd + exit_leg.trading_fee_usd,
            total_gst_usd=entry.gst_usd + exit_leg.gst_usd,
            notional_entry_usd=entry.notional_usd,
            notional_exit_usd=exit_leg.notional_usd,
        )

    def gross_pnl_usd(
        self,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
    ) -> float:
        """Gross P&L in USD before fees (price diff × BTC qty)."""
        qty = self.qty_btc(size)
        if side == "long":
            return (exit_price - entry_price) * qty
        return (entry_price - exit_price) * qty

    @staticmethod
    def fee_from_order(order: dict[str, Any]) -> float | None:
        """Use exchange-reported fee if CCXT returns it (includes GST if API bundles it)."""
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

    def apply_api_fee_to_leg(
        self,
        leg: LegFeeBreakdown,
        api_total_fee: float,
    ) -> LegFeeBreakdown:
        """Split API total into trading + GST using configured GST rate."""
        if api_total_fee <= 0:
            return leg
        trading = api_total_fee / (1.0 + self.gst_rate)
        gst = api_total_fee - trading
        return LegFeeBreakdown(
            spot_price=leg.spot_price,
            qty_btc=leg.qty_btc,
            notional_usd=leg.notional_usd,
            trading_fee_usd=trading,
            gst_usd=gst,
            total_fee_usd=api_total_fee,
            order_role=leg.order_role,
            fee_rate_percent=leg.fee_rate_percent,
        )
