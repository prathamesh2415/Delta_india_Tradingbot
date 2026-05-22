"""
Main trading bot loop: 5 EMA breakout on 15m BTC via Delta Exchange.
"""

from __future__ import annotations

import logging
import time
from typing import Literal, cast

from trading_bot.config import Settings
from trading_bot.db.repository import TradeRepository
from trading_bot.fees.calculator import FeeCalculator
from trading_bot.exchange.delta_client import DeltaExchangeClient
from trading_bot.monitoring.pnl_tracker import PnLTracker
from trading_bot.notifications.telegram import TelegramNotifier
from trading_bot.risk.manager import RiskManager
from trading_bot.risk.position_sizer import PositionSizer
from trading_bot.strategy.ema_breakout import EmaBreakoutStrategy, TradeSetup
from trading_bot.utils.sessions import is_london_ny_session

logger = logging.getLogger(__name__)


class TradingBot:
    """Orchestrates strategy, risk, execution, and monitoring."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.exchange = DeltaExchangeClient(
            settings.delta_api_key,
            settings.delta_api_secret,
            paper_trading=settings.paper_trading,
            equity_fallback_usd=settings.account_equity_fallback,
            max_retries=settings.reconnect_max_retries,
            base_delay_sec=settings.reconnect_base_delay_sec,
        )
        self.repository = TradeRepository(settings.database_path)
        self.strategy = EmaBreakoutStrategy(
            ema_length=settings.ema_length,
            target_rr=settings.target_rr,
            signal_window_bars=settings.signal_window_bars,
            filter_buy=settings.filter_buy,
            filter_sell=settings.filter_sell,
        )
        initial_equity = self._fetch_live_equity()
        self.risk_manager = RiskManager(
            settings.max_daily_loss_percent,
            settings.max_daily_trades,
            initial_equity,
        )
        self.position_sizer = PositionSizer(
            initial_equity,
            settings.risk_per_trade_percent,
            settings.max_position_size,
        )
        self.telegram = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
        )
        self.pnl_tracker = PnLTracker(self.repository, self.exchange)
        self.fee_calculator = FeeCalculator(settings.taker_fee_percent)
        self._last_bar_ts: int | None = None
        self._active_trade_id: int | None = None
        self._account_equity_usd = initial_equity

    def _fetch_live_equity(self) -> float:
        """Load tradable balance from Delta Exchange."""
        equity = self.exchange.fetch_account_equity(
            self.settings.account_equity_fallback
        )
        self._account_equity_usd = equity
        return equity

    def _refresh_account_equity(self) -> float:
        """Update risk sizing from latest exchange balance."""
        equity = self._fetch_live_equity()
        self.risk_manager.update_account_equity(equity)
        self.position_sizer.update_account_equity(equity)
        return equity

    def _poll_interval_sec(self) -> int:
        tf = self.settings.timeframe
        mapping = {"1m": 30, "5m": 60, "15m": 90, "1h": 300}
        return mapping.get(tf, 90)

    def _has_open_position(self) -> bool:
        if self._active_trade_id:
            return True
        open_trades = self.repository.get_open_trades(self.settings.trading_symbol)
        if open_trades:
            self._active_trade_id = open_trades[0].id
            return True
        try:
            return self.exchange.fetch_position_size(self.settings.trading_symbol) != 0
        except Exception:
            return bool(open_trades)

    def _execute_setup(self, setup: TradeSetup) -> None:
        equity = self._refresh_account_equity()
        min_equity = 1.0
        if equity < min_equity:
            logger.warning(
                "Account balance $%.2f too low to trade (min $%.2f)",
                equity,
                min_equity,
            )
            return

        size_result = self.position_sizer.calculate(setup.entry, setup.stop_loss)
        if not size_result:
            logger.warning("Position size calculation failed; skipping trade")
            return

        order = self.exchange.place_bracket_order(
            self.settings.trading_symbol,
            setup.side,
            size_result.contracts,
            setup.entry,
            setup.stop_loss,
            setup.take_profit,
        )
        order_id = str(order.get("id", ""))
        entry_fee = self.fee_calculator.entry_fee(setup.entry, size_result.contracts)
        api_fee = self.fee_calculator.fee_from_order(order)
        if api_fee is not None:
            entry_fee = api_fee
        trade_id = self.repository.insert_trade(
            symbol=self.settings.trading_symbol,
            side=setup.side,
            entry_price=setup.entry,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit,
            size=size_result.contracts,
            order_id=order_id,
            notes=f"signal_bar={setup.signal_index}",
            entry_fee_usd=entry_fee,
        )
        self._active_trade_id = trade_id
        self.telegram.trade_opened(
            self.settings.trading_symbol,
            setup.side,
            setup.entry,
            setup.stop_loss,
            setup.take_profit,
            size_result.contracts,
        )
        logger.info(
            "Opened %s %s contracts=%s entry=%s sl=%s tp=%s",
            setup.side,
            self.settings.trading_symbol,
            size_result.contracts,
            setup.entry,
            setup.stop_loss,
            setup.take_profit,
        )

    def _check_exit(self) -> None:
        """Monitor open trade against SL/TP using last price."""
        if not self._active_trade_id:
            return
        open_trades = self.repository.get_open_trades(self.settings.trading_symbol)
        if not open_trades:
            self._active_trade_id = None
            return

        trade = open_trades[0]
        try:
            price = self.exchange.fetch_ticker_price(self.settings.trading_symbol)
        except Exception as exc:
            logger.error("Price fetch failed: %s", exc)
            return

        closed = False
        exit_price = price
        status = "closed"
        reason = "monitor"

        if trade.side == "long":
            if price <= trade.stop_loss:
                exit_price = trade.stop_loss
                status = "stopped"
                reason = "stop_loss"
                closed = True
            elif price >= trade.take_profit:
                exit_price = trade.take_profit
                status = "taken"
                reason = "take_profit"
                closed = True
        else:
            if price >= trade.stop_loss:
                exit_price = trade.stop_loss
                status = "stopped"
                reason = "stop_loss"
                closed = True
            elif price <= trade.take_profit:
                exit_price = trade.take_profit
                status = "taken"
                reason = "take_profit"
                closed = True

        if not closed:
            return

        if trade.side == "long":
            pnl = (exit_price - trade.entry_price) * trade.size
        else:
            pnl = (trade.entry_price - exit_price) * trade.size

        self.exchange.close_position(self.settings.trading_symbol)
        exit_fee = self.fee_calculator.exit_fee(exit_price, trade.size)
        total_fee = (trade.entry_fee_usd or 0) + exit_fee
        net_pnl = pnl - total_fee
        close_status = cast(Literal["closed", "stopped", "taken"], status)
        self.repository.close_trade(
            trade.id, exit_price, pnl, close_status, exit_fee_usd=exit_fee
        )
        self.risk_manager.record_trade_result(net_pnl)
        self._active_trade_id = None
        self.telegram.send(
            f"<b>Trade Closed</b>\n"
            f"{self.settings.trading_symbol}\n"
            f"Gross P&L: ${pnl:.2f}\n"
            f"Fees: ${total_fee:.4f}\n"
            f"<b>Net P&L: ${net_pnl:.2f}</b>\n"
            f"Reason: {reason}"
        )
        logger.info(
            "Closed trade id=%s gross=%.2f fees=%.4f net=%.2f reason=%s",
            trade.id,
            pnl,
            total_fee,
            net_pnl,
            reason,
        )

    def run_once(self) -> None:
        """Single iteration: fetch data, evaluate signal, manage positions."""
        in_session = is_london_ny_session(
            start_hour=self.settings.session_start_utc_hour,
            end_hour=self.settings.session_end_utc_hour,
        )

        equity = self._refresh_account_equity()
        snap = self.pnl_tracker.snapshot(
            self.settings.trading_symbol,
            self.settings.account_equity_fallback,
            wallet_balance_usd=equity,
        )
        logger.info(self.pnl_tracker.format_status(snap))
        logger.info(
            "1%% risk per trade = $%.2f (based on live balance $%.2f)",
            equity * (self.settings.risk_per_trade_percent / 100.0),
            equity,
        )

        self._check_exit()

        try:
            df = self.exchange.fetch_ohlcv(
                self.settings.trading_symbol,
                self.settings.timeframe,
                limit=120,
            )
        except Exception as exc:
            logger.error("OHLCV fetch failed: %s", exc)
            self.telegram.error("OHLCV fetch", str(exc))
            return

        last_ts = int(df.iloc[-2]["timestamp"])
        if self._last_bar_ts == last_ts:
            return
        self._last_bar_ts = last_ts

        setup = self.strategy.latest_signal_on_closed_bars(df)
        if not setup:
            return

        verdict = self.risk_manager.can_open_trade(
            in_session, self._has_open_position()
        )
        if not verdict.allowed:
            logger.info("Trade blocked: %s", verdict.reason)
            return

        self._execute_setup(setup)

    def run(self) -> None:
        """Continuous bot loop."""
        mode = "PAPER" if self.settings.paper_trading else "LIVE"
        equity = self._fetch_live_equity()
        risk_usd = equity * (self.settings.risk_per_trade_percent / 100.0)
        self.telegram.alert(
            "Bot Started",
            f"Mode: {mode}\nSymbol: {self.settings.trading_symbol}\n"
            f"TF: {self.settings.timeframe}\n"
            f"Live balance: ${equity:.2f}\n"
            f"Risk per trade (1%): ${risk_usd:.2f}",
        )
        logger.info("Trading bot started (%s)", mode)

        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                self.telegram.alert("Bot Stopped", "Manual shutdown")
                break
            except Exception as exc:
                logger.exception("Unhandled error in main loop: %s", exc)
                self.telegram.error("Main loop", str(exc))
            time.sleep(self._poll_interval_sec())


def run_bot() -> None:
    settings = Settings.from_env()
    settings.ensure_paths()
    from trading_bot.utils.logging_setup import setup_logging

    setup_logging(settings.log_level, settings.log_file)
    bot = TradingBot(settings)
    bot.run()
