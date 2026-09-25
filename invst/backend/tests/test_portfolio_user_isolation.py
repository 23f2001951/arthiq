"""Unit tests verifying user portfolio and target list table separation and multi-user isolation."""

import sqlite3
import pytest
from fastapi.testclient import TestClient

from invst.api.app import app
from invst.api.auth import create_access_token
from invst.portfolio.health import (
    UserHolding,
    init_portfolio_db,
    save_user_holdings,
    load_user_holdings,
    list_portfolios,
    get_portfolio,
    create_portfolio,
    delete_portfolio,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_table_separation_and_schema():
    """Verify user_portfolios and user_target_lists exist as distinct tables."""
    conn = sqlite3.connect(":memory:")
    init_portfolio_db(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}

    assert "user_portfolios" in tables
    assert "user_portfolio_holdings" in tables
    assert "user_target_lists" in tables
    assert "user_target_list_items" in tables
    conn.close()


def test_user_11_holdings_and_dip_list_isolation():
    """Verify User 11 and User 12 have completely isolated portfolios and dip target lists."""
    conn = sqlite3.connect(":memory:")
    init_portfolio_db(conn)

    # 1. User 11 (itsmandeepbeniwal@gmail.com) holdings
    u11_holdings = [
        UserHolding(symbol="GOLDIETF", shares=19.0, buy_price=110.02),
        UserHolding(symbol="SILVERIETF", shares=25.0, buy_price=162.55),
        UserHolding(symbol="NIFTYBEES", shares=8.0, buy_price=261.40),
    ]
    save_user_holdings(conn, u11_holdings, portfolio_id="default", user_id=11)

    # 2. User 11 dip target list
    u11_dips = [
        UserHolding(symbol="KSCL", shares=10.0, buy_price=768.80, target_price=768.80),
        UserHolding(symbol="IDBI", shares=10.0, buy_price=77.70, target_price=77.70),
        UserHolding(symbol="IDFCFIRSTB", shares=10.0, buy_price=77.40, target_price=77.40),
    ]
    create_portfolio(
        conn,
        portfolio_id="targetlist_dips",
        name="Tactical Dip Target List",
        portfolio_type="target_list",
        initial_holdings=u11_dips,
        user_id=11,
    )

    # 3. User 12 (different user) with their own default portfolio
    u12_holdings = [
        UserHolding(symbol="RELIANCE", shares=50.0, buy_price=2900.0),
    ]
    save_user_holdings(conn, u12_holdings, portfolio_id="default", user_id=12)

    # Verify User 11 sees their 3 holdings
    loaded_11 = load_user_holdings(conn, portfolio_id="default", user_id=11)
    assert len(loaded_11) == 3
    assert {h.symbol for h in loaded_11} == {"GOLDIETF", "SILVERIETF", "NIFTYBEES"}

    # Verify User 12 sees only RELIANCE in their default portfolio
    loaded_12 = load_user_holdings(conn, portfolio_id="default", user_id=12)
    assert len(loaded_12) == 1
    assert loaded_12[0].symbol == "RELIANCE"

    # Verify User 11's target list
    p11_dips = get_portfolio(conn, "targetlist_dips", user_id=11)
    assert p11_dips is not None
    assert len(p11_dips.holdings) == 3
    assert {h.symbol for h in p11_dips.holdings} == {"KSCL", "IDBI", "IDFCFIRSTB"}

    # Verify User 12 cannot see User 11's target list
    p12_dips = get_portfolio(conn, "targetlist_dips", user_id=12)
    assert p12_dips is None

    # Verify list_portfolios filters by user_id
    u11_portfolios = list_portfolios(conn, portfolio_type="portfolio", user_id=11)
    assert len(u11_portfolios) == 1
    assert u11_portfolios[0]["id"] == "default"

    u11_targets = list_portfolios(conn, portfolio_type="target_list", user_id=11)
    assert len(u11_targets) == 1
    assert u11_targets[0]["id"] == "targetlist_dips"

    u12_targets = list_portfolios(conn, portfolio_type="target_list", user_id=12)
    assert len(u12_targets) == 0

    conn.close()


def test_api_multi_user_isolation(client):
    """Verify FastAPI routes strictly scope portfolio data to the authenticated user."""
    # Generate tokens for two different users
    token_11 = create_access_token({"id": 11, "email": "itsmandeepbeniwal@gmail.com", "role": "user"})
    token_99 = create_access_token({"id": 99, "email": "other_investor@example.com", "role": "user"})

    headers_11 = {"Authorization": f"Bearer {token_11}"}
    headers_99 = {"Authorization": f"Bearer {token_99}"}

    # User 11 retrieves portfolios
    res_11 = client.get("/api/v2/portfolios", headers=headers_11)
    assert res_11.status_code == 200
    p_ids_11 = {p["id"] for p in res_11.json()}
    assert "default" in p_ids_11
    assert "targetlist_dips" in p_ids_11

    # User 99 retrieves portfolios (should not see User 11's custom targetlist_dips)
    res_99 = client.get("/api/v2/portfolios", headers=headers_99)
    assert res_99.status_code == 200
    p_ids_99 = {p["id"] for p in res_99.json()}
    assert "targetlist_dips" not in p_ids_99
