"""Pure ML Ranking and Information Coefficient (IC) Evaluation Module.

Decouples predictive signal validation from portfolio optimization (HRP)
by computing quarter-by-quarter cross-sectional Pearson IC, Spearman Rank IC,
and Long/Short quintile return spreads.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy import stats

from invst.data_access import PointInTimeDataAccess
from invst.ml.classifier import OutperformanceClassifier
from invst.ml.features import (
    build_ml_feature_dataset,
    compute_forward_excess_label,
    compute_forward_return,
)
from invst.scoring.sectors.normalization import normalize_cross_sectional_features_by_sector

logger = logging.getLogger(__name__)


def compute_information_coefficient(
    predictions: Sequence[float],
    realized_returns: Sequence[float],
) -> dict[str, float]:
    """Calculate Pearson IC and Spearman Rank IC between predictions and realized returns."""
    p = np.asarray(predictions, dtype=float)
    r = np.asarray(realized_returns, dtype=float)

    if len(p) < 3 or len(r) < 3 or len(p) != len(r):
        return {"pearson_ic": 0.0, "spearman_rank_ic": 0.0, "p_value": 1.0}

    # Handle constant arrays
    if np.std(p) < 1e-9 or np.std(r) < 1e-9:
        return {"pearson_ic": 0.0, "spearman_rank_ic": 0.0, "p_value": 1.0}

    pearson_r, p_val = stats.pearsonr(p, r)
    spearman_r, _ = stats.spearmanr(p, r)

    return {
        "pearson_ic": round(float(pearson_r), 4),
        "spearman_rank_ic": round(float(spearman_r), 4),
        "p_value": round(float(p_val), 4),
    }


def compute_long_short_spread(
    symbols: list[str],
    scores: Sequence[float],
    realized_returns: Sequence[float],
    top_quantile: float = 0.20,
    bottom_quantile: float = 0.20,
) -> dict[str, Any]:
    """Calculate Long-Short spread between top-quantile and bottom-quantile assets."""
    s_arr = np.asarray(scores, dtype=float)
    r_arr = np.asarray(realized_returns, dtype=float)
    n = len(symbols)

    if n < 4 or len(s_arr) != n or len(r_arr) != n:
        return {
            "long_return": 0.0,
            "short_return": 0.0,
            "long_short_spread": 0.0,
            "long_count": 0,
            "short_count": 0,
            "long_symbols": [],
            "short_symbols": [],
        }

    # Sort indices by score descending
    sorted_indices = np.argsort(-s_arr)

    k_top = max(1, int(np.ceil(n * top_quantile)))
    k_bottom = max(1, int(np.ceil(n * bottom_quantile)))

    top_idx = sorted_indices[:k_top]
    bottom_idx = sorted_indices[-k_bottom:]

    long_ret = float(np.mean(r_arr[top_idx]))
    short_ret = float(np.mean(r_arr[bottom_idx]))
    spread = long_ret - short_ret

    return {
        "long_return": round(long_ret, 4),
        "short_return": round(short_ret, 4),
        "long_short_spread": round(spread, 4),
        "long_count": len(top_idx),
        "short_count": len(bottom_idx),
        "long_symbols": [symbols[i] for i in top_idx],
        "short_symbols": [symbols[i] for i in bottom_idx],
    }


def compute_cross_sectional_quintiles(
    symbols: list[str],
    scores: Sequence[float],
    realized_returns: Sequence[float],
) -> dict[str, Any]:
    """Calculate 5-quintile bucket returns (Q1=lowest score to Q5=highest score) and Q5-Q1 spread."""
    s_arr = np.asarray(scores, dtype=float)
    r_arr = np.asarray(realized_returns, dtype=float)
    n = len(symbols)

    if n < 5 or len(s_arr) != n or len(r_arr) != n:
        return {
            "q1_mean": 0.0,
            "q2_mean": 0.0,
            "q3_mean": 0.0,
            "q4_mean": 0.0,
            "q5_mean": 0.0,
            "q5_minus_q1": 0.0,
            "is_monotonic": False,
        }

    # Sort indices by score ascending (Q1 lowest score -> Q5 highest score)
    sort_idx = np.argsort(s_arr)
    chunks = np.array_split(sort_idx, 5)
    q_means = [float(np.mean(r_arr[c])) if len(c) > 0 else 0.0 for c in chunks]

    is_monotonic = bool(all(q_means[i] <= q_means[i + 1] for i in range(len(q_means) - 1)))

    return {
        "q1_mean": round(q_means[0], 4),
        "q2_mean": round(q_means[1], 4),
        "q3_mean": round(q_means[2], 4),
        "q4_mean": round(q_means[3], 4),
        "q5_mean": round(q_means[4], 4),
        "q5_minus_q1": round(q_means[4] - q_means[0], 4),
        "is_monotonic": is_monotonic,
    }


def compute_bootstrap_confidence_interval(
    values: Sequence[float],
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    random_state: int = 42,
) -> dict[str, Any]:
    """Calculate non-parametric bootstrap confidence intervals and empirical probability of positive alpha."""
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n < 3:
        m = float(np.mean(arr)) if n > 0 else 0.0
        return {
            "mean": round(m, 4),
            "std": 0.0,
            "ci_lower": round(m, 4),
            "ci_upper": round(m, 4),
            "prob_positive": 1.0 if m > 0.0 else 0.0,
            "is_significant_positive": False,
        }

    rng = np.random.default_rng(random_state)
    boot_means = np.empty(n_bootstraps, dtype=float)
    for i in range(n_bootstraps):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    alpha_tail = (1.0 - ci) / 2.0
    lower_pct = alpha_tail * 100.0
    upper_pct = (1.0 - alpha_tail) * 100.0

    ci_lower = float(np.percentile(boot_means, lower_pct))
    ci_upper = float(np.percentile(boot_means, upper_pct))
    prob_pos = float(np.mean(boot_means > 0.0))

    return {
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(boot_means)), 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "prob_positive": round(prob_pos, 4),
        "is_significant_positive": bool(ci_lower > 0.0),
    }


# Atomic feature groups
FUND_FEATS = ["roe_5yr", "roce_5yr", "debt_equity"]
VAL_FEATS = ["pe_ttm", "pb", "ev_ebitda"]
RISK_FEATS = ["annualised_vol", "beta", "max_drawdown", "downside_semivariance"]
MOM_FEATS = ["momentum_6_12_1", "dist_from_52w_high", "risk_adjusted_momentum"]
MACRO_FEATS = ["news_sentiment", "macro_vix", "macro_vix_change_30d", "macro_usd_inr", "quality_to_valuation_ratio"]
SCORE_FEATS = ["composite_score", "investment_score", "business_score", "growth_score"]

ALL_24_FEATS = (
    SCORE_FEATS
    + FUND_FEATS
    + VAL_FEATS
    + RISK_FEATS
    + [
        "momentum_6_12_1",
        "dist_from_52w_high",
        "news_sentiment",
        "macro_vix",
        "macro_vix_change_30d",
        "macro_usd_inr",
        "quality_to_valuation_ratio",
        "risk_adjusted_momentum",
    ]
)

FEATURE_SUBSETS: dict[str, list[str]] = {
    # 8-Set Diagnostic Subsets
    "set_a": FUND_FEATS,
    "set_b": VAL_FEATS,
    "set_c": RISK_FEATS,
    "set_d": MOM_FEATS,
    "set_e": FUND_FEATS + VAL_FEATS,
    "set_f": FUND_FEATS + RISK_FEATS,
    "set_g": FUND_FEATS + VAL_FEATS + RISK_FEATS,
    "set_h": ALL_24_FEATS,
    # Leave-One-Group-Out (LOGO) Subsets
    "logo_fundamentals": [f for f in ALL_24_FEATS if f not in set(FUND_FEATS)],
    "logo_valuation": [f for f in ALL_24_FEATS if f not in set(VAL_FEATS)],
    "logo_risk": [f for f in ALL_24_FEATS if f not in set(RISK_FEATS)],
    "logo_momentum": [f for f in ALL_24_FEATS if f not in set(MOM_FEATS)],
    # Focused Pairwise Subsets
    "pair_fund_val": FUND_FEATS + VAL_FEATS,
    "pair_fund_risk": FUND_FEATS + RISK_FEATS,
    "pair_fund_mom": FUND_FEATS + MOM_FEATS,
    "pair_fund_sent": FUND_FEATS + ["news_sentiment"],
}


def evaluate_walk_forward_ranking(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
    model_type: str = "lightgbm",
    calibration_method: str = "isotonic",
    horizon_days: int = 90,
    min_train_quarters: int = 16,
    feature_mode: str = "all",  # "all", "raw_only", "scores_only", or "set_a" through "set_h"
    reverse_signal: bool = False,  # Priority 2: P_reverse = 1 - P
    sector_normalize: bool = False,  # V0.4-C: Sector archetype-relative standardization
) -> dict[str, Any]:
    """Run walk-forward expanding window predictive ranking test across rebalances.

    Decouples raw predictive capability from portfolio optimizer.
    """
    quarterly_records: list[dict[str, Any]] = []

    for idx in range(min_train_quarters, len(rebalance_dates) - 1):
        rebal_date_str = rebalance_dates[idx]
        from datetime import date
        rebal_dt = date.fromisoformat(rebal_date_str)
        pit = PointInTimeDataAccess(conn, asof=rebal_dt)
        universe = pit.get_universe()
        if not universe:
            continue

        # 1. Build training data strictly from prior rebalance dates
        X_train_list = []
        y_train_list = []

        for train_idx in range(idx):
            t_str = rebalance_dates[train_idx]
            t_dt = date.fromisoformat(t_str)
            pit_train = PointInTimeDataAccess(conn, asof=t_dt)
            univ_train = pit_train.get_universe()

            comp_scores: dict[str, float] = {}
            for sym in univ_train:
                row = conn.execute(
                    "SELECT investment_score FROM scorecards_v2_history WHERE symbol = ? AND asof_date <= ? ORDER BY asof_date DESC LIMIT 1",
                    (sym, t_str),
                ).fetchone()
                comp_scores[sym] = float(row[0]) if row and row[0] is not None else 50.0

            X_t, valid_syms, feat_names = build_ml_feature_dataset(pit_train, univ_train, comp_scores)
            if len(valid_syms) == 0:
                continue

            if sector_normalize and len(valid_syms) > 0:
                t_sec_map = pit_train.get_universe_with_sectors()
                X_t = normalize_cross_sectional_features_by_sector(X_t, valid_syms, t_sec_map)

            for s_idx, sym in enumerate(valid_syms):
                label_res = compute_forward_excess_label(
                    conn, sym, benchmark_symbol, t_dt, horizon_days=horizon_days
                )
                if label_res is not None:
                    y_train_list.append(label_res[0])
                    X_train_list.append(X_t[s_idx])

        if len(y_train_list) < 20 or len(np.unique(y_train_list)) < 2:
            continue

        X_train = np.array(X_train_list, dtype=np.float32)
        y_train = np.array(y_train_list, dtype=int)

        # Apply feature filtering if requested
        feat_indices = list(range(len(feat_names)))
        if feature_mode == "raw_only":
            feat_indices = [i for i, name in enumerate(feat_names) if not name.endswith("_score")]
        elif feature_mode == "scores_only":
            feat_indices = [i for i, name in enumerate(feat_names) if name.endswith("_score")]
        elif feature_mode.lower() in FEATURE_SUBSETS:
            target_feats = set(FEATURE_SUBSETS[feature_mode.lower()])
            feat_indices = [i for i, name in enumerate(feat_names) if name in target_feats]

        X_train = X_train[:, feat_indices]

        # 2. Fit classifier
        clf = OutperformanceClassifier(
            model_type=model_type,
            calibration_method=calibration_method,
        )
        clf.fit(X_train, y_train)

        # 3. Predict probabilities for current rebalance
        comp_scores_curr: dict[str, float] = {}
        for sym in universe:
            row = conn.execute(
                "SELECT investment_score FROM scorecards_v2_history WHERE symbol = ? AND asof_date <= ? ORDER BY asof_date DESC LIMIT 1",
                (sym, rebal_date_str),
            ).fetchone()
            comp_scores_curr[sym] = float(row[0]) if row and row[0] is not None else 50.0

        X_curr, valid_curr_syms, _ = build_ml_feature_dataset(pit, universe, comp_scores_curr)
        if len(valid_curr_syms) == 0:
            continue

        if sector_normalize and len(valid_curr_syms) > 0:
            curr_sec_map = pit.get_universe_with_sectors()
            X_curr = normalize_cross_sectional_features_by_sector(X_curr, valid_curr_syms, curr_sec_map)

        X_curr = X_curr[:, feat_indices]
        probs = clf.predict_proba(X_curr)

        # 4. Measure realized forward excess and raw returns
        realized_excess: list[float] = []
        realized_raw: list[float] = []
        eval_symbols: list[str] = []
        eval_probs: list[float] = []
        eval_scores: list[float] = []

        for s_i, sym in enumerate(valid_curr_syms):
            stock_ret = compute_forward_return(conn, sym, rebal_dt, horizon_days=horizon_days)
            bench_ret = compute_forward_return(conn, benchmark_symbol, rebal_dt, horizon_days=horizon_days)
            if stock_ret is not None and bench_ret is not None:
                realized_excess.append(stock_ret - bench_ret)
                realized_raw.append(stock_ret)
                eval_symbols.append(sym)
                p_val = float(probs[s_i])
                if reverse_signal:
                    p_val = 1.0 - p_val
                eval_probs.append(p_val)
                eval_scores.append(comp_scores_curr.get(sym, 50.0))

        if len(eval_symbols) < 4:
            continue

        # 5. Compute IC metrics & Quintiles
        ic_res = compute_information_coefficient(eval_probs, realized_excess)
        ls_res = compute_long_short_spread(eval_symbols, eval_probs, realized_excess, 0.20, 0.20)
        quint_res = compute_cross_sectional_quintiles(eval_symbols, eval_probs, realized_excess)

        # Also score IC for Investment/Composite Score for direct comparison
        score_ic_res = compute_information_coefficient(eval_scores, realized_excess)

        # Macro / Regime info
        vix = pit.get_price("INDIA_VIX") or 15.0
        bench_fwd = compute_forward_return(conn, benchmark_symbol, rebal_dt, horizon_days=horizon_days) or 0.0

        quarterly_records.append(
            {
                "date": rebal_date_str,
                "symbols_count": len(eval_symbols),
                "pearson_ic": ic_res["pearson_ic"],
                "spearman_rank_ic": ic_res["spearman_rank_ic"],
                "score_rank_ic": score_ic_res["spearman_rank_ic"],
                "long_return": ls_res["long_return"],
                "short_return": ls_res["short_return"],
                "long_short_spread": ls_res["long_short_spread"],
                "long_symbols": ls_res["long_symbols"],
                "short_symbols": ls_res["short_symbols"],
                "quintiles": quint_res,
                "prob_min": round(float(np.min(eval_probs)), 3),
                "prob_q1": round(float(np.percentile(eval_probs, 25)), 3),
                "prob_median": round(float(np.median(eval_probs)), 3),
                "prob_q3": round(float(np.percentile(eval_probs, 75)), 3),
                "prob_max": round(float(np.max(eval_probs)), 3),
                "prob_std": round(float(np.std(eval_probs)), 3),
                "vix": float(vix),
                "benchmark_return": float(bench_fwd),
                "regime_bull": bench_fwd > 0.0,
                "regime_high_vix": vix > 18.0,
            }
        )

    if not quarterly_records:
        return {"quarters": [], "summary": {}}

    # Compute aggregate summary statistics
    rank_ics = [q["spearman_rank_ic"] for q in quarterly_records]
    pearson_ics = [q["pearson_ic"] for q in quarterly_records]
    score_rank_ics = [q["score_rank_ic"] for q in quarterly_records]
    ls_spreads = [q["long_short_spread"] for q in quarterly_records]

    mean_rank_ic = float(np.mean(rank_ics))
    std_rank_ic = float(np.std(rank_ics)) or 1e-6
    rank_ic_ir = mean_rank_ic / std_rank_ic

    mean_pearson_ic = float(np.mean(pearson_ics))
    std_pearson_ic = float(np.std(pearson_ics)) or 1e-6
    pearson_ic_ir = mean_pearson_ic / std_pearson_ic

    mean_score_rank_ic = float(np.mean(score_rank_ics))
    pct_positive_ic = float(np.mean([1.0 if x > 0 else 0.0 for x in rank_ics])) * 100.0

    # Long-Short annualized metrics (assuming 4 quarters/year)
    mean_ls_quarterly = float(np.mean(ls_spreads))
    ann_ls_return = ((1.0 + mean_ls_quarterly) ** 4) - 1.0 if mean_ls_quarterly > -1.0 else -1.0
    ann_ls_vol = float(np.std(ls_spreads)) * 2.0  # sqrt(4)
    ls_sharpe = (ann_ls_return - 0.05) / max(0.01, ann_ls_vol) if ann_ls_vol > 0 else 0.0

    # Cross-sectional quintile summaries
    q1_mean = float(np.mean([q["quintiles"]["q1_mean"] for q in quarterly_records]))
    q2_mean = float(np.mean([q["quintiles"]["q2_mean"] for q in quarterly_records]))
    q3_mean = float(np.mean([q["quintiles"]["q3_mean"] for q in quarterly_records]))
    q4_mean = float(np.mean([q["quintiles"]["q4_mean"] for q in quarterly_records]))
    q5_mean = float(np.mean([q["quintiles"]["q5_mean"] for q in quarterly_records]))
    q5_minus_q1 = float(np.mean([q["quintiles"]["q5_minus_q1"] for q in quarterly_records]))
    mono_pct = float(np.mean([1.0 if q["quintiles"]["is_monotonic"] else 0.0 for q in quarterly_records])) * 100.0

    # Bootstrap statistical significance
    boot_rank_ic = compute_bootstrap_confidence_interval(rank_ics)
    boot_ls_spread = compute_bootstrap_confidence_interval(ls_spreads)
    boot_q5_q1 = compute_bootstrap_confidence_interval([q["quintiles"]["q5_minus_q1"] for q in quarterly_records])

    summary = {
        "total_quarters": len(quarterly_records),
        "mean_rank_ic": round(mean_rank_ic, 4),
        "std_rank_ic": round(std_rank_ic, 4),
        "rank_ic_ir": round(rank_ic_ir, 2),
        "rank_ic_ci_lower": boot_rank_ic["ci_lower"],
        "rank_ic_ci_upper": boot_rank_ic["ci_upper"],
        "rank_ic_prob_positive": boot_rank_ic["prob_positive"],
        "rank_ic_is_significant": boot_rank_ic["is_significant_positive"],
        "mean_pearson_ic": round(mean_pearson_ic, 4),
        "std_pearson_ic": round(std_pearson_ic, 4),
        "pearson_ic_ir": round(pearson_ic_ir, 2),
        "pct_positive_ic": round(pct_positive_ic, 1),
        "mean_score_rank_ic": round(mean_score_rank_ic, 4),
        "mean_quarterly_ls_spread": round(mean_ls_quarterly, 4),
        "annualized_ls_return": round(ann_ls_return, 4),
        "annualized_ls_vol": round(ann_ls_vol, 4),
        "ls_sharpe": round(ls_sharpe, 2),
        "ls_ci_lower": boot_ls_spread["ci_lower"],
        "ls_ci_upper": boot_ls_spread["ci_upper"],
        "ls_prob_positive": boot_ls_spread["prob_positive"],
        "q1_mean": round(q1_mean, 4),
        "q2_mean": round(q2_mean, 4),
        "q3_mean": round(q3_mean, 4),
        "q4_mean": round(q4_mean, 4),
        "q5_mean": round(q5_mean, 4),
        "q5_minus_q1": round(q5_minus_q1, 4),
        "q5_minus_q1_ci_lower": boot_q5_q1["ci_lower"],
        "q5_minus_q1_ci_upper": boot_q5_q1["ci_upper"],
        "q5_minus_q1_prob_positive": boot_q5_q1["prob_positive"],
        "monotonic_quarters_pct": round(mono_pct, 1),
    }

    return {"quarters": quarterly_records, "summary": summary}
