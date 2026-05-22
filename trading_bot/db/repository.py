"""SQLite persistence for trades, fees, and P&L."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Literal


@dataclass
class TradeRecord:
    id: int | None
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    status: str
    order_id: str | None
    exit_price: float | None
    pnl_usd: float | None
    entry_fee_usd: float
    exit_fee_usd: float
    total_fee_usd: float
    net_pnl_usd: float | None
    entry_trading_fee_usd: float
    entry_gst_usd: float
    exit_trading_fee_usd: float
    exit_gst_usd: float
    entry_notional_usd: float
    exit_notional_usd: float
    opened_at: str
    closed_at: str | None
    notes: str | None


class TradeRepository:
    """CRUD for trade history in SQLite."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(trades)").fetchall()}
        migrations = [
            ("entry_fee_usd", "REAL NOT NULL DEFAULT 0"),
            ("exit_fee_usd", "REAL NOT NULL DEFAULT 0"),
            ("total_fee_usd", "REAL NOT NULL DEFAULT 0"),
            ("net_pnl_usd", "REAL"),
            ("entry_trading_fee_usd", "REAL NOT NULL DEFAULT 0"),
            ("entry_gst_usd", "REAL NOT NULL DEFAULT 0"),
            ("exit_trading_fee_usd", "REAL NOT NULL DEFAULT 0"),
            ("exit_gst_usd", "REAL NOT NULL DEFAULT 0"),
            ("entry_notional_usd", "REAL NOT NULL DEFAULT 0"),
            ("exit_notional_usd", "REAL NOT NULL DEFAULT 0"),
        ]
        for name, typedef in migrations:
            if name not in cols:
                conn.execute(f"ALTER TABLE trades ADD COLUMN {name} {typedef}")

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    size REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    order_id TEXT,
                    exit_price REAL,
                    pnl_usd REAL,
                    entry_fee_usd REAL NOT NULL DEFAULT 0,
                    exit_fee_usd REAL NOT NULL DEFAULT 0,
                    total_fee_usd REAL NOT NULL DEFAULT 0,
                    net_pnl_usd REAL,
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    notes TEXT
                )
                """
            )
            self._migrate_columns(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pnl_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equity_usd REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )

    def insert_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        size: float,
        order_id: str | None = None,
        notes: str | None = None,
        entry_fee_usd: float = 0.0,
        entry_trading_fee_usd: float = 0.0,
        entry_gst_usd: float = 0.0,
        entry_notional_usd: float = 0.0,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO trades (
                    symbol, side, entry_price, stop_loss, take_profit,
                    size, status, order_id, opened_at, notes,
                    entry_fee_usd, exit_fee_usd, total_fee_usd,
                    entry_trading_fee_usd, entry_gst_usd,
                    entry_notional_usd
                ) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    side,
                    entry_price,
                    stop_loss,
                    take_profit,
                    size,
                    order_id,
                    now,
                    notes,
                    entry_fee_usd,
                    entry_fee_usd,
                    entry_trading_fee_usd,
                    entry_gst_usd,
                    entry_notional_usd,
                ),
            )
            return int(cur.lastrowid)

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl_usd: float,
        status: Literal["closed", "stopped", "taken"] = "closed",
        exit_fee_usd: float = 0.0,
        exit_trading_fee_usd: float = 0.0,
        exit_gst_usd: float = 0.0,
        exit_notional_usd: float = 0.0,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT entry_fee_usd FROM trades WHERE id = ?",
                (trade_id,),
            ).fetchone()
            entry_fee = float(row["entry_fee_usd"]) if row else 0.0
            total_fee = entry_fee + exit_fee_usd
            net_pnl = pnl_usd - total_fee
            conn.execute(
                """
                UPDATE trades
                SET status = ?, exit_price = ?, pnl_usd = ?, closed_at = ?,
                    exit_fee_usd = ?, total_fee_usd = ?, net_pnl_usd = ?,
                    exit_trading_fee_usd = ?, exit_gst_usd = ?, exit_notional_usd = ?
                WHERE id = ?
                """,
                (
                    status,
                    exit_price,
                    pnl_usd,
                    now,
                    exit_fee_usd,
                    total_fee,
                    net_pnl,
                    exit_trading_fee_usd,
                    exit_gst_usd,
                    exit_notional_usd,
                    trade_id,
                ),
            )

    def get_open_trades(self, symbol: str | None = None) -> list[TradeRecord]:
        query = "SELECT * FROM trades WHERE status = 'open'"
        params: list[Any] = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_trade_history(self, limit: int = 100) -> list[TradeRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_trades_with_fees(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, symbol, side, entry_price, exit_price, size, status,
                       pnl_usd, entry_fee_usd, exit_fee_usd, total_fee_usd,
                       net_pnl_usd, entry_trading_fee_usd, entry_gst_usd,
                       exit_trading_fee_usd, exit_gst_usd,
                       entry_notional_usd, exit_notional_usd,
                       opened_at, closed_at
                FROM trades
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            gross = float(r["pnl_usd"] or 0)
            fees = float(r["total_fee_usd"] or 0)
            net = r["net_pnl_usd"]
            if net is None and r["pnl_usd"] is not None:
                net = gross - fees
            entry_tf = float(r["entry_trading_fee_usd"] or 0)
            entry_gst = float(r["entry_gst_usd"] or 0)
            exit_tf = float(r["exit_trading_fee_usd"] or 0)
            exit_gst = float(r["exit_gst_usd"] or 0)
            result.append(
                {
                    "id": r["id"],
                    "symbol": r["symbol"],
                    "side": r["side"],
                    "entry_price": r["entry_price"],
                    "exit_price": r["exit_price"],
                    "size": r["size"],
                    "status": r["status"],
                    "entry_notional_usd": round(float(r["entry_notional_usd"] or 0), 2),
                    "exit_notional_usd": round(float(r["exit_notional_usd"] or 0), 2),
                    "gross_pnl_usd": round(gross, 4),
                    "entry_trading_fee_usd": round(entry_tf, 4),
                    "entry_gst_usd": round(entry_gst, 4),
                    "exit_trading_fee_usd": round(exit_tf, 4),
                    "exit_gst_usd": round(exit_gst, 4),
                    "entry_fee_usd": round(float(r["entry_fee_usd"] or 0), 4),
                    "exit_fee_usd": round(float(r["exit_fee_usd"] or 0), 4),
                    "total_trading_fee_usd": round(entry_tf + exit_tf, 4),
                    "total_gst_usd": round(entry_gst + exit_gst, 4),
                    "total_fee_usd": round(fees, 4),
                    "net_pnl_usd": round(float(net or 0), 4),
                    "beats_fees": float(net or 0) > 0,
                    "opened_at": r["opened_at"],
                    "closed_at": r["closed_at"],
                }
            )
        return result

    def get_fee_statistics(self) -> dict[str, float | int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_trades,
                    SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) AS closed_trades,
                    COALESCE(SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END), 0) AS gross_profit,
                    COALESCE(SUM(CASE WHEN pnl_usd < 0 THEN pnl_usd ELSE 0 END), 0) AS gross_loss,
                    COALESCE(SUM(total_fee_usd), 0) AS total_fees,
                    COALESCE(SUM(entry_trading_fee_usd + exit_trading_fee_usd), 0) AS total_trading_fees,
                    COALESCE(SUM(entry_gst_usd + exit_gst_usd), 0) AS total_gst,
                    COALESCE(SUM(
                        COALESCE(net_pnl_usd, pnl_usd - total_fee_usd, 0)
                    ), 0) AS net_profit,
                    SUM(CASE WHEN net_pnl_usd > 0 THEN 1 ELSE 0 END) AS winning_trades,
                    SUM(CASE WHEN net_pnl_usd < 0 THEN 1 ELSE 0 END) AS losing_trades
                FROM trades
                """
            ).fetchone()
        if not row:
            return _empty_stats()
        return {
            "total_trades": int(row["total_trades"] or 0),
            "open_trades": int(row["open_trades"] or 0),
            "closed_trades": int(row["closed_trades"] or 0),
            "gross_profit": float(row["gross_profit"] or 0),
            "gross_loss": float(row["gross_loss"] or 0),
            "total_fees": float(row["total_fees"] or 0),
            "total_trading_fees": float(row["total_trading_fees"] or 0),
            "total_gst": float(row["total_gst"] or 0),
            "net_profit": float(row["net_profit"] or 0),
            "winning_trades": int(row["winning_trades"] or 0),
            "losing_trades": int(row["losing_trades"] or 0),
        }

    def total_realized_pnl(self) -> float:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(COALESCE(net_pnl_usd, pnl_usd)), 0) AS total
                FROM trades WHERE pnl_usd IS NOT NULL
                """
            ).fetchone()
        return float(row["total"]) if row else 0.0

    def get_equity_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT equity_usd, unrealized_pnl, realized_pnl, recorded_at
                FROM pnl_snapshots
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "equity_usd": r["equity_usd"],
                "unrealized_pnl": r["unrealized_pnl"],
                "realized_pnl": r["realized_pnl"],
                "recorded_at": r["recorded_at"],
            }
            for r in reversed(rows)
        ]

    def record_pnl_snapshot(
        self,
        equity_usd: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pnl_snapshots (equity_usd, unrealized_pnl, realized_pnl, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (equity_usd, unrealized_pnl, realized_pnl, now),
            )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TradeRecord:
        return TradeRecord(
            id=row["id"],
            symbol=row["symbol"],
            side=row["side"],
            entry_price=row["entry_price"],
            stop_loss=row["stop_loss"],
            take_profit=row["take_profit"],
            size=row["size"],
            status=row["status"],
            order_id=row["order_id"],
            exit_price=row["exit_price"],
            pnl_usd=row["pnl_usd"],
            entry_fee_usd=float(row["entry_fee_usd"] or 0),
            exit_fee_usd=float(row["exit_fee_usd"] or 0),
            total_fee_usd=float(row["total_fee_usd"] or 0),
            net_pnl_usd=row["net_pnl_usd"],
            entry_trading_fee_usd=float(row["entry_trading_fee_usd"] or 0),
            entry_gst_usd=float(row["entry_gst_usd"] or 0),
            exit_trading_fee_usd=float(row["exit_trading_fee_usd"] or 0),
            exit_gst_usd=float(row["exit_gst_usd"] or 0),
            entry_notional_usd=float(row["entry_notional_usd"] or 0),
            exit_notional_usd=float(row["exit_notional_usd"] or 0),
            opened_at=row["opened_at"],
            closed_at=row["closed_at"],
            notes=row["notes"],
        )


def _empty_stats() -> dict[str, float | int]:
    return {
        "total_trades": 0,
        "open_trades": 0,
        "closed_trades": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "total_fees": 0.0,
        "total_trading_fees": 0.0,
        "total_gst": 0.0,
        "net_profit": 0.0,
        "winning_trades": 0,
        "losing_trades": 0,
    }
