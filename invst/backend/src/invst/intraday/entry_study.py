"""
IIM Entry Study Harness & Rigorous Cost Framework.

Evaluates raw forward returns of standalone features BEFORE stop/target simulation.
- Measures forward returns over fixed horizons: 2, 4, 8, 16 bars (30m, 1h, 2h, 4h).
- Models round-trip transaction costs dynamically in basis points of turnover.
- Evaluates statistical significance (t-statistic, p-value, Information Ratio).
- Uses Day-Clustered Bootstrapping to account for cross-asset market correlation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("invst.intraday.entry_study")

# ---------------------------------------------------------------------------
# Dynamic Cost Model for Indian Intraday Equity
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndianIntradayCostModel:
    """
    Realistic Indian Intraday Equity Transaction Cost Structure.
    - Brokerage: ₹20 per executed order or 0.03%, whichever is lower.
    - STT (Securities Transaction Tax): 0.025% on sell side (intraday equity).
    - Exchange Transaction Charges (NSE): 0.00345% on turnover.
    - SEBI Turnover Fee: ₹10 per crore (0.0001%).
    - Stamp Duty: 0.003% on buy side.
    - GST: 18% on (Brokerage + Exchange Charges + SEBI).
    - Modelled Slippage: 2 bps per side (0.04% round trip for liquid F&O).
    """
    brokerage_per_order: float = 20.0  # ₹
    slippage_bps: float = 4.0          # 4 bps (0.04%) round trip
    statutory_bps: float = 3.5         # STT + Exch + SEBI + Stamp + GST ≈ 3.5 bps

    def calculate_round_trip_cost_bps(self, trade_value: float) -> float:
        """
        Total friction in basis points of position turnover (entry value).
        """
        if trade_value <= 0:
            return 8.0  # conservative baseline bps
        fixed_brokerage = min(self.brokerage_per_order * 2, trade_value * 0.0006)
        brokerage_bps = (fixed_brokerage / trade_value) * 10000.0
        return brokerage_bps + self.statutory_bps + self.slippage_bps

    def cost_in_r(self, entry_price: float, sl_distance: float, capital_risk_inr: float = 5000.0) -> float:
        """
        Convert realistic rupee transaction friction to R units.
        """
        if sl_distance <= 0:
            return float("inf")
        shares = int(capital_risk_inr / sl_distance)
        trade_value = shares * entry_price
        cost_bps = self.calculate_round_trip_cost_bps(trade_value)
        cost_inr = trade_value * (cost_bps / 10000.0)
        return cost_inr / capital_risk_inr


# ---------------------------------------------------------------------------
# Forward Return Feature Evaluation
# ---------------------------------------------------------------------------

@dataclass
class FeatureStudyResult:
    feature_name: str
    horizon_bars: int
    sample_size: int
    unique_days: int
    mean_return_bps: float
    median_return_bps: float
    std_return_bps: float
    t_statistic: float
    p_value: float
    hurdle_cost_bps: float
    net_mean_return_bps: float
    win_rate: float
    day_clustered_ci_lower_bps: float
    day_clustered_ci_upper_bps: float
    edge_detected: bool

    def summary(self) -> str:
        status = "✅ EDGE CONFIRMED" if self.edge_detected else "❌ NO EDGE"
        return (
            f"[{self.feature_name} | {self.horizon_bars} bars] {status}\n"
            f"  n = {self.sample_size} trades across {self.unique_days} days\n"
            f"  Gross Mean: {self.mean_return_bps:+.1f} bps | Hurdle Cost: {self.hurdle_cost_bps:.1f} bps\n"
            f"  Net Mean:   {self.net_mean_return_bps:+.1f} bps | Win Rate: {self.win_rate*100:.1f}%\n"
            f"  t-stat:     {self.t_statistic:.2f} (p = {self.p_value:.4f})\n"
            f"  90% Day-Clustered CI: [{self.day_clustered_ci_lower_bps:+.1f}, {self.day_clustered_ci_upper_bps:+.1f}] bps"
        )


def analyze_feature_forward_returns(
    df_signals: pd.DataFrame,
    feature_name: str,
    horizon_bars: int = 4,
    cost_model: IndianIntradayCostModel = IndianIntradayCostModel(),
    n_bootstrap: int = 1000,
) -> FeatureStudyResult:
    """
    Analyze forward returns for a specific boolean signal feature.
    
    df_signals must have columns:
      - 'signal': bool (True when entry condition triggered)
      - 'direction': 1 for LONG, -1 for SHORT
      - 'forward_ret': forward return over horizon (fractional, e.g. 0.005 = 50 bps)
      - 'date': calendar date (for day-clustering)
      - 'close': price for turnover estimation
    """
    triggered = df_signals[df_signals["signal"] == True].copy()
    n = len(triggered)
    
    # Baseline hurdle cost in bps
    hurdle_cost_bps = cost_model.calculate_round_trip_cost_bps(trade_value=100000.0)

    if n < 30:
        return FeatureStudyResult(
            feature_name=feature_name,
            horizon_bars=horizon_bars,
            sample_size=n,
            unique_days=triggered["date"].nunique() if n > 0 else 0,
            mean_return_bps=0.0,
            median_return_bps=0.0,
            std_return_bps=0.0,
            t_statistic=0.0,
            p_value=1.0,
            hurdle_cost_bps=hurdle_cost_bps,
            net_mean_return_bps=-hurdle_cost_bps,
            win_rate=0.0,
            day_clustered_ci_lower_bps=0.0,
            day_clustered_ci_upper_bps=0.0,
            edge_detected=False,
        )

    # Returns in basis points
    ret_bps = (triggered["forward_ret"] * triggered["direction"] * 10000.0).values
    dates = triggered["date"].values
    unique_dates = np.unique(dates)

    mean_bps = float(np.mean(ret_bps))
    median_bps = float(np.median(ret_bps))
    std_bps = float(np.std(ret_bps, ddof=1))
    t_stat, p_val = stats.ttest_1samp(ret_bps, popmean=hurdle_cost_bps)
    win_rate = float(np.mean(ret_bps > 0))
    net_mean = mean_bps - hurdle_cost_bps

    # Day-Clustered Bootstrap: resample by calendar day, not by trade
    day_indices = {d: np.where(dates == d)[0] for d in unique_dates}
    boot_means = []
    
    for _ in range(n_bootstrap):
        sampled_days = np.random.choice(unique_dates, size=len(unique_dates), replace=True)
        sampled_idx = np.concatenate([day_indices[d] for d in sampled_days])
        boot_means.append(float(np.mean(ret_bps[sampled_idx])))

    ci_lo = float(np.percentile(boot_means, 5.0))
    ci_hi = float(np.percentile(boot_means, 95.0))

    # Real statistical edge requires:
    # 1. Net mean > 0 (exceeds round-trip transaction costs)
    # 2. Day-clustered lower 90% CI > 0
    # 3. p-value < 0.05 vs hurdle cost
    edge_detected = (net_mean > 0) and (ci_lo > hurdle_cost_bps) and (p_val < 0.05) and (t_stat > 2.0)

    return FeatureStudyResult(
        feature_name=feature_name,
        horizon_bars=horizon_bars,
        sample_size=n,
        unique_days=len(unique_dates),
        mean_return_bps=round(mean_bps, 2),
        median_return_bps=round(median_bps, 2),
        std_return_bps=round(std_bps, 2),
        t_statistic=round(t_stat, 2),
        p_value=round(p_val, 4),
        hurdle_cost_bps=round(hurdle_cost_bps, 2),
        net_mean_return_bps=round(net_mean, 2),
        win_rate=round(win_rate, 4),
        day_clustered_ci_lower_bps=round(ci_lo, 2),
        day_clustered_ci_upper_bps=round(ci_hi, 2),
        edge_detected=edge_detected,
    )
