"""Daily risk limits and trade gating."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RiskVerdict:
    allowed: bool
    reason: str


class RiskManager:
    """Enforce max daily loss, max trades, and session rules."""

    def __init__(
        self,
        max_daily_loss_percent: float,
        max_daily_trades: int,
        account_equity_usd: float,
    ) -> None:
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_daily_trades = max_daily_trades
        self.account_equity_usd = account_equity_usd
        self._daily_pnl: dict[date, float] = {}
        self._daily_trades: dict[date, int] = {}

    def update_account_equity(self, equity_usd: float) -> None:
        """Refresh equity from live exchange balance."""
        if equity_usd > 0:
            self.account_equity_usd = equity_usd

    def record_trade_result(self, pnl_usd: float, trade_date: date | None = None) -> None:
        d = trade_date or date.today()
        self._daily_pnl[d] = self._daily_pnl.get(d, 0.0) + pnl_usd
        self._daily_trades[d] = self._daily_trades.get(d, 0) + 1

    def get_daily_pnl(self, trade_date: date | None = None) -> float:
        d = trade_date or date.today()
        return self._daily_pnl.get(d, 0.0)

    def get_daily_trade_count(self, trade_date: date | None = None) -> int:
        d = trade_date or date.today()
        return self._daily_trades.get(d, 0)

    def can_open_trade(
        self,
        in_session: bool,
        has_open_position: bool,
        trade_date: date | None = None,
    ) -> RiskVerdict:
        if not in_session:
            return RiskVerdict(False, "Outside London-NY session")
        if has_open_position:
            return RiskVerdict(False, "Position already open")
        d = trade_date or date.today()
        if self.get_daily_trade_count(d) >= self.max_daily_trades:
            return RiskVerdict(False, "Max daily trades reached")
        max_loss = self.account_equity_usd * (self.max_daily_loss_percent / 100.0)
        if self.get_daily_pnl(d) <= -max_loss:
            return RiskVerdict(False, "Max daily loss reached")
        return RiskVerdict(True, "OK")
