"""Walk-forward Quarterly Simulation Backtest Engine.

Implements rigorous anti-cheating, point-in-time portfolio backtesting:
- Walk-forward quarterly simulation loop
- Point-in-time universe, fundamentals, and prices via PointInTimeDataAccess
- Next-day execution fills with realistic transaction costs & slippage
- Daily mark-to-market performance accounting
- Records frozen config and execution history to database
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np

from invst.backtest.execution import execute_rebalance
from invst.backtest.metrics import BacktestMetrics, compute_backtest_metrics
from invst.data_access import PointInTimeDataAccess
from invst.ml.classifier import OutperformanceClassifier
from invst.ml.features import build_ml_feature_dataset, compute_forward_excess_label
from invst.ml.ranking import FEATURE_SUBSETS
from invst.optimization.hrp import optimize_hrp_portfolio
from invst.optimization.mean_variance import estimate_returns_and_covariance, optimize_portfolio
from invst.optimization.ml_hrp import optimize_ml_tilted_hrp_portfolio
from invst.scoring.composite import compute_composite_scores, select_shortlist_with_sector_caps
from invst.scoring.composite_v2 import compute_scorecards_v2

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Full backtest simulation output."""

    run_id: str
    metrics: BacktestMetrics
    equity_dates: list[str]
    portfolio_equity: list[float]
    benchmark_equity: list[float]
    rebalance_history: list[dict[str, Any]]


def generate_quarterly_dates(start_date: date, end_date: date) -> list[date]:
    """Generate quarterly rebalance dates (last day of Mar, Jun, Sep, Dec)."""
    dates: list[date] = []
    curr_year = start_date.year
    end_year = end_date.year
    today = date.today()
    effective_end = min(end_date, today)

    quarter_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]

    for yr in range(curr_year, end_year + 1):
        for month, day in quarter_ends:
            try:
                q_date = date(yr, month, day)
                if start_date <= q_date <= effective_end:
                    dates.append(q_date)
            except ValueError:
                continue

    return sorted(dates)


