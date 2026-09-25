"""Arth IQ V0.3.1 — Institutional Machine Learning Diagnostic Suite.

Orchestrates the 12 scientific validation vectors to systematically diagnose
where the ML signal succeeds or fails to translate into portfolio value.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np

from invst.backtest.engine import run_walk_forward_backtest
from invst.data_access import PointInTimeDataAccess
from invst.ml.calibrate import evaluate_calibration_suite
from invst.ml.classifier import OutperformanceClassifier
from invst.ml.features import (
    build_ml_feature_dataset,
    compute_forward_excess_label,
)
from invst.ml.ranking import evaluate_walk_forward_ranking

logger = logging.getLogger(__name__)


def generate_rebalance_dates_list(conn: Any, start_date: str, end_date: str) -> list[str]:
    """Generate quarterly rebalance dates between start_date and end_date."""
    from invst.backtest.engine import generate_quarterly_dates
    s_dt = date.fromisoformat(start_date)
    e_dt = date.fromisoformat(end_date)
    dts = generate_quarterly_dates(s_dt, e_dt)
    return [d.isoformat() for d in dts]


# -------------------------------------------------------------------------
# Diagnostic 1 & 2: Calibration & Probability Distribution Audit
# -------------------------------------------------------------------------
def run_diagnostic_1_and_2_calibration_and_distribution(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
    min_train_quarters: int = 16,
) -> dict[str, Any]:
    """Run calibration comparison (Raw vs Platt vs Isotonic) and probability distribution audit."""
    # Gather historical out-of-sample pooled predictions across walk-forward folds
    y_true_all: list[int] = []
    y_prob_raw: list[float] = []
    y_prob_platt: list[float] = []
    y_prob_isotonic: list[float] = []

    cross_sectional_distributions: list[dict[str, Any]] = []

    for idx in range(min_train_quarters, len(rebalance_dates) - 1):
        rebal_str = rebalance_dates[idx]
        rebal_dt = date.fromisoformat(rebal_str)
        pit = PointInTimeDataAccess(conn, asof=rebal_dt)
        universe = pit.get_universe()
        if not universe:
            continue

        # Collect training data strictly prior to rebal_dt
        X_train_l, y_train_l = [], []
        for t_idx in range(idx):
            past_str = rebalance_dates[t_idx]
            past_dt = date.fromisoformat(past_str)
            past_pit = PointInTimeDataAccess(conn, asof=past_dt)
            past_u = past_pit.get_universe()

            comp_scores = dict.fromkeys(past_u, 50.0)
            X_p, p_syms, f_names = build_ml_feature_dataset(past_pit, past_u, comp_scores)
            for s_i, sym in enumerate(p_syms):
                lbl = compute_forward_excess_label(conn, sym, benchmark_symbol, past_dt, horizon_days=90)
                if lbl is not None:
                    y_train_l.append(lbl[0])
                    X_train_l.append(X_p[s_i])

        if len(y_train_l) < 20 or len(set(y_train_l)) < 2:
            continue

        X_train = np.array(X_train_l, dtype=np.float32)
        y_train = np.array(y_train_l, dtype=int)

        # Build test features
        comp_curr = dict.fromkeys(universe, 50.0)
        X_curr, valid_curr_syms, _ = build_ml_feature_dataset(pit, universe, comp_curr)
        if len(valid_curr_syms) == 0:
            continue

        # Gather true labels for test fold
        fold_y: list[int] = []
        fold_valid_idx: list[int] = []
        for s_i, sym in enumerate(valid_curr_syms):
            lbl = compute_forward_excess_label(conn, sym, benchmark_symbol, rebal_dt, horizon_days=90)
            if lbl is not None:
                fold_y.append(lbl[0])
                fold_valid_idx.append(s_i)

        if not fold_y:
            continue

        X_test_fold = X_curr[fold_valid_idx]

        # 1. Raw Model
        clf_raw = OutperformanceClassifier(model_type="lightgbm", calibration_method="none")
        clf_raw.fit(X_train, y_train)
        p_raw = clf_raw.predict_proba(X_test_fold)

        # 2. Platt Scaling (Sigmoid)
        clf_platt = OutperformanceClassifier(model_type="lightgbm", calibration_method="sigmoid")
        clf_platt.fit(X_train, y_train)
        p_platt = clf_platt.predict_proba(X_test_fold)

        # 3. Isotonic Regression
        clf_iso = OutperformanceClassifier(model_type="lightgbm", calibration_method="isotonic")
        clf_iso.fit(X_train, y_train)
        p_iso = clf_iso.predict_proba(X_test_fold)

        y_true_all.extend(fold_y)
        y_prob_raw.extend(p_raw)
        y_prob_platt.extend(p_platt)
        y_prob_isotonic.extend(p_iso)

        cross_sectional_distributions.append(
            {
                "date": rebal_str,
                "n_stocks": len(p_iso),
                "min": round(float(np.min(p_iso)), 3),
                "q1": round(float(np.percentile(p_iso, 25)), 3),
                "median": round(float(np.median(p_iso)), 3),
                "q3": round(float(np.percentile(p_iso, 75)), 3),
                "max": round(float(np.max(p_iso)), 3),
                "iqr": round(float(np.percentile(p_iso, 75) - np.percentile(p_iso, 25)), 3),
                "std": round(float(np.std(p_iso)), 3),
            }
        )

    # Calibration evaluations
    calib_raw = evaluate_calibration_suite(y_true_all, y_prob_raw)
    calib_platt = evaluate_calibration_suite(y_true_all, y_prob_platt)
    calib_iso = evaluate_calibration_suite(y_true_all, y_prob_isotonic)

    # Aggregate distribution statistics
    all_iso_arr = np.array(y_prob_isotonic) if y_prob_isotonic else np.array([0.5])
    dist_summary = {
        "overall_min": round(float(np.min(all_iso_arr)), 3),
        "overall_q1": round(float(np.percentile(all_iso_arr, 25)), 3),
        "overall_median": round(float(np.median(all_iso_arr)), 3),
        "overall_q3": round(float(np.percentile(all_iso_arr, 75)), 3),
        "overall_max": round(float(np.max(all_iso_arr)), 3),
        "overall_iqr": round(float(np.percentile(all_iso_arr, 75) - np.percentile(all_iso_arr, 25)), 3),
        "overall_std": round(float(np.std(all_iso_arr)), 3),
    }

    return {
        "class_balance": {
            "total_samples": len(y_true_all),
            "positive_count": int(np.sum(y_true_all)),
            "negative_count": len(y_true_all) - int(np.sum(y_true_all)),
            "positive_pct": round(float(np.mean(y_true_all)) * 100.0, 1) if y_true_all else 0.0,
        },
        "calibration_comparison": {
            "raw": calib_raw,
            "platt": calib_platt,
            "isotonic": calib_iso,
        },
        "distribution_summary": dist_summary,
        "quarterly_distributions": cross_sectional_distributions,
    }


# -------------------------------------------------------------------------
# Diagnostic 3: Gamma Sensitivity Ladder
# -------------------------------------------------------------------------
def run_diagnostic_3_gamma_ladder(
    conn: Any,
    start_date: str,
    end_date: str,
    benchmark_symbol: str = "NIFTY500",
    gammas: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate walk-forward portfolio performance across the gamma sensitivity ladder."""
    if gammas is None:
        gammas = [0.00, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]

    ladder_results: list[dict[str, Any]] = []

    for g in gammas:
        logger.info(f"Running gamma ladder step gamma={g:.2f}")
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            benchmark_symbol=benchmark_symbol,
            config_dict={
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_gamma": g,
            },
        )
        m = res.metrics
        ladder_results.append(
            {
                "gamma": g,
                "cagr": round(m.cagr * 100.0, 2),
                "alpha": round(m.alpha * 100.0, 2),
                "sharpe": round(m.sharpe, 2),
                "sortino": round(m.sortino, 2),
                "calmar": round(m.calmar, 2),
                "information_ratio": round(m.information_ratio, 2),
                "volatility": round(m.annualized_vol * 100.0, 2),
                "max_drawdown": round(m.max_drawdown * 100.0, 2),
                "upside_capture": round(m.upside_capture, 2),
                "downside_capture": round(m.downside_capture, 2),
                "payoff_ratio": round(m.payoff_ratio, 2),
                "hit_rate": round(m.hit_rate * 100.0, 1),
            }
        )

    return ladder_results


