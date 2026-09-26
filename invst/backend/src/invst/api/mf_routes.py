"""FastAPI Route Handlers for Mutual Funds & SIP Intelligence."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from invst.api.auth import get_current_user, require_auth
from invst.api.mf_schemas import (
    MFAddSIPRequest,
    MFPortfolioResponse,
    MFReallocateSIPRequest,
    MFRecommendationRequest,
    MFRecommendationResponse,
    MFResumeSIPRequest,
    MFRiskMetricsResponse,
    MFRollingReturnsResponse,
    MFSavePortfolioRequest,
    MFSchemeDetailResponse,
    MFSchemeSearchItem,
    MFSIPBatchCheckinRequest,
    MFSIPCalculateRequest,
    MFSIPCalculateResponse,
    MFSIPCheckinRequest,
)
from invst.db.engine import get_db_connection
from invst.ingestion.mf_ingestion import (
    fetch_and_cache_scheme_nav,
    get_scheme_nav_series,
    search_schemes,
)
from invst.portfolio.mf_portfolio_service import (
    add_or_update_sip,
    analyze_mf_portfolio,
    batch_record_sip_checkin,
    get_or_create_user_mf_portfolio,
    get_pending_sip_checkins,
    get_sip_checkin_history,
    predict_mf_portfolio_health,
    reallocate_user_sip,
    record_sip_checkin,
    reset_user_mf_portfolio,
    resume_user_sip,
    save_user_mf_portfolio,
)
from invst.scoring.mf_advisor import generate_mf_recommendation
from invst.scoring.mf_metrics import (
    calculate_risk_metrics,
    calculate_rolling_returns,
    calculate_sip_projection,
    calculate_trailing_returns,
    compute_analyst_conviction_score,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/mf", tags=["Mutual Funds"])


def _extract_user_id(current_user: dict[str, Any] | None) -> int:
    """Extract authenticated integer user ID with fallback for test tokens."""
    if not current_user or not isinstance(current_user, dict):
        return 11
    val = current_user.get("user_id") or current_user.get("id") or 11
    try:
        return int(val)
    except (ValueError, TypeError):
        return 11


# -----------------------------------------------------------------------------
# 1. Fund Discovery & Search
# -----------------------------------------------------------------------------
@router.get("/search", response_model=list[MFSchemeSearchItem])
def search_mutual_funds(
    q: str = Query(default="", description="Search query by scheme name or AMC"),
    category: str | None = Query(default=None, description="Category filter"),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Search mutual funds in database matching query and category filter."""
    return search_schemes(query=q, category=category, limit=limit)


