#!/usr/bin/env python3
"""
Migration runner for the invst SQLite database.

Usage:
    python db/migrate.py
    python db/migrate.py --db-path /path/to/invst.db
    python db/migrate.py --status

Features:
- Discovers SQL migrations from db/migrations/ sorted by version prefix (0001_*.sql, etc.)
- Tracks applied migrations in the schema_version table
- Automatically skips already-applied migrations
- Wraps each migration in an atomic transaction with rollback on failure
- Supports relative and absolute database paths
"""

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_default_db_path() -> Path:
    """Returns the default path to the invst SQLite database."""
    # Check if run from invst/ directory with db/ present
    cwd_db = Path("db/invst.db")
    if cwd_db.parent.exists():
        return cwd_db.resolve()
    # Otherwise resolve relative to this script file
    return (Path(__file__).resolve().parent / "invst.db").resolve()


def get_default_migrations_dir() -> Path:
    """Returns the default migrations directory path."""
    return (Path(__file__).resolve().parent / "migrations").resolve()


def init_schema_version_table(conn: sqlite3.Connection) -> None:
    """Ensures the schema_version table exists in the database."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version          INTEGER PRIMARY KEY,
            filename         TEXT    NOT NULL,
            applied_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> Dict[int, Tuple[str, str]]:
    """
    Fetches all applied migrations from schema_version.

    Returns:
        dict mapping version (int) -> (filename, applied_at)
    """
    init_schema_version_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT version, filename, applied_at FROM schema_version ORDER BY version ASC;")
    return {row[0]: (row[1], str(row[2])) for row in cur.fetchall()}


def discover_migrations(migrations_dir: Path) -> List[Tuple[int, Path]]:
    """
    Discovers migration SQL files in migrations_dir and sorts them by version.

    Matches files named like: 0001_init.sql, 0002_add_feature.sql

    Returns:
        Sorted list of tuples: (version, Path)
    """
    if not migrations_dir.exists() or not migrations_dir.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    pattern = re.compile(r"^(\d+)_(.+)\.sql$")
    migrations: List[Tuple[int, Path]] = []
    seen_versions: Dict[int, Path] = {}

    for file_path in sorted(migrations_dir.glob("*.sql")):
        match = pattern.match(file_path.name)
        if match:
            version = int(match.group(1))
            if version in seen_versions:
                raise ValueError(
                    f"Duplicate migration version {version}: '{file_path.name}' "
                    f"conflicts with '{seen_versions[version].name}'"
                )
            seen_versions[version] = file_path
            migrations.append((version, file_path))
        else:
            print(f"[WARN]  Skipping non-conforming SQL filename: {file_path.name}")

    migrations.sort(key=lambda item: item[0])
    return migrations


def parse_sql_script(sql_content: str) -> Tuple[List[str], str]:
    """
    Separates PRAGMA directives from the rest of the SQL script.

    PRAGMA statements like `PRAGMA journal_mode = WAL;` cannot execute inside
    an active transaction block in SQLite, so they are extracted to be executed
    prior to beginning the transaction.

    Returns:
        tuple of (pragma_statements, remaining_sql_body)
    """
    lines = sql_content.splitlines()
    pragmas: List[str] = []
    body_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^PRAGMA\s+[^;]+;?$", stripped, re.IGNORECASE):
            if not stripped.endswith(";"):
                stripped += ";"
            pragmas.append(stripped)
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return pragmas, body


def apply_migration(conn: sqlite3.Connection, version: int, filepath: Path) -> None:
    """
    Applies a single migration file atomically.

    PRAGMA statements run first outside a transaction.
    The remaining SQL and the schema_version record are executed inside
    an atomic transaction that is rolled back on any error.
    """
    sql_content = filepath.read_text(encoding="utf-8")
    pragmas, body = parse_sql_script(sql_content)

    # Execute PRAGMA statements first (must run outside transaction block)
    for pragma in pragmas:
        conn.execute(pragma)

    # Check if the script manages its own transaction
    has_transaction = bool(re.search(r"\bBEGIN\b", body, re.IGNORECASE))
    escaped_filename = filepath.name.replace("'", "''")

    if not has_transaction:
        # Wrap migration body and schema_version tracking in a single atomic transaction
        exec_sql = (
            "BEGIN TRANSACTION;\n"
            f"{body}\n"
            f"INSERT OR IGNORE INTO schema_version (version, filename) VALUES ({version}, '{escaped_filename}');\n"
            "COMMIT;"
        )
    else:
        exec_sql = body

    try:
        conn.executescript(exec_sql)
        # Ensure schema_version is updated if script managed its own transaction
        if has_transaction:
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, filename) VALUES (?, ?);",
                (version, filepath.name),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.execute("ROLLBACK;")
        except sqlite3.OperationalError:
            pass  # No active transaction to rollback
        raise exc


def show_status(db_path: Path, migrations_dir: Path) -> int:
    """Displays migration status (applied vs pending) without modifying the database."""
    print(f"Database:             {db_path}")
    print(f"Migrations directory: {migrations_dir}")
    print("-" * 70)

    if not db_path.exists():
        print(f"Database file does not exist yet at {db_path}.")
        migrations = discover_migrations(migrations_dir)
        print(f"Pending migrations ({len(migrations)}):")
        for version, path in migrations:
            print(f"  [PENDING] {version:04d}: {path.name}")
        return 0

    conn = sqlite3.connect(str(db_path))
    try:
        applied = get_applied_migrations(conn)
        migrations = discover_migrations(migrations_dir)

        print(f"{'Version':<10} {'Filename':<35} {'Status':<10} {'Applied At'}")
        print("-" * 70)

        for version, path in migrations:
            if version in applied:
                _, applied_at = applied[version]
                print(f"{version:<10} {path.name:<35} {'APPLIED':<10} {applied_at}")
            else:
                print(f"{version:<10} {path.name:<35} {'PENDING':<10} -")

        return 0
    finally:
        conn.close()


def run_migrations(
    db_path: Optional[Path] = None,
    migrations_dir: Optional[Path] = None,
    verbose: bool = False,
) -> int:
    """
    Runs all pending migrations on the database.

    Args:
        db_path: Path to the SQLite database file.
        migrations_dir: Path to directory containing migration .sql files.
        verbose: If True, prints additional debug information.

    Returns:
        0 on success, non-zero on failure.
    """
    if db_path is None:
        db_path = get_default_db_path()
    else:
        db_path = Path(db_path).expanduser().resolve()

    if migrations_dir is None:
        migrations_dir = get_default_migrations_dir()
    else:
        migrations_dir = Path(migrations_dir).expanduser().resolve()

    print(f"Database:             {db_path}")
    print(f"Migrations directory: {migrations_dir}")

    # Ensure parent directory of database file exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    migrations = discover_migrations(migrations_dir)
    if not migrations:
        print("No migration files found in migrations directory.")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    applied_count = 0
    skipped_count = 0

    try:
        applied = get_applied_migrations(conn)

        for version, filepath in migrations:
            if version in applied:
                skipped_count += 1
                if verbose:
                    _, applied_at = applied[version]
                    print(f"[SKIP]  {filepath.name} (version {version} applied at {applied_at})")
            else:
                print(f"[APPLY] {filepath.name} (version {version})...", end=" ", flush=True)
                try:
                    apply_migration(conn, version, filepath)
                    print("OK")
                    applied_count += 1
                except Exception as exc:
                    print("FAILED")
                    print(f"\n[ERROR] Migration failed on {filepath.name}: {exc}", file=sys.stderr)
                    return 1

        print("-" * 50)
        if applied_count == 0:
            print(f"Database is up to date ({skipped_count} migration(s) already applied).")
        else:
            print(f"Migrations completed: {applied_count} applied, {skipped_count} skipped.")

        return 0
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run database migrations for the invst SQLite database."
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database file (default: db/invst.db)",
    )
    parser.add_argument(
        "--migrations-dir",
        type=str,
        default=None,
        help="Path to migrations directory (default: db/migrations/)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status (applied/pending) without applying changes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output including skipped migrations",
    )

    args = parser.parse_args()

    db_path = Path(args.db_path).expanduser().resolve() if args.db_path else get_default_db_path()
    migrations_dir = (
        Path(args.migrations_dir).expanduser().resolve()
        if args.migrations_dir
        else get_default_migrations_dir()
    )

    if args.status:
        exit_code = show_status(db_path=db_path, migrations_dir=migrations_dir)
    else:
        exit_code = run_migrations(
            db_path=db_path,
            migrations_dir=migrations_dir,
            verbose=args.verbose,
        )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
