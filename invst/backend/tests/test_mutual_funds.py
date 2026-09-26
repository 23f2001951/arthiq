"""Unit & Integration Tests for Mutual Fund Quant Engine & API Endpoints."""

import datetime
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from invst.api.app import create_app
from invst.db.engine import get_db_connection
from invst.ingestion.mf_ingestion import seed_curated_mutual_funds
from invst.portfolio.mf_portfolio_service import (
    add_or_update_sip,
    analyze_mf_portfolio,
    get_or_create_user_mf_portfolio,
)
from invst.scoring.mf_advisor import generate_mf_recommendation
from invst.scoring.mf_metrics import (
    calculate_cagr,
    calculate_portfolio_overlap,
    calculate_required_sip_for_goal,
    calculate_risk_metrics,
    calculate_rolling_returns,
    calculate_sip_projection,
    calculate_trailing_returns,
    calculate_xirr,
)


@pytest.fixture(scope="module")
def app_client():
    app = create_app()
    seed_curated_mutual_funds()

    # Seed synthetic daily NAVs for scheme 122639 to ensure offline tests pass
    conn = get_db_connection()
    cur = conn.cursor()
    dates = pd.date_range(end=datetime.date.today(), periods=1100, freq="B")
    nav_entries = [
        (122639, d.strftime("%Y-%m-%d"), round(50.0 * (1.15 ** (i / 252.0)), 4))
        for i, d in enumerate(dates)
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO mf_nav_history (scheme_code, nav_date, nav) VALUES (?, ?, ?);",
        nav_entries,
    )
    conn.commit()
    conn.close()

    return TestClient(app)


def test_calculate_cagr():
    # 100 growing to 200 in 5 years is ~14.87%
    cagr = calculate_cagr(100.0, 200.0, 5.0)
    assert round(cagr * 100, 2) == 14.87

    # Edge cases
    assert calculate_cagr(0, 100, 5) == 0.0
    assert calculate_cagr(100, 0, 5) == 0.0
    assert calculate_cagr(100, 200, 0) == 0.0


def test_calculate_xirr():
    # Regular monthly investments of 10,000 reaching 35,000 after 1 year
    cashflows = [
        ("2023-01-01", -10000),
        ("2023-02-01", -10000),
        ("2023-03-01", -10000),
        ("2024-01-01", 35000),
    ]
    xirr = calculate_xirr(cashflows)
    assert xirr is not None
    assert 17.0 <= xirr <= 20.0

    # Test invalid / single-sign cash flows
    assert calculate_xirr([("2023-01-01", -10000)]) is None
    assert calculate_xirr([("2023-01-01", -10000), ("2023-02-01", -10000)]) is None


def test_sip_projections_and_step_up():
    # 10,000 monthly for 10 years at 12% CAGR
    flat_sip = calculate_sip_projection(monthly_sip=10000, expected_cagr_pct=12.0, years=10, step_up_pct=0.0)
    assert flat_sip["total_invested"] == 1200000.0
    assert flat_sip["estimated_corpus"] > 2200000.0

    # With 10% annual step-up
    step_sip = calculate_sip_projection(monthly_sip=10000, expected_cagr_pct=12.0, years=10, step_up_pct=10.0)
    assert step_sip["estimated_corpus"] > flat_sip["estimated_corpus"]

    # Goal calculator
    goal = calculate_required_sip_for_goal(target_corpus_today=5000000, years=10, expected_cagr_pct=12.0)
    assert goal["flat_monthly_sip"] > 0
    assert goal["step_up_starting_monthly_sip"] < goal["flat_monthly_sip"]


def test_rolling_returns_calculation():
    # Create synthetic daily NAV series over 4 years
    dates = pd.date_range("2020-01-01", "2024-01-01", freq="B")
    # Upward compounding trend with small noise
    nav_vals = [10.0 * (1.12 ** (i / 252.0)) for i in range(len(dates))]
    nav_series = pd.Series(nav_vals, index=dates)

    res = calculate_rolling_returns(nav_series, window_years=1)
    assert "error" not in res
    assert res["sample_count"] > 100
    assert 11.0 <= res["median_return_pct"] <= 13.0
    assert res["negative_return_prob_pct"] == 0.0


def test_portfolio_overlap_matrix():
    holdings = {
        "FundA": [
            {"company_name": "HDFC Bank", "symbol": "HDFCBANK", "weight_pct": 10.0},
            {"company_name": "Reliance", "symbol": "RELIANCE", "weight_pct": 8.0},
            {"company_name": "Infosys", "symbol": "INFY", "weight_pct": 5.0},
        ],
        "FundB": [
            {"company_name": "HDFC Bank", "symbol": "HDFCBANK", "weight_pct": 9.0},
            {"company_name": "Reliance", "symbol": "RELIANCE", "weight_pct": 7.0},
            {"company_name": "TCS", "symbol": "TCS", "weight_pct": 6.0},
        ],
    }
    overlap = calculate_portfolio_overlap(holdings)
    # Expected overlap = min(10, 9) + min(8, 7) = 9 + 7 = 16%
    assert overlap["pairwise_overlap_matrix"]["FundA"]["FundB"] == 16.0
    assert len(overlap["common_holdings"]) == 2


