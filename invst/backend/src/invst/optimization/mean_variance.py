"""Constrained Mean-Variance Portfolio Optimizer.

Optimizes portfolio allocations under realistic investment constraints:
- Target holdings: top 8 names
- Single-stock maximum cap: <= 25% (0.25)
- Sector maximum cap: <= 40% (0.40)
- Fully invested: sum(w_i) == 1.0
- Long-only: w_i >= 0

Objective:
    maximize   w^T mu - lambda * w^T Sigma w
    subject to sum(w_i) = 1
               0 <= w_i <= 0.25
               sum_{i in sector s} w_i <= 0.40
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date

import numpy as np

try:
    from scipy.optimize import minimize
except ImportError:
    minimize = None

from invst.data_access import PointInTimeDataAccess

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    weights: dict[str, float]  # symbol -> weight (e.g. 0.125)
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    status: str
    sector_allocations: dict[str, float]


def estimate_returns_and_covariance(
    pit: PointInTimeDataAccess,
    symbols: list[str],
    lookback_days: int = 756,  # ~3 years of trading days
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Estimate expected returns vector (mu) and covariance matrix (Sigma)."""
    asof = pit.asof
    start_date = date.fromordinal(asof.toordinal() - int(lookback_days * 1.5))

    price_series: dict[str, dict[str, float]] = {}
    valid_symbols: list[str] = []

    for sym in symbols:
        rows = pit.get_price_series(sym, start=start_date, end=asof)
        if len(rows) >= 60:
            price_series[sym] = {r.trade_date: r.close for r in rows}
            valid_symbols.append(sym)

    if len(valid_symbols) < 2:
        # Fallback for synthetic / minimal data
        n = len(symbols)
        return np.ones(n) * 0.12, np.eye(n) * 0.04, symbols

    # Find common trading dates
    common_dates = sorted(set.intersection(*(set(price_series[s].keys()) for s in valid_symbols)))
    if len(common_dates) < 30:
        n = len(valid_symbols)
        return np.ones(n) * 0.12, np.eye(n) * 0.04, valid_symbols

    # Build price matrix
    prices = np.array([[price_series[s][d] for s in valid_symbols] for d in common_dates])
    # Compute weekly returns to reduce micro-structure noise
    weekly_prices = prices[::5]
    if len(weekly_prices) < 10:
        weekly_prices = prices

    returns = (weekly_prices[1:] - weekly_prices[:-1]) / weekly_prices[:-1]

    # Annualize mu and Sigma (52 weeks/year)
    periods_per_year = 52 if len(prices) > len(weekly_prices) * 2 else 252
    mu = np.mean(returns, axis=0) * periods_per_year
    sigma = np.cov(returns, rowvar=False) * periods_per_year

    # Ensure positive semi-definiteness with shrinkage
    sigma = sigma + np.eye(len(valid_symbols)) * 1e-4

    return mu, sigma, valid_symbols


def optimize_portfolio(
    symbols: list[str],
    sector_map: dict[str, str],
    mu: np.ndarray,
    sigma: np.ndarray,
    target_holdings: int = 8,
    max_stock_weight: float = 0.25,
    max_sector_weight: float = 0.40,
    risk_aversion: float = 1.0,
    risk_free_rate: float = 0.065,
) -> OptimizationResult:
    """Solve constrained mean-variance optimization using SLSQP."""
    n = len(symbols)
    if n == 0:
        return OptimizationResult({}, 0.0, 0.0, 0.0, "empty", {})

    # If symbols count exceeds target_holdings, select top names by Sharpe or composite
    if n > target_holdings:
        # Sort by Sharpe or individual mu/sigma
        vols = np.sqrt(np.diag(sigma))
        sharpes = (mu - risk_free_rate) / np.maximum(vols, 1e-4)
        top_indices = np.argsort(sharpes)[::-1][:target_holdings]
        symbols = [symbols[i] for i in top_indices]
        mu = mu[top_indices]
        sigma = sigma[np.ix_(top_indices, top_indices)]
        n = len(symbols)

    # Initial equal weights
    w0 = np.ones(n) / n

    # Objective: Minimize 0.5 * risk_aversion * w^T Sigma w - w^T mu
    def objective(w: np.ndarray) -> float:
        port_var = float(np.dot(w.T, np.dot(sigma, w)))
        port_ret = float(np.dot(w, mu))
        return 0.5 * risk_aversion * port_var - port_ret

    def objective_grad(w: np.ndarray) -> np.ndarray:
        return risk_aversion * np.dot(sigma, w) - mu

    # Constraints
    # 1. sum(w) = 1.0
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    # 2. Sector cap constraints: sum_{i in sector} w_i <= max_sector_weight
    sectors = sorted({sector_map.get(s, "diversified") for s in symbols})
    for sec in sectors:
        sec_mask = np.array(
            [1.0 if sector_map.get(s, "diversified") == sec else 0.0 for s in symbols]
        )
        constraints.append(
            {
                "type": "ineq",
                "fun": lambda w, m=sec_mask: max_sector_weight - np.dot(w, m),
            }
        )

    # Bounds: 0 <= w_i <= max_stock_weight
    bounds = [(0.0, max_stock_weight) for _ in range(n)]

    # If n < 1 / max_stock_weight, loosen max_stock_weight so sum(w) == 1 is feasible
    if n * max_stock_weight < 1.0:
        eff_cap = 1.0 / n
        bounds = [(0.0, eff_cap) for _ in range(n)]

    res = minimize(
        objective,
        w0,
        jac=objective_grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-7},
    )

    if res.success:
        raw_weights = res.x
        status = "optimal"
    else:
        logger.warning(
            f"Optimization did not converge ({res.message}), falling back to capped equal weights"
        )
        raw_weights = w0
        status = "fallback_equal_weight"

    # Clean small epsilon weights & renormalize
    raw_weights = np.maximum(0.0, raw_weights)
    if np.sum(raw_weights) > 0:
        weights_norm = raw_weights / np.sum(raw_weights)
    else:
        weights_norm = np.ones(n) / n

    weights_dict = {symbols[i]: round(float(weights_norm[i]), 4) for i in range(n)}

    exp_ret = float(np.dot(weights_norm, mu))
    exp_var = float(np.dot(weights_norm.T, np.dot(sigma, weights_norm)))
    exp_vol = math.sqrt(max(0.0, exp_var))
    sharpe = (exp_ret - risk_free_rate) / max(exp_vol, 1e-4)

    # Sector allocations
    sec_alloc: dict[str, float] = {}
    for s, w in weights_dict.items():
        sec = sector_map.get(s, "diversified")
        sec_alloc[sec] = round(sec_alloc.get(sec, 0.0) + w, 4)

    return OptimizationResult(
        weights=weights_dict,
        expected_return=round(exp_ret, 4),
        expected_volatility=round(exp_vol, 4),
        sharpe_ratio=round(sharpe, 3),
        status=status,
        sector_allocations=sec_alloc,
    )
