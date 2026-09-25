"""Neon Serverless PostgreSQL Database Migration Script.

Migrates the complete Arth IQ financial intelligence database from local SQLite
(db/invst.db) to Neon Serverless PostgreSQL with high-throughput batching,
referential integrity preservation, sequence realignment, and row parity verification.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

from invst.db.engine import get_database_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("invst.migrate_to_neon")

# Migration order respecting foreign key dependencies
MIGRATION_TABLES = [
    "schema_version",
    "users",
    "user_portfolios",
    "user_portfolio_holdings",
    "user_target_lists",
    "user_target_list_items",
    "index_constituents_history",
    "daily_prices",
    "fundamentals_quarterly",
    "fundamentals_pit",
    "corporate_actions_pit",
    "corporate_events_pit",
    "news_sentiment",
    "backtest_runs",
    "portfolio_history",
    "model_predictions",
    "scorecards_v2_history",
]

# Tables with SERIAL primary key sequences that need realignment after migration
SERIAL_TABLES = {
    "users": "id",
    "fundamentals_pit": "id",
    "corporate_actions_pit": "id",
}


def mask_url(url: str) -> str:
    """Mask password in PostgreSQL URL for secure display."""
    return re.sub(r":([^@]+)@", ":****@", url)


def get_schema_sql_path() -> Path:
    """Locate the PostgreSQL schema DDL file."""
    return Path(__file__).resolve().parent / "postgres_schema.sql"


def apply_schema(pg_conn: Any, schema_path: Path) -> None:
    """Execute the PostgreSQL DDL schema against the target database."""
    logger.info("Applying PostgreSQL schema from %s...", schema_path)
    sql = schema_path.read_text(encoding="utf-8")
    with pg_conn.cursor() as cur:
        cur.execute(sql)
    pg_conn.commit()
    logger.info("PostgreSQL schema successfully applied.")


def reset_sequences(pg_conn: Any) -> None:
    """Reset PostgreSQL serial sequences to MAX(id) for auto-incrementing tables."""
    logger.info("Realigning PostgreSQL serial sequences...")
    with pg_conn.cursor() as cur:
        for table, col in SERIAL_TABLES.items():
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', '{col}'),
                    COALESCE((SELECT MAX({col}) FROM {table}), 1)
                );
                """
            )
    pg_conn.commit()
    logger.info("Sequences realigned.")


def migrate_data(
    sqlite_conn: sqlite3.Connection,
    pg_conn: Any,
    batch_size: int = 2500,
) -> dict[str, tuple[int, int]]:
    """Migrate all tables from SQLite to PostgreSQL with batching and return row counts."""
    results: dict[str, tuple[int, int]] = {}

    for table in MIGRATION_TABLES:
        t0 = time.time()
        # 1. Fetch column names from SQLite
        s_cur = sqlite_conn.cursor()
        s_cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in s_cur.fetchall()]
        col_names = ", ".join(cols)

        # 2. Count source rows
        s_cur.execute(f"SELECT COUNT(*) FROM {table}")
        source_count = s_cur.fetchone()[0]

        if source_count == 0:
            logger.info("Table '%s' is empty (0 rows). Skipping data transfer.", table)
            with pg_conn.cursor() as p_cur:
                p_cur.execute(f"SELECT COUNT(*) FROM {table}")
                dest_count = p_cur.fetchone()[0]
            results[table] = (source_count, dest_count)
            continue

        logger.info("Migrating table '%s' (%d rows, %d columns)...", table, source_count, len(cols))

        # 3. Read in batches from SQLite and write to Postgres
        s_cur.execute(f"SELECT {col_names} FROM {table}")
        insert_query = f"INSERT INTO {table} ({col_names}) VALUES %s ON CONFLICT DO NOTHING"

        total_inserted = 0
        with pg_conn.cursor() as p_cur:
            while True:
                rows = s_cur.fetchmany(batch_size)
                if not rows:
                    break
                execute_values(p_cur, insert_query, rows, page_size=batch_size)
                total_inserted += len(rows)
        pg_conn.commit()

        # 4. Verify target count
        with pg_conn.cursor() as p_cur:
            p_cur.execute(f"SELECT COUNT(*) FROM {table}")
            dest_count = p_cur.fetchone()[0]

        elapsed = time.time() - t0
        logger.info(
            "Completed '%s': %d source -> %d target in %.2fs (%.1f rows/sec)",
            table,
            source_count,
            dest_count,
            elapsed,
            source_count / max(elapsed, 0.001),
        )
        results[table] = (source_count, dest_count)

    # Realign sequences for auto-incrementing tables
    reset_sequences(pg_conn)
    return results


