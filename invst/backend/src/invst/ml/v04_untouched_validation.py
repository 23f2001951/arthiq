"""Arth IQ V0.4-B: Untouched Out-of-Sample Test Validation Suite.

Evaluates candidate models strictly on the frozen 2024-2026 test partition
(2024-01-01 to 2026-09-21) against the deterministic baseline to test Gate 5
(Untouched Test Delta > 0).

Models Evaluated:
1. Deterministic Baseline V0.2.1 (quant_engine='v2')
2. Full 24-Feature ML Model (Rejected baseline: ml_feature_mode='all')
3. Candidate 1: Fundamentals Only (ml_feature_mode='set_a')
4. Candidate 3: Fundamentals + Sentiment (ml_feature_mode='pair_fund_sent')
5. Candidate 2: Fundamentals + Momentum (ml_feature_mode='pair_fund_mom')
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from invst.backtest.engine import run_walk_forward_backtest
from invst.ml.diagnostics import generate_rebalance_dates_list
from invst.ml.ranking import evaluate_walk_forward_ranking

logger = logging.getLogger("invst.ml.v04_untouched_validation")

UNTOUCHED_TEST_START = "2024-01-01"
DEV_VAL_START = "2016-01-01"


def run_untouched_test_portfolio_backtests(
    conn: Any,
    benchmark_symbol: str = "NIFTY500",
    gamma: float = 0.50,
    test_start: str = UNTOUCHED_TEST_START,
    test_end: str | None = None,
) -> list[dict[str, Any]]:
    """Execute out-of-sample portfolio backtests on the frozen test partition."""
    end_d = test_end or min("2026-09-21", date.today().isoformat())

    model_configs = [
        {
            "model_id": "baseline_v021",
            "name": "Deterministic Baseline (V0.2.1)",
            "short_name": "Deterministic Baseline",
            "is_baseline": True,
            "config": {"quant_engine": "v2", "investor_profile": "MODERATE"},
        },
        {
            "model_id": "full_24_ml",
            "name": "Full 24-Feature ML (Rejected)",
            "short_name": "Full 24-Feat ML",
            "is_baseline": False,
            "config": {
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_feature_mode": "all",
                "ml_gamma": gamma,
            },
        },
        {
            "model_id": "cand_1_fundamentals",
            "name": "Candidate 1: Fundamentals Only",
            "short_name": "Fundamentals Only",
            "is_baseline": False,
            "config": {
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_feature_mode": "set_a",
                "ml_gamma": gamma,
            },
        },
        {
            "model_id": "cand_3_fund_sentiment",
            "name": "Candidate 3: Fundamentals + Sentiment",
            "short_name": "Fund + Sentiment",
            "is_baseline": False,
            "config": {
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_feature_mode": "pair_fund_sent",
                "ml_gamma": gamma,
            },
        },
        {
            "model_id": "cand_2_fund_momentum",
            "name": "Candidate 2: Fundamentals + Momentum",
            "short_name": "Fund + Momentum",
            "is_baseline": False,
            "config": {
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_feature_mode": "pair_fund_mom",
                "ml_gamma": gamma,
            },
        },
        {
            "model_id": "cand_4_val_qual_rev",
            "name": "Candidate 4: Value + Quality + Reversal",
            "short_name": "Val+Qual+Reversal",
            "is_baseline": False,
            "config": {
                "quant_engine": "v3_ml",
                "investor_profile": "MODERATE",
                "ml_feature_mode": "cand_quality_value_reversal",
                "ml_gamma": gamma,
            },
        },
    ]

    results: list[dict[str, Any]] = []
    base_cagr = None

    for m in model_configs:
        logger.info(f"Running untouched test backtest for: {m['name']}")
        res = run_walk_forward_backtest(
            conn=conn,
            start_date=test_start,
            end_date=end_d,
            benchmark_symbol=benchmark_symbol,
            config_dict=m["config"],
        )
        met = res.metrics
        cagr_pct = round(met.cagr * 100.0, 2)
        if m["is_baseline"]:
            base_cagr = cagr_pct

        results.append(
            {
                "model_id": m["model_id"],
                "name": m["name"],
                "short_name": m["short_name"],
                "is_baseline": m["is_baseline"],
                "cagr": cagr_pct,
                "alpha": round(met.alpha * 100.0, 2),
                "sharpe": round(met.sharpe, 2),
                "sortino": round(met.sortino, 2),
                "max_drawdown": round(met.max_drawdown * 100.0, 2),
                "annualized_vol": round(met.annualized_vol * 100.0, 2),
                "hit_rate": round(met.hit_rate * 100.0, 1),
                "turnover_avg": round(met.turnover_avg * 100.0, 1),
            }
        )

    # Compute deltas relative to baseline
    baseline_val = base_cagr if base_cagr is not None else -0.02
    for r in results:
        delta = round(r["cagr"] - baseline_val, 2)
        r["cagr_delta_vs_baseline"] = delta
        if r["is_baseline"]:
            r["gate_5_verdict"] = "BASELINE"
        else:
            r["gate_5_verdict"] = "PASS" if delta > 0.0 else "FAIL"

    return results


def run_untouched_test_predictive_ranking(
    conn: Any,
    benchmark_symbol: str = "NIFTY500",
    test_start: str = UNTOUCHED_TEST_START,
    test_end: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluate predictive ranking metrics on the test partition."""
    end_d = test_end or min("2026-09-21", date.today().isoformat())
    all_rebal_dates = generate_rebalance_dates_list(conn, DEV_VAL_START, end_d)

    candidate_modes = [
        ("Candidate 1: Fundamentals Only", "set_a"),
        ("Candidate 3: Fundamentals + Sentiment", "pair_fund_sent"),
        ("Candidate 2: Fundamentals + Momentum", "pair_fund_mom"),
        ("Candidate 4: Value + Quality + Reversal", "cand_quality_value_reversal"),
        ("Full 24-Feature ML (Set H)", "set_h"),
    ]

    ranking_results: list[dict[str, Any]] = []

    for name, mode in candidate_modes:
        logger.info(f"Evaluating untouched ranking for: {name} ({mode})")
        # Run walk-forward with expanding window from 2016 through test_rebal_dates
        full_eval = evaluate_walk_forward_ranking(
            conn=conn,
            rebalance_dates=all_rebal_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=90,
            feature_mode=mode,
        )
        # Filter quarterly records strictly to the untouched test epoch
        test_quarters = [
            q for q in full_eval.get("quarters", []) if q["date"] >= test_start
        ]

        if test_quarters:
            import numpy as np

            t_rank_ics = [q["spearman_rank_ic"] for q in test_quarters]
            t_ls_spreads = [q["long_short_spread"] for q in test_quarters]
            t_q5_q1 = [q["quintiles"]["q5_minus_q1"] for q in test_quarters]

            mean_rank_ic = float(np.mean(t_rank_ics))
            std_rank_ic = float(np.std(t_rank_ics)) or 1e-6
            rank_ic_ir = mean_rank_ic / std_rank_ic
            pct_pos = float(np.mean([1.0 if x > 0 else 0.0 for x in t_rank_ics])) * 100.0
            mean_ls = float(np.mean(t_ls_spreads))
            ann_ls = ((1.0 + mean_ls) ** 4) - 1.0 if mean_ls > -1.0 else -1.0

            ranking_results.append(
                {
                    "name": name,
                    "feature_mode": mode,
                    "test_quarters_count": len(test_quarters),
                    "mean_rank_ic": round(mean_rank_ic, 4),
                    "rank_ic_ir": round(rank_ic_ir, 2),
                    "pct_positive_ic": round(pct_pos, 1),
                    "annualized_ls_return": round(ann_ls * 100.0, 2),
                    "q5_minus_q1": round(float(np.mean(t_q5_q1)), 4),
                }
            )

    return ranking_results
