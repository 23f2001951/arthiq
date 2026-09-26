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

// -----------------------------------------------------------------------------
// Mutual Funds & SIP Types
// -----------------------------------------------------------------------------
export interface MFSchemeSearchItem {
  scheme_code: number;
  isin?: string;
  scheme_name: string;
  fund_house: string;
  category: string;
  plan_type: string;
  option_type: string;
  expense_ratio?: number;
  aum_cr?: number;
  crisil_rating?: number;
  risk_level?: string;
}

export interface MFHoldingItem {
  company_name: string;
  symbol?: string;
  sector?: string;
  weight_pct: number;
}

export interface MFAnalystConviction {
  conviction_score: number;
  verdict: string;
  conviction_badge: string;
  portfolio_role: string;
  pillars: Record<string, { score: number; max: number }>;
  analyst_memo: {
    bull_case: string;
    bear_risks: string;
    recommendation_summary: string;
  };
}

export interface MFSchemeDetailResponse {
  scheme_code: number;
  isin?: string;
  scheme_name: string;
  fund_house: string;
  category: string;
  plan_type: string;
  option_type: string;
  benchmark_index?: string;
  expense_ratio?: number;
  aum_cr?: number;
  fund_manager?: string;
  crisil_rating?: number;
  risk_level?: string;
  inception_date?: string;
  current_nav?: number;
  latest_nav_date?: string;
  trailing_returns: {
    '1m'?: number | null;
    '3m'?: number | null;
    '6m'?: number | null;
    '1y'?: number | null;
    '3y'?: number | null;
    '5y'?: number | null;
    'inception'?: number | null;
  };
  top_holdings: MFHoldingItem[];
  analyst_conviction?: MFAnalystConviction;
}

export interface MFRollingReturnsResponse {
  window_years: number;
  sample_count: number;
  mean_return_pct: number;
  median_return_pct: number;
  p25_return_pct: number;
  p75_return_pct: number;
  min_return_pct: number;
  max_return_pct: number;
  negative_return_prob_pct: number;
  outperformance_pct?: number | null;
  series: Array<{
    start_date: string;
    end_date: string;
    fund_return: number;
    benchmark_return?: number | null;
  }>;
}

export interface MFRiskMetricsResponse {
  cagr: number;
  volatility: number;
  downside_deviation: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  beta: number;
  alpha: number;
  upside_capture?: number | null;
  downside_capture?: number | null;
}

export interface MFRecommendationRequest {
  risk_profile: string;
  horizon_years: number;
  goal_type: string;
  monthly_budget: number;
  step_up_pct: number;
}

export interface MFRecommendationResponse {
  user_profile: {
    risk_profile: string;
    horizon_years: number;
    goal_type: string;
    monthly_budget: number;
    step_up_pct: number;
    risk_label: string;
    expected_cagr_pct: number;
  };
  asset_allocation: Record<string, number>;
  recommended_funds: Array<{
    scheme_code: number;
    scheme_name: string;
    fund_house: string;
    category: string;
    allocation_pct: number;
    monthly_sip: number;
    expense_ratio?: number;
    aum_cr?: number;
    crisil_rating?: number;
    risk_level?: string;
    fund_manager?: string;
    rationale: string;
  }>;
  total_monthly_sip: number;
  wealth_projection: {
    monthly_sip: number;
    expected_cagr_pct: number;
    years: number;
    step_up_pct: number;
    total_invested: number;
    estimated_corpus: number;
    estimated_gain: number;
    wealth_multiplier: number;
    trajectory: Array<{
      year: number;
      monthly_sip: number;
      total_invested: number;
      estimated_corpus: number;
      wealth_gain: number;
      real_purchasing_power: number;
    }>;
  };
  advisory_rationale?: string;
  market_context?: string;
  tax_optimization_memo?: {
    regime: string;
    equity_ltcg_rate: string;
    equity_stcg_rate: string;
    tax_harvesting_strategy: string;
    debt_taxation: string;
    elss_lockin: string;
  };
  rebalancing_protocol?: {
    tolerance_band_pct: number;
    review_cadence: string;
    execution_strategy: string;
    glide_path: string;
  };
  multi_scenario_projections?: {
    expected_cagr: number;
    bull_cagr: number;
    bear_cagr: number;
    terminal_base: number;
    terminal_bull: number;
    terminal_bear: number;
    total_invested: number;
    unified_trajectory: Array<{
      year: number;
      monthly_sip: number;
      total_invested: number;
      corpus_base: number;
      corpus_bull: number;
      corpus_bear: number;
      real_purchasing_power: number;
    }>;
  };
}

export interface MFSIPCalculateRequest {
  monthly_sip: number;
  expected_cagr_pct: number;
  years: number;
  step_up_pct: number;
  inflation_pct: number;
}

export interface MFSIPCalculateResponse {
  monthly_sip: number;
  expected_cagr_pct: number;
  years: number;
  step_up_pct: number;
  inflation_pct: number;
  total_invested: number;
  estimated_corpus: number;
  estimated_gain: number;
  wealth_multiplier: number;
  trajectory: Array<{
    year: number;
    monthly_sip: number;
    total_invested: number;
    estimated_corpus: number;
    wealth_gain: number;
    real_purchasing_power: number;
  }>;
}

export interface MFSwitchOption {
  target_scheme_code: number;
  target_scheme_name: string;
  fund_house: string;
  category: string;
  crisil_rating: number;
  expense_ratio: number;
  trailing_3y_cagr: number;
  downside_capture?: number | null;
  overlap_with_current_pct: number;
  comparison_advantage: string;
  execution_modes: {
    full_switch: string;
    pause_and_redirect: string;
    partial_switch: string;
  };
}

