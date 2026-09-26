"""Database engine and unified connection manager.

Provides dual-engine capability:
- Local offline development and unit tests with SQLite.
- Production and cloud environments with Neon Serverless PostgreSQL.

Includes transparent SQL syntax translation (? -> %s, PRAGMA handling, and
standard ON CONFLICT upsert adaptation) and a sqlite3.Row-compatible Row mapping
so existing services and routes run seamlessly across both databases.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Known primary keys for UPSERT translation in PostgreSQL
TABLE_PK_MAP: dict[str, list[str]] = {
    "users": ["email"],
    "user_portfolios": ["id", "user_id"],
    "user_portfolio_holdings": ["portfolio_id", "user_id", "symbol"],
    "user_target_lists": ["id", "user_id"],
    "user_target_list_items": ["list_id", "user_id", "symbol"],
    "daily_prices": ["symbol", "trade_date", "source"],
    "fundamentals_quarterly": ["symbol", "period_end", "metric", "source"],
    "fundamentals_pit": ["symbol", "period_end", "disclosed_at", "metric", "source"],
    "corporate_actions_pit": ["symbol", "action_type", "ex_date", "source"],
    "corporate_events_pit": ["symbol", "event_type", "record_date", "effective_date"],
    "news_sentiment": ["headline_id"],
    "scorecards_v2_history": ["asof_date", "symbol"],
    "portfolio_history": ["run_id", "symbol"],
    "backtest_runs": ["run_id"],
    "model_predictions": ["asof_date", "symbol", "model_name"],
    "index_constituents_history": ["effective_date", "symbol"],
    "mf_schemes": ["scheme_code"],
    "mf_nav_history": ["scheme_code", "nav_date"],
    "mf_holdings": ["scheme_code", "as_of_date", "company_name"],
    "user_mf_portfolios": ["id"],
    "mf_sip_schedules": ["id"],
    "mf_transactions": ["id"],
    "mf_sip_checkins": ["id"],
}


def get_database_url() -> str | None:
    """Retrieve the configured database URL from environment or .env file."""
    # During automated pytest runs, default to offline local database unless explicitly forced
    if "PYTEST_CURRENT_TEST" in os.environ and "FORCE_NEON_TEST" not in os.environ:
        return None

    if os.environ.get("USE_LOCAL_DB") == "1":
        return None

    url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if url:
        return url.strip()


    # Check for .env file in project root or backend directory
    for env_path in [Path(".env"), Path("../.env"), Path(__file__).resolve().parents[3] / ".env"]:
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k in ("DATABASE_URL", "NEON_DATABASE_URL") and v:
                            return v
            except Exception:
                pass
    return None


def is_postgres(url: str | None = None) -> bool:
    """Return True if the database URL points to a PostgreSQL database."""
    target_url = url or get_database_url()
    if not target_url:
        return False
    lower = target_url.lower()
    return lower.startswith("postgres://") or lower.startswith("postgresql://")


def adapt_sql(sql: str) -> str:
    """Adapt SQLite-dialect SQL to PostgreSQL-compatible syntax."""
    s = sql.strip()

    # 0. Transform SQLite AUTOINCREMENT to Postgres SERIAL
    s = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "SERIAL PRIMARY KEY",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bINT\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "SERIAL PRIMARY KEY",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bAUTOINCREMENT\b",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # 1. Transform INSERT OR IGNORE INTO <table> (...)
    if re.match(r"INSERT\s+OR\s+IGNORE\s+INTO", s, re.IGNORECASE):
        s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, count=1, flags=re.IGNORECASE)
        if "ON CONFLICT" not in s.upper():
            s = s.rstrip("; ") + " ON CONFLICT DO NOTHING"

    # 2. Transform INSERT OR REPLACE INTO <table> (<cols>) VALUES (...)
    match_replace = re.match(
        r"INSERT\s+OR\s+REPLACE\s+INTO\s+[\"']?([a-zA-Z0-9_]+)[\"']?\s*\(([^)]+)\)\s*VALUES\s*(.*)",
        s,
        re.IGNORECASE | re.DOTALL,
    )
    if match_replace:
        tbl = match_replace.group(1).lower()
        cols = [c.strip().strip("\"'").lower() for c in match_replace.group(2).split(",")]
        vals = match_replace.group(3).rstrip("; ")
        pk_cols = TABLE_PK_MAP.get(tbl, [])
        if pk_cols and "ON CONFLICT" not in s.upper():
            update_cols = [c for c in cols if c not in pk_cols]
            pk_str = ", ".join(pk_cols)
            if update_cols:
                set_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                s = f"INSERT INTO {tbl} ({', '.join(cols)}) VALUES {vals} ON CONFLICT ({pk_str}) DO UPDATE SET {set_str}"
            else:
                s = f"INSERT INTO {tbl} ({', '.join(cols)}) VALUES {vals} ON CONFLICT ({pk_str}) DO NOTHING"
        else:
            s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s, count=1, flags=re.IGNORECASE)

    # 2.5 Transform SQLite date arithmetic like date(col, '-14 days') or date(?, '-' || ? || ' days')
    s = re.sub(
        r"\bdate\s*\(\s*([^,]+?)\s*,\s*'-'\s*\|\|\s*([^,]+?)\s*\|\|\s*'\s*days'\s*\)",
        r"((\1)::date - ((\2)::text || ' days')::interval)::date",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bdate\s*\(\s*([^,]+?)\s*,\s*'-(\d+)\s*days'\s*\)",
        r"((\1)::date - interval '\2 days')::date",
        s,
        flags=re.IGNORECASE,
    )

    # 3. Replace '?' parameter placeholders with '%s' outside quotes
    result: list[str] = []
    in_single = False
    in_double = False
    for ch in s:
        if ch == "'" and not in_double:
            in_single = not in_single
            result.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            result.append(ch)
        elif ch == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(ch)
    return "".join(result)


class Row(Sequence[Any]):
    """sqlite3.Row-compatible dictionary and indexable mapping for PostgreSQL results."""

    __slots__ = ("_keys", "_values", "_mapping", "_mapping_lower")

    def __init__(self, description: Sequence[Any] | None, values: Sequence[Any]) -> None:
        self._keys = [d[0] for d in description] if description else []
        self._values = tuple(values)
        self._mapping = {k: v for k, v in zip(self._keys, self._values)}
        self._mapping_lower = {k.lower(): v for k, v in zip(self._keys, self._values)}

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, (int, slice)):
            return self._values[item]
        if isinstance(item, str):
            if item in self._mapping:
                return self._mapping[item]
            if item.lower() in self._mapping_lower:
                return self._mapping_lower[item.lower()]
            raise KeyError(item)
        raise TypeError(f"Row indices must be integers, slices, or strings, not {type(item).__name__}")

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Iterator[Any]:
        # Sequence protocol: must iterate over column values (like sqlite3.Row)
        # to support tuple unpacking `(a, b) = row` and parameter passing `tuple(row)`.
        return iter(self._values)

    def keys(self) -> list[str]:
        return list(self._keys)

    def values(self) -> tuple[Any, ...]:
        return self._values

    def items(self) -> list[tuple[str, Any]]:
        return list(zip(self._keys, self._values))

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._mapping:
            return self._mapping[key]
        return self._mapping_lower.get(key.lower(), default)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return key in self._mapping or key.lower() in self._mapping_lower or key in self._values
        return key in self._values

    def __repr__(self) -> str:
        return f"<Row {self._mapping}>"


class PostgresCursorWrapper:
    """Cursor wrapper for psycopg2 that mimics sqlite3 Cursor methods and behavior."""

    def __init__(self, raw_cursor: Any, conn_wrapper: PostgresConnectionWrapper) -> None:
        self._cur = raw_cursor
        self._conn_wrapper = conn_wrapper

    @property
    def description(self) -> Any:
        return self._cur.description

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursorWrapper:
        stripped = sql.strip()
        upper = stripped.upper()

        # Handle SQLite PRAGMA commands
        if upper.startswith("PRAGMA"):
            # PRAGMA table_info(table_name)
            match_table_info = re.match(r"PRAGMA\s+table_info\(([^)]+)\)", stripped, re.IGNORECASE)
            if match_table_info:
                table_name = match_table_info.group(1).strip().strip("\"'").lower()
                query = """
                    SELECT 
                        ordinal_position - 1 AS cid,
                        column_name AS name,
                        data_type AS type,
                        CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                        column_default AS dflt_value,
                        0 AS pk
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """
                self._cur.execute(query, (table_name,))
                return self

            # Other PRAGMAs (foreign_keys, journal_mode, etc.) are no-ops in PostgreSQL
            return self

        adapted = adapt_sql(sql)
        try:
            if params is not None:
                self._cur.execute(adapted, tuple(params))
            else:
                self._cur.execute(adapted)
        except Exception as exc:
            err_msg = str(exc).lower()
            # If server closed connection unexpectedly or connection is closed, attempt one reconnect & retry
            if "closed" in err_msg or "terminated" in err_msg or "connection" in err_msg:
                logger.warning("Postgres connection lost during execute (%s). Reconnecting and retrying once...", exc)
                try:
                    raw_conn = self._conn_wrapper._get_raw_conn(force_reconnect=True)
                    self._cur = raw_conn.cursor()
                    if params is not None:
                        self._cur.execute(adapted, tuple(params))
                    else:
                        self._cur.execute(adapted)
                    return self
                except Exception as retry_exc:
                    logger.error("Retry after reconnect failed: %s", retry_exc)

            logger.error("Failed to execute adapted SQL on Postgres:\nSQL: %s\nAdapted: %s\nError: %s", sql, adapted, exc)
            try:
                self._conn_wrapper.rollback()
            except Exception:
                pass
            raise
        return self

    def executemany(self, sql: str, seq_of_parameters: Sequence[Sequence[Any]]) -> PostgresCursorWrapper:
        adapted = adapt_sql(sql)
        try:
            self._cur.executemany(adapted, [tuple(p) for p in seq_of_parameters])
        except Exception as exc:
            err_msg = str(exc).lower()
            if "closed" in err_msg or "terminated" in err_msg or "connection" in err_msg:
                logger.warning("Postgres connection lost during executemany (%s). Reconnecting and retrying once...", exc)
                try:
                    raw_conn = self._conn_wrapper._get_raw_conn(force_reconnect=True)
                    self._cur = raw_conn.cursor()
                    self._cur.executemany(adapted, [tuple(p) for p in seq_of_parameters])
                    return self
                except Exception as retry_exc:
                    logger.error("Retry after reconnect failed: %s", retry_exc)

            logger.error("Failed to execute adapted SQL on Postgres:\nSQL: %s\nAdapted: %s\nError: %s", sql, adapted, exc)
            try:
                self._conn_wrapper.rollback()
            except Exception:
                pass
            raise
        return self

    def fetchone(self) -> Row | None:
        row = self._cur.fetchone()
        if row is None:
            return None
        return Row(self._cur.description, row)

    def fetchall(self) -> list[Row]:
        rows = self._cur.fetchall()
        desc = self._cur.description
        return [Row(desc, r) for r in rows]

    def fetchmany(self, size: int = 1) -> list[Row]:
        rows = self._cur.fetchmany(size)
        desc = self._cur.description
        return [Row(desc, r) for r in rows]

    def __iter__(self) -> Iterator[Row]:
        desc = self._cur.description
        for row in self._cur:
            yield Row(desc, row)

    def close(self) -> None:
        try:
            self._cur.close()
        except Exception:
            pass

    def __enter__(self) -> PostgresCursorWrapper:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class PostgresConnectionWrapper:
    """Connection wrapper for psycopg2 that mimics sqlite3.Connection with auto-reconnection."""

    def __init__(self, raw_conn: Any, connect_url: str | None = None) -> None:
        self._raw_conn = raw_conn
        self._connect_url = connect_url
        self.row_factory = None
        if self._raw_conn:
            try:
                self._raw_conn.autocommit = True
            except Exception:
                pass

    def _get_raw_conn(self, force_reconnect: bool = False) -> Any:
        """Return healthy connection, automatically reconnecting to Neon if disconnected."""
        is_broken = force_reconnect
        if not is_broken:
            try:
                if self._raw_conn is None or getattr(self._raw_conn, "closed", 1) != 0:
                    is_broken = True
                else:
                    with self._raw_conn.cursor() as cur:
                        cur.execute("SELECT 1")
            except Exception:
                is_broken = True

        if is_broken and self._connect_url:
            import psycopg2
            logger.info("Re-establishing PostgreSQL connection to %s...", self._connect_url.split("@")[-1] if "@" in self._connect_url else "database")
            try:
                self._raw_conn = psycopg2.connect(
                    self._connect_url,
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5,
                )
                self._raw_conn.autocommit = True
            except Exception as exc:
                logger.error("Failed to re-establish PostgreSQL connection: %s", exc)
                raise
        return self._raw_conn

    def cursor(self) -> PostgresCursorWrapper:
        raw_conn = self._get_raw_conn()
        return PostgresCursorWrapper(raw_conn.cursor(), self)

    def commit(self) -> None:
        try:
            if self._raw_conn and not getattr(self._raw_conn, "closed", 1) and not getattr(self._raw_conn, "autocommit", False):
                self._raw_conn.commit()
        except Exception:
            pass

    def rollback(self) -> None:
        try:
            if self._raw_conn and not getattr(self._raw_conn, "closed", 1) and not getattr(self._raw_conn, "autocommit", False):
                self._raw_conn.rollback()
        except Exception:
            pass

    def close(self) -> None:
        try:
            if self._raw_conn and not getattr(self._raw_conn, "closed", 1):
                self._raw_conn.close()
        except Exception:
            pass

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_parameters: Sequence[Sequence[Any]]) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.executemany(sql, seq_of_parameters)
        return cur

    def __enter__(self) -> PostgresConnectionWrapper:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


def get_db_connection(
    db_path: str | Path | None = None,
    db_url: str | None = None,
) -> Any:
    """Get a database connection, connecting to Neon PostgreSQL or SQLite.

    If db_url or DATABASE_URL/NEON_DATABASE_URL is provided, connects to PostgreSQL.
    Otherwise, connects to the local SQLite database at db_path (or config default).
    """
    target_url = db_url or get_database_url()

    if target_url and is_postgres(target_url):
        # Replace postgres:// with postgresql:// if needed for psycopg2
        clean_url = target_url
        if clean_url.startswith("postgres://"):
            clean_url = "postgresql://" + clean_url[len("postgres://") :]

        try:
            import psycopg2

            raw_conn = psycopg2.connect(
                clean_url,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            raw_conn.autocommit = True
            return PostgresConnectionWrapper(raw_conn, connect_url=clean_url)
        except Exception as exc:
            clean_host = clean_url.split("@")[-1] if "@" in clean_url else "database"
            logger.warning(
                "Could not connect to PostgreSQL database (%s): %s. Gracefully falling back to local SQLite database.",
                clean_host,
                exc,
            )

    # SQLite connection
    import sqlite3

    if db_path is None:
        from invst.config import load_config

        cfg = load_config()
        target_path = Path(cfg.database.path)
    else:
        target_path = Path(db_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
