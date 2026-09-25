export interface HoldingItem {
  symbol: string;
  sector: string;
  target_weight: number;
  action: string;
  shares_target: number | null;
  executed: boolean;
}

export interface MainPortfolioPositionItem {
  symbol: string;
  shares: number;
  buy_price: number;
  current_price: number;
  current_value: number;
  weight_pct: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  sector: string;
  action_verdict: string;
  action_badge: string;
  action_rationale: string;
  expected_return_12m: number;
}

export interface MainPortfolioStatus {
  portfolio_id: string;
  portfolio_name: string;
  holdings_count: number;
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  overall_health_score: number;
  overall_health_grade: string;
  weighted_business_score: number;
  weighted_valuation_score: number;
  critical_redline_alerts: string[];
  sector_warnings: string[];
  positions: MainPortfolioPositionItem[];
  sector_exposures: Record<string, number>;
}

export interface MacroPulseItem {
  india_vix: number;
  nifty_50: number;
  regime: string;
  regime_description: string;
  is_live: boolean;
}

export interface DashboardResponse {
  latest_asof: string | null;
  target_holdings: number;
  max_stock_cap: number;
  holdings: HoldingItem[];
  sector_allocations: Record<string, number>;
  main_portfolio?: MainPortfolioStatus | null;
  macro_pulse?: MacroPulseItem | null;
}

export interface StockRecommendationItem {
  symbol: string;
  sector: string;
  action: string;
  target_weight: number;
  current_weight: number;
  rationale: string;
  composite_score: number;
  quality_score: number;
  valuation_score: number;
  risk_score: number;
  sentiment_overlay_points: number;
  p_outperform?: number;
  expected_alpha_pct?: number;
  arth_score?: number;
  signal_agreement?: number;
  conviction_tier?: string;
  quality_metrics: Record<string, number | null>;
  valuation_metrics: Record<string, number | null>;
  risk_metrics: Record<string, number | null>;
}

export interface RecommendationsResponse {
  asof_date: string;
  count: number;
  recommendations: StockRecommendationItem[];
}

export interface QuickPickItem {
  rank: number;
  symbol: string;
  sector: string;
  action: string;
  suggested_weight: number;
  latest_close: number | null;
  composite_score: number;
  quality_score: number;
  valuation_score: number;
  risk_score: number;
  sentiment_overlay_points: number;
  rationale: string;
  p_outperform?: number;
  expected_alpha_pct?: number;
  arth_score?: number;
  signal_agreement?: number;
  conviction_tier?: string;
  model_name?: string;
  horizon_days?: number;
  multi_horizon_projections?: Record<string, number>;
  quality_metrics: Record<string, number | null>;
  valuation_metrics: Record<string, number | null>;
  risk_metrics: Record<string, number | null>;
}

export interface QuickPicksResponse {
  asof_date: string;
  n_requested: number;
  count: number;
  deployment_context: string;
  model_status?: string;
  model_name?: string;
  brier_score?: number;
  picks: QuickPickItem[];
}

export interface ModelTrainRequest {
  model_type: string;
  horizon_days: number;
  feature_mode: string;
  calibration_method: string;
  asof?: string;
}

export interface ModelTrainResponse {
  status: string;
  model_name: string;
  model_type: string;
  horizon_days: number;
  feature_mode: string;
  sample_count: number;
  positive_ratio: number;
  brier_score: number;
  train_accuracy: number;
  feature_importances: Record<string, number>;
  trained_at: string;
  message: string;
}

export interface ModelStatusResponse {
  status: string;
  is_trained: boolean;
  model_name: string;
  model_type: string;
  horizon_days: number;
  feature_mode: string;
  sample_count: number;
  positive_ratio: number;
  brier_score: number;
  train_accuracy: number;
  feature_importances: Record<string, number>;
  trained_at: string | null;
}


export interface BacktestMetricsSummary {
  cagr: number | null;
  sharpe: number | null;
  sortino: number | null;
  calmar: number | null;
  max_drawdown: number | null;
  annualized_vol: number | null;
  turnover_avg: number | null;
  hit_rate: number | null;
  worst_5d_return: number | null;
  rebalance_count: number;
  benchmark_cagr: number | null;
  benchmark_sharpe: number | null;
  benchmark_max_drawdown: number | null;
}

export interface BacktestRunRequest {
  start_date: string;
  end_date: string;
  initial_capital?: number;
  benchmark_symbol?: string;
  target_holdings?: number;
}

export interface BacktestRunResponse {
  run_id: string;
  metrics: BacktestMetricsSummary;
  equity_dates: string[];
  portfolio_equity: number[];
  benchmark_equity: number[];
  status: string;
}

export interface BacktestHistoryItem {
  run_id: string;
  started_at: string;
  start_date: string;
  end_date: string;
  cagr: number | null;
  sharpe: number | null;
  max_drawdown: number | null;
  turnover_avg: number | null;
  benchmark_cagr: number | null;
  status: string;
}

