"""FastAPI Route Handlers for invst."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from invst.api.auth import (
    activate_user_password,
    create_access_token,
    create_invited_user,
    create_session,
    decode_access_token,
    delete_user_by_id,
    get_admin_email,
    get_current_user,
    get_session_expiry_hours,
    get_user_by_email,
    get_user_by_id,
    init_users_table,
    is_auth_enabled,
    list_all_users,
    require_admin,
    require_auth,
    revoke_session,
    update_user_last_login,
    update_user_password,
    update_user_profile,
    update_user_status,
    validate_session,
    verify_password,
    verify_password_hash,
)
from invst.api.schemas import (
    AdminCreateUserRequest,
    AdminSummaryResponse,
    AdminUpdateStatusRequest,
    AuthVerifyResponse,
    BacktestHistoryItem,
    BacktestMetricsSummary,
    BacktestRunRequest,
    BacktestRunResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    CorporateEventItem,
    DashboardResponse,
    EmailLookupRequest,
    EmailLookupResponse,
    EventsFeedResponse,
    HealthCheckItem,
    HealthResponse,
    HoldingItem,
    HRPPortfolioRequest,
    HRPPortfolioResponse,
    LoginRequest,
    LoginResponse,
    MacroPulseItem,
    MarketTickerItem,
    MainPortfolioPositionItem,
    MainPortfolioStatus,
    QuickPickItem,
    QuickPicksResponse,
    RecommendationsResponse,
    RecommendationsV2Response,
    ScenarioSchema,
    SetPasswordRequest,
    SetPasswordResponse,
    StockRecommendationItem,
    StockRecommendationV2Item,
    UniverseResponse,
    UserProfile,
    FullStockAnalysisResponse,
    MacroPulseResponse,
    ModelStatusResponse,
    ModelTrainRequest,
    ModelTrainResponse,
    PortfolioHealthResponse,
    PortfolioSaveRequest,
    UserHoldingSchema,
    PortfolioSummarySchema,
    PortfolioDetailSchema,
    CreatePortfolioRequest,
    UpdatePortfolioRequest,
    UpdateProfileRequest,
    AddStockToPortfolioRequest,
)
from invst.backtest.engine import run_walk_forward_backtest
from invst.config import get_config
from invst.data_access import PointInTimeDataAccess
from invst.ml.alpha_service import alpha_service
from invst.monitoring.data_quality import run_all_data_quality_checks
from invst.monitoring.pit_audit import run_full_pit_audit
from invst.optimization.hrp import optimize_hrp_portfolio
from invst.reporting.rationale import generate_plain_english_rationale
from invst.scoring.composite import compute_composite_scores, select_quick_picks
from invst.scoring.composite_v2 import compute_scorecards_v2

logger = logging.getLogger("invst.api")
router = APIRouter(prefix="/api")


from invst.db.engine import get_db_connection

# -------------------------------------------------------------------------
# Database Dependency
# -------------------------------------------------------------------------
def get_db() -> Generator[Any, None, None]:
    """Provide a database connection supporting Neon PostgreSQL and SQLite."""
    conn = get_db_connection()
    init_users_table(conn)
    try:
        yield conn
    finally:
        conn.close()



# -------------------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------------------
@router.post("/auth/lookup-email", response_model=EmailLookupResponse)
def lookup_email(payload: EmailLookupRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Check if an email exists and return account onboarding status."""
    clean_email = payload.email.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address.",
        )
    parts = clean_email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address (e.g. user@institution.com).",
        )
    try:
        user = get_user_by_email(conn, clean_email)
    except Exception as exc:
        logger.exception("Failed to query user by email '%s': %s", clean_email, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Database error during email lookup: {exc}",
        )
    if not user:
        return EmailLookupResponse(
            email=clean_email,
            exists=False,
            status="NOT_FOUND",
        )
    return EmailLookupResponse(
        email=user["email"],
        exists=True,
        status=user["status"],
        name=user["name"],
        role=user["role"],
        user_type=user.get("user_type") or ("ADMIN" if user.get("role") == "admin" else "PRO_INVESTOR"),
    )