def test_mf_recommendation_engine():
    # Test aggressive long-term investor
    rec = generate_mf_recommendation(
        risk_profile="AGGRESSIVE",
        horizon_years=10,
        goal_type="WEALTH_CREATION",
        monthly_budget=25000.0,
        step_up_pct=10.0,
    )
    assert len(rec["recommended_funds"]) >= 3
    assert rec["user_profile"]["expected_cagr_pct"] >= 13.0
    assert rec["total_monthly_sip"] > 0
    assert rec["wealth_projection"]["estimated_corpus"] > 0
    assert "advisory_rationale" in rec and len(rec["advisory_rationale"]) > 20
    assert "tax_optimization_memo" in rec and "1.25 Lakh" in rec["tax_optimization_memo"]["equity_ltcg_rate"]
    assert "rebalancing_protocol" in rec and rec["rebalancing_protocol"]["tolerance_band_pct"] == 5.0
    assert "multi_scenario_projections" in rec
    assert len(rec["multi_scenario_projections"]["unified_trajectory"]) == 10
    assert rec["multi_scenario_projections"]["terminal_bull"] > rec["multi_scenario_projections"]["terminal_base"]
    assert rec["multi_scenario_projections"]["terminal_base"] > rec["multi_scenario_projections"]["terminal_bear"]

    # Test conservative short-term investor
    rec_cons = generate_mf_recommendation(
        risk_profile="CONSERVATIVE",
        horizon_years=2,
        goal_type="EMERGENCY_FUND",
        monthly_budget=10000.0,
    )
    assert "Debt: Liquid" in rec_cons["asset_allocation"] or "Hybrid: Balanced Advantage" in rec_cons["asset_allocation"]


def test_mf_portfolio_with_active_and_closed_sips():
    # Ensure fresh test portfolio
    user_id = 999
    pid = get_or_create_user_mf_portfolio(user_id=user_id, portfolio_name="PyTest Portfolio")

    # Add active SIP
    s1 = add_or_update_sip(
        portfolio_id=pid,
        scheme_code=122639,
        amount=10000.0,
        start_date="2024-01-05",
        status="ACTIVE",
        sip_day=5,
    )
    assert s1.startswith("sip_")

    # Add closed SIP
    s2 = add_or_update_sip(
        portfolio_id=pid,
        scheme_code=120847,
        amount=5000.0,
        start_date="2023-01-05",
        end_date="2023-12-05",
        status="CLOSED",
        sip_day=5,
    )
    assert s2.startswith("sip_")

    # Analyze portfolio
    diag = analyze_mf_portfolio(pid)
    assert diag["total_invested"] > 0
    assert diag["current_value"] > 0
    assert len(diag["active_sips"]) >= 1
    assert len(diag["closed_sips"]) >= 1
    assert diag["active_sips"][0]["status"] == "ACTIVE"
    assert diag["closed_sips"][0]["status"] == "CLOSED"
    assert "post_mortem" in diag["closed_sips"][0]


def test_mf_api_routes(app_client):
    # 1. Search
    res = app_client.get("/api/v2/mf/search?q=Flexi")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1

    # 2. Scheme details
    code = items[0]["scheme_code"]
    res_det = app_client.get(f"/api/v2/mf/{code}/details")
    assert res_det.status_code == 200
    det = res_det.json()
    assert det["scheme_name"] is not None

    # 3. Rolling returns
    res_roll = app_client.get(f"/api/v2/mf/{code}/rolling-returns?window_years=3")
    assert res_roll.status_code == 200
    assert "median_return_pct" in res_roll.json()

    # 4. Risk metrics
    res_risk = app_client.get(f"/api/v2/mf/{code}/metrics")
    assert res_risk.status_code == 200
    assert "sharpe_ratio" in res_risk.json()

    # 5. Recommendation
    res_rec = app_client.post(
        "/api/v2/mf/recommend",
        json={"risk_profile": "MODERATE", "horizon_years": 5, "goal_type": "WEALTH_CREATION", "monthly_budget": 20000},
    )
    assert res_rec.status_code == 200
    assert "recommended_funds" in res_rec.json()

    # 6. SIP Calculate
    res_sip = app_client.post(
        "/api/v2/mf/sip/calculate",
        json={"monthly_sip": 10000, "expected_cagr_pct": 12, "years": 10, "step_up_pct": 10},
    )
    assert res_sip.status_code == 200
    assert res_sip.json()["estimated_corpus"] > 0


