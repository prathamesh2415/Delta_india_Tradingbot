"""Real-time P&L tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from trading_bot.db.repository import TradeRepository
from trading_bot.exchange.delta_client import DeltaExchangeClient

logger = logging.getLogger(__name__)


@dataclass
class PnLSnapshot:
    wallet_balance_usd: float
    equity_usd: float
    unrealized_pnl: float
    realized_pnl: float
    open_positions: int
    min_trade_equity: float = 1.0


class PnLTracker:
    """Track realized and unrealized P&L against live wallet balance."""

    def __init__(
        self,
        repository: TradeRepository,
        exchange: DeltaExchangeClient,
    ) -> None:
        self.repository = repository
        self.exchange = exchange

    def snapshot(
        self,
        symbol: str,
        fallback_usd: float | None = None,
        wallet_balance_usd: float | None = None,
    ) -> PnLSnapshot:
        wallet = (
            wallet_balance_usd
            if wallet_balance_usd is not None
            else self.exchange.fetch_account_equity(fallback_usd)
        )
        realized = self.repository.total_realized_pnl()
        open_trades = self.repository.get_open_trades(symbol)
        unrealized = 0.0

        try:
            price = self.exchange.fetch_ticker_price(symbol)
            for trade in open_trades:
                if trade.side == "long":
                    unrealized += (price - trade.entry_price) * trade.size
                else:
                    unrealized += (trade.entry_price - price) * trade.size
        except Exception as exc:
            logger.warning("Could not compute unrealized P&L: %s", exc)

        snap = PnLSnapshot(
            wallet_balance_usd=wallet,
            equity_usd=wallet,
            unrealized_pnl=unrealized,
            realized_pnl=realized,
            open_positions=len(open_trades),
        )
        self.repository.record_pnl_snapshot(
            wallet, unrealized, realized
        )
        return snap

    def format_status(self, snap: PnLSnapshot) -> str:
        return (
            f"Balance: ${snap.wallet_balance_usd:.2f} (live) | "
            f"Session realized: ${snap.realized_pnl:.2f} | "
            f"Est. unrealized: ${snap.unrealized_pnl:.2f} | "
            f"Open: {snap.open_positions}"
        )