export interface HealthCheckItem {
  name: string;
  passed: boolean;
  message: string;
  details: Record<string, any>;
}

export interface HealthResponse {
  overall_status: 'HEALTHY' | 'ATTENTION_REQUIRED';
  data_quality_checks: HealthCheckItem[];
  pit_audits: HealthCheckItem[];
}

export interface UniverseResponse {
  asof_date: string;
  total_symbols: number;
  sectors: Record<string, number>;
}

export interface MacroPulseResponse {
  asof_date: string;
  india_vix: number;
  nifty_50: number;
  usd_inr: number;
  regime: 'NEUTRAL' | 'HIGH_VOLATILITY' | 'EXPANSIONARY' | string;
  regime_description: string;
  is_live: boolean;
}

export interface TickerItem {
  symbol: string;
  price: string;
  change: string;
  isPositive: boolean;
  change_pct?: number;
  price_val?: number;
  category?: string;
  raw_symbol?: string;
  last_updated?: string;
}

export interface HorizonProjection {
  horizon: string;
  months: number;
  target_price_bear: number;
  target_price_base: number;
  target_price_bull: number;
  return_bear_pct: number;
  return_base_pct: number;
  return_bull_pct: number;
  expected_return_pct: number;
  downside_to_upside_ratio: number;
  cagr_pct?: number | null;
}

export interface NewsHeadlineItem {
  headline: string;
  sentiment_score: number | null;
  source: string | null;
  published_at: string | null;
}

export interface TacticalExecutionPlan {
  verdict_reasoning: string;
  recommended_entry_min: number;
  recommended_entry_max: number;
  dip_target_price: number;
  dip_discount_pct: number;
  stop_loss_level: number;
  target_price_12m: number;
  target_price_bull: number;
  risk_reward_ratio: number;
}

export interface ScoreExplanation {
  score: number;
  tier: string;
  sub_metrics: Record<string, any>;
  interpretation: string;
}

export interface ScoreBreakdowns {
  business_quality: ScoreExplanation;
  valuation: ScoreExplanation;
  growth: ScoreExplanation;
  risk: ScoreExplanation;
  investment_conviction: ScoreExplanation;
}

export interface TechnicalOverview {
  trend_phase: string;
  rsi_14: number;
  dma_20: number;
  dma_50: number;
  dma_200: number;
  pct_from_52w_high: number;
  pct_from_52w_low: number;
  pct_from_50dma: number;
  pct_from_200dma: number;
  structure_summary: string;
}

export interface SectorContext {
  sector: string;
  sector_archetype: string;
  is_etf: boolean;
  sector_tailwinds: string[];
  peer_standing: string;
}

export interface ResearchReport {
  executive_summary: string;
  fundamental_moat: string;
  valuation_expectations: string;
  technical_trend: string;
  sector_catalysts: string;
  tactical_action_plan: string;
}

export interface FullStockAnalysisResponse {
  symbol: string;
  company_name: string;
  sector: string;
  sector_archetype: string;
  asof_date: string;
  current_price: number;
  change_pct: number;
  high_52w: number;
  low_52w: number;
  dma_50: number;
  dma_200: number;
  market_cap_cr: number;
  is_live_data: boolean;
  is_etf?: boolean;

  business_quality_score: number;
  growth_score: number;
  business_score: number;
  valuation_score: number;
  risk_score: number;
  investment_score: number;

  matrix_quadrant: string;
  action_verdict: 'STRONG_BUY' | 'TACTICAL_BUY' | 'HOLD_WAIT' | 'AVOID' | 'REDLINE_REJECT' | string;
  verdict_badge: string;
  is_investment_worthy: boolean;

  tactical_action?: TacticalExecutionPlan;
  score_breakdowns?: ScoreBreakdowns;
  technical_overview?: TechnicalOverview;
  sector_context?: SectorContext;

  redlines_triggered: string[];
  is_redline_clean: boolean;

  macro_regime: string;
  horizon_3m: HorizonProjection;
  horizon_6m: HorizonProjection;
  horizon_12m: HorizonProjection;
  horizon_3y: HorizonProjection;

  sentiment_score: number;
  headlines: NewsHeadlineItem[];

  thesis_rationale: string;
  research_report?: ResearchReport;
  primary_risks: string[];
  growth_drivers: string[];
}

export interface UserHoldingItem {
  symbol: string;
  shares: number;
  buy_price: number;
  target_price?: number | null;
  notes?: string;
}

