"""Integration tests for FastAPI REST API endpoints."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from invst.api.app import create_app
from invst.api.routes import get_db


@pytest.fixture
def client(scoring_db: sqlite3.Connection):
    """Create a test client with dependency override to use scoring_db."""
    app = create_app()

    def override_get_db():
        yield scoring_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def test_api_docs(client: TestClient):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower() or "openapi" in resp.text.lower()


def test_api_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "data_quality_checks" in data
    assert "pit_audits" in data


def test_api_dashboard(client: TestClient):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "target_holdings" in data
    assert "max_stock_cap" in data
    assert "holdings" in data


def test_api_recommendations(client: TestClient):
    resp = client.get("/api/recommendations?asof=2024-03-31&top_n=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asof_date"] == "2024-03-31"
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

    first = data["recommendations"][0]
    assert "symbol" in first
    assert "rationale" in first
    assert "composite_score" in first
    assert "quality_score" in first


def test_api_quick_picks(client: TestClient):
    resp = client.get("/api/recommendations/picks?asof=2024-03-31&n=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asof_date"] == "2024-03-31"
    assert data["n_requested"] == 2
    assert "picks" in data
    assert len(data["picks"]) <= 2
    if data["picks"]:
        pick = data["picks"][0]
        assert "symbol" in pick
        assert "rationale" in pick
        assert "suggested_weight" in pick
        assert pick["suggested_weight"] > 0


def test_api_universe(client: TestClient):
    resp = client.get("/api/universe?asof=2024-03-31")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asof_date"] == "2024-03-31"
    assert data["total_symbols"] > 0
    assert "sectors" in data


def test_api_backtest_run_and_list(client: TestClient):
    # Run backtest
    payload = {
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "initial_capital": 1000000.0,
        "benchmark_symbol": "NIFTY500",
        "target_holdings": 8,
    }
    resp = client.post("/api/backtest/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert "metrics" in data
    assert data["metrics"]["cagr"] is not None

    # List backtest runs
    list_resp = client.get("/api/backtest/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) > 0
    assert runs[0]["run_id"] == data["run_id"]


def test_spa_static_serving(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Arth IQ" in resp.text
    assert '<div id="root"></div>' in resp.text
