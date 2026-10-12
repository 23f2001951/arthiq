// IIM — Intraday types
export type SignalType = 'LONG' | 'SHORT';
export type SignalStatus =
  | 'PENDING' | 'ENTRY_FILLED' | 'T1_HIT' | 'T2_HIT'
  | 'SL_HIT' | 'TRAILING_STOP_HIT' | 'EXPIRED' | 'MANUAL_EXIT';

export interface IntradaySignal {
  id: number;
  symbol: string;
  strategy_id: string;
  mode: 'live' | 'paper';
  signal_type: SignalType;
  entry_price: number | null;
  sl_price: number;
  target_1: number;
  target_2: number | null;
  sl_distance: number;
  reward_risk: number;
  atr_at_signal: number;
  confidence_score: number | null;
  pillars_met: string;          // JSON string: ["PRICE_TREND","VOLUME_OBV",...]
  regime: string;
  vwap_at_signal: number | null;
  todvol_ratio: number | null;
  rationale: string | null;
  current_status: SignalStatus;
  net_pnl_r: number | null;
  mfe_r: number | null;
  mae_r: number | null;
  created_at: string;
}

export interface IntradayStockItem {
  symbol: string;
  iss_score: number;
  liquidity_score: number | null;
  atr_pct_15m: number | null;
  momentum_score: number | null;
  todvol_score: number | null;
  level_setup_score: number | null;
  news_score: number | null;
  gap_type: string | null;
  iep_price: number | null;
  selected_at: string | null;
}

export interface Candle {
  candle_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema21?: number | null;
  supertrend?: number | null;
  supertrend_dir?: number | null;
  atr14?: number | null;
  vwap?: number | null;
  todvol_ratio?: number | null;
}

export interface ChartData {
  symbol: string;
  timeframe: string;
  candles: Candle[];
  pivot_levels: Record<string, number>;
  orb_high: number | null;
  orb_low: number | null;
  prev_day_high: number | null;
  prev_day_low: number | null;
}

export interface RegimeState {
  regime: 'TRENDING_BULL' | 'TRENDING_BEAR' | 'AMBIGUOUS' | 'RANGING' | 'AVOID';
  adx: number;
  india_vix: number;
  nifty_ema21_slope: number;
  sl_atr_adjustment: number;
  reason: string;
  timestamp: string;
}

export interface AccuracyReport {
  strategy_id: string;
  mode: string;
  total_trades: number;
  win_rate: number;
  avg_win_r: number;
  avg_loss_r: number;
  expectancy_net: number;
  profit_factor: number;
  max_drawdown_r: number;
  ci_lower: number;
  ci_upper: number;
  rolling_50_expectancy: number;
  auto_disabled: boolean;
  regime_breakdown: Record<string, { count: number; win_rate: number; expectancy: number }>;
  data_source_note: string;
  computed_at: string;
}

export type SSEEvent =
  | { type: 'SIGNAL_NEW'; data: IntradaySignal & { sizing?: Record<string, number> } }
  | { type: 'CANDLE_UPDATE'; symbol: string; data: Candle }
  | { type: 'SIGNAL_UPDATE'; signal_id: number; status: SignalStatus; exit_price?: number }
  | { type: 'HEARTBEAT'; ts: string };