export interface PortfolioSummary {
  id: string;
  name: string;
  description: string;
  portfolio_type: 'PORTFOLIO' | 'TARGETLIST' | string;
  holdings_count: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioDetail {
  id: string;
  name: string;
  description: string;
  portfolio_type: 'PORTFOLIO' | 'TARGETLIST' | string;
  holdings: UserHoldingItem[];
  created_at: string;
  updated_at: string;
}

export interface CreatePortfolioRequest {
  name: string;
  description?: string;
  portfolio_type?: 'PORTFOLIO' | 'TARGETLIST' | string;
  holdings?: UserHoldingItem[];
}

export interface UpdatePortfolioRequest {
  name?: string;
  description?: string;
  portfolio_type?: 'PORTFOLIO' | 'TARGETLIST' | string;
  holdings?: UserHoldingItem[];
}

export interface AddStockToPortfolioRequest {
  symbol: string;
  shares?: number;
  buy_price: number;
  target_price?: number | null;
  notes?: string;
}

export interface PositionHealthItem {
  symbol: string;
  shares: number;
  buy_price: number;
  current_price: number;
  current_value: number;
  weight_pct: number;
  target_weight_pct: number;
  shares_to_adjust: number;
  capital_delta: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  business_quality_score: number;
  valuation_score: number;
  risk_score: number;
  investment_score: number;
  quality_tier: string;
  action_verdict: 'BUY_MORE' | 'HOLD' | 'TRIM' | 'EXIT_SELL' | string;
  action_badge: string;
  action_rationale: string;
  dip_target_price: number;
  dip_discount_pct: number;
  stop_loss_level: number;
  technical_trend: string;
  is_etf: boolean;
  redlines_triggered: string[];
  expected_return_12m: number;
  sector: string;
  target_price?: number | null;
  notes?: string;
}

export interface PortfolioHorizonSummary {
  horizon_name: string;
  expected_return_pct: number;
  bull_return_pct: number;
  bear_return_pct: number;
  projected_portfolio_value: number;
  cagr_pct?: number | null;
}

export interface PortfolioFactorHealth {
  score: number;
  tier: string;
  interpretation: string;
  summary_metric: string;
}

export interface PortfolioDiversification {
  hhi_score: number;
  diversification_tier: string;
  equity_weight_pct: number;
  etf_weight_pct: number;
  top_3_concentration_pct: number;
  total_positions: number;
  sector_count: number;
}

export interface RebalanceOrder {
  symbol: string;
  action: 'SELL' | 'TRIM' | 'ACCUMULATE' | string;
  shares: number;
  estimated_price: number;
  capital_impact: number;
  target_weight_pct: number;
  rationale: string;
}

export interface RebalancingBlueprint {
  total_capital_unlocked: number;
  total_capital_needed: number;
  net_cash_flow: number;
  rebalance_urgency: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | string;
  orders: RebalanceOrder[];
  strategic_summary: string;
}

export interface PortfolioReplacementIdea {
  symbol: string;
  sector: string;
  composite_score: number;
  quality_score: number;
  valuation_score: number;
  suggested_role: string;
}

export interface PortfolioHealthResponse {
  asof_date: string;
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  weighted_business_score: number;
  weighted_valuation_score: number;
  weighted_risk_score?: number;
  weighted_investment_score: number;
  overall_health_score: number;
  overall_health_grade: 'EXCELLENT' | 'GOOD' | 'NEEDS_ATTENTION' | 'HIGH_RISK' | string;
  positions: PositionHealthItem[];
  sector_exposures: Record<string, number>;
  sector_warnings: string[];
  critical_redline_alerts: string[];
  suggested_replacements: PortfolioReplacementIdea[];
  summary_action_plan: string;
  portfolio_horizons?: Record<string, PortfolioHorizonSummary>;
  factor_health?: Record<string, PortfolioFactorHealth>;
  diversification?: PortfolioDiversification;
  rebalancing_blueprint?: RebalancingBlueprint;
}

export interface UserProfile {
  id: number;
  email: string;
  name: string | null;
  role: 'admin' | 'user' | string;
  user_type?: 'ADMIN' | 'PRO_INVESTOR' | string;
  status: 'INVITED' | 'ACTIVE' | 'SUSPENDED' | string;
  created_at: string | null;
  last_login: string | null;
}

export interface EmailLookupResponse {
  email: string;
  exists: boolean;
  status: 'INVITED' | 'ACTIVE' | 'SUSPENDED' | 'NOT_FOUND';
  name?: string | null;
  role?: string | null;
  user_type?: 'ADMIN' | 'PRO_INVESTOR' | string;
}

export interface SetPasswordResponse {
  token: string;
  email: string;
  role: string;
  user_type?: string;
  status: string;
  message: string;
}

export interface AdminSummaryResponse {
  total_users: number;
  active_users: number;
  invited_users: number;
  suspended_users: number;
  model_trained: boolean;
  model_version: string | null;
  backtests_count: number;
  system_status: string;
}

export interface AdminCreateUserRequest {
  email: string;
  name?: string | null;
  role?: 'user' | 'admin' | string;
  user_type?: 'ADMIN' | 'PRO_INVESTOR' | string;
}

export interface AdminUpdateStatusRequest {
  status: 'ACTIVE' | 'SUSPENDED' | 'INVITED' | string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  message: string;
}

export interface UpdateProfileRequest {
  name?: string | null;
}

