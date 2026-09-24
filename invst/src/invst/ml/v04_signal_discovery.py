"""Arth IQ V0.4-A: Signal Discovery Deep Dive Suite.

Evaluates and benchmarks the 3 breakout signal candidates:
1. Candidate 1: Fundamentals Only (Set A: roe_5yr, roce_5yr, debt_equity)
2. Candidate 2: Fundamentals + Momentum (pair_fund_mom)
3. Candidate 3: Fundamentals + Sentiment (pair_fund_sent)

Conducts multi-horizon decay analysis (30D to 252D), non-parametric bootstrap
confidence intervals, quintile progression (Q1 -> Q5), and formal institutional
scorecarding against Promotion Gates 1-4, 6, and 7.
"""

from __future__ import annotations

import logging
from typing import Any

from invst.ml.diagnostics import evaluate_model_promotion_gates
from invst.ml.ranking import evaluate_walk_forward_ranking

logger = logging.getLogger("invst.ml.v04_signal_discovery")

CANDIDATE_SPECS: list[dict[str, Any]] = [
    {
        "candidate_id": "cand_1_fundamentals",
        "name": "Candidate 1: Fundamentals Only",
        "short_name": "Fundamentals Only",
        "feature_mode": "set_a",
        "features": ["roe_5yr", "roce_5yr", "debt_equity"],
        "economic_hypothesis": (
            "High capital efficiency (RoE, RoCE) combined with conservative "
            "debt-to-equity drives sustained fundamental compounding over quarterly cycles."
        ),
    },
    {
        "candidate_id": "cand_2_fund_momentum",
        "name": "Candidate 2: Fundamentals + Momentum",
        "short_name": "Fund + Momentum",
        "feature_mode": "pair_fund_mom",
        "features": [
            "roe_5yr",
            "roce_5yr",
            "debt_equity",
            "momentum_6_12_1",
            "dist_from_52w_high",
            "risk_adjusted_momentum",
        ],
        "economic_hypothesis": (
            "Fundamental quality filtered by intermediate 6-12M relative price strength "
            "captures compounding persistence while actively filtering out stagnant value traps."
        ),
    },
    {
        "candidate_id": "cand_3_fund_sentiment",
        "name": "Candidate 3: Fundamentals + Sentiment",
        "short_name": "Fund + Sentiment",
        "feature_mode": "pair_fund_sent",
        "features": ["roe_5yr", "roce_5yr", "debt_equity", "news_sentiment"],
        "economic_hypothesis": (
            "Fundamental balance sheet quality confirmed by non-negative media / earnings "
            "tone provides early downside shock resistance against governance surprises."
        ),
    },
]

HORIZON_SPECS: list[tuple[str, int]] = [
    ("30 Days (1 Month)", 30),
    ("60 Days (2 Months)", 60),
    ("90 Days (1 Quarter)", 90),
    ("180 Days (Half-Year)", 180),
    ("252 Days (1 Year)", 252),
]


def evaluate_candidate_across_horizons(
    conn: Any,
    rebalance_dates: list[str],
    candidate_spec: dict[str, Any],
    benchmark_symbol: str = "NIFTY500",
) -> list[dict[str, Any]]:
    """Evaluate a candidate signal across all 5 prediction horizons."""
    mode_key = candidate_spec["feature_mode"]
    name = candidate_spec["name"]
    horizon_results: list[dict[str, Any]] = []

    for label, h_days in HORIZON_SPECS:
        logger.info(f"[{name}] Evaluating horizon: {label}")
        res = evaluate_walk_forward_ranking(
            conn=conn,
            rebalance_dates=rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=h_days,
            feature_mode=mode_key,
        )
        s = res.get("summary", {})
        horizon_results.append(
            {
                "horizon_days": h_days,
                "horizon_label": label,
                "mean_rank_ic": s.get("mean_rank_ic", 0.0),
                "rank_ic_ir": s.get("rank_ic_ir", 0.0),
                "rank_ic_ci_lower": s.get("rank_ic_ci_lower", 0.0),
                "rank_ic_ci_upper": s.get("rank_ic_ci_upper", 0.0),
                "rank_ic_prob_positive": s.get("rank_ic_prob_positive", 0.0),
                "pct_positive_ic": s.get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
                "q5_minus_q1": s.get("q5_minus_q1", 0.0),
                "monotonic_quarters_pct": s.get("monotonic_quarters_pct", 0.0),
            }
        )

    return horizon_results


def evaluate_all_three_candidates(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
    primary_horizon: int = 90,
) -> dict[str, Any]:
    """Execute complete V0.4-A Signal Discovery evaluation across all 3 candidates."""
    candidates_data: list[dict[str, Any]] = []

    for spec in CANDIDATE_SPECS:
        logger.info(f"Executing deep dive for {spec['name']} ({spec['feature_mode']})")
        # 1. Primary 90D Walk-Forward Run
        primary_res = evaluate_walk_forward_ranking(
            conn=conn,
            rebalance_dates=rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=primary_horizon,
            feature_mode=spec["feature_mode"],
        )
        s = primary_res.get("summary", {})

        # 2. Multi-horizon ladder
        horizons = evaluate_candidate_across_horizons(
            conn=conn,
            rebalance_dates=rebalance_dates,
            candidate_spec=spec,
            benchmark_symbol=benchmark_symbol,
        )

        candidates_data.append(
            {
                "spec": spec,
                "primary_summary": s,
                "horizons": horizons,
                "raw_ranking_result": primary_res,
            }
        )

    # Generate comparative scorecard
    scorecard = generate_v04a_candidate_scorecard(candidates_data)

    return {
        "candidates": candidates_data,
        "scorecard": scorecard,
        "primary_horizon": primary_horizon,
    }


def generate_v04a_candidate_scorecard(
    candidates_data: list[dict[str, Any]],
    pit_violations: int = 0,
) -> list[dict[str, Any]]:
    """Evaluate candidate metrics against institutional promotion gates."""
    scorecard: list[dict[str, Any]] = []

    for item in candidates_data:
        spec = item["spec"]
        s = item["primary_summary"]
        gates_eval = evaluate_model_promotion_gates(
            s,
            pit_violations=pit_violations,
            untouched_test_delta=None,  # Pending V0.4-B
            portfolio_cagr_delta=None,  # Pending V0.4-D
        )

        scorecard.append(
            {
                "candidate_id": spec["candidate_id"],
                "name": spec["name"],
                "short_name": spec["short_name"],
                "feature_count": len(spec["features"]),
                "features": spec["features"],
                "mean_rank_ic": s.get("mean_rank_ic", 0.0),
                "rank_ic_ir": s.get("rank_ic_ir", 0.0),
                "rank_ic_ci": f"[{s.get('rank_ic_ci_lower', 0.0):+.4f}, {s.get('rank_ic_ci_upper', 0.0):+.4f}]",
                "prob_positive_ic": s.get("rank_ic_prob_positive", 0.0),
                "pct_positive_ic": s.get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
                "q5_minus_q1": s.get("q5_minus_q1", 0.0),
                "monotonic_quarters_pct": s.get("monotonic_quarters_pct", 0.0),
                "passed_gates": gates_eval["passed_count"],
                "total_gates": gates_eval["total_gates"],
                "verdict": gates_eval["verdict"],
                "gates": gates_eval["gates"],
            }
        )

    # Sort scorecard by Mean Rank IC descending
    scorecard.sort(key=lambda x: x["mean_rank_ic"], reverse=True)
    return scorecard