def run_walk_forward_backtest(
    conn: sqlite3.Connection,
    start_date: date | str = "2016-01-01",
    end_date: date | str = "2026-09-30",
    initial_capital: float = 1_000_000.0,
    benchmark_symbol: str = "NIFTY500",
    buy_cost_bps: float = 30.0,
    sell_cost_bps: float = 20.0,
    slippage_bps: float = 5.0,
    target_holdings: int = 8,
    config_dict: dict[str, Any] | None = None,
) -> BacktestResult:
    """Execute walk-forward quarterly simulation."""
    s_date = date.fromisoformat(start_date) if isinstance(start_date, str) else start_date
    e_date = date.fromisoformat(end_date) if isinstance(end_date, str) else end_date

    today = date.today()
    if e_date > today:
        logger.info(f"Clamping requested backtest end_date {e_date} to today's date {today}")
        e_date = today

    run_id = str(uuid.uuid4())
    logger.info(f"Starting Walk-Forward Backtest {run_id} ({s_date} -> {e_date})")

    rebalance_dates = generate_quarterly_dates(s_date, e_date)
    if not rebalance_dates:
        # Fallback to single start date if range is narrow
        rebalance_dates = [s_date]

    portfolio_equity: list[float] = []
    benchmark_equity: list[float] = []
    equity_dates: list[str] = []
    turnovers: list[float] = []
    rebalance_history: list[dict[str, Any]] = []

    current_portfolio_weights: dict[str, float] = {}
    current_cash = initial_capital
    current_shares: dict[str, int] = {}
    portfolio_val = initial_capital

    bench_initial_price = None

    for rebal_idx, r_date in enumerate(rebalance_dates):
        logger.info(f"Rebalance {rebal_idx + 1}/{len(rebalance_dates)} as of {r_date.isoformat()}")
        pit = PointInTimeDataAccess(conn, asof=r_date)

        # 1. Point-in-time universe
        univ = pit.get_universe()
        if not univ:
            # If constituents table is unpopulated, fallback to symbols with prices
            cur = conn.execute(
                "SELECT DISTINCT symbol FROM daily_prices WHERE trade_date <= ?",
                (r_date.isoformat(),),
            )
            univ = [r[0] for r in cur.fetchall() if r[0] != benchmark_symbol]

        if not univ:
            logger.warning(f"No symbols found in universe on {r_date.isoformat()}")
            continue

        # 2 & 3. Quant Scoring & Shortlisting (V1 or V2)
        engine_ver = config_dict.get("quant_engine", "v1").lower() if config_dict else "v1"

        if engine_ver in ["v3", "v3_ml", "ml"]:
            scorecards_v2 = compute_scorecards_v2(pit, symbols=univ)
            if not scorecards_v2:
                continue
            shortlist_v2 = scorecards_v2[:15]
            shortlist_symbols = [sc.symbol for sc in shortlist_v2]
            sector_map = {sc.symbol: sc.sector for sc in shortlist_v2}
            returns_map = {sc.symbol: sc.scenario.expected_return_pct for sc in shortlist_v2}

            # Build feature dataset for current candidates
            comp_map = {sc.symbol: sc.investment_score for sc in shortlist_v2}
            inv_map = {sc.symbol: sc.investment_score for sc in shortlist_v2}
            bus_map = {sc.symbol: sc.business_score for sc in shortlist_v2}
            gro_map = {sc.symbol: sc.growth_score for sc in shortlist_v2}

            X_curr, valid_cand_syms, feat_names = build_ml_feature_dataset(
                pit,
                shortlist_symbols,
                composite_scores_map=comp_map,
                investment_scores_map=inv_map,
                business_scores_map=bus_map,
                growth_scores_map=gro_map,
            )

            # Historical training data strictly from completed past rebalance windows
            X_hist_list: list[np.ndarray] = []
            y_hist_list: list[int] = []

            for past_d in rebalance_dates:
                if past_d >= r_date:
                    break
                # Forward 90-day window must have elapsed strictly on or before r_date
                if date.fromordinal(past_d.toordinal() + 90) <= r_date:
                    past_pit = PointInTimeDataAccess(conn, asof=past_d)
                    past_univ = past_pit.get_universe()
                    if not past_univ:
                        continue
                    past_sample = past_univ[:15]
                    X_past, p_syms, _ = build_ml_feature_dataset(
                        past_pit,
                        past_sample,
                        composite_scores_map=dict.fromkeys(past_sample, 50.0),
                    )
                    for idx, sym in enumerate(p_syms):
                        label_info = compute_forward_excess_label(
                            conn, sym, benchmark_symbol, past_d, horizon_days=90
                        )
                        if label_info is not None:
                            X_hist_list.append(X_past[idx])
                            y_hist_list.append(label_info[0])

            # Feature mode filtering (for ablation studies)
            feat_mode = config_dict.get("ml_feature_mode", "all") if config_dict else "all"
            if feat_mode == "raw_only":
                keep_idx = [i for i, name in enumerate(feat_names) if not name.endswith("_score")]
                feat_names = [feat_names[i] for i in keep_idx]
                X_curr = X_curr[:, keep_idx]
                X_hist_list = [row[keep_idx] for row in X_hist_list]
            elif feat_mode == "scores_only":
                keep_idx = [i for i, name in enumerate(feat_names) if name.endswith("_score")]
                feat_names = [feat_names[i] for i in keep_idx]
                X_curr = X_curr[:, keep_idx]
                X_hist_list = [row[keep_idx] for row in X_hist_list]
            elif feat_mode in FEATURE_SUBSETS:
                target_feats = set(FEATURE_SUBSETS[feat_mode])
                keep_idx = [i for i, name in enumerate(feat_names) if name in target_feats]
                if keep_idx:
                    feat_names = [feat_names[i] for i in keep_idx]
                    X_curr = X_curr[:, keep_idx]
                    X_hist_list = [row[keep_idx] for row in X_hist_list]

            model_kind = config_dict.get("ml_model_type", "lightgbm") if config_dict else "lightgbm"
            calib_kind = config_dict.get("ml_calibration_method", "isotonic") if config_dict else "isotonic"
            clf = OutperformanceClassifier(model_type=model_kind, calibration_method=calib_kind)

            if len(X_hist_list) >= 15 and len(set(y_hist_list)) > 1:
                clf.train(np.array(X_hist_list), np.array(y_hist_list), feature_names=feat_names)
                probs = clf.predict_proba(X_curr)
                prob_map = {s: float(p) for s, p in zip(valid_cand_syms, probs, strict=False)}
            else:
                prob_map = dict.fromkeys(shortlist_symbols, 0.5)

            # Score blending if requested (e.g. 70% Inv Score / 30% ML)
            blend_w = float(config_dict.get("ml_blend_weight", 1.0)) if config_dict else 1.0
            if blend_w < 1.0:
                blended_map = {}
                for s in shortlist_symbols:
                    norm_inv = min(1.0, max(0.0, inv_map.get(s, 50.0) / 100.0))
                    p = prob_map.get(s, 0.5)
                    blended_map[s] = (1.0 - blend_w) * norm_inv + blend_w * p
                prob_map = blended_map

            # 4. ML-Tilted HRP Optimization
            profile = config_dict.get("investor_profile", "MODERATE") if config_dict else "MODERATE"
            tilt_gamma = float(config_dict.get("ml_gamma", 1.0)) if config_dict else 1.0
            ml_hrp_res = optimize_ml_tilted_hrp_portfolio(
                pit,
                symbols=shortlist_symbols,
                sector_map=sector_map,
                ml_probabilities=prob_map,
                capital=portfolio_val,
                investor_profile=profile,
                gamma=tilt_gamma,
                expected_returns_map=returns_map,
            )
            target_weights = ml_hrp_res.weights
        elif engine_ver == "v2":
            scorecards_v2 = compute_scorecards_v2(pit, symbols=univ)
            if not scorecards_v2:
                continue
            shortlist_v2 = scorecards_v2[:15]
            shortlist_symbols = [sc.symbol for sc in shortlist_v2]
            sector_map = {sc.symbol: sc.sector for sc in shortlist_v2}
            returns_map = {sc.symbol: sc.scenario.expected_return_pct for sc in shortlist_v2}

            # 4. HRP Optimization (V2)
            profile = config_dict.get("investor_profile", "MODERATE") if config_dict else "MODERATE"
            hrp_res = optimize_hrp_portfolio(
                pit,
                symbols=shortlist_symbols,
                sector_map=sector_map,
                capital=portfolio_val,
                investor_profile=profile,
                expected_returns_map=returns_map,
            )
            target_weights = hrp_res.weights
        else:
            # V1 Legacy Pipeline
            scorecards = compute_composite_scores(pit, symbols=univ, filter_universe_first=False)
            if not scorecards:
                continue
            shortlist = select_shortlist_with_sector_caps(scorecards, shortlist_size=15)
            shortlist_symbols = [c.symbol for c in shortlist]
            sector_map = {c.symbol: c.sector for c in shortlist}

            mu, sigma, opt_symbols = estimate_returns_and_covariance(pit, shortlist_symbols)
            opt_res = optimize_portfolio(
                opt_symbols,
                sector_map,
                mu,
                sigma,
                target_holdings=target_holdings,
            )
            target_weights = opt_res.weights

        # 5. Next-day execution fills
        next_day_prices = pit.get_prices_multi(
            list(target_weights.keys()) + list(current_shares.keys())
        )

        # Mark-to-market portfolio value at rebalance
        holdings_val = sum(
            current_shares.get(s, 0) * next_day_prices.get(s, 0.0) for s in current_shares
        )
        portfolio_val = holdings_val + current_cash

        exec_res = execute_rebalance(
            target_weights=target_weights,
            current_weights=current_portfolio_weights,
            prices=next_day_prices,
            portfolio_value=portfolio_val,
            buy_cost_bps=buy_cost_bps,
            sell_cost_bps=sell_cost_bps,
            slippage_bps=slippage_bps,
        )

        turnovers.append(exec_res.turnover)
        current_portfolio_weights = exec_res.final_weights

        # Update share quantities & cash
        new_shares: dict[str, int] = {}
        spent = 0.0
        for o in exec_res.orders:
            if o.shares > 0 and o.action != "SELL":
                new_shares[o.symbol] = o.shares
                spent += o.shares * o.trade_price
            elif o.action == "SELL":
                pass
        current_shares = new_shares
        current_cash = max(0.0, portfolio_val - spent - exec_res.total_cost)

        # Record portfolio_history rows into DB
        for o in exec_res.orders:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_history (
                    run_id, asof_date, symbol, target_weight, action, shares_target, rationale_text, executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    r_date.isoformat(),
                    o.symbol,
                    o.target_weight,
                    o.action,
                    o.shares,
                    f"Composite rank shortlist target allocation {o.target_weight * 100:.1f}%",
                    0,
                ),
            )

        # 6. Mark to market until next rebalance (Trading Days Only)
        next_rebal_date = (
            rebalance_dates[rebal_idx + 1] if rebal_idx + 1 < len(rebalance_dates) else e_date
        )
        daily_holding_dates = [
            date.fromordinal(d)
            for d in range(r_date.toordinal() + 1, next_rebal_date.toordinal() + 1)
            if date.fromordinal(d).weekday() < 5 and date.fromordinal(d) <= today
        ]
        if not daily_holding_dates:
            daily_holding_dates = [min(r_date, today)]

        for d in daily_holding_dates:
            d_str = d.isoformat()
            d_pit = PointInTimeDataAccess(conn, asof=d)
            d_prices = d_pit.get_prices_multi(list(current_shares.keys()))

            h_val = sum(
                qty * d_prices.get(s, next_day_prices.get(s, 0.0))
                for s, qty in current_shares.items()
            )
            day_total = h_val + current_cash

            equity_dates.append(d_str)
            portfolio_equity.append(round(day_total, 2))

            # Benchmark mark-to-market
            b_price = d_pit.get_price(benchmark_symbol)
            if b_price:
                if bench_initial_price is None:
                    bench_initial_price = b_price
                b_val = initial_capital * (b_price / bench_initial_price)
            else:
                b_val = initial_capital
            benchmark_equity.append(round(b_val, 2))

        rebalance_history.append(
            {
                "rebalance_date": r_date.isoformat(),
                "target_weights": target_weights,
                "turnover": exec_res.turnover,
                "costs": exec_res.total_cost,
            }
        )

    conn.commit()

    # 7. Compute consolidated performance metrics
    metrics = compute_backtest_metrics(
        daily_dates=equity_dates,
        portfolio_equity=portfolio_equity,
        benchmark_equity=benchmark_equity,
        turnover_per_rebalance=turnovers,
        rebalance_count=len(rebalance_dates),
    )

    # 8. Record run into backtest_runs table
    frozen_cfg = json.dumps(
        config_dict
        or {
            "start_date": s_date.isoformat(),
            "end_date": e_date.isoformat(),
            "target_holdings": target_holdings,
            "buy_cost_bps": buy_cost_bps,
            "sell_cost_bps": sell_cost_bps,
            "slippage_bps": slippage_bps,
        }
    )

    conn.execute(
        """
        INSERT OR REPLACE INTO backtest_runs (
            run_id, started_at, finished_at, start_date, end_date, config_json,
            cagr, sharpe, max_drawdown, turnover_avg, benchmark_cagr, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            s_date.isoformat(),
            e_date.isoformat(),
            frozen_cfg,
            metrics.cagr,
            metrics.sharpe,
            metrics.max_drawdown,
            metrics.turnover_avg,
            metrics.benchmark_cagr,
            "completed",
        ),
    )
    conn.commit()

    logger.info(
        f"Backtest {run_id} completed: CAGR={metrics.cagr * 100:.1f}%, Sharpe={metrics.sharpe:.2f}, MaxDD={metrics.max_drawdown * 100:.1f}%"
    )

    return BacktestResult(
        run_id=run_id,
        metrics=metrics,
        equity_dates=equity_dates,
        portfolio_equity=portfolio_equity,
        benchmark_equity=benchmark_equity,
        rebalance_history=rebalance_history,
    )
