"""Aggregate stats for the profit vs fees dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from trading_bot.db.repository import TradeRepository


@dataclass
class DashboardSummary:
    live_balance_usd: float
    gross_profit_usd: float
    gross_loss_usd: float
    total_fees_usd: float
    net_profit_usd: float
    profitable_after_fees: bool
    total_trades: int
    closed_trades: int
    open_trades: int
    winning_trades: int
    losing_trades: int
    fee_to_gross_ratio_percent: float
    avg_fee_per_trade_usd: float
    avg_net_per_trade_usd: float
    total_trading_fees_usd: float
    total_gst_usd: float
    paper_trading: bool


class DashboardAnalytics:
    def __init__(self, repository: TradeRepository) -> None:
        self.repository = repository

    def build_summary(
        self,
        live_balance_usd: float = 0.0,
        paper_trading: bool = False,
    ) -> DashboardSummary:
        stats = self.repository.get_fee_statistics()
        gross_profit = stats["gross_profit"]
        gross_loss = stats["gross_loss"]
        total_fees = stats["total_fees"]
        net = stats["net_profit"]
        closed = stats["closed_trades"]
        return DashboardSummary(
            live_balance_usd=live_balance_usd,
            gross_profit_usd=gross_profit,
            gross_loss_usd=gross_loss,
            total_fees_usd=total_fees,
            net_profit_usd=net,
            profitable_after_fees=net > 0,
            total_trades=stats["total_trades"],
            closed_trades=closed,
            open_trades=stats["open_trades"],
            winning_trades=stats["winning_trades"],
            losing_trades=stats["losing_trades"],
            fee_to_gross_ratio_percent=(
                (total_fees / gross_profit * 100.0) if gross_profit > 0 else 0.0
            ),
            avg_fee_per_trade_usd=(
                total_fees / closed if closed > 0 else 0.0
            ),
            avg_net_per_trade_usd=(net / closed if closed > 0 else 0.0),
            total_trading_fees_usd=float(stats["total_trading_fees"]),
            total_gst_usd=float(stats["total_gst"]),
            paper_trading=paper_trading,
        )
