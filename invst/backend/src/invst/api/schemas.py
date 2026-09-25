"""Pydantic data schemas for invst REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HoldingItem(BaseModel):
    symbol: str
    sector: str = "general"
    target_weight: float
    action: str = "BUY"
    shares_target: int | None = None
    executed: bool = False


class MainPortfolioPositionItem(BaseModel):
    symbol: str
    shares: float
    buy_price: float
    current_price: float
    current_value: float
    weight_pct: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    sector: str = "general"
    action_verdict: str = "HOLD"
    action_badge: str = "HOLD"
    action_rationale: str = ""
    expected_return_12m: float = 0.0


class MainPortfolioStatus(BaseModel):
    portfolio_id: str = "default"
    portfolio_name: str = "Main Portfolio"
    holdings_count: int = 0
    total_invested: float = 0.0
    total_current_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_unrealized_pnl_pct: float = 0.0
    overall_health_score: float = 0.0
    overall_health_grade: str = "N/A"
    weighted_business_score: float = 0.0
    weighted_valuation_score: float = 0.0
    critical_redline_alerts: list[str] = Field(default_factory=list)
    sector_warnings: list[str] = Field(default_factory=list)
    positions: list[MainPortfolioPositionItem] = Field(default_factory=list)
    sector_exposures: dict[str, float] = Field(default_factory=dict)


class MacroPulseItem(BaseModel):
    india_vix: float = 14.5
    nifty_50: float = 24500.0
    regime: str = "NEUTRAL"
    regime_description: str = "Normal market volatility. Standard scenario weights apply."
    is_live: bool = False


class DashboardResponse(BaseModel):
    latest_asof: str | None = None
    target_holdings: int = 8
    max_stock_cap: float = 0.25
    max_sector_cap: float = 0.40
    holdings: list[HoldingItem] = Field(default_factory=list)
    sector_allocations: dict[str, float] = Field(default_factory=dict)
    main_portfolio: MainPortfolioStatus | None = None
    macro_pulse: MacroPulseItem | None = None


class StockRecommendationItem(BaseModel):
    symbol: str
    sector: str
    action: str = "BUY"
    target_weight: float
    current_weight: float = 0.0
    rationale: str
    composite_score: float
    quality_score: float
    valuation_score: float
    risk_score: float
    sentiment_overlay_points: float
    p_outperform: float = 0.50
    expected_alpha_pct: float = 0.0
    arth_score: float = 50.0
    signal_agreement: float = 1.0
    conviction_tier: str = "SOLID OUTPERFORMER"
    quality_metrics: dict[str, Any] = Field(default_factory=dict)
    valuation_metrics: dict[str, Any] = Field(default_factory=dict)
    risk_metrics: dict[str, Any] = Field(default_factory=dict)


class RecommendationsResponse(BaseModel):
    asof_date: str
    count: int
    recommendations: list[StockRecommendationItem] = Field(default_factory=list)


class QuickPickItem(BaseModel):
    rank: int
    symbol: str
    sector: str
    action: str = "BUY"
    suggested_weight: float
    latest_close: float | None = None
    composite_score: float
    quality_score: float
    valuation_score: float
    risk_score: float
    sentiment_overlay_points: float
    rationale: str
    p_outperform: float = 0.50
    expected_alpha_pct: float = 0.0
    arth_score: float = 50.0
    signal_agreement: float = 1.0
    conviction_tier: str = "HIGH CONVICTION ALPHA"
    model_name: str = "Calibrated Fund+Momentum Booster (Candidate 2)"
    horizon_days: int = 90
    multi_horizon_projections: dict[str, float] = Field(default_factory=dict)
    quality_metrics: dict[str, Any] = Field(default_factory=dict)
    valuation_metrics: dict[str, Any] = Field(default_factory=dict)
    risk_metrics: dict[str, Any] = Field(default_factory=dict)


class QuickPicksResponse(BaseModel):
    asof_date: str
    n_requested: int
    count: int
    deployment_context: str
    model_status: str = "TRAINED"
    model_name: str = "Calibrated Fund+Momentum Booster (Candidate 2)"
    brier_score: float = 0.25
    picks: list[QuickPickItem] = Field(default_factory=list)


class ModelTrainRequest(BaseModel):
    model_type: str = "lightgbm"
    horizon_days: int = 90
    feature_mode: str = "pair_fund_mom"
    calibration_method: str = "isotonic"
    asof: str | None = None


class ModelTrainResponse(BaseModel):
    status: str
    model_name: str
    model_type: str
    horizon_days: int
    feature_mode: str
    sample_count: int
    positive_ratio: float
    brier_score: float
    train_accuracy: float
    feature_importances: dict[str, float] = Field(default_factory=dict)
    trained_at: str
    message: str


class ModelStatusResponse(BaseModel):
    status: str
    is_trained: bool
    model_name: str
    model_type: str
    horizon_days: int
    feature_mode: str
    sample_count: int
    positive_ratio: float
    brier_score: float
    train_accuracy: float
    feature_importances: dict[str, float] = Field(default_factory=dict)
    trained_at: str | None = None


class BacktestRunRequest(BaseModel):
    start_date: str = "2020-01-01"
    end_date: str = "2024-03-31"
    initial_capital: float = 1_000_000.0
    benchmark_symbol: str = "NIFTY500"
    target_holdings: int = 8


class BacktestMetricsSummary(BaseModel):
    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    annualized_vol: float
    turnover_avg: float
    hit_rate: float
    worst_5d_return: float
    rebalance_count: int
    benchmark_cagr: float
    benchmark_sharpe: float
    benchmark_max_drawdown: float
    alpha: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    beta: float = 1.0
    jensen_alpha: float = 0.0
    upside_capture: float = 1.0
    downside_capture: float = 1.0
    payoff_ratio: float = 1.0


class BacktestRunResponse(BaseModel):
    run_id: str
    metrics: BacktestMetricsSummary
    equity_dates: list[str] = Field(default_factory=list)
    portfolio_equity: list[float] = Field(default_factory=list)
    benchmark_equity: list[float] = Field(default_factory=list)
    status: str = "completed"


class BacktestHistoryItem(BaseModel):
    run_id: str
    started_at: str
    start_date: str
    end_date: str
    cagr: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    turnover_avg: float | None = None
    benchmark_cagr: float | None = None
    alpha: float | None = None
    information_ratio: float | None = None
    status: str = "completed"


class HealthCheckItem(BaseModel):
    name: str
    passed: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    overall_status: str
    data_quality_checks: list[HealthCheckItem]
    pit_audits: list[HealthCheckItem]


class UniverseResponse(BaseModel):
    asof_date: str
    total_symbols: int
    sectors: dict[str, int]


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in_hours: int = 72
    status: str = "authenticated"


class AuthVerifyResponse(BaseModel):
    authenticated: bool
    auth_enabled: bool


# -------------------------------------------------------------------------
# V0.2 Quantitative Engine Schemas
# -------------------------------------------------------------------------

class ScenarioSchema(BaseModel):
    current_price: float
    p_bear: float
    p_base: float
    p_bull: float
    return_bear_pct: float
    return_base_pct: float
    return_bull_pct: float
    expected_return_pct: float
    probability_bear: float
    probability_base: float
    probability_bull: float
    downside_to_upside_ratio: float
    probability_of_loss: float


class StockRecommendationV2Item(BaseModel):
    symbol: str
    sector: str
    sector_archetype: str
    rank: int
    investment_score: float
    business_score: float
    growth_score: float
    growth_confidence: float
    valuation_score: float
    risk_score: float
    market_score: float
    matrix_quadrant: str
    scenario: ScenarioSchema
    drivers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    rationale: str


class RecommendationsV2Response(BaseModel):
    asof_date: str
    count: int
    recommendations: list[StockRecommendationV2Item] = Field(default_factory=list)


class HRPPortfolioRequest(BaseModel):
    capital: float = 1_000_000.0
    profile: str = "MODERATE"
    asof: str | None = None
    top_n: int = 15


class HRPPortfolioResponse(BaseModel):
    weights: dict[str, float]
    target_shares: dict[str, int]
    cash_balance: float
    total_invested: float
    expected_portfolio_return: float
    expected_portfolio_volatility: float
    sharpe_ratio: float
    sector_allocations: dict[str, float]
    investor_profile: str


class CorporateEventItem(BaseModel):
    event_id: str
    symbol: str
    event_type: str
    headline: str
    direction: str
    materiality_score: float
    confidence_score: float
    affected_factors: list[str]
    effective_date: str


class EventsFeedResponse(BaseModel):
    count: int
    events: list[CorporateEventItem] = Field(default_factory=list)


# -------------------------------------------------------------------------
# Live Feeds, Single Stock Analyzer & Personal Portfolio Schemas
# -------------------------------------------------------------------------

class MacroPulseResponse(BaseModel):
    asof_date: str
    india_vix: float
    nifty_50: float
    usd_inr: float
    regime: str
    regime_description: str
    is_live: bool


class HorizonProjectionSchema(BaseModel):
    horizon: str
    months: int
    target_price_bear: float
    target_price_base: float
    target_price_bull: float
    return_bear_pct: float
    return_base_pct: float
    return_bull_pct: float
    expected_return_pct: float
    downside_to_upside_ratio: float
    cagr_pct: float | None = None


class NewsHeadlineSchema(BaseModel):
    headline: str
    sentiment_score: float | None = None
    source: str | None = None
    published_at: str | None = None


class TacticalExecutionSchema(BaseModel):
    verdict_reasoning: str
    recommended_entry_min: float
    recommended_entry_max: float
    dip_target_price: float
    dip_discount_pct: float
    stop_loss_level: float
    target_price_12m: float
    target_price_bull: float
    risk_reward_ratio: float


class ScoreExplanationSchema(BaseModel):
    score: float
    tier: str
    sub_metrics: dict[str, Any] = Field(default_factory=dict)
    interpretation: str


class ScoreBreakdownsSchema(BaseModel):
    business_quality: ScoreExplanationSchema
    valuation: ScoreExplanationSchema
    growth: ScoreExplanationSchema
    risk: ScoreExplanationSchema
    investment_conviction: ScoreExplanationSchema


class TechnicalOverviewSchema(BaseModel):
    trend_phase: str
    rsi_14: float
    dma_20: float
    dma_50: float
    dma_200: float
    pct_from_52w_high: float
    pct_from_52w_low: float
    pct_from_50dma: float
    pct_from_200dma: float
    structure_summary: str


class SectorContextSchema(BaseModel):
    sector: str
    sector_archetype: str
    is_etf: bool
    sector_tailwinds: list[str] = Field(default_factory=list)
    peer_standing: str


class ResearchReportSchema(BaseModel):
    executive_summary: str
    fundamental_moat: str
    valuation_expectations: str
    technical_trend: str
    sector_catalysts: str
    tactical_action_plan: str


class FullStockAnalysisResponse(BaseModel):
    symbol: str
    company_name: str
    sector: str
    sector_archetype: str
    asof_date: str
    current_price: float
    change_pct: float
    high_52w: float
    low_52w: float
    dma_50: float
    dma_200: float
    market_cap_cr: float
    is_live_data: bool
    is_etf: bool = False

    business_quality_score: float
    growth_score: float
    business_score: float
    valuation_score: float
    risk_score: float
    investment_score: float

    matrix_quadrant: str
    action_verdict: str
    verdict_badge: str
    is_investment_worthy: bool

    tactical_action: TacticalExecutionSchema | None = None
    score_breakdowns: ScoreBreakdownsSchema | None = None
    technical_overview: TechnicalOverviewSchema | None = None
    sector_context: SectorContextSchema | None = None

    redlines_triggered: list[str] = Field(default_factory=list)
    is_redline_clean: bool

    macro_regime: str
    horizon_3m: HorizonProjectionSchema
    horizon_6m: HorizonProjectionSchema
    horizon_12m: HorizonProjectionSchema
    horizon_3y: HorizonProjectionSchema

    sentiment_score: float
    headlines: list[NewsHeadlineSchema] = Field(default_factory=list)

    thesis_rationale: str
    research_report: ResearchReportSchema | None = None
    primary_risks: list[str] = Field(default_factory=list)
    growth_drivers: list[str] = Field(default_factory=list)


class UserHoldingSchema(BaseModel):
    symbol: str
    shares: float
    buy_price: float
    target_price: float | None = None
    notes: str = ""


class PortfolioSaveRequest(BaseModel):
    holdings: list[UserHoldingSchema] = Field(default_factory=list)


class PortfolioSummarySchema(BaseModel):
    id: str
    name: str
    description: str = ""
    portfolio_type: str = "PORTFOLIO"
    holdings_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class PortfolioDetailSchema(BaseModel):
    id: str
    name: str
    description: str = ""
    portfolio_type: str = "PORTFOLIO"
    holdings: list[UserHoldingSchema] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class CreatePortfolioRequest(BaseModel):
    name: str
    description: str = ""
    portfolio_type: str = "PORTFOLIO"
    holdings: list[UserHoldingSchema] = Field(default_factory=list)


class UpdatePortfolioRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    portfolio_type: str | None = None
    holdings: list[UserHoldingSchema] | None = None


class AddStockToPortfolioRequest(BaseModel):
    symbol: str
    shares: float = 1.0
    buy_price: float
    target_price: float | None = None
    notes: str = ""


class PositionHealthSchema(BaseModel):
    symbol: str
    shares: float
    buy_price: float
    current_price: float
    current_value: float
    weight_pct: float
    target_weight_pct: float = 0.0
    shares_to_adjust: float = 0.0
    capital_delta: float = 0.0
    unrealized_pnl: float
    unrealized_pnl_pct: float
    business_quality_score: float
    valuation_score: float = 50.0
    risk_score: float = 50.0
    investment_score: float
    quality_tier: str = "TIER_2_STABLE_COMPOUNDER"
    action_verdict: str
    action_badge: str
    action_rationale: str
    dip_target_price: float = 0.0
    dip_discount_pct: float = 0.0
    stop_loss_level: float = 0.0
    technical_trend: str = "Neutral"
    is_etf: bool = False
    redlines_triggered: list[str] = Field(default_factory=list)
    expected_return_12m: float
    sector: str
    target_price: float | None = None
    notes: str = ""


class PortfolioHorizonSummarySchema(BaseModel):
    horizon_name: str
    expected_return_pct: float
    bull_return_pct: float
    bear_return_pct: float
    projected_portfolio_value: float
    cagr_pct: float | None = None


class PortfolioFactorHealthSchema(BaseModel):
    score: float
    tier: str
    interpretation: str
    summary_metric: str


class PortfolioDiversificationSchema(BaseModel):
    hhi_score: float
    diversification_tier: str
    equity_weight_pct: float
    etf_weight_pct: float
    top_3_concentration_pct: float
    total_positions: int
    sector_count: int


class RebalanceOrderSchema(BaseModel):
    symbol: str
    action: str
    shares: float
    estimated_price: float
    capital_impact: float
    target_weight_pct: float
    rationale: str


class RebalancingBlueprintSchema(BaseModel):
    total_capital_unlocked: float
    total_capital_needed: float
    net_cash_flow: float
    rebalance_urgency: str
    orders: list[RebalanceOrderSchema] = Field(default_factory=list)
    strategic_summary: str = ""


class PortfolioReplacementIdea(BaseModel):
    symbol: str
    sector: str
    composite_score: float
    quality_score: float
    valuation_score: float
    suggested_role: str


class PortfolioHealthResponse(BaseModel):
    asof_date: str
    total_invested: float
    total_current_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    weighted_business_score: float
    weighted_valuation_score: float
    weighted_risk_score: float = 50.0
    weighted_investment_score: float
    overall_health_score: float
    overall_health_grade: str
    positions: list[PositionHealthSchema] = Field(default_factory=list)
    sector_exposures: dict[str, float] = Field(default_factory=dict)
    sector_warnings: list[str] = Field(default_factory=list)
    critical_redline_alerts: list[str] = Field(default_factory=list)
    suggested_replacements: list[PortfolioReplacementIdea] = Field(default_factory=list)
    summary_action_plan: str
    portfolio_horizons: dict[str, PortfolioHorizonSummarySchema] = Field(default_factory=dict)
    factor_health: dict[str, PortfolioFactorHealthSchema] = Field(default_factory=dict)
    diversification: PortfolioDiversificationSchema | None = None
    rebalancing_blueprint: RebalancingBlueprintSchema | None = None