export interface MFActiveSIPDiagnostic {
  sip_id: string;
  scheme_code: number;
  scheme_name: string;
  category: string;
  monthly_amount: number;
  sip_day: number;
  start_date: string;
  end_date?: string;
  status: string;
  step_up_pct: number;
  installments_count: number;
  total_invested: number;
  current_value: number;
  profit: number;
  xirr_pct?: number | null;
  expected_installments?: number;
  actual_installments?: number;
  skipped_installments_count?: number;
  regularity_pct?: number;
  fund_cagr_3y?: number | null;
  benchmark_cagr_3y?: number;
  benchmark_name?: string;
  rolling_alpha_pct?: number | null;
  downside_capture?: number | null;
  expense_ratio?: number | null;
  health_status?: string;
  action_type?: string;
  action_headline?: string;
  recommendation?: string;
  cashflow_diagnostic_memo?: string;
  trailing_3y_cagr?: number | null;
  switch_options?: MFSwitchOption[];
  next_sip_date?: string;
  days_until_next_sip?: number;
  current_month_checkin_status?: 'PAID' | 'SKIPPED' | 'PENDING' | 'UPCOMING';
  due_date_current_month?: string;
}

export interface MFSIPCheckinItem {
  checkin_id: string;
  sip_id: string;
  scheme_code: number;
  scheme_name: string;
  category: string;
  monthly_amount: number;
  sip_day: number;
  due_date: string;
  month_label: string;
  status: 'PENDING' | 'PAID' | 'SKIPPED';
  is_overdue: boolean;
  days_ago: number;
  question: string;
}

export interface MFSIPCheckinHistoryItem {
  checkin_id: string;
  sip_id: string;
  scheme_code: number;
  scheme_name: string;
  category: string;
  due_date: string;
  status: 'PAID' | 'SKIPPED';
  confirmed_date?: string | null;
  amount: number;
}

export interface MFPortfolioResponse {
  portfolio_id: string;
  portfolio_name?: string;
  notes?: string | null;
  last_saved_at?: string | null;
  total_invested: number;
  current_value: number;
  unrealized_profit: number;
  absolute_return_pct: number;
  portfolio_xirr_pct?: number | null;
  monthly_sip_run_rate: number;
  active_sips_count: number;
  closed_sips_count: number;
  active_sips: MFActiveSIPDiagnostic[];
  pending_checkins?: MFSIPCheckinItem[];
  checkin_history?: MFSIPCheckinHistoryItem[];
  closed_sips: Array<{
    sip_id: string;
    scheme_code: number;
    scheme_name: string;
    category: string;
    monthly_amount: number;
    sip_day: number;
    start_date: string;
    end_date?: string;
    status: string;
    step_up_pct: number;
    installments_count: number;
    total_invested: number;
    current_value: number;
    profit: number;
    xirr_pct?: number | null;
    post_mortem?: {
      stopped_date?: string;
      months_inactive: number;
      retained_units: number;
      retained_valuation: number;
      verdict: string;
    };
    action_options?: {
      resume?: {
        action: string;
        title: string;
        description: string;
        suggested_amount: number;
        suggested_sip_day: number;
        rationale: string;
      };
      reallocate?: {
        action: string;
        title: string;
        description: string;
        rationale: string;
        options: Array<{
          target_scheme_code: number;
          target_scheme_name: string;
          fund_house: string;
          category: string;
          crisil_rating: number;
          expense_ratio: number;
          trailing_3y_cagr: number;
          downside_capture: number;
          overlap_with_current_pct: number;
          comparison_advantage: string;
          execution_modes: {
            full_switch: string;
            pause_and_redirect: string;
            partial_switch: string;
          };
        }>;
      };
      let_compound?: {
        action: string;
        title: string;
        description: string;
        rationale: string;
        expected_cagr_pct: number;
        projections: {
          years_1: number;
          years_3: number;
          years_5: number;
          years_10: number;
        };
      };
    };
  }>;
  scheme_holdings: Array<{
    scheme_code: number;
    scheme_name: string;
    category: string;
    total_units: number;
    invested_amount: number;
    current_value: number;
    current_nav: number;
    unrealized_profit: number;
    abs_return_pct: number;
    xirr_pct?: number | null;
  }>;
  asset_allocation: Record<string, number>;
  overlap_analysis: {
    schemes?: string[];
    pairwise_overlap_matrix?: Record<string, Record<string, number>>;
    average_overlap_pct?: number;
    high_overlap_warning?: boolean;
    common_holdings?: Array<{
      stock: string;
      funds_holding_count: number;
      fund_weights: Record<string, number>;
      avg_weight_pct: number;
    }>;
  };
}

export interface MFPortfolioHealthResponse {
  portfolio_id: string;
  health_score: number;
  verdict: string;
  rating_label: string;
  current_valuation?: number;
  portfolio_xirr?: number | null;
  pillars: {
    alpha_performance: number;
    downside_protection?: number;
    overlap_efficiency: number;
    diversification: number;
    sip_discipline: number;
  };
  cash_flow_discipline_analysis?: {
    total_active_sips: number;
    total_skipped_installments: number;
    average_regularity_pct: number;
    verdict: string;
    insight: string;
  };
  actionable_switches?: Array<{
    scheme_name: string;
    scheme_code: number;
    category: string;
    current_value: number;
    monthly_amount: number;
    action_type: string;
    action_headline: string;
    recommendation: string;
    cashflow_diagnostic_memo: string;
    switch_options: MFSwitchOption[];
  }>;
  holding_diagnostics?: MFActiveSIPDiagnostic[];
  predictive_scenarios: Array<{
    horizon_years: number;
    base_case_13pct: number;
    bull_case_16pct: number;
    bear_case_8pct: number;
  }>;
  actionable_recommendations: string[];
}


