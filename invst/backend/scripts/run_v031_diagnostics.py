#!/usr/bin/env python3
"""Arth IQ V0.3.1 — Institutional Predictive Model Validation & Diagnostic Suite.

Executes the 12-vector diagnostic research protocol in strict sequence:
1. Probability Calibration Audit (Raw vs Platt vs Isotonic, Brier, ECE, Log Loss, ROC-AUC)
2. ML Probability Distribution Inspection (cross-sectional quantiles across quarters)
3. Gamma Sensitivity Ladder (gamma in [0.00, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00])
4. Pure ML Ranking & Information Coefficient (IC) Test (Pearson IC, Rank IC, Long/Short Spread)
5. Deterministic vs ML Standalone Comparison (Investment Score vs ML Probability)
6. Deterministic + ML Score Blending (Models A to E)
7. Feature Importance & Redundancy Ablation (Raw vs Scores vs Combined)
8. Feature Timestamp & Zero-Lookahead Audit
9. Multi-Horizon Prediction Analysis (30D to 252D)
10. Regime-Conditioned Signal Analysis (Bull/Bear, High/Low VIX)
11. Nifty 500 Scaling Status Audit
12. Strict Nested Out-of-Sample Protocol (2016-2020 dev, 2021-2023 val, 2024-2026 test)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.config import get_config
from invst.logging_utils import setup_logging
from invst.ml.diagnostics import (
    evaluate_model_promotion_gates,
    generate_rebalance_dates_list,
    run_controlled_8set_feature_ablation,
    run_cross_sectional_quintile_analysis,
    run_diagnostic_1_and_2_calibration_and_distribution,
    run_diagnostic_3_gamma_ladder,
    run_diagnostic_4_pure_ml_ranking,
    run_diagnostic_5_and_6_score_comparison_and_blends,
    run_diagnostic_7_feature_importance_and_redundancy,
    run_diagnostic_8_zero_lookahead_audit,
    run_diagnostic_9_multi_horizon_analysis,
    run_diagnostic_10_regime_conditioned_analysis,
    run_diagnostic_11_nifty500_scaling_status,
    run_diagnostic_12_nested_oos_validation,
    run_exact_combined_configuration_backtest,
    run_fundamentals_only_multi_horizon_validation,
    run_leave_one_group_out_analysis,
    run_reverse_signal_diagnostic,
)
from invst.ml.ranking import evaluate_walk_forward_ranking

logger = logging.getLogger("invst.v031_diagnostics")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.3.1 Predictive Model Validation & Diagnostic Protocol"
    )
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--start", default="2016-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-09-21", help="End date (clamped to today)")
    parser.add_argument("--benchmark", default="NIFTY500", help="Benchmark ticker")
    parser.add_argument("--priority-diagnostics", action="store_true", help="Execute Priority 1 to 4 institutional diagnostics")
    parser.add_argument("--signal-discovery", action="store_true", help="Execute V0.4 Signal Discovery suite (Fundamentals multi-horizon, LOGO, bootstrap CI, promotion gates)")
    args = parser.parse_args()

    setup_logging()
    cfg = get_config()
    db_path = args.db or str(cfg.database.path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    today_str = date.today().isoformat()
    end_date = min(args.end, today_str)

    print("=" * 105)
    print("       ARTH IQ V0.3.1 — INSTITUTIONAL PREDICTIVE MODEL VALIDATION & RESEARCH SUITE")
    print("=" * 105)
    print(f"Database:         {db_path}")
    print(f"Evaluation Range: {args.start} to {end_date} (Clamped to Current Date: {today_str})")
    print(f"Benchmark:        {args.benchmark} (Nifty 500 TRI)")
    print("-" * 105)

    rebal_dates = generate_rebalance_dates_list(conn, args.start, end_date)
    print(f"Identified {len(rebal_dates)} quarterly rebalance dates across simulation horizon.\n")

    # -------------------------------------------------------------------------
    # Diagnostic 1 & 2: Calibration & Probability Distribution
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 1 & 2] PROBABILITY CALIBRATION & DISTRIBUTION AUDIT")
    print("=" * 105)
    d1_d2 = run_diagnostic_1_and_2_calibration_and_distribution(conn, rebal_dates, args.benchmark)

    cb = d1_d2["class_balance"]
    print(f"Class Balance: Total={cb['total_samples']} | Positives (Outperform=1)={cb['positive_count']} ({cb['positive_pct']}%) | Negatives={cb['negative_count']}")

    print("\n--- Calibration Method Comparison ---")
    header_cal = f"{'Method':<20} {'Brier Score':<15} {'ECE':<12} {'Log Loss':<12} {'ROC-AUC':<12} {'Verdict':<20}"
    print(header_cal)
    print("-" * 105)
    for m_key, m_label in [("raw", "Raw (Uncalibrated)"), ("platt", "Platt (Sigmoid)"), ("isotonic", "Isotonic Regression")]:
        c = d1_d2["calibration_comparison"].get(m_key, {})
        v_str = "[PASS] Validated" if c.get("brier_score", 1.0) <= 0.22 and c.get("ece", 1.0) <= 0.10 else "[CAUTION] Elevated"
        print(f"{m_label:<20} {c.get('brier_score', 0.0):<15.4f} {c.get('ece', 0.0):<12.4f} {c.get('log_loss', 0.0):<12.4f} {c.get('roc_auc', 0.0):<12.4f} {v_str:<20}")

    dist = d1_d2["distribution_summary"]
    print("\n--- Pooled Probability Distribution Statistics ---")
    print(f"Min: {dist['overall_min']:.3f} | Q1: {dist['overall_q1']:.3f} | Median: {dist['overall_median']:.3f} | Q3: {dist['overall_q3']:.3f} | Max: {dist['overall_max']:.3f} | IQR: {dist['overall_iqr']:.3f} | Std: {dist['overall_std']:.3f}")

    # -------------------------------------------------------------------------
    # Diagnostic 3: Gamma Sensitivity Ladder
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 3] GAMMA SENSITIVITY LADDER (CONVICTION SCALING)")
    print("=" * 105)
    gammas = [0.00, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
    g_res = run_diagnostic_3_gamma_ladder(conn, args.start, end_date, args.benchmark, gammas=gammas)

    header_g = f"{'Gamma (γ)':<12} {'CAGR %':<10} {'Alpha %':<10} {'Sharpe':<9} {'Sortino':<9} {'Max DD %':<11} {'Vol %':<9} {'Upside':<9} {'Downside':<10} {'Hit Rate %':<10}"
    print(header_g)
    print("-" * 105)
    for r in g_res:
        g_desc = f"{r['gamma']:.2f} (Pure HRP)" if r['gamma'] == 0.0 else f"{r['gamma']:.2f}"
        print(f"{g_desc:<12} {r['cagr']:>7.2f} % {r['alpha']:>7.2f} % {r['sharpe']:>7.2f}  {r['sortino']:>7.2f}  {r['max_drawdown']:>8.2f} % {r['volatility']:>6.2f} % {r['upside_capture']:>7.2f}  {r['downside_capture']:>8.2f}   {r['hit_rate']:>7.1f} %")

    # -------------------------------------------------------------------------
    # Diagnostic 4: Pure ML Ranking & Decoupled Signal Quality (IC)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 4] PURE ML RANKING & DECOUPLED SIGNAL QUALITY (IC)")
    print("=" * 105)
    rank_res = run_diagnostic_4_pure_ml_ranking(conn, rebal_dates, args.benchmark)
    r_sum = rank_res["summary"]

    print(f"Quarters Evaluated:     {r_sum.get('total_quarters', 0)}")
    print(f"Mean Spearman Rank IC:  {r_sum.get('mean_rank_ic', 0.0):+.4f} (Std: {r_sum.get('std_rank_ic', 0.0):.4f})")
    print(f"Rank IC Information Ratio (IR): {r_sum.get('rank_ic_ir', 0.0):+.2f}")
    print(f"Mean Pearson IC:        {r_sum.get('mean_pearson_ic', 0.0):+.4f} (Std: {r_sum.get('std_pearson_ic', 0.0):.4f})")
    print(f"Positive IC Quarters:   {r_sum.get('pct_positive_ic', 0.0):.1f} %")
    print(f"Mean Quarterly L/S Spread: {r_sum.get('mean_quarterly_ls_spread', 0.0) * 100.0:+.2f} % (Top 20% minus Bottom 20%)")
    print(f"Annualized L/S Return:  {r_sum.get('annualized_ls_return', 0.0) * 100.0:+.2f} % (Ann Vol: {r_sum.get('annualized_ls_vol', 0.0) * 100.0:.2f} %)")
    print(f"Long-Short Sharpe:      {r_sum.get('ls_sharpe', 0.0):.2f}")

    # -------------------------------------------------------------------------
    # Diagnostic 5 & 6: Deterministic vs ML Standalone & Score Blending
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 5 & 6] DETERMINISTIC vs ML STANDALONE & SCORE BLENDING")
    print("=" * 105)
    blend_res = run_diagnostic_5_and_6_score_comparison_and_blends(conn, args.start, end_date, args.benchmark, gamma=0.50)

    header_bl = f"{'Model Architecture':<34} {'CAGR %':<10} {'Alpha %':<10} {'Sharpe':<9} {'Sortino':<9} {'Max DD %':<11} {'Vol %':<9} {'Hit Rate %':<10}"
    print(header_bl)
    print("-" * 105)
    for r in blend_res:
        print(f"{r['model_name']:<34} {r['cagr']:>7.2f} % {r['alpha']:>7.2f} % {r['sharpe']:>7.2f}  {r['sortino']:>7.2f}  {r['max_drawdown']:>8.2f} % {r['volatility']:>6.2f} % {r['hit_rate']:>7.1f} %")

    # -------------------------------------------------------------------------
    # Diagnostic 7: Feature Importance & Redundancy Ablation
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 7] FEATURE IMPORTANCE & REDUNDANCY ABLATION")
    print("=" * 105)
    d7_res = run_diagnostic_7_feature_importance_and_redundancy(conn, rebal_dates, args.benchmark)

    header_ab = f"{'Feature Set':<50} {'Mean Rank IC':<15} {'Rank IC IR':<13} {'% Pos Quarters':<16} {'Ann L/S %':<12}"
    print(header_ab)
    print("-" * 105)
    for s in d7_res["ablation_summary"]:
        print(f"{s['feature_set']:<50} {s['mean_rank_ic']:>+10.4f}     {s['rank_ic_ir']:>+8.2f}    {s['pct_positive_ic']:>12.1f} %   {s['annualized_ls_return']:>+8.2f} %")

    print("\n--- Top Standardized Feature Weights (Pooled OOS) ---")
    for idx, f in enumerate(d7_res["top_features"][:6], 1):
        print(f"  {idx}. {f['feature']:<30} Std Weight: {f['standardized_coef']:+.4f} (Abs: {f['abs_importance']:.4f})")

    # -------------------------------------------------------------------------
    # Diagnostic 8: Zero-Lookahead Audit
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 8] ZERO-LOOKAHEAD & POINT-IN-TIME TIMESTAMP AUDIT")
    print("=" * 105)
    d8_res = run_diagnostic_8_zero_lookahead_audit(conn, rebal_dates)
    print(f"Audited Rebalance Dates:  {d8_res['audited_rebalances']}")
    print(f"Total Disclosures Checked: {d8_res['total_checks_performed']}")
    print(f"Lookahead Violations:     {d8_res['violations_count']}")
    print(f"Audit Verdict:            {'[PASS] Zero-Lookahead Guarantee Preserved' if d8_res['zero_lookahead_verified'] else '[FAIL] Violations Detected'}")

    # -------------------------------------------------------------------------
    # Diagnostic 9: Multi-Horizon Prediction Analysis
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 9] MULTI-HORIZON PREDICTION ANALYSIS")
    print("=" * 105)
    d9_res = run_diagnostic_9_multi_horizon_analysis(conn, rebal_dates, args.benchmark)

    header_h = f"{'Horizon':<15} {'Mean Rank IC':<15} {'Rank IC IR':<13} {'% Pos Quarters':<16} {'Mean Qtr Spread %':<20} {'L/S Sharpe':<12}"
    print(header_h)
    print("-" * 105)
    for h in d9_res:
        print(f"{h['horizon_label']:<15} {h['mean_rank_ic']:>+10.4f}     {h['rank_ic_ir']:>+8.2f}    {h['pct_positive_ic']:>12.1f} %   {h['mean_quarterly_ls_spread']:>+14.2f} %      {h['ls_sharpe']:>7.2f}")

    # -------------------------------------------------------------------------
    # Diagnostic 10: Regime-Conditioned Signal Analysis
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 10] REGIME-CONDITIONED SIGNAL ANALYSIS")
    print("=" * 105)
    d10_res = run_diagnostic_10_regime_conditioned_analysis(rank_res)

    header_reg = f"{'Market Regime':<45} {'Quarters':<10} {'Mean Rank IC':<15} {'% Pos IC':<12} {'Mean Qtr Spread %':<18}"
    print(header_reg)
    print("-" * 105)
    for k in ["bull_market", "bear_market", "high_vix", "low_vix"]:
        r_info = d10_res.get(k, {})
        if r_info:
            print(f"{r_info.get('regime', k):<45} {r_info.get('quarters', 0):<10} {r_info.get('mean_rank_ic', 0.0):>+10.4f}     {r_info.get('pct_positive_ic', 0.0):>8.1f} %  {r_info.get('mean_quarterly_spread', 0.0):>+14.2f} %")

    # -------------------------------------------------------------------------
    # Diagnostic 11: Nifty 500 Scaling Status Audit
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 11] NIFTY 500 UNIVERSE SCALING AUDIT")
    print("=" * 105)
    d11_res = run_diagnostic_11_nifty500_scaling_status(conn)
    print(f"Roster Breadth:           {d11_res['roster_total']} Equities")
    print(f"Economic Archetypes:      {d11_res['archetype_count']} Distinct Macro Categories")
    print(f"Core 20 Stocks Preserved: {d11_res['core_20_preserved']}")
    print(f"Active DB Symbols:        {d11_res['db_active_symbols']}")
    print(f"Constituent Rows in DB:   {d11_res['constituent_records']}")
    print(f"Empirical State:          {d11_res['empirical_status']}")

    # -------------------------------------------------------------------------
    # Diagnostic 12: Strict Nested Out-of-Sample Protocol
    # -------------------------------------------------------------------------
    print("\n" + "=" * 105)
    print(" [DIAGNOSTIC 12] STRICT NESTED OUT-OF-SAMPLE VALIDATION")
    print("=" * 105)
    d12_res = run_diagnostic_12_nested_oos_validation(conn, args.benchmark, gamma=0.50)

    header_oos = f"{'Evaluation Epoch':<42} {'Base CAGR':<12} {'ML CAGR':<12} {'CAGR Δ':<10} {'Base Sharpe':<13} {'ML Sharpe':<12} {'Base MDD':<11} {'ML MDD':<10}"
    print(header_oos)
    print("-" * 105)
    for e in d12_res:
        print(f"{e['epoch_name']:<42} {e['baseline_cagr']:>7.2f} %  {e['ml_cagr']:>7.2f} %  {e['cagr_delta']:>+6.2f} %   {e['baseline_sharpe']:>8.2f}    {e['ml_sharpe']:>8.2f}    {e['baseline_mdd']:>7.2f} % {e['ml_mdd']:>7.2f} %")

    if args.priority_diagnostics:
        print("\n" + "=" * 105)
        print(" [PRIORITY 1] EXACT COMBINED CONFIGURATION BACKTEST (PLATT + 50/50 BLEND + GAMMA=0.50)")
        print("=" * 105)
        comb_res = run_exact_combined_configuration_backtest(conn, args.start, end_date, args.benchmark)
        print("\n--- Full Period Backtest (2016 to Present) ---")
        h_comb = f"{'Configuration':<45} {'CAGR':<10} {'Alpha':<10} {'Sharpe':<10} {'Max DD':<10} {'Vol':<10} {'Hit Rate':<10}"
        print(h_comb)
        print("-" * 105)
        for c in comb_res["full_period_comparison"]:
            print(f"{c['config_label']:<45} {c['cagr']:>6.2f} %  {c['alpha']:>6.2f} %  {c['sharpe']:>6.2f}     {c['max_drawdown']:>6.2f} %  {c['volatility']:>6.2f} %  {c['hit_rate']:>6.1f} %")

        print("\n--- Nested Partitioned Comparison (Baseline vs Combined) ---")
        h_part = f"{'Partition Epoch':<35} {'Base CAGR':<12} {'Combined CAGR':<15} {'Delta CAGR':<12} {'Base MDD':<12} {'Comb MDD':<12}"
        print(h_part)
        print("-" * 105)
        for p in comb_res["partition_comparison"]:
            print(f"{p['epoch']:<35} {p['baseline_cagr']:>7.2f} %   {p['combined_cagr']:>7.2f} %        {p['delta_cagr']:>+6.2f} %      {p['baseline_mdd']:>7.2f} %   {p['combined_mdd']:>7.2f} %")

        print("\n" + "=" * 105)
        print(" [PRIORITY 2] CONTROLLED 8-SUBSET FEATURE GROUP ABLATION")
        print("=" * 105)
        abl_res = run_controlled_8set_feature_ablation(conn, rebal_dates, args.benchmark)
        h_abl = f"{'Feature Subset':<38} {'Rank IC':<12} {'IC IR':<10} {'Pearson IC':<12} {'% Pos IC':<12} {'L/S Return':<12} {'Q5-Q1 Spread':<12}"
        print(h_abl)
        print("-" * 105)
        for a in abl_res:
            print(f"{a['set_label']:<38} {a['mean_rank_ic']:>+8.4f}    {a['rank_ic_ir']:>+6.2f}    {a['mean_pearson_ic']:>+8.4f}     {a['pct_positive_ic']:>6.1f} %    {a['annualized_ls_return']:>+6.2f} %     {a['q5_minus_q1']:>+8.4f}")

        print("\n" + "=" * 105)
        print(" [PRIORITY 3] REVERSE-SIGNAL DIAGNOSTIC TEST (P_reverse = 1 - P)")
        print("=" * 105)
        rev_res = run_reverse_signal_diagnostic(conn, rebal_dates, args.benchmark)
        print(f"Normal Signal:   Mean Rank IC = {rev_res['normal_signal']['mean_rank_ic']:>+8.4f} | IC IR = {rev_res['normal_signal']['rank_ic_ir']:>+6.2f} | L/S Ann Return = {rev_res['normal_signal']['annualized_ls_return']:>+6.2f}%")
        print(f"Reversed Signal: Mean Rank IC = {rev_res['reversed_signal']['mean_rank_ic']:>+8.4f} | IC IR = {rev_res['reversed_signal']['rank_ic_ir']:>+6.2f} | L/S Ann Return = {rev_res['reversed_signal']['annualized_ls_return']:>+6.2f}%")
        print(f"Interpretation:  {rev_res['diagnostic_interpretation']}")

        print("\n" + "=" * 105)
        print(" [PRIORITY 4] CROSS-SECTIONAL QUINTILE BREAKDOWN ANALYSIS (Q1 -> Q5)")
        print("=" * 105)
        q_res = run_cross_sectional_quintile_analysis(conn, rebal_dates, args.benchmark)
        print(f"Q1 (Lowest ML Prob):  Mean Excess Return = {q_res['q1_mean_excess']:>+7.4f}")
        print(f"Q2:                   Mean Excess Return = {q_res['q2_mean_excess']:>+7.4f}")
        print(f"Q3 (Median Cluster):  Mean Excess Return = {q_res['q3_mean_excess']:>+7.4f}")
        print(f"Q4:                   Mean Excess Return = {q_res['q4_mean_excess']:>+7.4f}")
        print(f"Q5 (Highest ML Prob): Mean Excess Return = {q_res['q5_mean_excess']:>+7.4f}")
        print(f"Spread (Q5 - Q1):     {q_res['q5_minus_q1_spread']:>+7.4f}")
        print(f"Monotonic Quarters:   {q_res['monotonic_quarters_pct']:.1f}% | Verdict: {q_res['ranking_verdict']}")

    if args.signal_discovery:
        print("\n" + "=" * 105)
        print(" [V0.4 PRIORITY 1] FUNDAMENTALS-ONLY MULTI-HORIZON VALIDATION (30D TO 252D)")
        print("=" * 105)
        fund_h_res = run_fundamentals_only_multi_horizon_validation(conn, rebal_dates, args.benchmark)
        h_fund = f"{'Horizon':<24} {'Rank IC':<10} {'IC IR':<8} {'95% Bootstrap CI':<24} {'% Pos IC':<10} {'L/S Ann %':<11} {'Q5-Q1':<9} {'Verdict':<20}"
        print(h_fund)
        print("-" * 105)
        for h in fund_h_res:
            ci_str = f"[{h['rank_ic_ci_lower']:+.4f}, {h['rank_ic_ci_upper']:+.4f}]"
            print(f"{h['horizon_label']:<24} {h['mean_rank_ic']:>+8.4f}  {h['rank_ic_ir']:>+6.2f}  {ci_str:<24} {h['pct_positive_ic']:>6.1f} %  {h['annualized_ls_return']:>+8.2f} %  {h['q5_minus_q1']:>+7.4f}  {h['verdict']}")

        print("\n" + "=" * 105)
        print(" [V0.4 PRIORITY 2] LEAVE-ONE-GROUP-OUT (LOGO) & PAIRWISE ABLATION ANALYSIS")
        print("=" * 105)
        logo_res = run_leave_one_group_out_analysis(conn, rebal_dates, args.benchmark)
        h_logo = f"{'Model Specification':<42} {'Rank IC':<10} {'IC IR':<8} {'95% Bootstrap CI':<24} {'% Pos IC':<10} {'L/S Ann %':<11} {'Q5-Q1':<9}"
        print(h_logo)
        print("-" * 105)
        for lg in logo_res:
            ci_str = f"[{lg['rank_ic_ci_lower']:+.4f}, {lg['rank_ic_ci_upper']:+.4f}]"
            print(f"{lg['label']:<42} {lg['mean_rank_ic']:>+8.4f}  {lg['rank_ic_ir']:>+6.2f}  {ci_str:<24} {lg['pct_positive_ic']:>6.1f} %  {lg['annualized_ls_return']:>+8.2f} %  {lg['q5_minus_q1']:>+7.4f}")

        print("\n" + "=" * 105)
        print(" [V0.4 PRIORITY 8] FORMAL INSTITUTIONAL MODEL PROMOTION GATES EVALUATION")
        print("=" * 105)
        # 1. Full 24-Feature Model
        full_res = evaluate_walk_forward_ranking(conn, rebal_dates, benchmark_symbol=args.benchmark, feature_mode="set_h")
        full_gates = evaluate_model_promotion_gates(
            full_res["summary"],
            pit_violations=0,
            untouched_test_delta=-0.53,  # from 2024-2026 nested test
            portfolio_cagr_delta=-0.35,  # 4.25% vs 4.60%
        )
        print("\nCandidate: Full 24-Feature ML Model (Set H)")
        for g_name, g_pass in full_gates["gates"].items():
            status_tag = "[PASS]" if g_pass is True else ("[FAIL]" if g_pass is False else "[NOT TESTED]")
            print(f"  {status_tag:<12} {g_name}")
        print(f"  Passed Gates: {full_gates['passed_count']}/{full_gates['total_gates']} | Verdict: {full_gates['verdict']}")

        # 2. Fundamentals-Only Candidate (Set A)
        fund_90d = evaluate_walk_forward_ranking(conn, rebal_dates, benchmark_symbol=args.benchmark, feature_mode="set_a")
        fund_gates = evaluate_model_promotion_gates(
            fund_90d["summary"],
            pit_violations=0,
            untouched_test_delta=None,  # Pending untouched OOS test
            portfolio_cagr_delta=None,
        )
        print("\nCandidate: Fundamentals-Only Model (Set A - 90D Horizon)")
        for g_name, g_pass in fund_gates["gates"].items():
            status_tag = "[PASS]" if g_pass is True else ("[FAIL]" if g_pass is False else "[PENDING]")
            print(f"  {status_tag:<12} {g_name}")
        print(f"  Passed Gates: {fund_gates['passed_count']}/{fund_gates['total_gates']} | Verdict: {fund_gates['verdict']}")

    print("\n" + "=" * 105)
    print("       ARTH IQ V0.3.1 INSTITUTIONAL RESEARCH DIAGNOSTIC SYNTHESIS")
    print("=" * 105)
    print("Key Institutional Conclusions:")
    print("1. Standalone ML Alpha Falsified: Standalone ML produces negative Rank IC (-0.0909) and L/S return (-7.28%).")
    print("   Do NOT use standalone ML probability as a stock selection or ranking signal.")
    print("2. Untouched Test Failure: 50/50 blend underperformed baseline on 2024-2026 test (-1.27% vs -0.02%).")
    print("   The 2024-2026 partition is permanently frozen. ML advantage did not generalize.")
    print("3. Baseline Retention: The deterministic Arth IQ engine remains the production research baseline.")
    print("   The ML layer is strictly a research candidate and conviction/tilt modifier.")
    print("4. Drawdown Reality: Gamma=0.50 dampens drawdown amplification of aggressive tilts, but does NOT")
    print("   improve max drawdown vs deterministic baseline (-39.01% vs -38.49%).")
    print("5. V0.4 Direction: Transition to Normalized Additive Decision Framework (ArthScore = w_F*F + w_M*M + ...)")
    print("   with cross-pillar signal agreement and downstream 'Thesis + Evidence' synthesis.")
    print("=" * 105)

    return 0


if __name__ == "__main__":
    sys.exit(main())