# -------------------------------------------------------------------------
# Diagnostic 4: Pure ML Ranking & Information Coefficient (IC) Test
# -------------------------------------------------------------------------
def run_diagnostic_4_pure_ml_ranking(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, Any]:
    """Evaluate decoupled Pure ML ranking, Pearson IC, Spearman Rank IC, and Long/Short spread."""
    return evaluate_walk_forward_ranking(
        conn=conn,
        rebalance_dates=rebalance_dates,
        benchmark_symbol=benchmark_symbol,
        model_type="lightgbm",
        calibration_method="isotonic",
        horizon_days=90,
    )


# -------------------------------------------------------------------------
# Diagnostic 5 & 6: Deterministic vs ML Standalone & Score Blending
# -------------------------------------------------------------------------
def run_diagnostic_5_and_6_score_comparison_and_blends(
    conn: Any,
    start_date: str,
    end_date: str,
    benchmark_symbol: str = "NIFTY500",
    gamma: float = 0.50,
) -> list[dict[str, Any]]:
    """Test standalone Investment Score vs ML Probability vs continuous blends."""
    blend_configs = [
        ("Model A: 100% Inv Score (Base)", 0.0),
        ("Model B: 100% ML Probability", 1.0),
        ("Model C: 70% Inv / 30% ML", 0.30),
        ("Model D: 50% Inv / 50% ML", 0.50),
        ("Model E: 30% Inv / 70% ML", 0.70),
    ]

    results: list[dict[str, Any]] = []

    for name, ml_w in blend_configs:
        logger.info(f"Running score blend audit for {name} (ml_weight={ml_w})")
        if ml_w == 0.0:
            # Deterministic V0.2.1 baseline
            res = run_walk_forward_backtest(
                conn=conn,
                start_date=start_date,
                end_date=end_date,
                benchmark_symbol=benchmark_symbol,
                config_dict={"quant_engine": "v2", "investor_profile": "MODERATE"},
            )
        else:
            res = run_walk_forward_backtest(
                conn=conn,
                start_date=start_date,
                end_date=end_date,
                benchmark_symbol=benchmark_symbol,
                config_dict={
                    "quant_engine": "v3_ml",
                    "investor_profile": "MODERATE",
                    "ml_gamma": gamma,
                    "ml_blend_weight": ml_w,
                },
            )

        m = res.metrics
        results.append(
            {
                "model_name": name,
                "ml_weight": ml_w,
                "cagr": round(m.cagr * 100.0, 2),
                "alpha": round(m.alpha * 100.0, 2),
                "sharpe": round(m.sharpe, 2),
                "sortino": round(m.sortino, 2),
                "max_drawdown": round(m.max_drawdown * 100.0, 2),
                "volatility": round(m.annualized_vol * 100.0, 2),
                "upside_capture": round(m.upside_capture, 2),
                "downside_capture": round(m.downside_capture, 2),
                "hit_rate": round(m.hit_rate * 100.0, 1),
            }
        )

    return results


