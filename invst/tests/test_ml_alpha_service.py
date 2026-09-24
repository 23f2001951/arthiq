"""Unit and integration tests for AlphaModelService and ML-powered Alpha Picks API."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invst.api.app import app
from invst.config import get_config
from invst.ml.alpha_service import AlphaModelService, alpha_service


@pytest.fixture
def db_conn():
    cfg = get_config()
    conn = sqlite3.connect(str(cfg.database.path))
    yield conn
    conn.close()


@pytest.fixture
def client():
    return TestClient(app)


def test_alpha_model_service_training_and_prediction(db_conn, tmp_path):
    temp_model_path = tmp_path / "test_alpha_model.joblib"
    svc = AlphaModelService(model_file=temp_model_path)

    # 1. Initial status check
    init_status = svc.get_status()
    assert init_status.status in ["UNTRAINED", "TRAINED"]

    # 2. Train model
    meta = svc.train_model(
        conn=db_conn,
        asof_date="2026-09-21",
        horizon_days=90,
        model_type="logistic",
        feature_mode="pair_fund_mom",
        calibration_method="sigmoid",
    )

    assert meta.status == "TRAINED"
    assert meta.sample_count > 0
    assert 0.0 <= meta.brier_score <= 1.0
    assert 0.0 <= meta.train_accuracy <= 1.0
    assert len(meta.feature_importances) > 0
    assert temp_model_path.exists()

    # 3. Predict Alpha Picks
    picks = svc.predict_alpha_picks(
        conn=db_conn,
        asof_date="2026-09-21",
        n=2,
        horizon_days=90,
    )

    assert len(picks) == 2
    for rank_idx, pick in enumerate(picks, start=1):
        assert pick.rank == rank_idx
        assert pick.symbol
        assert pick.sector
        assert 0.0 < pick.p_outperform < 1.0
        assert 0.0 <= pick.arth_score <= 100.0
        assert 0.50 <= pick.signal_agreement <= 1.0
        assert pick.conviction_tier in [
            "HIGH CONVICTION ALPHA",
            "STRONG OUTPERFORMER",
            "MARKET PERFORM",
            "UNDERPERFORM CAUTION",
        ]
        assert "30D" in pick.multi_horizon_projections
        assert "90D" in pick.multi_horizon_projections
        assert "180D" in pick.multi_horizon_projections
        assert "252D" in pick.multi_horizon_projections
        assert "Calibrated Alpha Model" in pick.rationale


def test_ml_train_and_status_api_endpoints(client):
    # 1. Test GET /api/ml/status
    res_status = client.get("/api/ml/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "status" in data_status
    assert "model_name" in data_status
    assert "feature_importances" in data_status

    # 2. Test POST /api/ml/train
    res_train = client.post(
        "/api/ml/train",
        json={
            "model_type": "logistic",
            "horizon_days": 90,
            "feature_mode": "pair_fund_mom",
            "calibration_method": "sigmoid",
            "asof": "2026-09-21",
        },
    )
    assert res_train.status_code == 200
    data_train = res_train.json()
    assert data_train["status"] == "TRAINED"
    assert data_train["sample_count"] > 0
    assert "Successfully trained" in data_train["message"]


def test_recommendations_picks_ml_enrichment(client):
    res = client.get("/api/recommendations/picks?n=3&asof=2026-09-21")
    assert res.status_code == 200
    data = res.json()

    assert data["count"] == 3
    assert len(data["picks"]) == 3
    for p in data["picks"]:
        assert 0.0 < p["p_outperform"] < 1.0
        assert 0.0 <= p["arth_score"] <= 100.0
        assert 0.50 <= p["signal_agreement"] <= 1.0
        assert p["conviction_tier"]
        assert "30D" in p["multi_horizon_projections"]
