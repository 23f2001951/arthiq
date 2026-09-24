"""Stage 3: Risk Scoring.

Computes price-based and balance-sheet risk metrics:
- Annualized volatility (252 trading days) — 25%
- Beta vs. Nifty 500 (2 years) — 20%
- Max drawdown (3 years) — 25%
- Downside deviation (1 year) — 15%
- Altman's Z-score — 15% (higher is safer)

Risk score is subtractive: higher risk penalties reduce the score.
Final score is normalized to a 0–100 scale where 100 is safest.
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

from invst.data_access import PointInTimeDataAccess

logger = logging.getLogger(__name__)

DEFAULT_RISK_WEIGHTS = {
    "annualised_vol_252d": 0.25,
    "beta_nifty500_2yr": 0.20,
    "max_drawdown_3yr": 0.25,
    "downside_deviation_1yr": 0.15,
    "altman_z_score": 0.15,
}


def compute_price_risk_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, float | None]:
    """Compute risk statistics from daily price series ending at pit.asof."""
    asof = pit.asof
    start_3yr = date.fromordinal(asof.toordinal() - 3 * 365)
    prices = pit.get_price_series(symbol, start=start_3yr, end=asof)

    if not prices or len(prices) < 30:
        return {
            "annualised_vol_252d": None,
            "beta_nifty500_2yr": None,
            "max_drawdown_3yr": None,
            "downside_deviation_1yr": None,
        }

    closes = [p.close for p in prices]
    # Daily returns
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]

    # 1. 252d Volatility (1 year)
    ret_1yr = returns[-252:] if len(returns) >= 252 else returns
    mean_ret = sum(ret_1yr) / len(ret_1yr)
    var_1yr = sum((r - mean_ret) ** 2 for r in ret_1yr) / max(len(ret_1yr) - 1, 1)
    ann_vol = math.sqrt(var_1yr) * math.sqrt(252)

    # 2. Downside deviation (1 year, target return 0.0)
    downside_sq = [min(0.0, r) ** 2 for r in ret_1yr]
    downside_dev = math.sqrt(sum(downside_sq) / len(ret_1yr)) * math.sqrt(252)

    # 3. Max drawdown (3 years)
    running_max = closes[0]
    max_dd = 0.0
    for price in closes:
        if price > running_max:
            running_max = price
        dd = (price - running_max) / running_max
        if dd < max_dd:
            max_dd = dd  # negative number e.g. -0.25

    # 4. Beta vs. benchmark (2 years)
    start_2yr = date.fromordinal(asof.toordinal() - 2 * 365)
    bench_prices = pit.get_price_series(benchmark_symbol, start=start_2yr, end=asof)

    beta = 1.0
    if bench_prices and len(bench_prices) >= 60:
        bench_dict = {p.trade_date: p.close for p in bench_prices}
        matched_stock = []
        matched_bench = []
        for p in prices:
            if p.trade_date in bench_dict:
                matched_stock.append(p.close)
                matched_bench.append(bench_dict[p.trade_date])

        if len(matched_stock) >= 30:
            stock_ret = [
                (matched_stock[i] - matched_stock[i - 1]) / matched_stock[i - 1]
                for i in range(1, len(matched_stock))
            ]
            bench_ret = [
                (matched_bench[i] - matched_bench[i - 1]) / matched_bench[i - 1]
                for i in range(1, len(matched_bench))
            ]

            mean_s = sum(stock_ret) / len(stock_ret)
            mean_b = sum(bench_ret) / len(bench_ret)
            cov = sum(
                (stock_ret[i] - mean_s) * (bench_ret[i] - mean_b) for i in range(len(stock_ret))
            ) / (len(stock_ret) - 1)
            var_b = sum((b - mean_b) ** 2 for b in bench_ret) / (len(bench_ret) - 1)
            if var_b > 1e-8:
                beta = cov / var_b

    return {
        "annualised_vol_252d": round(ann_vol, 4),
        "beta_nifty500_2yr": round(beta, 3),
        "max_drawdown_3yr": round(max_dd, 4),
        "downside_deviation_1yr": round(downside_dev, 4),
    }


def score_risk_universe(
    pit: PointInTimeDataAccess,
    symbols: list[str],
    weights: dict[str, float] | None = None,
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, dict[str, Any]]:
    """Compute Risk scores for all symbols. Lower risk yields a higher score (safer)."""
    w = weights or DEFAULT_RISK_WEIGHTS
    results: dict[str, dict[str, Any]] = {}

    all_metrics = {}
    for sym in symbols:
        m = compute_price_risk_metrics(pit, sym, benchmark_symbol=benchmark_symbol)
        m["altman_z_score"] = pit.get_fundamental(sym, "altman_z_score") or 3.0  # safe baseline
        all_metrics[sym] = m

    # Cross-sectional normalisation
    # For vol, beta, max_drawdown (absolute), downside_dev: higher is riskiest
    # For altman_z: higher is safest
    for sym in symbols:
        m = all_metrics[sym]
        vol = m.get("annualised_vol_252d") or 0.30
        beta = m.get("beta_nifty500_2yr") or 1.0
        dd = abs(m.get("max_drawdown_3yr") or -0.25)
        ddev = m.get("downside_deviation_1yr") or 0.20
        alt_z = m.get("altman_z_score") or 3.0

        # Subtractive penalty scoring
        # Benchmark reference points: vol ~ 25%, beta ~ 1.0, dd ~ 25%, ddev ~ 18%, z ~ 3.0
        p_vol = max(0.0, (vol - 0.15) / 0.35)  # 0 at 15% vol, 1.0 at 50% vol
        p_beta = max(0.0, (beta - 0.7) / 1.0)  # 0 at 0.7 beta, 1.0 at 1.7 beta
        p_dd = max(0.0, (dd - 0.10) / 0.40)  # 0 at 10% dd, 1.0 at 50% dd
        p_ddev = max(0.0, (ddev - 0.10) / 0.30)  # 0 at 10% ddev, 1.0 at 40% ddev
        p_z = max(0.0, (3.0 - alt_z) / 2.0)  # 0 if z >= 3.0, 1.0 if z <= 1.0

        penalty = (
            w.get("annualised_vol_252d", 0.25) * min(1.0, p_vol)
            + w.get("beta_nifty500_2yr", 0.20) * min(1.0, p_beta)
            + w.get("max_drawdown_3yr", 0.25) * min(1.0, p_dd)
            + w.get("downside_deviation_1yr", 0.15) * min(1.0, p_ddev)
            + w.get("altman_z_score", 0.15) * min(1.0, p_z)
        )

        score = max(0.0, min(100.0, 100.0 * (1.0 - penalty)))

        results[sym] = {
            "risk_score": round(score, 2),
            "penalty": round(penalty, 3),
            "metrics": m,
        }

    return results