def run_verification(
    sqlite_conn: sqlite3.Connection,
    pg_conn: Any,
) -> bool:
    """Audit row parity between SQLite and PostgreSQL across all tables."""
    print("\n" + "=" * 75)
    print(f"{'TABLE NAME':<30} | {'SQLITE':<12} | {'NEON POSTGRES':<14} | {'STATUS'}")
    print("-" * 75)

    all_matched = True
    s_cur = sqlite_conn.cursor()
    p_cur = pg_conn.cursor()

    for table in MIGRATION_TABLES:
        s_cur.execute(f"SELECT COUNT(*) FROM {table}")
        s_count = s_cur.fetchone()[0]

        p_cur.execute(f"SELECT COUNT(*) FROM {table}")
        p_count = p_cur.fetchone()[0]

        status = "MATCH [OK]" if s_count == p_count else "MISMATCH [FAIL]"
        if s_count != p_count:
            all_matched = False

        print(f"{table:<30} | {s_count:<12} | {p_count:<14} | {status}")

    print("=" * 75 + "\n")
    return all_matched


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Arth IQ database from SQLite to Neon PostgreSQL.")
    parser.add_argument(
        "--url",
        "--neon-url",
        dest="neon_url",
        type=str,
        default=None,
        help="Neon PostgreSQL connection URL (e.g. postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require)",
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Path to source SQLite database (defaults to db/invst.db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2500,
        help="Batch size for bulk insertion (default: 2500)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Perform row count verification without migrating data",
    )
    args = parser.parse_args()

    # Determine Neon PostgreSQL URL
    neon_url = args.neon_url or get_database_url()
    if not neon_url:
        logger.error(
            "No PostgreSQL URL provided. Set DATABASE_URL/NEON_DATABASE_URL or pass --url 'postgresql://...'"
        )
        return 1

    clean_url = neon_url.strip()
    if clean_url.startswith("postgres://"):
        clean_url = "postgresql://" + clean_url[len("postgres://") :]

    # Determine SQLite source path
    sqlite_path = Path(args.sqlite_path) if args.sqlite_path else Path(__file__).resolve().parents[3] / "db" / "invst.db"
    if not sqlite_path.is_file():
        # Fallback to local db/invst.db relative to cwd
        sqlite_path = Path("db/invst.db").resolve()
    if not sqlite_path.is_file():
        logger.error("Source SQLite database not found at %s", sqlite_path)
        return 1

    logger.info("Source SQLite DB: %s", sqlite_path)
    logger.info("Destination Neon: %s", mask_url(clean_url))

    # Connect to databases
    try:
        s_conn = sqlite3.connect(str(sqlite_path))
    except Exception as exc:
        logger.error("Failed to connect to SQLite: %s", exc)
        return 1

    try:
        p_conn = psycopg2.connect(clean_url)
    except Exception as exc:
        logger.error("Failed to connect to Neon PostgreSQL: %s", exc)
        return 1

    try:
        if args.verify_only:
            success = run_verification(s_conn, p_conn)
            return 0 if success else 2

        # 1. Apply schema
        schema_path = get_schema_sql_path()
        apply_schema(p_conn, schema_path)

        # 2. Migrate data
        migrate_data(s_conn, p_conn, batch_size=args.batch_size)

        # 3. Verify
        success = run_verification(s_conn, p_conn)
        if success:
            logger.info("MIGRATION COMPLETED SUCCESSFULLY WITH 100%% ROW PARITY!")
            return 0
        else:
            logger.error("Migration completed with discrepancies. Please review the audit table above.")
            return 2
    finally:
        s_conn.close()
        p_conn.close()


if __name__ == "__main__":
    sys.exit(main())
