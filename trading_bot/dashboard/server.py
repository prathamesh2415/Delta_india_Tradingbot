"""FastAPI dashboard: profit vs fees."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from trading_bot.config import Settings
from trading_bot.dashboard.analytics import DashboardAnalytics
from trading_bot.db.repository import TradeRepository
from trading_bot.exchange.delta_client import DeltaExchangeClient

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repo = TradeRepository(settings.database_path)
    analytics = DashboardAnalytics(repo)

    app = FastAPI(title="Trading Bot Dashboard", version="1.0.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def _check_auth(password: str | None) -> None:
        if settings.dashboard_password and password != settings.dashboard_password:
            raise HTTPException(status_code=401, detail="Invalid dashboard password")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/summary")
    def api_summary(password: str | None = Query(None)) -> dict:
        _check_auth(password)
        live_balance = 0.0
        try:
            client = DeltaExchangeClient(
                settings.delta_api_key,
                settings.delta_api_secret,
                paper_trading=settings.paper_trading,
                equity_fallback_usd=settings.account_equity_fallback,
            )
            live_balance = client.fetch_account_equity(
                settings.account_equity_fallback
            )
        except Exception:
            pass
        s = analytics.build_summary(live_balance, settings.paper_trading)
        return {
            "live_balance_usd": round(s.live_balance_usd, 2),
            "gross_profit_usd": round(s.gross_profit_usd, 2),
            "gross_loss_usd": round(s.gross_loss_usd, 2),
            "total_fees_usd": round(s.total_fees_usd, 2),
            "net_profit_usd": round(s.net_profit_usd, 2),
            "profitable_after_fees": s.profitable_after_fees,
            "total_trades": s.total_trades,
            "closed_trades": s.closed_trades,
            "open_trades": s.open_trades,
            "winning_trades": s.winning_trades,
            "losing_trades": s.losing_trades,
            "fee_to_gross_ratio_percent": round(s.fee_to_gross_ratio_percent, 2),
            "avg_fee_per_trade_usd": round(s.avg_fee_per_trade_usd, 4),
            "avg_net_per_trade_usd": round(s.avg_net_per_trade_usd, 4),
            "paper_trading": s.paper_trading,
            "taker_fee_percent": settings.taker_fee_percent,
        }

    @app.get("/api/trades")
    def api_trades(
        password: str | None = Query(None),
        limit: int = Query(50, ge=1, le=500),
    ) -> dict:
        _check_auth(password)
        rows = repo.get_trades_with_fees(limit=limit)
        return {"trades": rows}

    @app.get("/api/equity-history")
    def api_equity_history(
        password: str | None = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ) -> dict:
        _check_auth(password)
        return {"snapshots": repo.get_equity_history(limit=limit)}

    return app