def test_mf_portfolio_reset_and_health_prediction(app_client):
    from invst.api.auth import create_access_token
    token = create_access_token({"id": 11, "email": "itsmandeepbeniwal@gmail.com", "role": "user"})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch current portfolio
    res = app_client.get("/api/v2/mf/portfolio", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "portfolio_id" in data

    # 2. Add an active SIP with custom valuation
    res_add = app_client.post(
        "/api/v2/mf/portfolio/sip",
        headers=auth_headers,
        json={
            "scheme_code": 122639,
            "amount": 10000.0,
            "start_date": "2024-01-01",
            "status": "ACTIVE",
            "custom_invested": 120000.0,
            "custom_current_value": 145000.0,
        },
    )
    assert res_add.status_code == 200

    # 3. Predict health
    res_health = app_client.get("/api/v2/mf/portfolio/predict-health", headers=auth_headers)
    assert res_health.status_code == 200
    health = res_health.json()
    assert "health_score" in health
    assert health["health_score"] > 0
    assert "pillars" in health
    assert "predictive_scenarios" in health
    assert len(health["predictive_scenarios"]) == 3

    # 4. Reset portfolio
    res_reset = app_client.post("/api/v2/mf/portfolio/reset", headers=auth_headers)
    assert res_reset.status_code == 200

    # 5. Verify portfolio is now clean/empty
    res_after = app_client.get("/api/v2/mf/portfolio", headers=auth_headers)
    assert res_after.status_code == 200
    empty_data = res_after.json()
    assert empty_data["total_invested"] == 0
    assert empty_data["active_sips_count"] == 0


def test_mf_portfolio_save_and_monthly_sip_checkin(app_client):
    from invst.api.auth import create_access_token
    token = create_access_token({"id": 11, "email": "itsmandeepbeniwal@gmail.com", "role": "user"})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Save portfolio metadata (name and notes)
    res_save = app_client.post(
        "/api/v2/mf/portfolio/save",
        headers=auth_headers,
        json={"portfolio_name": "My Growth SIP Plan", "notes": "Core retirement fund allocations"},
    )
    assert res_save.status_code == 200
    save_data = res_save.json()
    assert save_data["status"] == "success"
    assert "last_saved_at" in save_data

    # 2. Add an active SIP with a specific SIP day (e.g. 5th)
    res_add = app_client.post(
        "/api/v2/mf/portfolio/sip",
        headers=auth_headers,
        json={
            "scheme_code": 122639,
            "amount": 5000.0,
            "sip_day": 5,
            "start_date": "2024-01-01",
            "status": "ACTIVE",
            "custom_invested": 50000.0,
            "custom_current_value": 62000.0,
        },
    )
    assert res_add.status_code == 200
    sip_id = res_add.json()["sip_id"]

    # 3. Check portfolio includes metadata, pending checkins, and schedule attributes
    res_port = app_client.get("/api/v2/mf/portfolio", headers=auth_headers)
    assert res_port.status_code == 200
    pdata = res_port.json()
    assert pdata["portfolio_name"] == "My Growth SIP Plan"
    assert pdata["notes"] == "Core retirement fund allocations"
    assert pdata["last_saved_at"] is not None
    assert len(pdata["active_sips"]) == 1
    active_sip = pdata["active_sips"][0]
    assert "next_sip_date" in active_sip
    assert "days_until_next_sip" in active_sip
    assert "current_month_checkin_status" in active_sip

    # 4. Check check-ins endpoint
    res_chk = app_client.get("/api/v2/mf/portfolio/checkins", headers=auth_headers)
    assert res_chk.status_code == 200
    chk_data = res_chk.json()
    assert "pending_checkins" in chk_data

    # 5. Record SIP check-in: mark as PAID for current month
    due_date = active_sip["due_date_current_month"]
    res_paid = app_client.post(
        "/api/v2/mf/portfolio/sip/checkin",
        headers=auth_headers,
        json={
            "sip_id": sip_id,
            "due_date": due_date,
            "status": "PAID",
            "amount": 5000.0,
            "notes": "Debited automatically via ECS",
        },
    )
    assert res_paid.status_code == 200
    assert res_paid.json()["checkin_status"] == "PAID"

    # 6. Verify active SIP now reflects PAID status
    res_port2 = app_client.get("/api/v2/mf/portfolio", headers=auth_headers)
    pdata2 = res_port2.json()
    assert pdata2["active_sips"][0]["current_month_checkin_status"] == "PAID"
    assert "debited & confirmed" in pdata2["active_sips"][0]["cashflow_diagnostic_memo"]

    # 7. Record check-in: mark as SKIPPED
    res_skipped = app_client.post(
        "/api/v2/mf/portfolio/sip/checkin",
        headers=auth_headers,
        json={
            "sip_id": sip_id,
            "due_date": due_date,
            "status": "SKIPPED",
            "notes": "Skipped due to festival expenses",
        },
    )
    assert res_skipped.status_code == 200
    assert res_skipped.json()["checkin_status"] == "SKIPPED"

    res_port3 = app_client.get("/api/v2/mf/portfolio", headers=auth_headers)
    pdata3 = res_port3.json()
    assert pdata3["active_sips"][0]["current_month_checkin_status"] == "SKIPPED"


def test_dynamic_sip_day_and_skipped_months_and_closed_sip_action_modes(app_client):
    from invst.api.auth import create_access_token
    token = create_access_token({"id": 42, "email": "sip_tester@example.com", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    # Reset portfolio
    app_client.post("/api/v2/mf/portfolio/reset", headers=headers)

    # 1. Add SIP with start_date on the 14th without specifying sip_day -> should derive sip_day = 14
    # and mark two skipped months
    res_add = app_client.post(
        "/api/v2/mf/portfolio/sip",
        headers=headers,
        json={
            "scheme_code": 122639,
            "amount": 2500.0,
            "start_date": "2024-03-14",
            "end_date": "2024-08-14",
            "status": "CLOSED",
            "skipped_months": ["2024-05", "2024-07"],
            "custom_invested": 10000.0,
            "custom_current_value": 11500.0,
        },
    )
    assert res_add.status_code == 200
    sip_id = res_add.json()["sip_id"]

    # 2. Get portfolio and verify SIP day derivation and closed SIP action modes
    res_port = app_client.get("/api/v2/mf/portfolio", headers=headers)
    assert res_port.status_code == 200
    port = res_port.json()
    assert port["closed_sips_count"] == 1
    closed_sip = port["closed_sips"][0]

    # Verify derived sip_day from 2024-03-14 is 14
    assert closed_sip["sip_day"] == 14

    # Verify action_options exist for closed SIP: resume, reallocate, let_compound
    assert "action_options" in closed_sip
    assert "resume" in closed_sip["action_options"]
    assert "reallocate" in closed_sip["action_options"]
    assert "let_compound" in closed_sip["action_options"]

    # Check resume details
    resume_opt = closed_sip["action_options"]["resume"]
    assert resume_opt["suggested_sip_day"] == 14
    assert resume_opt["suggested_amount"] == 2500.0

    # Check let_compound projections
    let_compound_opt = closed_sip["action_options"]["let_compound"]
    assert "projections" in let_compound_opt
    assert "years_1" in let_compound_opt["projections"]
    assert "years_3" in let_compound_opt["projections"]
    assert "years_5" in let_compound_opt["projections"]
    assert "years_10" in let_compound_opt["projections"]
    assert let_compound_opt["projections"]["years_3"] > closed_sip["current_value"]

    # Check reallocate switch options
    reallocate_opt = closed_sip["action_options"]["reallocate"]
    assert "options" in reallocate_opt
    assert len(reallocate_opt["options"]) > 0

    # 3. Test Resume SIP route
    res_resume = app_client.post(
        f"/api/v2/mf/portfolio/sip/{sip_id}/resume",
        headers=headers,
        json={"amount": 3000.0, "sip_day": 14},
    )
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "success"
    assert res_resume.json()["amount"] == 3000.0

    # Verify portfolio now reflects resumed active SIP
    res_port_after = app_client.get("/api/v2/mf/portfolio", headers=headers)
    port_after = res_port_after.json()
    assert port_after["active_sips_count"] == 1
    assert port_after["closed_sips_count"] == 0
    assert port_after["active_sips"][0]["monthly_amount"] == 3000.0


def test_nav_history_time_series_api(app_client):
    """Verify historical NAV trajectory endpoint works across periods (1m, 1y, 3y, max)."""
    # Test for Parag Parikh Flexi Cap (122639)
    res_1y = app_client.get("/api/v2/mf/122639/nav-history?period=1y")
    assert res_1y.status_code == 200
    data_1y = res_1y.json()
    assert data_1y["scheme_code"] == 122639
    assert data_1y["period"] == "1y"
    assert data_1y["count"] > 10
    assert len(data_1y["points"]) > 10
    assert "date" in data_1y["points"][0]
    assert "nav" in data_1y["points"][0]

    # Test short period 1m
    res_1m = app_client.get("/api/v2/mf/122639/nav-history?period=1m")
    assert res_1m.status_code == 200
    data_1m = res_1m.json()
    assert data_1m["count"] <= data_1y["count"]

    # Test max period
    res_max = app_client.get("/api/v2/mf/122639/nav-history?period=max")
    assert res_max.status_code == 200
    assert res_max.json()["count"] > 0