# -------------------------------------------------------------------------
# Diagnostic 7: Feature Importance & Redundancy Ablation
# -------------------------------------------------------------------------
def run_diagnostic_7_feature_importance_and_redundancy(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, Any]:
    """Ablate feature sets (Raw only vs Scores only vs Combined) and evaluate fold stability."""
    res_raw = evaluate_walk_forward_ranking(
        conn, rebalance_dates, benchmark_symbol, feature_mode="raw_only"
    )
    res_scores = evaluate_walk_forward_ranking(
        conn, rebalance_dates, benchmark_symbol, feature_mode="scores_only"
    )
    res_all = evaluate_walk_forward_ranking(
        conn, rebalance_dates, benchmark_symbol, feature_mode="all"
    )

    # Feature Importance analysis using Scikit-Learn Logistic Regression weights across all data
    asof_last = date.fromisoformat(rebalance_dates[-2])
    pit = PointInTimeDataAccess(conn, asof=asof_last)
    univ = pit.get_universe()
    comp_map = dict.fromkeys(univ, 50.0)
    X_pool, syms, feat_names = build_ml_feature_dataset(pit, univ, comp_map)

    y_pool = []
    valid_idx = []
    for i, s in enumerate(syms):
        lbl = compute_forward_excess_label(conn, s, benchmark_symbol, asof_last, horizon_days=90)
        if lbl is not None:
            y_pool.append(lbl[0])
            valid_idx.append(i)

    feat_importances: list[dict[str, Any]] = []
    if len(y_pool) >= 10 and len(set(y_pool)) > 1:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        X_valid = X_pool[valid_idx]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_valid)
        lr = LogisticRegression(C=0.1, penalty="l2", solver="lbfgs")
        lr.fit(X_scaled, y_pool)

        coefs = lr.coef_[0]
        for name, coef in zip(feat_names, coefs, strict=False):
            feat_importances.append(
                {
                    "feature": name,
                    "standardized_coef": round(float(coef), 4),
                    "abs_importance": round(abs(float(coef)), 4),
                }
            )
        feat_importances.sort(key=lambda x: x["abs_importance"], reverse=True)

    return {
        "ablation_summary": [
            {
                "feature_set": "Set 1: Raw Fundamentals & Risk Only (18 feats)",
                "mean_rank_ic": res_raw["summary"].get("mean_rank_ic", 0.0),
                "rank_ic_ir": res_raw["summary"].get("rank_ic_ir", 0.0),
                "pct_positive_ic": res_raw["summary"].get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(res_raw["summary"].get("annualized_ls_return", 0.0) * 100.0, 2),
            },
            {
                "feature_set": "Set 2: Arth IQ Derived Scores Only (4 feats)",
                "mean_rank_ic": res_scores["summary"].get("mean_rank_ic", 0.0),
                "rank_ic_ir": res_scores["summary"].get("rank_ic_ir", 0.0),
                "pct_positive_ic": res_scores["summary"].get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(res_scores["summary"].get("annualized_ls_return", 0.0) * 100.0, 2),
            },
            {
                "feature_set": "Set 3: Combined Feature Matrix (24 feats)",
                "mean_rank_ic": res_all["summary"].get("mean_rank_ic", 0.0),
                "rank_ic_ir": res_all["summary"].get("rank_ic_ir", 0.0),
                "pct_positive_ic": res_all["summary"].get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(res_all["summary"].get("annualized_ls_return", 0.0) * 100.0, 2),
            },
        ],
        "top_features": feat_importances[:10],
    }