# -----------------------------------------------------------------------------
# 2. Single-Fund Deep Dive & Metrics
# -----------------------------------------------------------------------------
@router.get("/{scheme_code}/details", response_model=MFSchemeDetailResponse)
def get_scheme_details(scheme_code: int):
    """Get scheme overview, metadata, latest NAV, trailing returns, and top holdings."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT scheme_code, isin, scheme_name, fund_house, category,
                   plan_type, option_type, benchmark_index, expense_ratio,
                   aum_cr, fund_manager, crisil_rating, risk_level, inception_date
            FROM mf_schemes
            WHERE scheme_code = ?;
            """,
            (scheme_code,),
        )
        row = cur.fetchone()
        if not row:
            # Try fetching from MFAPI to see if valid scheme
            res = fetch_and_cache_scheme_nav(scheme_code)
            if not res.get("data"):
                raise HTTPException(status_code=404, detail=f"Mutual Fund scheme {scheme_code} not found")
            cur.execute(
                """
                SELECT scheme_code, isin, scheme_name, fund_house, category,
                       plan_type, option_type, benchmark_index, expense_ratio,
                       aum_cr, fund_manager, crisil_rating, risk_level, inception_date
                FROM mf_schemes
                WHERE scheme_code = ?;
                """,
                (scheme_code,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Scheme details could not be loaded")

        # Fetch latest NAV
        cur.execute(
            "SELECT nav_date, nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;",
            (scheme_code,),
        )
        nav_row = cur.fetchone()
        current_nav = float(nav_row[1]) if nav_row else None
        latest_nav_date = nav_row[0] if nav_row else None

        # Fetch holdings
        cur.execute(
            "SELECT company_name, symbol, sector, weight_pct FROM mf_holdings WHERE scheme_code = ? ORDER BY weight_pct DESC LIMIT 15;",
            (scheme_code,),
        )
        h_rows = cur.fetchall()
        top_holdings = [
            {"company_name": hr[0], "symbol": hr[1], "sector": hr[2], "weight_pct": float(hr[3])}
            for hr in h_rows
        ]

        # Calculate trailing returns, risk ratios, and analyst conviction
        nav_series = get_scheme_nav_series(scheme_code)
        trailing = calculate_trailing_returns(nav_series)
        risk = calculate_risk_metrics(nav_series)
        conviction = compute_analyst_conviction_score(
            cagr_3y=trailing.get("3y") * 100 if trailing.get("3y") is not None else None,
            sharpe=risk.get("sharpe_ratio"),
            sortino=risk.get("sortino_ratio"),
            expense_ratio=row[8],
            aum_cr=row[9],
            crisil_rating=row[11],
            category=row[4],
            scheme_name=row[2],
        )

        return {
            "scheme_code": row[0],
            "isin": row[1],
            "scheme_name": row[2],
            "fund_house": row[3],
            "category": row[4],
            "plan_type": row[5],
            "option_type": row[6],
            "benchmark_index": row[7],
            "expense_ratio": row[8],
            "aum_cr": row[9],
            "fund_manager": row[10],
            "crisil_rating": row[11],
            "risk_level": row[12],
            "inception_date": row[13],
            "current_nav": current_nav,
            "latest_nav_date": latest_nav_date,
            "trailing_returns": trailing,
            "top_holdings": top_holdings,
            "analyst_conviction": conviction,
        }
    finally:
        conn.close()


@router.get("/{scheme_code}/rolling-returns", response_model=MFRollingReturnsResponse)
def get_rolling_returns(
    scheme_code: int,
    window_years: int = Query(default=3, ge=1, le=10),
):
    """Calculate rolling returns distribution (mean, median, p25, p75, min, max, negative prob)."""
    nav_series = get_scheme_nav_series(scheme_code)
    if nav_series.empty:
        raise HTTPException(status_code=404, detail="No historical NAV available for this scheme")

    res = calculate_rolling_returns(nav_series, window_years=window_years)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/{scheme_code}/metrics", response_model=MFRiskMetricsResponse)
def get_fund_risk_metrics(scheme_code: int):
    """Compute institutional risk ratios (Sharpe, Sortino, Beta, Alpha, Capture ratios)."""
    nav_series = get_scheme_nav_series(scheme_code)
    if nav_series.empty:
        raise HTTPException(status_code=404, detail="No historical NAV available for this scheme")

    metrics = calculate_risk_metrics(nav_series)
    return metrics


@router.get("/{scheme_code}/nav-history")
def get_nav_history(
    scheme_code: int,
    period: str = Query(default="1y", description="1m, 3m, 6m, 1y, 3y, 5y, max"),
):
    """Get historical daily NAV data points formatted for time-series charting."""
    nav_series = get_scheme_nav_series(scheme_code)
    if nav_series.empty:
        raise HTTPException(status_code=404, detail="No historical NAV available")

    # Filter period
    end_date = nav_series.index[-1]
    if period == "1m":
        start_date = end_date - pd.DateOffset(months=1)
    elif period == "3m":
        start_date = end_date - pd.DateOffset(months=3)
    elif period == "6m":
        start_date = end_date - pd.DateOffset(months=6)
    elif period == "1y":
        start_date = end_date - pd.DateOffset(years=1)
    elif period == "3y":
        start_date = end_date - pd.DateOffset(years=3)
    elif period == "5y":
        start_date = end_date - pd.DateOffset(years=5)
    else:
        start_date = nav_series.index[0]

    filtered = nav_series.loc[start_date:]
    if filtered.empty:
        filtered = nav_series

    # Downsample if too large for fast UI rendering
    step = max(1, len(filtered) // 300)
    sampled = filtered.iloc[::step]
    if not sampled.empty and not filtered.empty and sampled.index[-1] != filtered.index[-1]:
        sampled = pd.concat([sampled, filtered.iloc[[-1]]])

    data_points = [
        {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
        for d, v in zip(sampled.index, sampled.values)
    ]
    return {"scheme_code": scheme_code, "period": period, "count": len(data_points), "points": data_points}


# -----------------------------------------------------------------------------
# 3. Interactive Goal & Risk Profile Recommendation Engine
# -----------------------------------------------------------------------------
@router.post("/recommend", response_model=MFRecommendationResponse)
def get_fund_recommendations(payload: MFRecommendationRequest):
    """Generate risk-profiled mutual fund basket and asset allocation."""
    return generate_mf_recommendation(
        risk_profile=payload.risk_profile,
        horizon_years=payload.horizon_years,
        goal_type=payload.goal_type,
        monthly_budget=payload.monthly_budget,
        step_up_pct=payload.step_up_pct,
    )


# -----------------------------------------------------------------------------
# 4. SIP Simulator & Calculator
# -----------------------------------------------------------------------------
@router.post("/sip/calculate", response_model=MFSIPCalculateResponse)
def calculate_sip(payload: MFSIPCalculateRequest):
    """Calculate compound wealth trajectory with annual step-up and inflation adjustments."""
    return calculate_sip_projection(
        monthly_sip=payload.monthly_sip,
        expected_cagr_pct=payload.expected_cagr_pct,
        years=payload.years,
        step_up_pct=payload.step_up_pct,
        inflation_pct=payload.inflation_pct,
    )


# -----------------------------------------------------------------------------
# 5. User Portfolio & Active/Closed SIP Diagnostics
# -----------------------------------------------------------------------------
@router.get("/portfolio", response_model=MFPortfolioResponse, dependencies=[Depends(require_auth)])
def get_user_portfolio(current_user: dict[str, Any] = Depends(get_current_user)):
    """Retrieve full mutual fund portfolio diagnostic for the current user."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    return analyze_mf_portfolio(pid)


@router.post("/portfolio/sip", dependencies=[Depends(require_auth)])
def register_user_sip(
    payload: MFAddSIPRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Register or update an active or closed SIP in the user's portfolio."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    sip_id = add_or_update_sip(
        portfolio_id=pid,
        scheme_code=payload.scheme_code,
        amount=payload.amount,
        start_date=payload.start_date,
        status=payload.status,
        end_date=payload.end_date,
        folio_number=payload.folio_number,
        step_up_pct=payload.step_up_pct,
        sip_day=payload.sip_day,
        custom_invested=payload.custom_invested,
        custom_current_value=payload.custom_current_value,
        custom_units=payload.custom_units,
        skipped_months=payload.skipped_months,
        paid_months=payload.paid_months,
    )
    return {"status": "success", "sip_id": sip_id, "portfolio_id": pid}


@router.post("/portfolio/sip/{sip_id}/resume", dependencies=[Depends(require_auth)])
def resume_sip_route(
    sip_id: str,
    payload: MFResumeSIPRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Resume a stopped or paused SIP schedule."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    return resume_user_sip(
        portfolio_id=pid,
        sip_id=sip_id,
        amount=payload.amount,
        sip_day=payload.sip_day,
    )


@router.post("/portfolio/sip/{sip_id}/reallocate", dependencies=[Depends(require_auth)])
def reallocate_sip_route(
    sip_id: str,
    payload: MFReallocateSIPRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Reallocate units or redirect SIP into a target scheme."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    return reallocate_user_sip(
        portfolio_id=pid,
        sip_id=sip_id,
        target_scheme_code=payload.target_scheme_code,
        allocation_mode=payload.allocation_mode,
        amount=payload.amount,
    )


@router.post("/portfolio/reset", dependencies=[Depends(require_auth)])
def reset_portfolio(current_user: dict[str, Any] = Depends(get_current_user)):
    """Reset the user's mutual fund portfolio to empty slate."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    reset_user_mf_portfolio(pid)
    return {"status": "success", "message": "Portfolio cleared successfully", "portfolio_id": pid}


@router.get("/portfolio/predict-health", dependencies=[Depends(require_auth)])
def get_portfolio_health_prediction(current_user: dict[str, Any] = Depends(get_current_user)):
    """Compute comprehensive health score, diagnostic alerts, and 3/5/10Y predictive scenarios."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    return predict_mf_portfolio_health(pid)


@router.post("/portfolio/save", dependencies=[Depends(require_auth)])
def save_portfolio_metadata(
    payload: MFSavePortfolioRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Save or update mutual fund portfolio metadata, name, and notes with timestamp."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    res = save_user_mf_portfolio(
        portfolio_id=pid,
        portfolio_name=payload.portfolio_name,
        notes=payload.notes,
    )
    return res


@router.get("/portfolio/checkins", dependencies=[Depends(require_auth)])
def get_portfolio_checkins(current_user: dict[str, Any] = Depends(get_current_user)):
    """Retrieve pending monthly SIP check-ins requiring user confirmation."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    return {
        "portfolio_id": pid,
        "pending_checkins": get_pending_sip_checkins(pid),
        "checkin_history": get_sip_checkin_history(pid),
    }


@router.post("/portfolio/sip/checkin", dependencies=[Depends(require_auth)])
def submit_sip_checkin(
    payload: MFSIPCheckinRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Confirm whether a monthly fund SIP installment was paid or skipped."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    res = record_sip_checkin(
        portfolio_id=pid,
        sip_id=payload.sip_id,
        due_date=payload.due_date,
        status=payload.status,
        amount=payload.amount,
        notes=payload.notes,
    )
    return res


@router.post("/portfolio/sip/batch-checkin", dependencies=[Depends(require_auth)])
def submit_sip_batch_checkin(
    payload: MFSIPBatchCheckinRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Bulk confirm multiple pending check-ins as PAID or SKIPPED."""
    uid = _extract_user_id(current_user)
    pid = get_or_create_user_mf_portfolio(uid)
    res = batch_record_sip_checkin(
        portfolio_id=pid,
        action=payload.action,
        checkin_ids=payload.checkin_ids,
    )
    return res