@router.post("/auth/set-password", response_model=SetPasswordResponse)
def set_password(payload: SetPasswordRequest, conn: sqlite3.Connection = Depends(get_db)):
    """First-time password creation for invited Pro Investors to activate their account."""
    if len(payload.password.strip()) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters.",
        )
    user = activate_user_password(conn, payload.email, payload.password)
    expiry_hours = get_session_expiry_hours()
    token = create_access_token(user, expiry_hours=expiry_hours)
    return SetPasswordResponse(
        token=token,
        email=user["email"],
        role=user["role"],
        user_type=user.get("user_type") or ("ADMIN" if user.get("role") == "admin" else "PRO_INVESTOR"),
        status=user["status"],
        message="Account activated successfully.",
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Authenticate with email + password (or master password fallback) and receive JWT."""
    if not is_auth_enabled():
        return LoginResponse(
            token="auth_disabled",
            expires_in_hours=72,
            role="admin",
            user_type="ADMIN",
            email=get_admin_email(),
            name="Developer",
        )

    clean_email = payload.email.strip().lower() if payload.email else None

    # If email provided:
    if clean_email:
        if not payload.password:
            raise HTTPException(
                status_code=400,
                detail="Password is required.",
            )
        try:
            user = get_user_by_email(conn, clean_email)
        except Exception as exc:
            logger.exception("Database error during user login query for %s: %s", clean_email, exc)
            raise HTTPException(
                status_code=500,
                detail=f"Database error during login: {exc}",
            )
        if not user:
            raise HTTPException(
                status_code=401,
                detail=f"No account registered with email '{clean_email}'. Please contact your platform administrator.",
            )
        if user["status"] == "SUSPENDED":
            raise HTTPException(
                status_code=403,
                detail="Your account has been suspended. Please contact platform administrator.",
            )
        if user["status"] == "INVITED" and not user["password_hash"]:
            raise HTTPException(
                status_code=400,
                detail="Account not activated yet. Please set your password to activate your account.",
            )
        if not verify_password_hash(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect password. Please try again.",
            )
        try:
            update_user_last_login(conn, clean_email)
        except Exception as exc:
            logger.warning("Could not update last login for %s: %s", clean_email, exc)
        expiry_hours = get_session_expiry_hours()
        token = create_access_token(user, expiry_hours=expiry_hours)
        return LoginResponse(
            token=token,
            expires_in_hours=expiry_hours,
            status="authenticated",
            role=user["role"],
            user_type=user.get("user_type") or ("ADMIN" if user.get("role") == "admin" else "PRO_INVESTOR"),
            email=user["email"],
            name=user.get("name") or "",
        )

    # Admin direct login (admin@arth.iq is the master administrator)
    target_admin_email = get_admin_email()
    admin_user = get_user_by_email(conn, target_admin_email)
    if not admin_user:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, password_hash, role, user_type FROM users WHERE role = 'admin' LIMIT 1")
        r = cursor.fetchone()
        if r:
            admin_user = {"id": r[0], "email": r[1], "name": r[2], "password_hash": r[3], "role": r[4], "user_type": r[5]}

    if not admin_user or not admin_user.get("password_hash"):
        raise HTTPException(
            status_code=401,
            detail="Administrator account not found or has no password set.",
        )

    if not verify_password_hash(payload.password, admin_user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect administrator password. Access denied.",
        )

    update_user_last_login(conn, admin_user["email"])
    expiry_hours = get_session_expiry_hours()
    token = create_access_token(admin_user, expiry_hours=expiry_hours)
    return LoginResponse(
        token=token,
        expires_in_hours=expiry_hours,
        status="authenticated",
        role="admin",
        user_type="ADMIN",
        email=admin_user["email"],
        name=admin_user.get("name") or "Platform Administrator",
    )



@router.get("/auth/verify", response_model=AuthVerifyResponse)
def verify_auth(authorization: str | None = Header(None)):
    """Verify whether client's session token is currently valid and return role info."""
    if not is_auth_enabled():
        return AuthVerifyResponse(authenticated=True, auth_enabled=False, role="admin", user_type="ADMIN", email=get_admin_email())

    if not authorization:
        return AuthVerifyResponse(authenticated=False, auth_enabled=True)

    parts = authorization.split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    payload = decode_access_token(token)
    if payload:
        role = payload.get("role", "user")
        return AuthVerifyResponse(
            authenticated=True,
            auth_enabled=True,
            role=role,
            user_type=payload.get("user_type") or ("ADMIN" if role == "admin" else "PRO_INVESTOR"),
            email=payload.get("email"),
            name=payload.get("name"),
        )
    is_valid = validate_session(token)
    return AuthVerifyResponse(
        authenticated=is_valid,
        auth_enabled=True,
        role="admin" if is_valid else None,
        user_type="ADMIN" if is_valid else None,
        email=get_admin_email() if is_valid else None,
    )


@router.get("/auth/me", response_model=UserProfile, dependencies=[Depends(require_auth)])
def get_current_user_profile(
    current_user: dict = Depends(require_auth),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve profile of currently authenticated user."""
    email = current_user.get("email") or current_user.get("sub")
    user = get_user_by_email(conn, email) if email else None
    if not user:
        role = current_user.get("role", "user")
        return UserProfile(
            id=current_user.get("user_id", 1),
            email=email or "unknown@arth.iq",
            name=current_user.get("name", "User"),
            role=role,
            user_type=current_user.get("user_type") or ("ADMIN" if role == "admin" else "PRO_INVESTOR"),
            status="ACTIVE",
        )
    return UserProfile(**user)


@router.post("/auth/change-password", response_model=ChangePasswordResponse, dependencies=[Depends(require_auth)])
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(require_auth),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Authenticated user or admin updates their password after verifying current password."""
    email = current_user.get("email") or current_user.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Cannot identify user email.")
    update_user_password(conn, email, payload.current_password, payload.new_password)
    return ChangePasswordResponse(success=True, message="Password updated successfully.")


@router.patch("/auth/profile", response_model=UserProfile, dependencies=[Depends(require_auth)])
def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(require_auth),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Authenticated user updates their profile details."""
    email = current_user.get("email") or current_user.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Cannot identify user email.")
    updated = update_user_profile(conn, email, payload.name)
    return UserProfile(**updated)


@router.post("/auth/logout")
def logout(authorization: str | None = Header(None)):
    """Revoke session token on client logout."""
    if authorization:
        parts = authorization.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
        revoke_session(token)
    return {"status": "logged_out"}


# -------------------------------------------------------------------------
# Admin Platform Routes (Admin Role Required)
# -------------------------------------------------------------------------
@router.get("/admin/summary", response_model=AdminSummaryResponse, dependencies=[Depends(require_admin)])
def get_admin_summary(conn: sqlite3.Connection = Depends(get_db)):
    """Provide KPI summary for Admin Dashboard."""
    users = list_all_users(conn)
    total_users = len(users)
    active_users = sum(1 for u in users if u["status"] == "ACTIVE")
    invited_users = sum(1 for u in users if u["status"] == "INVITED")
    suspended_users = sum(1 for u in users if u["status"] == "SUSPENDED")

    # ML model status
    meta = alpha_service.get_status()
    model_trained = (meta.status == "TRAINED")
    model_version = meta.model_type if model_trained else None

    # Backtests count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM backtest_runs")
    backtests_count = cursor.fetchone()[0]

    return AdminSummaryResponse(
        total_users=total_users,
        active_users=active_users,
        invited_users=invited_users,
        suspended_users=suspended_users,
        model_trained=model_trained,
        model_version=model_version,
        backtests_count=backtests_count,
        system_status="HEALTHY",
    )


@router.get("/admin/users", response_model=list[UserProfile], dependencies=[Depends(require_admin)])
def admin_list_users(conn: sqlite3.Connection = Depends(get_db)):
    """List all platform users (admins and pro investors)."""
    users = list_all_users(conn)
    return [UserProfile(**u) for u in users]


@router.post("/admin/users", response_model=UserProfile, dependencies=[Depends(require_admin)])
def admin_create_user(payload: AdminCreateUserRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Admin registers a new pro investor via their email."""
    new_user = create_invited_user(conn, payload.email, payload.name, payload.role, payload.user_type)
    return UserProfile(**new_user)


@router.patch("/admin/users/{user_id}/status", response_model=UserProfile, dependencies=[Depends(require_admin)])
def admin_update_user_status(user_id: int, payload: AdminUpdateStatusRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Admin updates user status (ACTIVE, SUSPENDED, INVITED)."""
    updated = update_user_status(conn, user_id, payload.status)
    return UserProfile(**updated)


@router.delete("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def admin_delete_user(
    user_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Admin deletes user account."""
    current_admin_id = admin_user.get("user_id") or admin_user.get("id")
    delete_user_by_id(conn, user_id, current_admin_id)
    return {"status": "deleted", "user_id": user_id}



@router.get("/dashboard", response_model=DashboardResponse, dependencies=[Depends(require_auth)])
def get_dashboard(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Retrieve portfolio dashboard KPIs, active target holdings, and sector weights."""
    from invst.portfolio.health import get_portfolio, evaluate_portfolio_health
    from invst.ingestion.live_market_feed import fetch_live_macro_pulse

    # 1. Main Portfolio Status
    main_portfolio_status = None
    try:
        user_id = current_user.get("user_id") or current_user.get("id") or 11
        user_p = get_portfolio(conn, "default", user_id=user_id)
        if user_p and user_p.holdings:
            report = evaluate_portfolio_health(conn, user_p.holdings, fetch_live=True)
            pos_items = [
                MainPortfolioPositionItem(
                    symbol=p.symbol,
                    shares=p.shares,
                    buy_price=p.buy_price,
                    current_price=p.current_price,
                    current_value=p.current_value,
                    weight_pct=p.weight_pct,
                    unrealized_pnl=p.unrealized_pnl,
                    unrealized_pnl_pct=p.unrealized_pnl_pct,
                    sector=p.sector,
                    action_verdict=p.action_verdict,
                    action_badge=p.action_badge,
                    action_rationale=p.action_rationale,
                    expected_return_12m=p.expected_return_12m,
                )
                for p in report.positions
            ]
            main_portfolio_status = MainPortfolioStatus(
                portfolio_id=user_p.id,
                portfolio_name=user_p.name,
                holdings_count=len(user_p.holdings),
                total_invested=report.total_invested,
                total_current_value=report.total_current_value,
                total_unrealized_pnl=report.total_unrealized_pnl,
                total_unrealized_pnl_pct=report.total_unrealized_pnl_pct,
                overall_health_score=report.overall_health_score,
                overall_health_grade=report.overall_health_grade,
                weighted_business_score=report.weighted_business_score,
                weighted_valuation_score=report.weighted_valuation_score,
                critical_redline_alerts=report.critical_redline_alerts,
                sector_warnings=report.sector_warnings,
                positions=pos_items,
                sector_exposures=report.sector_exposures,
            )
        elif user_p:
            main_portfolio_status = MainPortfolioStatus(
                portfolio_id=user_p.id,
                portfolio_name=user_p.name,
                holdings_count=0,
            )
    except Exception as e:
        logger.warning(f"Could not compute main portfolio health for dashboard: {e}")

    # 2. Macro Pulse
    macro_pulse_obj = None
    try:
        pulse = fetch_live_macro_pulse(conn=conn, fetch_live=True)
        macro_pulse_obj = MacroPulseItem(
            india_vix=pulse.get("india_vix", 14.5),
            nifty_50=pulse.get("nifty_50", 24500.0),
            regime=pulse.get("regime", "NEUTRAL"),
            regime_description=pulse.get("regime_description", ""),
            is_live=pulse.get("is_live", False),
        )
    except Exception as e:
        logger.warning(f"Could not fetch macro pulse for dashboard: {e}")

    # 3. Algorithmic Target Model (portfolio_history)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, asof_date
        FROM portfolio_history
        ORDER BY asof_date DESC
        LIMIT 1
        """
    )
    latest = cur.fetchone()
    if not latest:
        return DashboardResponse(
            main_portfolio=main_portfolio_status,
            macro_pulse=macro_pulse_obj,
        )

    run_id, asof_date = latest
    cur.execute(
        """
        SELECT symbol, target_weight, action, shares_target, executed
        FROM portfolio_history
        WHERE run_id = ?
        ORDER BY target_weight DESC
        """,
        (run_id,),
    )
    rows = cur.fetchall()

    holdings = []
    sector_alloc: dict[str, float] = {}

    pit = PointInTimeDataAccess(conn, asof=date.fromisoformat(asof_date))
    sectors_map = pit.get_universe_with_sectors()

    for sym, w, action, shares, exec_flag in rows:
        sec = sectors_map.get(sym) or pit.get_sector(sym) or "diversified"
        holdings.append(
            HoldingItem(
                symbol=sym,
                sector=sec,
                target_weight=round(float(w), 4),
                action=action,
                shares_target=shares,
                executed=bool(exec_flag),
            )
        )
        sector_alloc[sec] = round(sector_alloc.get(sec, 0.0) + float(w), 4)

    return DashboardResponse(
        latest_asof=asof_date,
        target_holdings=len(holdings),
        holdings=holdings,
        sector_allocations=sector_alloc,
        main_portfolio=main_portfolio_status,
        macro_pulse=macro_pulse_obj,
    )


@router.get("/recommendations", response_model=RecommendationsResponse, dependencies=[Depends(require_auth)])
def get_recommendations(
    asof: str | None = Query(None, description="As-of date in YYYY-MM-DD format"),
    top_n: int = Query(8, ge=1, le=50),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve ranked stock recommendations with full factor scores and plain-English rationales."""
    asof_date = date.fromisoformat(asof) if asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    scorecards = compute_composite_scores(pit, filter_universe_first=False)
    if not scorecards:
        return RecommendationsResponse(asof_date=asof_date.isoformat(), count=0, recommendations=[])

    # Attempt to fetch trained model predictions for active universe
    alpha_picks = []
    try:
        alpha_picks = alpha_service.predict_alpha_picks(
            conn=conn,
            asof_date=asof_date,
            n=top_n,
            max_per_sector=99,
        )
    except Exception as e:
        logger.warning(f"Could not compute alpha predictions for recommendations: {e}")

    alpha_map = {p.symbol: p for p in alpha_picks}
    selected = scorecards[:top_n]
    recs = []
    weight_per_stock = round(1.0 / len(selected), 4)

    for sc in selected:
        p_info = alpha_map.get(sc.symbol)
        p_outperform = p_info.p_outperform if p_info else 0.50
        exp_alpha = p_info.expected_alpha_pct if p_info else 0.0
        arth_score = p_info.arth_score if p_info else round(sc.composite_score * 100.0, 1)
        agreement = p_info.signal_agreement if p_info else 1.0
        conviction = p_info.conviction_tier if p_info else "SOLID OUTPERFORMER"

        rationale = generate_plain_english_rationale(
            symbol=sc.symbol,
            company_name=sc.symbol,
            sector=sc.sector,
            action="BUY",
            target_weight=weight_per_stock,
            current_weight=0.0,
            scorecard={
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
                "sentiment_details": sc.sentiment_details,
            },
        )
        if p_info:
            rationale += (
                f" Calibrated Alpha Model: {p_outperform * 100:.1f}% probability of outperforming Nifty 500 "
                f"(Expected Excess Alpha: {exp_alpha:+.1f}%, ArthScore: {arth_score}/100)."
            )

        recs.append(
            StockRecommendationItem(
                symbol=sc.symbol,
                sector=sc.sector,
                action="BUY",
                target_weight=weight_per_stock,
                current_weight=0.0,
                rationale=rationale,
                composite_score=sc.composite_score,
                quality_score=sc.quality_score,
                valuation_score=sc.valuation_score,
                risk_score=sc.risk_score,
                sentiment_overlay_points=sc.sentiment_overlay_points,
                p_outperform=p_outperform,
                expected_alpha_pct=exp_alpha,
                arth_score=arth_score,
                signal_agreement=agreement,
                conviction_tier=conviction,
                quality_metrics=sc.quality_details.get("metrics", {}),
                valuation_metrics=sc.valuation_details.get("metrics", {}),
                risk_metrics=sc.risk_details.get("metrics", {}),
            )
        )

    return RecommendationsResponse(
        asof_date=asof_date.isoformat(),
        count=len(recs),
        recommendations=recs,
    )


@router.get("/recommendations/picks", response_model=QuickPicksResponse, dependencies=[Depends(require_auth)])
def get_quick_picks(
    asof: str | None = Query(None, description="As-of date in YYYY-MM-DD format"),
    n: int = Query(2, ge=1, le=50, description="Number of top picks to suggest (1 to 50)"),
    exclude_holdings: bool = Query(
        True, description="Exclude symbols currently held in latest portfolio rebalance"
    ),
    horizon_days: int = Query(90, ge=30, le=252, description="Target Alpha Horizon in days"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve top highest-conviction stocks powered by trained Calibrated Alpha Model & ArthScore."""
    asof_date = date.fromisoformat(asof) if asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    exclude_symbols: list[str] = []
    if exclude_holdings:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol FROM portfolio_history
            WHERE run_id = (SELECT run_id FROM portfolio_history ORDER BY asof_date DESC LIMIT 1)
            """
        )
        exclude_symbols = [r[0] for r in cur.fetchall()]

    # Execute prediction via AlphaModelService
    try:
        alpha_picks = alpha_service.predict_alpha_picks(
            conn=conn,
            asof_date=asof_date,
            n=n,
            exclude_symbols=exclude_symbols,
            max_per_sector=1,
            horizon_days=horizon_days,
        )
        if alpha_picks:
            picks = [
                QuickPickItem(
                    rank=p.rank,
                    symbol=p.symbol,
                    sector=p.sector,
                    action=p.action,
                    suggested_weight=p.suggested_weight,
                    latest_close=p.latest_close,
                    composite_score=p.composite_score,
                    quality_score=p.quality_score,
                    valuation_score=p.valuation_score,
                    risk_score=p.risk_score,
                    sentiment_overlay_points=p.sentiment_overlay_points,
                    rationale=p.rationale,
                    p_outperform=p.p_outperform,
                    expected_alpha_pct=p.expected_alpha_pct,
                    arth_score=p.arth_score,
                    signal_agreement=p.signal_agreement,
                    conviction_tier=p.conviction_tier,
                    model_name=p.model_name,
                    horizon_days=p.horizon_days,
                    multi_horizon_projections=p.multi_horizon_projections,
                    quality_metrics=p.quality_metrics,
                    valuation_metrics=p.valuation_metrics,
                    risk_metrics=p.risk_metrics,
                )
                for p in alpha_picks
            ]
            meta = alpha_service.get_status()
            weight_per_pick = round(1.0 / len(picks), 4) if picks else 0.0
            context_str = (
                f"Calibrated Alpha Tactical Allocation: split cash equally across {len(picks)} high-conviction "
                f"{'idea' if len(picks) == 1 else 'ideas'} ({weight_per_pick * 100:.1f}% each) backed by trained "
                f"{meta.model_name}."
            )
            return QuickPicksResponse(
                asof_date=asof_date.isoformat(),
                n_requested=n,
                count=len(picks),
                deployment_context=context_str,
                model_status=meta.status,
                model_name=meta.model_name,
                brier_score=meta.brier_score,
                picks=picks,
            )
    except Exception as e:
        logger.warning(f"AlphaModelService fallback to composite scoring: {e}")

    # Fallback to deterministic scoring if ML service encountered error
    scorecards = compute_composite_scores(pit, filter_universe_first=False)
    if not scorecards:
        return QuickPicksResponse(
            asof_date=asof_date.isoformat(),
            n_requested=n,
            count=0,
            deployment_context="No candidate stocks available for quick picks.",
            picks=[],
        )

    selected = select_quick_picks(
        scorecards, n=n, exclude_symbols=exclude_symbols, max_per_sector=1
    )
    weight_per_pick = round(1.0 / len(selected), 4) if selected else 0.0
    picks = []

    for rank_idx, sc in enumerate(selected, start=1):
        latest_px = pit.get_price(sc.symbol, asof_date)
        rationale = generate_plain_english_rationale(
            symbol=sc.symbol,
            company_name=sc.symbol,
            sector=sc.sector,
            action="BUY",
            target_weight=weight_per_pick,
            current_weight=0.0,
            scorecard={
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
                "sentiment_details": sc.sentiment_details,
            },
        )

        picks.append(
            QuickPickItem(
                rank=rank_idx,
                symbol=sc.symbol,
                sector=sc.sector,
                action="BUY",
                suggested_weight=weight_per_pick,
                latest_close=latest_px,
                composite_score=sc.composite_score,
                quality_score=sc.quality_score,
                valuation_score=sc.valuation_score,
                risk_score=sc.risk_score,
                sentiment_overlay_points=sc.sentiment_overlay_points,
                rationale=rationale,
                p_outperform=0.50,
                expected_alpha_pct=0.0,
                arth_score=round(sc.composite_score * 100.0, 1),
                signal_agreement=1.0,
                conviction_tier="SOLID OUTPERFORMER",
                model_name="Deterministic Heuristic Baseline",
                horizon_days=horizon_days,
                multi_horizon_projections={"90D": 0.0},
                quality_metrics=sc.quality_details.get("metrics", {}),
                valuation_metrics=sc.valuation_details.get("metrics", {}),
                risk_metrics=sc.risk_details.get("metrics", {}),
            )
        )

    context_str = (
        f"Tactical allocation: split fresh capital equally across {len(picks)} high-conviction "
        f"{'idea' if len(picks) == 1 else 'ideas'} ({weight_per_pick * 100:.1f}% each) without sector over-concentration."
    )

    return QuickPicksResponse(
        asof_date=asof_date.isoformat(),
        n_requested=n,
        count=len(picks),
        deployment_context=context_str,
        model_status="BASELINE",
        model_name="Deterministic Heuristic Baseline",
        brier_score=0.25,
        picks=picks,
    )


@router.post("/ml/train", response_model=ModelTrainResponse, dependencies=[Depends(require_admin)])
def post_train_ml_model(
    payload: ModelTrainRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Train or retrain the Point-in-Time Alpha Prediction Model."""
    cutoff_date = payload.asof or date.today().isoformat()
    try:
        meta = alpha_service.train_model(
            conn=conn,
            asof_date=cutoff_date,
            horizon_days=payload.horizon_days,
            model_type=payload.model_type,
            feature_mode=payload.feature_mode,
            calibration_method=payload.calibration_method,
        )
        return ModelTrainResponse(
            status=meta.status,
            model_name=meta.model_name,
            model_type=meta.model_type,
            horizon_days=meta.horizon_days,
            feature_mode=meta.feature_mode,
            sample_count=meta.sample_count,
            positive_ratio=meta.positive_ratio,
            brier_score=meta.brier_score,
            train_accuracy=meta.train_accuracy,
            feature_importances=meta.feature_importances,
            trained_at=meta.trained_at or datetime.now().isoformat(),
            message=f"Successfully trained {meta.model_name} on {meta.sample_count} PIT observations (Brier: {meta.brier_score:.3f}).",
        )
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model training error: {str(e)}")


@router.get("/ml/status", response_model=ModelStatusResponse, dependencies=[Depends(require_admin)])
def get_ml_model_status():
    """Retrieve current operational status and diagnostics of the Alpha Model."""
    meta = alpha_service.get_status()
    return ModelStatusResponse(
        status=meta.status,
        is_trained=(meta.status == "TRAINED"),
        model_name=meta.model_name,
        model_type=meta.model_type,
        horizon_days=meta.horizon_days,
        feature_mode=meta.feature_mode,
        sample_count=meta.sample_count,
        positive_ratio=meta.positive_ratio,
        brier_score=meta.brier_score,
        train_accuracy=meta.train_accuracy,
        feature_importances=meta.feature_importances,
        trained_at=meta.trained_at,
    )


@router.post("/backtest/run", response_model=BacktestRunResponse, dependencies=[Depends(require_admin)])
def trigger_backtest(
    req: BacktestRunRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Execute a walk-forward quarterly simulation and persist metrics to database."""
    try:
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            benchmark_symbol=req.benchmark_symbol,
            target_holdings=req.target_holdings,
        )

        m = res.metrics
        summary = BacktestMetricsSummary(
            cagr=m.cagr,
            sharpe=m.sharpe,
            sortino=m.sortino,
            calmar=m.calmar,
            max_drawdown=m.max_drawdown,
            annualized_vol=m.annualized_vol,
            turnover_avg=m.turnover_avg,
            hit_rate=m.hit_rate,
            worst_5d_return=m.worst_5d_return,
            rebalance_count=m.rebalance_count,
            benchmark_cagr=m.benchmark_cagr,
            benchmark_sharpe=m.benchmark_sharpe,
            benchmark_max_drawdown=m.benchmark_max_drawdown,
            alpha=m.alpha,
            information_ratio=m.information_ratio,
            tracking_error=m.tracking_error,
            beta=m.beta,
            jensen_alpha=m.jensen_alpha,
            upside_capture=m.upside_capture,
            downside_capture=m.downside_capture,
            payoff_ratio=m.payoff_ratio,
        )

        return BacktestRunResponse(
            run_id=res.run_id,
            metrics=summary,
            equity_dates=res.equity_dates,
            portfolio_equity=res.portfolio_equity,
            benchmark_equity=res.benchmark_equity,
            status="completed",
        )
    except Exception as e:
        logger.error(f"Backtest run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/backtest/runs", response_model=list[BacktestHistoryItem], dependencies=[Depends(require_admin)])
def list_backtest_runs(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve historical backtest runs stored in database."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, started_at, start_date, end_date, cagr, sharpe, max_drawdown, turnover_avg, benchmark_cagr, status
        FROM backtest_runs
        ORDER BY started_at DESC
        LIMIT 50
        """
    )
    rows = cur.fetchall()
    return [
        BacktestHistoryItem(
            run_id=r[0],
            started_at=r[1] or "",
            start_date=r[2],
            end_date=r[3],
            cagr=r[4],
            sharpe=r[5],
            max_drawdown=r[6],
            turnover_avg=r[7],
            benchmark_cagr=r[8],
            status=r[9] or "completed",
        )
        for r in rows
    ]


@router.get("/health", response_model=HealthResponse, dependencies=[Depends(require_admin)])
def get_health(conn: sqlite3.Connection = Depends(get_db)):
    """Run data quality and point-in-time anti-lookahead integrity checks."""
    dq_results = run_all_data_quality_checks(conn, asof=date.today())
    pit_results = run_full_pit_audit(conn, asof=date.today())

    dq_items = [
        HealthCheckItem(
            name=r.check_name,
            passed=r.passed,
            message=r.message,
            details=r.details,
        )
        for r in dq_results
    ]

    pit_items = [
        HealthCheckItem(
            name=r.audit_name,
            passed=r.passed,
            message=r.message,
            details={"violations_count": r.violations_count},
        )
        for r in pit_results
    ]

    all_passed = all(r.passed for r in dq_results) and all(r.passed for r in pit_results)

    return HealthResponse(
        overall_status="HEALTHY" if all_passed else "ATTENTION_REQUIRED",
        data_quality_checks=dq_items,
        pit_audits=pit_items,
    )


@router.get("/universe", response_model=UniverseResponse, dependencies=[Depends(require_auth)])
def get_universe(
    asof: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Return active universe constituent count grouped by sector."""
    asof_date = date.fromisoformat(asof) if asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)
    sectors_map = pit.get_universe_with_sectors()

    sector_counts: dict[str, int] = {}
    for sec in sectors_map.values():
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

    return UniverseResponse(
        asof_date=asof_date.isoformat(),
        total_symbols=len(sectors_map),
        sectors=sector_counts,
    )


# -------------------------------------------------------------------------
# V0.2 Decoupled Scoring & HRP Endpoints
# -------------------------------------------------------------------------

@router.get("/v2/recommendations", response_model=RecommendationsV2Response, dependencies=[Depends(require_auth)])
def get_recommendations_v2(
    asof: str | None = Query(None, description="As-of date in YYYY-MM-DD format"),
    top_n: int = Query(10, ge=1, le=50),
    sector: str | None = Query(None, description="Optional sector filter"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve V0.2 decoupled Business Score, Investment Score, and Scenario projections."""
    asof_date = date.fromisoformat(asof) if asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    scorecards = compute_scorecards_v2(pit, sector_filter=sector)
    selected = scorecards[:top_n]

    recs = []
    for sc in selected:
        scen_schema = ScenarioSchema(
            current_price=sc.scenario.current_price,
            p_bear=sc.scenario.p_bear,
            p_base=sc.scenario.p_base,
            p_bull=sc.scenario.p_bull,
            return_bear_pct=sc.scenario.return_bear_pct,
            return_base_pct=sc.scenario.return_base_pct,
            return_bull_pct=sc.scenario.return_bull_pct,
            expected_return_pct=sc.scenario.expected_return_pct,
            probability_bear=sc.scenario.probability_bear,
            probability_base=sc.scenario.probability_base,
            probability_bull=sc.scenario.probability_bull,
            downside_to_upside_ratio=sc.scenario.downside_to_upside_ratio,
            probability_of_loss=sc.scenario.probability_of_loss,
        )

        rationale = (
            f"{sc.symbol} ({sc.sector_archetype}): Ranked #{sc.rank} with Investment Score {sc.investment_score}/100. "
            f"Quadrant: '{sc.matrix_quadrant}'. Business Quality is {sc.business_score}/100 with Growth {sc.growth_score}/100. "
            f"Expected 1-yr scenario return is {sc.scenario.expected_return_pct}% (Bear: {sc.scenario.return_bear_pct}%, Bull: {sc.scenario.return_bull_pct}%)."
        )

        recs.append(
            StockRecommendationV2Item(
                symbol=sc.symbol,
                sector=sc.sector,
                sector_archetype=sc.sector_archetype,
                rank=sc.rank,
                investment_score=sc.investment_score,
                business_score=sc.business_score,
                growth_score=sc.growth_score,
                growth_confidence=sc.growth_confidence,
                valuation_score=sc.valuation_score,
                risk_score=sc.risk_score,
                market_score=sc.market_score,
                matrix_quadrant=sc.matrix_quadrant,
                scenario=scen_schema,
                drivers=sc.growth_result.drivers,
                risks=sc.growth_result.risks + sc.valuation_result.risks + sc.risk_result.redlines_triggered,
                rationale=rationale,
            )
        )

    return RecommendationsV2Response(
        asof_date=asof_date.isoformat(),
        count=len(recs),
        recommendations=recs,
    )


@router.post("/v2/portfolio/hrp", response_model=HRPPortfolioResponse, dependencies=[Depends(require_auth)])
def post_optimize_hrp(
    payload: HRPPortfolioRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Generate risk-budgeted HRP portfolio allocation with investor profile constraints."""
    asof_date = date.fromisoformat(payload.asof) if payload.asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    # 1. Shortlist high-conviction candidates using V0.2 engine
    scorecards = compute_scorecards_v2(pit)
    if not scorecards:
        raise HTTPException(status_code=400, detail="No candidates available for portfolio optimization.")

    shortlist = scorecards[: payload.top_n]
    symbols = [sc.symbol for sc in shortlist]
    sectors_map = {sc.symbol: sc.sector for sc in shortlist}
    returns_map = {sc.symbol: sc.scenario.expected_return_pct for sc in shortlist}

    hrp_res = optimize_hrp_portfolio(
        pit=pit,
        symbols=symbols,
        sector_map=sectors_map,
        capital=payload.capital,
        investor_profile=payload.profile,
        expected_returns_map=returns_map,
    )

    return HRPPortfolioResponse(
        weights=hrp_res.weights,
        target_shares=hrp_res.target_shares,
        cash_balance=hrp_res.cash_balance,
        total_invested=hrp_res.total_invested,
        expected_portfolio_return=hrp_res.expected_portfolio_return,
        expected_portfolio_volatility=hrp_res.expected_portfolio_volatility,
        sharpe_ratio=hrp_res.sharpe_ratio,
        sector_allocations=hrp_res.sector_allocations,
        investor_profile=hrp_res.investor_profile,
    )


@router.get("/v2/events/feed", response_model=EventsFeedResponse, dependencies=[Depends(require_auth)])
def get_events_feed(
    symbol: str | None = Query(None),
    asof: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve structured corporate disclosures and event intelligence stream."""
    asof_date = date.fromisoformat(asof) if asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    all_events = []
    target_symbols = [symbol] if symbol else pit.get_universe()[:20]

    for s in target_symbols:
        evs = pit.get_corporate_events(s, lookback_days=90)
        for e in evs:
            all_events.append(
                CorporateEventItem(
                    event_id=e.event_id,
                    symbol=e.symbol,
                    event_type=e.event_type,
                    headline=e.headline,
                    direction=e.direction,
                    materiality_score=e.materiality_score,
                    confidence_score=e.confidence_score,
                    affected_factors=e.affected_factors,
                    effective_date=e.effective_date,
                )
            )

    all_events.sort(key=lambda x: x.effective_date, reverse=True)
    return EventsFeedResponse(count=len(all_events), events=all_events)


# -------------------------------------------------------------------------
# Live Feeds, Stock Analyzer & Personal Portfolio API Routes
# -------------------------------------------------------------------------

@router.get("/v2/market/ticker-tape", response_model=list[MarketTickerItem])
@router.get("/market/ticker-tape", response_model=list[MarketTickerItem])
def get_market_ticker_tape(
    fetch_live: bool = True,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve real-time ticker tape quotes for NSE/BSE indices, major equities, and ETFs."""
    from invst.ingestion.live_market_feed import fetch_live_ticker_tape

    items = fetch_live_ticker_tape(conn=conn, fetch_live=fetch_live)
    return [MarketTickerItem(**it) for it in items]


@router.get("/v2/macro/pulse", response_model=MacroPulseResponse)
def get_macro_pulse(
    fetch_live: bool = True,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve real-time India VIX, Nifty 50, and macroeconomic regime status."""
    from invst.ingestion.live_market_feed import fetch_live_macro_pulse

    pulse = fetch_live_macro_pulse(conn=conn, fetch_live=fetch_live)
    return MacroPulseResponse(
        asof_date=pulse["asof_date"],
        india_vix=pulse["india_vix"],
        nifty_50=pulse["nifty_50"],
        usd_inr=pulse["usd_inr"],
        regime=pulse["regime"],
        regime_description=pulse["regime_description"],
        is_live=pulse["is_live"],
    )


@router.get("/v2/analyze/{symbol}", response_model=FullStockAnalysisResponse)
def get_stock_analysis(
    symbol: str,
    fetch_live: bool = True,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Perform on-demand quantitative diagnosis and multi-horizon return projections for any stock."""
    from invst.scoring.stock_analyzer import analyze_stock_on_demand

    clean_sym = symbol.strip().upper()
    try:
        res = analyze_stock_on_demand(conn, clean_sym, fetch_live=fetch_live)
        return FullStockAnalysisResponse(**res.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error analyzing {clean_sym}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed for {clean_sym}: {str(e)}") from e


@router.get("/v2/portfolio/holdings", response_model=list[UserHoldingSchema])
def get_user_portfolio_holdings(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Retrieve user's saved manual stock holdings."""
    from invst.portfolio.health import load_user_holdings

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    holdings = load_user_holdings(conn, user_id=user_id)
    return [
        UserHoldingSchema(symbol=h.symbol, shares=h.shares, buy_price=h.buy_price)
        for h in holdings
    ]


@router.post("/v2/portfolio/holdings")
def post_save_portfolio_holdings(
    payload: PortfolioSaveRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Save user's manual portfolio holdings to database."""
    from invst.portfolio.health import UserHolding, save_user_holdings

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    user_holdings = [
        UserHolding(
            symbol=h.symbol.strip().upper(),
            shares=h.shares,
            buy_price=h.buy_price,
            target_price=h.target_price,
            notes=h.notes,
        )
        for h in payload.holdings
    ]
    save_user_holdings(conn, user_holdings, portfolio_id="default", user_id=user_id)
    return {"status": "saved", "count": len(user_holdings)}


@router.post("/v2/portfolio/health", response_model=PortfolioHealthResponse)
def post_evaluate_portfolio_health(
    payload: PortfolioSaveRequest,
    fetch_live: bool = True,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Compute real-time health diagnostic, redlines, sector caps, and BUY/SELL/HOLD advice."""
    from invst.portfolio.health import UserHolding, evaluate_portfolio_health

    user_holdings = [
        UserHolding(
            symbol=h.symbol.strip().upper(),
            shares=h.shares,
            buy_price=h.buy_price,
            target_price=h.target_price,
            notes=h.notes,
        )
        for h in payload.holdings
    ]
    report = evaluate_portfolio_health(conn, user_holdings, fetch_live=fetch_live)
    return PortfolioHealthResponse(**report.to_dict())


@router.get("/v2/portfolios", response_model=list[PortfolioSummarySchema])
def get_user_portfolios(
    portfolio_type: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """List all portfolios and target lists, optionally filtered by portfolio_type."""
    from invst.portfolio.health import list_portfolios

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    items = list_portfolios(conn, portfolio_type=portfolio_type, user_id=user_id)
    return [PortfolioSummarySchema(**it) for it in items]


@router.post("/v2/portfolios", response_model=PortfolioDetailSchema)
def post_create_portfolio(
    payload: CreatePortfolioRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Create a new portfolio or target list."""
    from invst.portfolio.health import UserHolding, create_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    initial_holdings = [
        UserHolding(
            symbol=h.symbol.strip().upper(),
            shares=h.shares,
            buy_price=h.buy_price,
            target_price=h.target_price,
            notes=h.notes,
        )
        for h in payload.holdings
    ]
    p = create_portfolio(
        conn,
        name=payload.name,
        description=payload.description,
        portfolio_type=payload.portfolio_type,
        initial_holdings=initial_holdings,
        user_id=user_id,
    )
    return PortfolioDetailSchema(
        id=p.id,
        name=p.name,
        description=p.description,
        portfolio_type=p.portfolio_type,
        holdings=[
            UserHoldingSchema(
                symbol=h.symbol,
                shares=h.shares,
                buy_price=h.buy_price,
                target_price=h.target_price,
                notes=h.notes,
            )
            for h in p.holdings
        ],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/v2/portfolios/{portfolio_id}", response_model=PortfolioDetailSchema)
def get_user_portfolio_detail(
    portfolio_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Retrieve details and holdings for a specific portfolio."""
    from invst.portfolio.health import get_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    p = get_portfolio(conn, portfolio_id, user_id=user_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found")
    return PortfolioDetailSchema(
        id=p.id,
        name=p.name,
        description=p.description,
        portfolio_type=p.portfolio_type,
        holdings=[
            UserHoldingSchema(
                symbol=h.symbol,
                shares=h.shares,
                buy_price=h.buy_price,
                target_price=h.target_price,
                notes=h.notes,
            )
            for h in p.holdings
        ],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.put("/v2/portfolios/{portfolio_id}", response_model=PortfolioDetailSchema)
def put_update_user_portfolio(
    portfolio_id: str,
    payload: UpdatePortfolioRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update portfolio metadata and/or replace holdings."""
    from invst.portfolio.health import UserHolding, update_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    holdings = None
    if payload.holdings is not None:
        holdings = [
            UserHolding(
                symbol=h.symbol.strip().upper(),
                shares=h.shares,
                buy_price=h.buy_price,
                target_price=h.target_price,
                notes=h.notes,
            )
            for h in payload.holdings
        ]
    p = update_portfolio(
        conn,
        portfolio_id=portfolio_id,
        name=payload.name,
        description=payload.description,
        portfolio_type=payload.portfolio_type,
        holdings=holdings,
        user_id=user_id,
    )
    if not p:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found")
    return PortfolioDetailSchema(
        id=p.id,
        name=p.name,
        description=p.description,
        portfolio_type=p.portfolio_type,
        holdings=[
            UserHoldingSchema(
                symbol=h.symbol,
                shares=h.shares,
                buy_price=h.buy_price,
                target_price=h.target_price,
                notes=h.notes,
            )
            for h in p.holdings
        ],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.delete("/v2/portfolios/{portfolio_id}")
def delete_user_portfolio(
    portfolio_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a portfolio or target list."""
    from invst.portfolio.health import delete_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    ok = delete_portfolio(conn, portfolio_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found")
    return {"status": "deleted", "portfolio_id": portfolio_id}


@router.post("/v2/portfolios/{portfolio_id}/holdings")
def post_add_stock_to_portfolio(
    portfolio_id: str,
    payload: AddStockToPortfolioRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Add or update an individual stock in a specific portfolio or target list."""
    from invst.portfolio.health import UserHolding, add_or_update_holding_in_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    holding = UserHolding(
        symbol=payload.symbol.strip().upper(),
        shares=payload.shares,
        buy_price=payload.buy_price,
        target_price=payload.target_price,
        notes=payload.notes,
    )
    add_or_update_holding_in_portfolio(conn, portfolio_id, holding, user_id=user_id)
    return {
        "status": "success",
        "portfolio_id": portfolio_id,
        "symbol": holding.symbol,
        "shares": holding.shares,
        "buy_price": holding.buy_price,
        "target_price": holding.target_price,
    }


@router.delete("/v2/portfolios/{portfolio_id}/holdings/{symbol}")
def delete_stock_from_portfolio(
    portfolio_id: str,
    symbol: str,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Remove a stock from a specific portfolio or target list."""
    from invst.portfolio.health import remove_holding_from_portfolio

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    remove_holding_from_portfolio(conn, portfolio_id, symbol.strip().upper(), user_id=user_id)
    return {"status": "deleted", "portfolio_id": portfolio_id, "symbol": symbol.strip().upper()}


@router.post("/v2/portfolios/{portfolio_id}/health", response_model=PortfolioHealthResponse)
def post_evaluate_portfolio_health_by_id(
    portfolio_id: str,
    fetch_live: bool = True,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Evaluate health diagnosis for a specific saved portfolio or target list."""
    from invst.portfolio.health import evaluate_portfolio_health, load_user_holdings

    user_id = current_user.get("user_id") or current_user.get("id") or 11
    holdings = load_user_holdings(conn, portfolio_id=portfolio_id, user_id=user_id)
    report = evaluate_portfolio_health(conn, holdings, fetch_live=fetch_live)
    return PortfolioHealthResponse(**report.to_dict())


