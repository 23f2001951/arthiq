"""Unit tests for the unified database engine and Neon migration utilities."""

import sqlite3
from invst.db.engine import (
    TABLE_PK_MAP,
    Row,
    adapt_sql,
    get_db_connection,
    is_postgres,
)


def test_is_postgres_detection():
    assert not is_postgres(None)
    assert not is_postgres("sqlite:///db/invst.db")
    assert is_postgres("postgres://user:pass@ep-xyz.neon.tech/neondb")
    assert is_postgres("postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require")


def test_adapt_sql_placeholders():
    q = "SELECT id, email FROM users WHERE email = ? AND role = ?"
    adapted = adapt_sql(q)
    assert adapted == "SELECT id, email FROM users WHERE email = %s AND role = %s"


def test_adapt_sql_insert_or_ignore():
    q = "INSERT OR IGNORE INTO users (email, name) VALUES (?, ?)"
    adapted = adapt_sql(q)
    assert "INSERT INTO users" in adapted
    assert "ON CONFLICT DO NOTHING" in adapted
    assert "%s" in adapted


def test_adapt_sql_insert_or_replace():
    q = "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, open, close, source) VALUES (?, ?, ?, ?, ?)"
    adapted = adapt_sql(q)
    assert "INSERT INTO daily_prices" in adapted
    assert "ON CONFLICT (symbol, trade_date, source)" in adapted
    assert "DO UPDATE SET" in adapted
    assert "close = EXCLUDED.close" in adapted


def test_row_mapping_compatibility():
    description = [
        ("id", 23, None, None, None, None, None),
        ("email", 1043, None, None, None, None, None),
        ("role", 1043, None, None, None, None, None),
    ]
    values = (11, "itsmandeepbeniwal@gmail.com", "admin")
    row = Row(description, values)

    # Index access
    assert row[0] == 11
    assert row[1] == "itsmandeepbeniwal@gmail.com"
    assert row[2] == "admin"

    # Key access
    assert row["id"] == 11
    assert row["email"] == "itsmandeepbeniwal@gmail.com"
    assert row["role"] == "admin"
    assert row["EMAIL"] == "itsmandeepbeniwal@gmail.com"  # case-insensitive

    # Dict conversion
    d = dict(row)
    assert d == {
        "id": 11,
        "email": "itsmandeepbeniwal@gmail.com",
        "role": "admin",
    }
    assert "email" in row
    assert row.get("name", "Default") == "Default"


def test_sqlite_connection_works_transparently():
    conn = get_db_connection(":memory:")
    conn.execute("CREATE TABLE test_tab (id INT PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO test_tab (id, title) VALUES (?, ?)", (1, "Test"))
    cur = conn.execute("SELECT * FROM test_tab WHERE id = ?", (1,))
    res = cur.fetchone()
    assert res is not None
    assert res["id"] == 1
    assert res["title"] == "Test"


def test_adapt_sql_autoincrement_to_serial():
    q = "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL);"
    adapted = adapt_sql(q)
    assert "SERIAL PRIMARY KEY" in adapted
    assert "AUTOINCREMENT" not in adapted