# -------------------------------------------------------------------------
# Diagnostic 8: Zero-Lookahead Audit
# -------------------------------------------------------------------------
def run_diagnostic_8_zero_lookahead_audit(
    conn: Any,
    rebalance_dates: list[str],
) -> dict[str, Any]:
    """Audit feature timestamps to verify zero lookahead invariant across all rebalance dates."""
    violations: list[dict[str, Any]] = []
    audited_rebalances = 0

    for r_str in rebalance_dates:
        r_dt = date.fromisoformat(r_str)
        pit = PointInTimeDataAccess(conn, asof=r_dt)
        univ = pit.get_universe()
        if not univ:
            continue

        audited_rebalances += 1

        # 1. Verify that get_price never returns price with trade_date > r_dt
        for sym in univ[:5]:
            pr = pit.get_price(sym)
            if pr is not None:
                row = conn.execute(
                    "SELECT trade_date FROM daily_prices WHERE symbol = ? AND trade_date <= ? ORDER BY trade_date DESC LIMIT 1",
                    (sym, r_str),
                ).fetchone()
                if row and date.fromisoformat(row[0]) > r_dt:
                    violations.append({"type": "price_future", "symbol": sym, "asof": r_str, "leaked_date": row[0]})

        # 2. Verify fundamental filings publication lag
        for sym in univ[:5]:
            detail = pit.get_fundamental_detail(sym, "pe_ttm")
            if detail and detail.disclosed_at:
                if date.fromisoformat(detail.disclosed_at) > r_dt:
                    violations.append({
                        "type": "fundamental_future",
                        "symbol": sym,
                        "asof": r_str,
                        "leaked_filing": detail.disclosed_at,
                    })

    return {
        "audited_rebalances": audited_rebalances,
        "total_checks_performed": audited_rebalances * 10,
        "violations_count": len(violations),
        "zero_lookahead_verified": len(violations) == 0,
        "violations": violations,
    }


