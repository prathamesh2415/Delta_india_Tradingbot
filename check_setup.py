#!/usr/bin/env python3
"""Verify .env, API keys, and Delta connection (no trades)."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    print("=== Trading bot setup check ===\n")
    ok = True

    try:
        from trading_bot.config import Settings

        settings = Settings.from_env()
        print("[OK] DELTA_API_KEY and DELTA_API_SECRET loaded")
        print(f"     Symbol: {settings.trading_symbol}")
        print(f"     Timeframe: {settings.timeframe}")
        print(f"     Paper trading: {settings.paper_trading}")
        if settings.account_equity_fallback:
            print(f"     Fallback only: ${settings.account_equity_fallback}")
        else:
            print("     Balance: fetched live from Delta (no fixed $100)")
    except ValueError as exc:
        print(f"[FAIL] Config: {exc}")
        return 1

    try:
        from trading_bot.exchange.delta_client import DeltaExchangeClient

        client = DeltaExchangeClient(
            settings.delta_api_key,
            settings.delta_api_secret,
            paper_trading=settings.paper_trading,
            equity_fallback_usd=settings.account_equity_fallback,
            max_retries=3,
            base_delay_sec=1.0,
        )
        markets = client.load_markets()
        symbol = client.resolve_symbol(settings.trading_symbol)
        price = client.fetch_ticker_price(settings.trading_symbol)
        equity = client.fetch_account_equity(settings.account_equity_fallback)
        risk = equity * (settings.risk_per_trade_percent / 100.0)
        print(f"[OK] Delta API connected ({len(markets)} markets)")
        print(f"     Resolved symbol: {symbol}")
        print(f"     Last price: {price}")
        print(f"[OK] Live account balance: ${equity:.2f}")
        print(f"     1% risk per trade would be: ${risk:.2f}")
    except Exception as exc:
        print(f"[FAIL] Delta API: {exc}")
        ok = False

    if settings.telegram_bot_token and settings.telegram_chat_id:
        from trading_bot.notifications.telegram import TelegramNotifier

        n = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
        if n.send("Setup check: bot environment OK."):
            print("[OK] Telegram notification sent")
        else:
            print("[WARN] Telegram configured but send failed")
    else:
        print("[SKIP] Telegram not configured")

    print()
    if ok:
        print("Ready. Start the bot with:  python main.py")
        return 0
    print("Fix errors above, then run:  python check_setup.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
