"""Position sizing based on fixed fractional risk."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizeResult:
    contracts: float
    risk_amount_usd: float
    risk_per_unit: float


class PositionSizer:
    """Calculate position size for 1% (or configured) account risk."""

    def __init__(
        self,
        account_equity_usd: float,
        risk_percent: float = 1.0,
        max_position_size: float = 0.002,
    ) -> None:
        self.account_equity_usd = account_equity_usd
        self.risk_percent = risk_percent
        self.max_position_size = max_position_size

    def update_account_equity(self, equity_usd: float) -> None:
        if equity_usd > 0:
            self.account_equity_usd = equity_usd

    def calculate(
        self,
        entry: float,
        stop_loss: float,
        contract_value: float = 1.0,
    ) -> PositionSizeResult | None:
        """
        Size position so loss at stop equals risk_percent of equity.

        contracts = risk_usd / (|entry - sl| * contract_value)
        """
        risk_per_unit = abs(entry - stop_loss)
        if risk_per_unit <= 0:
            return None

        risk_amount = self.account_equity_usd * (self.risk_percent / 100.0)
        raw_size = risk_amount / (risk_per_unit * contract_value)
        contracts = min(raw_size, self.max_position_size)

        if contracts <= 0:
            return None

        return PositionSizeResult(
            contracts=contracts,
            risk_amount_usd=risk_amount,
            risk_per_unit=risk_per_unit,
        )