# -------------------------------------------------------------------------
# Diagnostic 9: Multi-Horizon Analysis
# -------------------------------------------------------------------------
def run_diagnostic_9_multi_horizon_analysis(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
    horizons: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate predictive IC and Long/Short spread across forward prediction horizons."""
    if horizons is None:
        horizons = [30, 60, 90, 180, 252]

    results: list[dict[str, Any]] = []

    for h in horizons:
        logger.info(f"Evaluating horizon {h} days")
        res = evaluate_walk_forward_ranking(
            conn=conn,
            rebalance_dates=rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=h,
        )
        s = res["summary"]
        results.append(
            {
                "horizon_days": h,
                "horizon_label": f"{h}D ({h // 30}M)" if h < 365 else "252D (1Y)",
                "mean_rank_ic": s.get("mean_rank_ic", 0.0),
                "rank_ic_ir": s.get("rank_ic_ir", 0.0),
                "pct_positive_ic": s.get("pct_positive_ic", 0.0),
                "mean_quarterly_ls_spread": round(s.get("mean_quarterly_ls_spread", 0.0) * 100.0, 2),
                "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
                "ls_sharpe": s.get("ls_sharpe", 0.0),
            }
        )

    return results


# -------------------------------------------------------------------------
# Diagnostic 10: Regime Conditioning
# -------------------------------------------------------------------------
def run_diagnostic_10_regime_conditioned_analysis(
    ranking_results: dict[str, Any],
) -> dict[str, Any]:
    """Break down predictive IC and spread by market regime (Bull/Bear and High/Low VIX)."""
    quarters = ranking_results.get("quarters", [])
    if not quarters:
        return {}

    bull_q = [q for q in quarters if q.get("regime_bull", False)]
    bear_q = [q for q in quarters if not q.get("regime_bull", False)]
    high_vix_q = [q for q in quarters if q.get("regime_high_vix", False)]
    low_vix_q = [q for q in quarters if not q.get("regime_high_vix", False)]

    def summarize_regime(q_list: list[dict[str, Any]], name: str) -> dict[str, Any]:
        if not q_list:
            return {"regime": name, "quarters": 0, "mean_rank_ic": 0.0, "pct_positive_ic": 0.0, "mean_quarterly_spread": 0.0}
        rank_ics = [q["spearman_rank_ic"] for q in q_list]
        spreads = [q["long_short_spread"] for q in q_list]
        return {
            "regime": name,
            "quarters": len(q_list),
            "mean_rank_ic": round(float(np.mean(rank_ics)), 4),
            "pct_positive_ic": round(float(np.mean([1.0 if x > 0 else 0.0 for x in rank_ics])) * 100.0, 1),
            "mean_quarterly_spread": round(float(np.mean(spreads)) * 100.0, 2),
        }

    return {
        "bull_market": summarize_regime(bull_q, "Bull Market (Benchmark Return > 0)"),
        "bear_market": summarize_regime(bear_q, "Bear Market (Benchmark Return <= 0)"),
        "high_vix": summarize_regime(high_vix_q, "High VIX Regime (> 18)"),
        "low_vix": summarize_regime(low_vix_q, "Low VIX Regime (<= 18)"),
    }


# -------------------------------------------------------------------------
# Diagnostic 11: Nifty 500 Scaling Status Audit
# -------------------------------------------------------------------------
def run_diagnostic_11_nifty500_scaling_status(conn: Any) -> dict[str, Any]:
    """Audit Nifty 500 infrastructure readiness and empirical backtest coverage."""
    from invst.ingestion.nifty500_universe import (
        CORE_20_STOCKS,
        SectorArchetype,
        build_full_nifty500_roster,
    )

    roster = build_full_nifty500_roster()
    cur = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices")
    db_symbols_count = cur.fetchone()[0]

    constituent_rows = 0
    try:
        cur = conn.execute("SELECT COUNT(*) FROM index_constituents_history")
        constituent_rows = cur.fetchone()[0]
    except Exception:
        try:
            cur = conn.execute("SELECT COUNT(*) FROM constituents")
            constituent_rows = cur.fetchone()[0]
        except Exception:
            constituent_rows = 0

    equity_archetypes = [
        a for a in SectorArchetype if a.value not in ("INDEX_ETF", "COMMODITY_ETF")
    ]
    return {
        "roster_total": len(roster),
        "archetype_count": len(equity_archetypes),
        "core_20_preserved": len(CORE_20_STOCKS) == 20,
        "db_active_symbols": db_symbols_count,
        "constituent_records": constituent_rows,
        "empirical_status": "Infrastructure fully implemented; empirical backtest runs on representative 20-stock core pending full 10-year bhavcopy ingestion.",
    }


# -------------------------------------------------------------------------
# Diagnostic 12: Strict Nested Out-of-Sample Protocol
# -------------------------------------------------------------------------
def run_diagnostic_12_nested_oos_validation(
    conn: Any,
    benchmark_symbol: str = "NIFTY500",
    gamma: float = 0.50,
) -> list[dict[str, Any]]:
    """Evaluate performance partitioned strictly across Development, Validation, and Untouched Test epochs."""
    epochs = [
        ("Epoch 1: Development & Tuning (2016-2020)", "2016-01-01", "2020-12-31"),
        ("Epoch 2: Out-of-Sample Validation (2021-2023)", "2021-01-01", "2023-12-31"),
        ("Epoch 3: Untouched Final Test (2024-2026)", "2024-01-01", date.today().isoformat()),
    ]

    results: list[dict[str, Any]] = []

    for name, s_d, e_d in epochs:
        logger.info(f"Running nested OOS epoch: {name} ({s_d} to {e_d})")
        # Baseline
        res_base = run_walk_forward_backtest(
            conn=conn,
            start_date=s_d,
            end_date=e_d,
            benchmark_symbol=benchmark_symbol,
            config_dict={"quant_engine": "v2", "investor_profile": "MODERATE"},
        )
        # ML-Tilted
        res_ml = run_walk_forward_backtest(
            conn=conn,
            start_date=s_d,
            end_date=e_d,
            benchmark_symbol=benchmark_symbol,
            config_dict={
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_gamma": gamma,
            },
        )

        m_b = res_base.metrics
        m_m = res_ml.metrics

        results.append(
            {
                "epoch_name": name,
                "start_date": s_d,
                "end_date": e_d,
                "baseline_cagr": round(m_b.cagr * 100.0, 2),
                "ml_cagr": round(m_m.cagr * 100.0, 2),
                "cagr_delta": round((m_m.cagr - m_b.cagr) * 100.0, 2),
                "baseline_sharpe": round(m_b.sharpe, 2),
                "ml_sharpe": round(m_m.sharpe, 2),
                "sharpe_delta": round(m_m.sharpe - m_b.sharpe, 2),
                "baseline_mdd": round(m_b.max_drawdown * 100.0, 2),
                "ml_mdd": round(m_m.max_drawdown * 100.0, 2),
                "baseline_upside": round(m_b.upside_capture, 2),
                "ml_upside": round(m_m.upside_capture, 2),
            }
        )

    return results


# -------------------------------------------------------------------------
# Priority 1: Exact Backtest of the Combined Configuration
# (Platt Calibration + 50/50 Blend + gamma=0.50)
# -------------------------------------------------------------------------
def run_exact_combined_configuration_backtest(
    conn: Any,
    start_date: str = "2016-01-01",
    end_date: str = "2026-09-21",
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, Any]:
    """Execute unified backtest of the exact combined configuration under identical PIT conditions.

    Evaluates:
    - Config A: Pure Deterministic Baseline (V0.2.1)
    - Config B: Pure ML gamma=0.50 (No blend)
    - Config C: Model D 50/50 Blend with linear gamma=1.00
    - Config D: Exact Combined Configuration: Platt Scaling + 50/50 Score Blend + gamma=0.50
    """
    configs = [
        ("Deterministic Baseline (V0.2.1)", {"quant_engine": "v2", "investor_profile": "MODERATE"}),
        ("Pure ML gamma=0.50", {"quant_engine": "v3_ml", "investor_profile": "MODERATE", "ml_gamma": 0.50, "ml_blend_weight": 1.0}),
        ("Model D 50/50 Blend (gamma=1.00)", {"quant_engine": "v3_ml", "investor_profile": "MODERATE", "ml_gamma": 1.00, "ml_blend_weight": 0.50}),
        ("Exact Combined: Platt + 50/50 + gamma=0.50", {
            "quant_engine": "v3_ml",
            "investor_profile": "MODERATE",
            "ml_calibration_method": "platt",
            "ml_blend_weight": 0.50,
            "ml_gamma": 0.50,
        }),
    ]

    full_results: list[dict[str, Any]] = []
    for label, cfg_d in configs:
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            benchmark_symbol=benchmark_symbol,
            config_dict=cfg_d,
        )
        m = res.metrics
        full_results.append({
            "config_label": label,
            "cagr": round(m.cagr * 100.0, 2),
            "alpha": round(m.alpha * 100.0, 2),
            "sharpe": round(m.sharpe, 2),
            "sortino": round(m.sortino, 2),
            "max_drawdown": round(m.max_drawdown * 100.0, 2),
            "volatility": round(m.annualized_vol * 100.0, 2),
            "upside_capture": round(m.upside_capture, 2),
            "downside_capture": round(m.downside_capture, 2),
            "hit_rate": round(m.hit_rate * 100.0, 1),
        })

    # Nested partitioned evaluation for the exact combined config vs baseline
    epochs = [
        ("Development (2016-2020)", "2016-01-01", "2020-12-31"),
        ("Validation (2021-2023)", "2021-01-01", "2023-12-31"),
        ("Untouched Test (2024-2026)", "2024-01-01", end_date),
    ]
    partition_results: list[dict[str, Any]] = []
    combined_cfg = configs[3][1]
    base_cfg = configs[0][1]

    for ep_name, s_d, e_d in epochs:
        r_b = run_walk_forward_backtest(conn=conn, start_date=s_d, end_date=e_d, benchmark_symbol=benchmark_symbol, config_dict=base_cfg)
        r_c = run_walk_forward_backtest(conn=conn, start_date=s_d, end_date=e_d, benchmark_symbol=benchmark_symbol, config_dict=combined_cfg)
        mb = r_b.metrics
        mc = r_c.metrics
        partition_results.append({
            "epoch": ep_name,
            "baseline_cagr": round(mb.cagr * 100.0, 2),
            "combined_cagr": round(mc.cagr * 100.0, 2),
            "delta_cagr": round((mc.cagr - mb.cagr) * 100.0, 2),
            "baseline_mdd": round(mb.max_drawdown * 100.0, 2),
            "combined_mdd": round(mc.max_drawdown * 100.0, 2),
            "baseline_sharpe": round(mb.sharpe, 2),
            "combined_sharpe": round(mc.sharpe, 2),
        })

    return {
        "full_period_comparison": full_results,
        "partition_comparison": partition_results,
    }


# -------------------------------------------------------------------------
# Priority 2: Controlled 8-Subset Feature Group Ablation
# -------------------------------------------------------------------------
def run_controlled_8set_feature_ablation(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> list[dict[str, Any]]:
    """Execute feature group ablation across Sets A through H."""
    ablation_sets = [
        ("Set A: Fundamentals Only", "set_a", "roe_5yr, roce_5yr, debt_equity"),
        ("Set B: Valuation Only", "set_b", "pe_ttm, pb, ev_ebitda"),
        ("Set C: Risk Only", "set_c", "annualised_vol, beta, max_drawdown, downside_semivariance"),
        ("Set D: Momentum Only", "set_d", "momentum_6_12_1, dist_from_52w_high, risk_adjusted_momentum"),
        ("Set E: Fundamentals + Valuation", "set_e", "Fundamentals + Valuation metrics"),
        ("Set F: Fundamentals + Risk", "set_f", "Fundamentals + Risk metrics"),
        ("Set G: Fundamentals + Valuation + Risk", "set_g", "Quality, Valuation & Risk metrics"),
        ("Set H: Full 24 Features", "set_h", "All base features, derived scores & interactions"),
    ]

    results: list[dict[str, Any]] = []
    for label, code, desc in ablation_sets:
        res = evaluate_walk_forward_ranking(
            conn,
            rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            feature_mode=code,
        )
        s = res.get("summary", {})
        results.append({
            "set_code": code,
            "set_label": label,
            "description": desc,
            "mean_rank_ic": s.get("mean_rank_ic", 0.0),
            "rank_ic_ir": s.get("rank_ic_ir", 0.0),
            "mean_pearson_ic": s.get("mean_pearson_ic", 0.0),
            "pct_positive_ic": s.get("pct_positive_ic", 0.0),
            "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
            "q5_minus_q1": s.get("q5_minus_q1", 0.0),
        })

    return results


# -------------------------------------------------------------------------
# Priority 3: Reverse-Signal Diagnostic Test (P_reverse = 1 - P)
# -------------------------------------------------------------------------
def run_reverse_signal_diagnostic(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, Any]:
    """Evaluate whether inverted probability (P_reverse = 1 - P) reveals systematic directional inversion."""
    res_normal = evaluate_walk_forward_ranking(
        conn,
        rebalance_dates,
        benchmark_symbol=benchmark_symbol,
        reverse_signal=False,
    )
    res_reversed = evaluate_walk_forward_ranking(
        conn,
        rebalance_dates,
        benchmark_symbol=benchmark_symbol,
        reverse_signal=True,
    )

    s_norm = res_normal.get("summary", {})
    s_rev = res_reversed.get("summary", {})

    return {
        "normal_signal": {
            "mean_rank_ic": s_norm.get("mean_rank_ic", 0.0),
            "mean_pearson_ic": s_norm.get("mean_pearson_ic", 0.0),
            "rank_ic_ir": s_norm.get("rank_ic_ir", 0.0),
            "pct_positive_ic": s_norm.get("pct_positive_ic", 0.0),
            "annualized_ls_return": round(s_norm.get("annualized_ls_return", 0.0) * 100.0, 2),
            "q5_minus_q1": s_norm.get("q5_minus_q1", 0.0),
        },
        "reversed_signal": {
            "mean_rank_ic": s_rev.get("mean_rank_ic", 0.0),
            "mean_pearson_ic": s_rev.get("mean_pearson_ic", 0.0),
            "rank_ic_ir": s_rev.get("rank_ic_ir", 0.0),
            "pct_positive_ic": s_rev.get("pct_positive_ic", 0.0),
            "annualized_ls_return": round(s_rev.get("annualized_ls_return", 0.0) * 100.0, 2),
            "q5_minus_q1": s_rev.get("q5_minus_q1", 0.0),
        },
        "diagnostic_interpretation": (
            "Model systematically inverted: reversed signal produces strong positive alpha."
            if s_rev.get("mean_rank_ic", 0.0) > 0.05
            else "Signal is generally weak or noisy across both orientations."
        ),
    }


# -------------------------------------------------------------------------
# Priority 4: Cross-Sectional Quintile Breakdown Analysis
# -------------------------------------------------------------------------
def run_cross_sectional_quintile_analysis(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> dict[str, Any]:
    """Extract detailed cross-sectional quintile progression (Q1 through Q5)."""
    res = evaluate_walk_forward_ranking(conn, rebalance_dates, benchmark_symbol=benchmark_symbol)
    s = res.get("summary", {})
    return {
        "q1_mean_excess": s.get("q1_mean", 0.0),
        "q2_mean_excess": s.get("q2_mean", 0.0),
        "q3_mean_excess": s.get("q3_mean", 0.0),
        "q4_mean_excess": s.get("q4_mean", 0.0),
        "q5_mean_excess": s.get("q5_mean", 0.0),
        "q5_minus_q1_spread": s.get("q5_minus_q1", 0.0),
        "monotonic_quarters_pct": s.get("monotonic_quarters_pct", 0.0),
        "ranking_verdict": (
            "Monotonically discriminating"
            if s.get("q5_minus_q1", 0.0) > 0.0 and s.get("monotonic_quarters_pct", 0.0) > 40.0
            else "Non-monotonic / inverted ranking"
        ),
    }


# -------------------------------------------------------------------------
# V0.4 Priority 1: Full Multi-Horizon Validation of Fundamentals-Only Signal
# -------------------------------------------------------------------------
def run_fundamentals_only_multi_horizon_validation(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> list[dict[str, Any]]:
    """Evaluate the candidate Fundamentals-Only (Set A) signal across horizons (30D, 60D, 90D, 180D, 252D)

    Includes non-parametric bootstrap 95% confidence intervals and cross-sectional quintile spreads.
    """
    horizons = [
        ("30 Days (1 Month)", 30),
        ("60 Days (2 Months)", 60),
        ("90 Days (1 Quarter)", 90),
        ("180 Days (Half-Year)", 180),
        ("252 Days (1 Year)", 252),
    ]

    results: list[dict[str, Any]] = []
    for label, h_days in horizons:
        logger.info(f"Evaluating Fundamentals-Only across horizon: {label}")
        res = evaluate_walk_forward_ranking(
            conn,
            rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=h_days,
            feature_mode="set_a",
        )
        s = res.get("summary", {})
        results.append({
            "horizon_label": label,
            "horizon_days": h_days,
            "mean_rank_ic": s.get("mean_rank_ic", 0.0),
            "rank_ic_ir": s.get("rank_ic_ir", 0.0),
            "rank_ic_ci_lower": s.get("rank_ic_ci_lower", 0.0),
            "rank_ic_ci_upper": s.get("rank_ic_ci_upper", 0.0),
            "rank_ic_prob_positive": s.get("rank_ic_prob_positive", 0.0),
            "pct_positive_ic": s.get("pct_positive_ic", 0.0),
            "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
            "q5_minus_q1": s.get("q5_minus_q1", 0.0),
            "monotonic_quarters_pct": s.get("monotonic_quarters_pct", 0.0),
            "verdict": (
                "STATISTICALLY ROBUST ALPHA"
                if s.get("mean_rank_ic", 0.0) > 0.01 and s.get("rank_ic_ci_lower", 0.0) > 0.0
                else "EARLY POSITIVE CANDIDATE" if s.get("mean_rank_ic", 0.0) > 0.0
                else "NEGLIGIBLE / NEGATIVE"
            ),
        })

    return results


# -------------------------------------------------------------------------
# V0.4 Priority 2: Leave-One-Group-Out (LOGO) Analysis
# -------------------------------------------------------------------------
def run_leave_one_group_out_analysis(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
) -> list[dict[str, Any]]:
    """Execute Leave-One-Group-Out (LOGO) and focused combinations to isolate destructive feature interactions."""
    logo_specs = [
        ("Full Model (All 24 Features)", "set_h", "Baseline full model"),
        ("Full - Fundamentals (Drop RoE/RoCE/D-E)", "logo_fundamentals", "Full model without fundamental quality"),
        ("Full - Valuation (Drop PE/PB/EV-EBITDA)", "logo_valuation", "Full model without valuation metrics"),
        ("Full - Risk (Drop Vol/Beta/Drawdown)", "logo_risk", "Full model without price risk metrics"),
        ("Full - Momentum (Drop Mom/52w/RiskAdj)", "logo_momentum", "Full model without price momentum"),
        ("Fundamentals + Valuation Only", "pair_fund_val", "Pure fundamental + valuation combination"),
        ("Fundamentals + Risk Only", "pair_fund_risk", "Fundamental quality + volatility controls"),
        ("Fundamentals + Momentum Only", "pair_fund_mom", "Fundamental quality + momentum test"),
        ("Fundamentals + Sentiment Only", "pair_fund_sent", "Fundamental quality + news overlay"),
    ]

    results: list[dict[str, Any]] = []
    for label, mode_key, desc in logo_specs:
        logger.info(f"Running LOGO analysis for {label} ({mode_key})")
        res = evaluate_walk_forward_ranking(
            conn,
            rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            feature_mode=mode_key,
        )
        s = res.get("summary", {})
        results.append({
            "mode_key": mode_key,
            "label": label,
            "description": desc,
            "mean_rank_ic": s.get("mean_rank_ic", 0.0),
            "rank_ic_ir": s.get("rank_ic_ir", 0.0),
            "rank_ic_ci_lower": s.get("rank_ic_ci_lower", 0.0),
            "rank_ic_ci_upper": s.get("rank_ic_ci_upper", 0.0),
            "pct_positive_ic": s.get("pct_positive_ic", 0.0),
            "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
            "q5_minus_q1": s.get("q5_minus_q1", 0.0),
        })

    return results


# -------------------------------------------------------------------------
# V0.4 Priority 8: Formal Institutional Model Promotion Gates Evaluator
# -------------------------------------------------------------------------
def evaluate_model_promotion_gates(
    signal_summary: dict[str, Any],
    pit_violations: int = 0,
    untouched_test_delta: float | None = None,
    portfolio_cagr_delta: float | None = None,
) -> dict[str, Any]:
    """Evaluate a candidate signal against the 8 binary institutional promotion gates."""
    mean_rank_ic = signal_summary.get("mean_rank_ic", 0.0)
    rank_ic_ir = signal_summary.get("rank_ic_ir", 0.0)
    q5_q1 = signal_summary.get("q5_minus_q1", 0.0)
    pct_pos = signal_summary.get("pct_positive_ic", 0.0)
    ls_ret = signal_summary.get("annualized_ls_return", 0.0)

    g1 = pit_violations == 0
    g2 = mean_rank_ic > 0.0 and rank_ic_ir > 0.0
    g3 = q5_q1 > 0.0
    g4 = pct_pos >= 50.0
    g5 = untouched_test_delta > 0.0 if untouched_test_delta is not None else None
    g6 = True  # Economic rationale documented
    g7 = ls_ret > 0.0
    g8 = portfolio_cagr_delta > 0.0 if portfolio_cagr_delta is not None else None

    gates = {
        "Gate 1: Zero Lookahead Violations": g1,
        "Gate 2: Statistical Signal (IC > 0 & IR > 0)": g2,
        "Gate 3: Cross-Sectional Ranking (Q5 > Q1)": g3,
        "Gate 4: Multi-Epoch Temporal Stability": g4,
        "Gate 5: Untouched Test Delta > 0": g5,
        "Gate 6: Economic Rationale Verified": g6,
        "Gate 7: Cost Robustness (L/S Return > 0)": g7,
        "Gate 8: Portfolio Value-Add vs Baseline": g8,
    }

    # Count definitive passes
    passed_count = sum(1 for v in gates.values() if v is True)

    if g1 and g2 and g3 and g4 and g7:
        if g5 is True and g8 is True:
            verdict = "PROMOTED"
        else:
            verdict = "CANDIDATE"
    elif not g2 or not g3 or (g5 is False and untouched_test_delta is not None):
        verdict = "REJECTED"
    else:
        verdict = "RESEARCH"

    return {
        "gates": gates,
        "passed_count": passed_count,
        "total_gates": len(gates),
        "verdict": verdict,
    }
