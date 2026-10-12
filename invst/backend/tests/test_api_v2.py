"""Integration tests for Arth IQ V0.2 API endpoints."""

import sqlite3
import pytest
from fastapi.testclient import TestClient

from invst.api.app import create_app
from invst.api.routes import get_db
from invst.config import get_config


@pytest.fixture
def client(tmp_path):
    cfg = get_config()
    test_db_path = tmp_path / "test_api_v2.db"
    with sqlite3.connect(str(cfg.database.path)) as src, sqlite3.connect(str(test_db_path)) as dst:
        src.backup(dst)

    app = create_app()

    def override_get_db():
        conn = sqlite3.connect(str(test_db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def test_v2_recommendations_endpoint(client):
    # Public or auth disabled
    response = client.get("/api/v2/recommendations?top_n=5")
    # Should succeed with 200
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "count" in data
    assert "asof_date" in data
    if data["count"] > 0:
        rec = data["recommendations"][0]
        assert "symbol" in rec
        assert "business_score" in rec
        assert "investment_score" in rec
        assert "matrix_quadrant" in rec
        assert "scenario" in rec
        assert "expected_return_pct" in rec["scenario"]


def test_v2_hrp_portfolio_endpoint(client):
    payload = {
        "capital": 250000.0,
        "profile": "MODERATE",
        "top_n": 8,
    }
    response = client.post("/api/v2/portfolio/hrp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "weights" in data
    assert "total_invested" in data
    assert "expected_portfolio_return" in data
    assert "sharpe_ratio" in data
    assert data["investor_profile"] == "MODERATE"


def test_v2_events_feed_endpoint(client):
    response = client.get("/api/v2/events/feed")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "events" in data


def test_v2_macro_pulse_endpoint(client):
    response = client.get("/api/v2/macro/pulse")
    assert response.status_code == 200
    data = response.json()
    assert "india_vix" in data
    assert "regime" in data
    assert "nifty_50" in data


def test_v2_analyze_endpoint(client):
    response = client.get("/api/v2/analyze/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TCS"
    assert "business_score" in data
    assert "investment_score" in data
    assert "action_verdict" in data
    assert "horizon_3m" in data
    assert "horizon_12m" in data
    assert "horizon_3y" in data


def test_stock_price_history_endpoint(client):
    response = client.get("/api/v2/analyze/TCS/price-history")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TCS"
    assert "points" in data
    assert "asof_date" in data
    assert all({"date", "close"}.issubset(point) for point in data["points"])
    assert [point["date"] for point in data["points"]] == sorted(point["date"] for point in data["points"])
    for period in ("1D", "30D", "6M", "1Y"):
        period_response = client.get(f"/api/v2/analyze/TCS/price-history?period={period}")
        assert period_response.status_code == 200
        assert period_response.json()["period"] == period
    assert client.get("/api/v2/analyze/TCS/price-history?period=5Y").status_code == 400


def test_v2_portfolio_endpoints(client):
    payload = {
        "holdings": [
            {"symbol": "TCS", "shares": 10.0, "buy_price": 1400.0},
            {"symbol": "INFY", "shares": 20.0, "buy_price": 1850.0},
        ]
    }
    # Test save
    res_save = client.post("/api/v2/portfolio/holdings", json=payload)
    assert res_save.status_code == 200
    assert res_save.json()["count"] == 2

    # Test load
    res_load = client.get("/api/v2/portfolio/holdings")
    assert res_load.status_code == 200
    loaded = res_load.json()
    assert len(loaded) == 2

    # Test health diagnosis
    res_health = client.post("/api/v2/portfolio/health", json=payload)
    assert res_health.status_code == 200
    h_data = res_health.json()
    assert h_data["total_current_value"] > 0.0
    assert "overall_health_score" in h_data
    assert len(h_data["positions"]) == 2
    assert "action_verdict" in h_data["positions"][0]


def test_v2_multiple_portfolios_and_targetlists_api(client):
    # 1. List portfolios
    res_list = client.get("/api/v2/portfolios")
    assert res_list.status_code == 200
    p_list = res_list.json()
    assert len(p_list) >= 1

    # 2. Create custom targetlist
    new_tl = {
        "name": "Breakout Watchlist",
        "description": "High momentum stocks on dip watchlist",
        "portfolio_type": "TARGETLIST",
        "holdings": [],
    }
    res_create = client.post("/api/v2/portfolios", json=new_tl)
    assert res_create.status_code == 200
    created = res_create.json()
    tl_id = created["id"]
    assert created["portfolio_type"] == "TARGETLIST"

    # 3. Add stock to targetlist (from analyzer workflow)
    stock_payload = {
        "symbol": "TCS",
        "shares": 10.0,
        "buy_price": 1400.0,
        "target_price": 1350.0,
        "notes": "Add on dip below 1350",
    }
    res_add = client.post(f"/api/v2/portfolios/{tl_id}/holdings", json=stock_payload)
    assert res_add.status_code == 200
    assert res_add.json()["status"] == "success"

    # 4. Fetch details
    res_detail = client.get(f"/api/v2/portfolios/{tl_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert len(detail["holdings"]) == 1
    assert detail["holdings"][0]["symbol"] == "TCS"
    assert detail["holdings"][0]["target_price"] == 1350.0

    # 5. Evaluate health for this specific portfolio
    res_health_id = client.post(f"/api/v2/portfolios/{tl_id}/health")
    assert res_health_id.status_code == 200
    health_data = res_health_id.json()
    assert len(health_data["positions"]) == 1
    assert health_data["positions"][0]["symbol"] == "TCS"

    # 6. Delete stock from portfolio
    res_del_stock = client.delete(f"/api/v2/portfolios/{tl_id}/holdings/TCS")
    assert res_del_stock.status_code == 200

    # 7. Delete portfolio
    res_del = client.delete(f"/api/v2/portfolios/{tl_id}")
    assert res_del.status_code == 200

