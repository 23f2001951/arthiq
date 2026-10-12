"""Pydantic schemas for Mutual Fund intelligence and SIP diagnostics."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MFCategoryRank(BaseModel):
    scheme_code: int
    category: str
    rank: int
    total_in_category: int
    percentile: float
    quartile: str
    rank_badge: str
    rank_label: str
    trailing_3y_cagr: float | None = None
    crisil_rating: int | None = None
    expense_ratio: float | None = None


class MFSchemeSearchItem(BaseModel):
    scheme_code: int
    isin: str | None = None
    scheme_name: str
    fund_house: str
    category: str
    plan_type: str = "Direct"
    option_type: str = "Growth"
    expense_ratio: float | None = None
    aum_cr: float | None = None
    crisil_rating: int | None = None
    risk_level: str | None = None
    current_nav: float | None = None
    powerup_form: dict[str, Any] | None = None
    category_rank: MFCategoryRank | None = None


class MFHoldingItem(BaseModel):
    company_name: str
    symbol: str | None = None
    sector: str | None = None
    weight_pct: float


class MFSchemeDetailResponse(BaseModel):
    scheme_code: int
    isin: str | None = None
    scheme_name: str
    fund_house: str
    category: str
    plan_type: str
    option_type: str
    benchmark_index: str | None = None
    expense_ratio: float | None = None
    aum_cr: float | None = None
    fund_manager: str | None = None
    crisil_rating: int | None = None
    risk_level: str | None = None
    inception_date: str | None = None
    current_nav: float | None = None
    latest_nav_date: str | None = None
    trailing_returns: dict[str, float | None]
    top_holdings: list[MFHoldingItem] = []
    analyst_conviction: dict[str, Any] | None = None
    powerup_form: dict[str, Any] = {}
    category_rank: MFCategoryRank | None = None


class MFRollingReturnsResponse(BaseModel):
    window_years: int
    sample_count: int
    mean_return_pct: float
    median_return_pct: float
    p25_return_pct: float
    p75_return_pct: float
    min_return_pct: float
    max_return_pct: float
    negative_return_prob_pct: float
    outperformance_pct: float | None = None
    series: list[dict[str, Any]] = []


class MFRiskMetricsResponse(BaseModel):
    cagr: float
    volatility: float
    downside_deviation: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    alpha: float
    upside_capture: float | None = None
    downside_capture: float | None = None


class MFRecommendationRequest(BaseModel):
    risk_profile: str = Field(default="MODERATE", description="CONSERVATIVE, MODERATE, GROWTH, AGGRESSIVE")
    horizon_years: int = Field(default=5, ge=1, le=30)
    goal_type: str = Field(default="WEALTH_CREATION", description="WEALTH_CREATION, TAX_SAVING, RETIREMENT, EMERGENCY_FUND")
    monthly_budget: float = Field(default=20000.0, ge=500.0)
    step_up_pct: float = Field(default=10.0, ge=0.0, le=50.0)


class MFRecommendationResponse(BaseModel):
    user_profile: dict[str, Any]
    asset_allocation: dict[str, float]
    recommended_funds: list[dict[str, Any]]
    total_monthly_sip: float
    wealth_projection: dict[str, Any]
    advisory_rationale: str | None = None
    market_context: str | None = None
    tax_optimization_memo: dict[str, Any] | None = None
    rebalancing_protocol: dict[str, Any] | None = None
    multi_scenario_projections: dict[str, Any] | None = None


class MFSIPCalculateRequest(BaseModel):
    monthly_sip: float = Field(default=10000.0, ge=500.0)
    expected_cagr_pct: float = Field(default=12.0, ge=1.0, le=40.0)
    years: int = Field(default=10, ge=1, le=40)
    step_up_pct: float = Field(default=0.0, ge=0.0, le=50.0)
    inflation_pct: float = Field(default=0.0, ge=0.0, le=20.0)


class MFSIPCalculateResponse(BaseModel):
    monthly_sip: float
    expected_cagr_pct: float
    years: int
    step_up_pct: float
    inflation_pct: float
    total_invested: float
    estimated_corpus: float
    estimated_gain: float
    wealth_multiplier: float
    trajectory: list[dict[str, Any]]


class MFAddSIPRequest(BaseModel):
    scheme_code: int
    amount: float = Field(gt=0)
    start_date: str
    end_date: str | None = None
    status: str = Field(default="ACTIVE", description="ACTIVE, PAUSED, CLOSED")
    sip_day: int | None = Field(default=None, ge=1, le=28, description="Day of month for SIP debit. Defaults to day of start_date.")
    step_up_pct: float = Field(default=0.0, ge=0.0)
    folio_number: str | None = None
    custom_invested: float | None = None
    custom_current_value: float | None = None
    custom_units: float | None = None
    skipped_months: list[str] = Field(default_factory=list, description="List of YYYY-MM strings that were skipped")
    paid_months: list[str] = Field(default_factory=list, description="List of YYYY-MM strings that were paid")
    sip_id: str | None = Field(default=None, description="Optional existing SIP schedule ID for in-place edit")


class MFResumeSIPRequest(BaseModel):
    amount: float | None = None
    sip_day: int | None = None


class MFReallocateSIPRequest(BaseModel):
    target_scheme_code: int
    allocation_mode: str = Field(default="full_switch", description="full_switch, partial_switch, pause_and_redirect")
    amount: float | None = None


class MFPortfolioResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str = "My Mutual Funds"
    notes: str | None = None
    last_saved_at: str | None = None
    total_invested: float
    current_value: float
    unrealized_profit: float
    absolute_return_pct: float
    portfolio_xirr_pct: float | None = None
    monthly_sip_run_rate: float
    active_invested: float | None = None
    active_current_value: float | None = None
    closed_invested: float | None = None
    closed_current_value: float | None = None
    active_profit: float | None = None
    closed_profit: float | None = None
    active_sips_count: int
    closed_sips_count: int
    active_sips: list[dict[str, Any]] = []
    closed_sips: list[dict[str, Any]] = []
    scheme_holdings: list[dict[str, Any]] = []
    asset_allocation: dict[str, float] = {}
    overlap_analysis: dict[str, Any] = {}
    pending_checkins: list[dict[str, Any]] = []
    checkin_history: list[dict[str, Any]] = []
    powerup_summary: dict[str, Any] = {}
    power_age_projection: dict[str, Any] = {}


class MFSavePortfolioRequest(BaseModel):
    portfolio_name: str | None = None
    notes: str | None = None


class MFSIPCheckinRequest(BaseModel):
    sip_id: str
    due_date: str
    status: str = Field(description="PAID, SKIPPED")
    amount: float | None = None
    notes: str | None = None


class MFSIPBatchCheckinRequest(BaseModel):
    action: str = Field(default="MARK_ALL_PAID", description="MARK_ALL_PAID, MARK_ALL_SKIPPED")
    checkin_ids: list[str] = []


class MFPowerAgeRequest(BaseModel):
    current_age: int = Field(default=28, ge=18, le=75)
    current_corpus: float = Field(default=0.0, ge=0.0)
    monthly_sip: float = Field(default=10000.0, ge=0.0)
    annual_step_up_pct: float = Field(default=10.0, ge=0.0, le=50.0)
    expected_cagr_pct: float = Field(default=13.0, ge=1.0, le=35.0)
    target_monthly_expense_today: float = Field(default=50000.0, ge=5000.0)
    inflation_pct: float = Field(default=6.0, ge=0.0, le=20.0)
    swr_pct: float = Field(default=5.0, ge=2.0, le=10.0)
    max_age: int = Field(default=80, ge=50, le=100)


class MFPowerAgeResponse(BaseModel):
    current_age: int
    power_age: int
    standard_power_age: int
    years_to_freedom: int
    years_saved_by_step_up: int
    corpus_at_power_age: float
    monthly_expenses_at_power_age: float
    monthly_passive_income_swp: float
    financial_freedom_year: int
    assumptions: dict[str, Any]
    trajectory: list[dict[str, Any]]
