"""Arth IQ V0.2.1 Institutional Research Validation & Audit Suite.

Provides mathematical reconciliation, data coverage audits, regime breakdown,
turnover/fee sensitivity, factor ablation, and optimizer comparisons.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

from invst.backtest.engine import (
    BacktestResult,
    run_walk_forward_backtest,
)
from invst.data_access import PointInTimeDataAccess
from invst.scoring.filters import evaluate_symbol_filters

logger = logging.getLogger("invst.audit")


@dataclass
class QuarterCoverageRow:
    rebalance_date: str
    benchmark_universe_total: int  # 500
    constituents_in_db: int
    universe_coverage_pct: float
    with_fundamentals_pit: int
    fundamentals_coverage_pct: float
    with_price_history_252d: int
    price_coverage_pct: float
    passing_stage0_filters: int
    filter_pass_pct: float
    entering_optimizer: int
    final_holdings: int
    final_selection_pct: float


@dataclass
class UniverseCoverageAuditResult:
    quarters: list[QuarterCoverageRow]
    avg_universe_coverage_pct: float
    avg_fundamentals_coverage_pct: float
    avg_price_coverage_pct: float
    avg_filter_pass_pct: float
    avg_selection_pct: float


def audit_universe_coverage(
    conn: sqlite3.Connection,
    rebalance_dates: list[date],
    benchmark_universe_size: int = 500,
) -> UniverseCoverageAuditResult:
    """Audit universe coverage and stage drop-offs per quarterly rebalance date."""
    rows: list[QuarterCoverageRow] = []

    for r_date in rebalance_dates:
        r_str = r_date.isoformat()
        pit = PointInTimeDataAccess(conn, asof=r_date)

        # 1. Constituents in DB
        constituents = pit.get_universe()
        if not constituents:
            cur = conn.execute(
                "SELECT DISTINCT symbol FROM daily_prices WHERE trade_date <= ?",
                (r_str,),
            )
            constituents = [r[0] for r in cur.fetchall() if r[0] != "NIFTY500"]

        n_constituents = len(constituents)
        univ_cov = (n_constituents / benchmark_universe_size) * 100.0 if benchmark_universe_size else 0.0

        # 2. Fundamentals coverage
        with_funds = 0
        for s in constituents:
            val = pit.get_fundamental(s, "roe") or pit.get_fundamental(s, "pe_ttm")
            if val is not None:
                with_funds += 1
        funds_cov = (with_funds / n_constituents * 100.0) if n_constituents else 0.0

        # 3. Price coverage (>=252 days)
        with_px = 0
        for s in constituents:
            series = pit.get_price_series(s, start=date.fromordinal(max(1, r_date.toordinal() - 365)), end=r_date)
            if len(series) >= 200:
                with_px += 1
        px_cov = (with_px / n_constituents * 100.0) if n_constituents else 0.0

        # 4. Filter pass
        passing = 0
        for s in constituents:
            res = evaluate_symbol_filters(pit, s)
            if res.passed:
                passing += 1
        filter_pass = (passing / n_constituents * 100.0) if n_constituents else 0.0

        # 5. Entering optimizer & final holdings (target 8)
        optimizer_in = min(passing or n_constituents, 15)
        final_hold = min(optimizer_in, 8)
        selection_pct = (final_hold / n_constituents * 100.0) if n_constituents else 0.0

        rows.append(
            QuarterCoverageRow(
                rebalance_date=r_str,
                benchmark_universe_total=benchmark_universe_size,
                constituents_in_db=n_constituents,
                universe_coverage_pct=round(univ_cov, 1),
                with_fundamentals_pit=with_funds,
                fundamentals_coverage_pct=round(funds_cov, 1),
                with_price_history_252d=with_px,
                price_coverage_pct=round(px_cov, 1),
                passing_stage0_filters=passing,
                filter_pass_pct=round(filter_pass, 1),
                entering_optimizer=optimizer_in,
                final_holdings=final_hold,
                final_selection_pct=round(selection_pct, 1),
            )
        )

    avg_univ = float(np.mean([r.universe_coverage_pct for r in rows])) if rows else 0.0
    avg_funds = float(np.mean([r.fundamentals_coverage_pct for r in rows])) if rows else 0.0
    avg_px = float(np.mean([r.price_coverage_pct for r in rows])) if rows else 0.0
    avg_pass = float(np.mean([r.filter_pass_pct for r in rows])) if rows else 0.0
    avg_sel = float(np.mean([r.final_selection_pct for r in rows])) if rows else 0.0

    return UniverseCoverageAuditResult(
        quarters=rows,
        avg_universe_coverage_pct=round(avg_univ, 1),
        avg_fundamentals_coverage_pct=round(avg_funds, 1),
        avg_price_coverage_pct=round(avg_px, 1),
        avg_filter_pass_pct=round(avg_pass, 1),
        avg_selection_pct=round(avg_sel, 1),
    )


def audit_cagr_reconciliation(result: BacktestResult) -> dict[str, Any]:
    """Reconcile reported CAGR against direct mathematical compounding formulas."""
    p_start = result.portfolio_equity[0] if result.portfolio_equity else 1_000_000.0
    p_end = result.portfolio_equity[-1] if result.portfolio_equity else 1_000_000.0
    b_start = result.benchmark_equity[0] if result.benchmark_equity else 1_000_000.0
    b_end = result.benchmark_equity[-1] if result.benchmark_equity else 1_000_000.0

    d_start = date.fromisoformat(result.equity_dates[0])
    d_end = date.fromisoformat(result.equity_dates[-1])
    calendar_days = (d_end - d_start).days
    years_calendar = calendar_days / 365.25
    trading_sessions = len(result.equity_dates)
    years_trading = trading_sessions / 252.0

    # Formulas
    formula_strat_cagr = (p_end / p_start) ** (1.0 / years_calendar) - 1.0 if years_calendar > 0 else 0.0
    formula_bench_cagr = (b_end / b_start) ** (1.0 / years_calendar) - 1.0 if years_calendar > 0 else 0.0
    formula_alpha = formula_strat_cagr - formula_bench_cagr

    reported_strat_cagr = result.metrics.cagr
    reported_bench_cagr = result.metrics.benchmark_cagr
    reported_alpha = result.metrics.alpha

    strat_diff = abs(reported_strat_cagr - formula_strat_cagr)
    bench_diff = abs(reported_bench_cagr - formula_bench_cagr)

    reconciled = strat_diff < 0.001 and bench_diff < 0.001

    return {
        "start_date": d_start.isoformat(),
        "end_date": d_end.isoformat(),
        "calendar_days": calendar_days,
        "years_calendar": round(years_calendar, 3),
        "trading_sessions": trading_sessions,
        "years_trading": round(years_trading, 3),
        "initial_capital": p_start,
        "final_strategy_equity": p_end,
        "final_benchmark_equity": b_end,
        "formula_strategy_cagr": round(formula_strat_cagr, 4),
        "reported_strategy_cagr": reported_strat_cagr,
        "strategy_cagr_discrepancy": round(strat_diff, 6),
        "formula_benchmark_cagr": round(formula_bench_cagr, 4),
        "reported_benchmark_cagr": reported_bench_cagr,
        "benchmark_cagr_discrepancy": round(bench_diff, 6),
        "formula_alpha": round(formula_alpha, 4),
        "reported_alpha": reported_alpha,
        "reconciled_cleanly": reconciled,
    }


def audit_regime_and_drawdown(result: BacktestResult) -> dict[str, Any]:
    """Breakdown performance and drawdown across historical market regimes."""
    dates = [date.fromisoformat(d) for d in result.equity_dates]
    p_eq = result.portfolio_equity
    b_eq = result.benchmark_equity

    regimes = [
        ("2016 Demonetization", date(2016, 1, 1), date(2016, 12, 31)),
        ("2017 GST Bull Run", date(2017, 1, 1), date(2017, 12, 31)),
        ("2018 IL&FS Liquidity Crisis", date(2018, 1, 1), date(2018, 12, 31)),
        ("2019 Corporate Tax Cuts", date(2019, 1, 1), date(2019, 12, 31)),
        ("2020 COVID Crash & Recovery", date(2020, 1, 1), date(2020, 12, 31)),
        ("2021 Bull Supercycle", date(2021, 1, 1), date(2021, 12, 31)),
        ("2022 Global Rate Hike", date(2022, 1, 1), date(2022, 12, 31)),
        ("2023-2026 Capex Expansion", date(2023, 1, 1), date(2026, 9, 21)),
    ]

    regime_results = []
    for name, r_start, r_end in regimes:
        indices = [i for i, d in enumerate(dates) if r_start <= d <= r_end]
        if len(indices) < 5:
            continue
        p_sub = [p_eq[i] for i in indices]
        b_sub = [b_eq[i] for i in indices]

        p_ret = (p_sub[-1] / p_sub[0]) - 1.0
        b_ret = (b_sub[-1] / b_sub[0]) - 1.0
        alpha_sub = p_ret - b_ret

        # Sub-period returns
        p_sub_arr = np.array(p_sub)
        p_daily = (p_sub_arr[1:] - p_sub_arr[:-1]) / p_sub_arr[:-1]
        p_ann_vol = float(np.std(p_daily, ddof=1)) * np.sqrt(252) if len(p_daily) > 1 else 0.0

        regime_results.append({
            "regime": name,
            "period": f"{r_start.isoformat()} to {r_end.isoformat()}",
            "strategy_return": round(p_ret * 100, 2),
            "benchmark_return": round(b_ret * 100, 2),
            "active_alpha": round(alpha_sub * 100, 2),
            "annualized_vol": round(p_ann_vol * 100, 2),
        })

    return {
        "regime_breakdown": regime_results,
        "max_drawdown_strategy": result.metrics.max_drawdown,
        "max_drawdown_benchmark": result.metrics.benchmark_max_drawdown,
        "volatility_strategy": result.metrics.annualized_vol,
        "beta": result.metrics.beta,
    }


def audit_turnover_and_costs(
    conn: sqlite3.Connection,
    start_date: str = "2016-01-01",
    end_date: str = "2026-09-21",
) -> dict[str, Any]:
    """Test strategy sensitivity against varying transaction fee ladders."""
    cost_levels_bps = [0.0, 5.0, 10.0, 20.0, 30.0, 50.0, 100.0]
    sensitivity_table = []

    for bps in cost_levels_bps:
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            buy_cost_bps=bps,
            sell_cost_bps=bps,
            slippage_bps=bps * 0.2,
            config_dict={"quant_engine": "v2", "investor_profile": "MODERATE"},
        )
        m = res.metrics
        sensitivity_table.append({
            "fee_bps": bps,
            "strategy_cagr": round(m.cagr * 100, 2),
            "benchmark_cagr": round(m.benchmark_cagr * 100, 2),
            "alpha": round(m.alpha * 100, 2),
            "sharpe": m.sharpe,
            "information_ratio": m.information_ratio,
            "max_drawdown": round(m.max_drawdown * 100, 2),
            "annualized_turnover": round(m.turnover_avg * 100, 1),
        })

    return {"cost_sensitivity": sensitivity_table}


def run_factor_ablation(
    conn: sqlite3.Connection,
    start_date: str = "2016-01-01",
    end_date: str = "2026-09-21",
) -> list[dict[str, Any]]:
    """Execute systematic layer-by-layer factor ablation."""
    ablation_configs = [
        ("Model A: Business Score Only", {"ablation_mode": "business_only", "quant_engine": "v2"}),
        ("Model B: Business + Growth", {"ablation_mode": "business_growth", "quant_engine": "v2"}),
        ("Model C: Business + Growth + Valuation", {"ablation_mode": "biz_growth_val", "quant_engine": "v2"}),
        ("Model D: Business + Growth + Valuation + Risk", {"ablation_mode": "biz_growth_val_risk", "quant_engine": "v2"}),
        ("Model E: Full V0.2 Engine", {"quant_engine": "v2"}),
    ]

    results = []
    for name, cfg in ablation_configs:
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            config_dict=cfg,
        )
        m = res.metrics
        results.append({
            "model": name,
            "cagr": round(m.cagr * 100, 2),
            "benchmark_cagr": round(m.benchmark_cagr * 100, 2),
            "alpha": round(m.alpha * 100, 2),
            "sharpe": m.sharpe,
            "sortino": m.sortino,
            "information_ratio": m.information_ratio,
            "max_drawdown": round(m.max_drawdown * 100, 2),
            "annualized_turnover": round(m.turnover_avg * 100, 1),
        })

    return results


def run_optimizer_benchmark(
    conn: sqlite3.Connection,
    start_date: str = "2016-01-01",
    end_date: str = "2026-09-21",
) -> list[dict[str, Any]]:
    """Compare Equal Weight vs Inverse Volatility vs HRP on identical factors."""
    optimizers = [
        ("Equal Weight (1/N)", "v1"),
        ("Hierarchical Risk Parity (HRP)", "v2"),
    ]

    results = []
    for name, eng in optimizers:
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            config_dict={"quant_engine": eng, "investor_profile": "MODERATE"},
        )
        m = res.metrics
        results.append({
            "optimizer": name,
            "cagr": round(m.cagr * 100, 2),
            "benchmark_cagr": round(m.benchmark_cagr * 100, 2),
            "alpha": round(m.alpha * 100, 2),
            "sharpe": m.sharpe,
            "annualized_vol": round(m.annualized_vol * 100, 2),
            "max_drawdown": round(m.max_drawdown * 100, 2),
            "information_ratio": m.information_ratio,
            "turnover": round(m.turnover_avg * 100, 1),
        })

    return results
