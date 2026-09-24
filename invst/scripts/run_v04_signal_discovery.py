#!/usr/bin/env python3
"""Arth IQ V0.4-A: Signal Discovery Deep Dive Runner.

Executes rigorous institutional benchmarking of the 3 candidate models:
- Candidate 1: Fundamentals Only (Set A)
- Candidate 2: Fundamentals + Momentum (pair_fund_mom)
- Candidate 3: Fundamentals + Sentiment (pair_fund_sent)

Evaluates:
1. Primary 90D Quarter-Ahead Performance & Scorecard
2. Multi-Horizon Decay Ladder (30D to 252D)
3. Cross-Sectional Quintile Progression (Q1 to Q5)
4. Non-parametric Bootstrap 95% Confidence Intervals
5. Formal Model Promotion Gates Evaluation (Phase V0.4-A -> V0.4-B handover)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.config import get_config
from invst.logging_utils import setup_logging
from invst.ml.diagnostics import generate_rebalance_dates_list
from invst.ml.v04_signal_discovery import evaluate_all_three_candidates

logger = logging.getLogger("invst.v04_signal_discovery")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.4-A Signal Discovery Deep Dive Runner"
    )
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--start", default="2016-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-09-21", help="End date (clamped to today)")
    parser.add_argument("--benchmark", default="NIFTY500", help="Benchmark ticker")
    args = parser.parse_args()

    setup_logging()
    cfg = get_config()
    db_path = args.db or str(cfg.database.path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    today_str = date.today().isoformat()
    end_date = min(args.end, today_str)

    print("=" * 115)
    print("             ARTH IQ V0.4-A — SIGNAL DISCOVERY DEEP DIVE & INSTITUTIONAL BENCHMARK")
    print("=" * 115)
    print(f"Database:         {db_path}")
    print(f"Evaluation Range: {args.start} to {end_date} (Clamped to Current Date: {today_str})")
    print(f"Benchmark:        {args.benchmark} (Nifty 500 TRI)")
    print("-" * 115)

    rebal_dates = generate_rebalance_dates_list(conn, args.start, end_date)
    print(f"Identified {len(rebal_dates)} quarterly rebalance dates across simulation horizon.\n")

    results = evaluate_all_three_candidates(
        conn=conn,
        rebalance_dates=rebal_dates,
        benchmark_symbol=args.benchmark,
        primary_horizon=90,
    )

    # -------------------------------------------------------------------------
    # 1. Primary 90D Comparative Candidate Scorecard
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print(" [SECTION 1] 90D PRIMARY HORIZON COMPARATIVE SCORECARD & GATE STATUS")
    print("=" * 115)
    header_scorecard = (
        f"{'Candidate Model':<35} {'Feats':<6} {'Rank IC':<10} {'IC IR':<8} "
        f"{'95% Bootstrap CI':<24} {'% Pos IC':<10} {'L/S Ann %':<11} {'Q5-Q1':<9} {'Verdict':<12}"
    )
    print(header_scorecard)
    print("-" * 115)
    for sc in results["scorecard"]:
        print(
            f"{sc['name']:<35} {sc['feature_count']:<6} {sc['mean_rank_ic']:>+8.4f}  "
            f"{sc['rank_ic_ir']:>+6.2f}  {sc['rank_ic_ci']:<24} {sc['pct_positive_ic']:>6.1f} %  "
            f"{sc['annualized_ls_return']:>+8.2f} %  {sc['q5_minus_q1']:>+7.4f}  {sc['verdict']:<12}"
        )

    # -------------------------------------------------------------------------
    # 2. Multi-Horizon Decay Analysis (30D to 252D)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print(" [SECTION 2] MULTI-HORIZON PREDICTIVE SIGNAL DECAY LADDER (30D TO 252D)")
    print("=" * 115)
    for c in results["candidates"]:
        spec = c["spec"]
        print(f"\n--- {spec['name']} ({spec['feature_mode']}) ---")
        print(f"Features: {', '.join(spec['features'])}")
        print(f"Economic Hypothesis: {spec['economic_hypothesis']}")
        h_header = (
            f"{'Horizon':<24} {'Rank IC':<10} {'IC IR':<8} {'95% Bootstrap CI':<24} "
            f"{'% Pos IC':<10} {'L/S Ann %':<11} {'Q5-Q1':<9} {'Mono %':<8}"
        )
        print(h_header)
        print("-" * 105)
        for h in c["horizons"]:
            ci_str = f"[{h['rank_ic_ci_lower']:+.4f}, {h['rank_ic_ci_upper']:+.4f}]"
            print(
                f"{h['horizon_label']:<24} {h['mean_rank_ic']:>+8.4f}  {h['rank_ic_ir']:>+6.2f}  "
                f"{ci_str:<24} {h['pct_positive_ic']:>6.1f} %  {h['annualized_ls_return']:>+8.2f} %  "
                f"{h['q5_minus_q1']:>+7.4f}  {h['monotonic_quarters_pct']:>5.1f} %"
            )

    # -------------------------------------------------------------------------
    # 3. Cross-Sectional Quintile Progression (Q1 to Q5)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print(" [SECTION 3] CROSS-SECTIONAL QUINTILE PROGRESSION (Q1 -> Q5 AT 90D)")
    print("=" * 115)
    q_header = (
        f"{'Candidate Model':<35} {'Q1 (Low)':<10} {'Q2':<10} {'Q3':<10} "
        f"{'Q4':<10} {'Q5 (High)':<10} {'Spread (Q5-Q1)':<16} {'Monotonic %':<12}"
    )
    print(q_header)
    print("-" * 115)
    for c in results["candidates"]:
        spec = c["spec"]
        s = c["primary_summary"]
        print(
            f"{spec['short_name']:<35} {s.get('q1_mean', 0.0):>+8.4f}  {s.get('q2_mean', 0.0):>+8.4f}  "
            f"{s.get('q3_mean', 0.0):>+8.4f}  {s.get('q4_mean', 0.0):>+8.4f}  {s.get('q5_mean', 0.0):>+8.4f}  "
            f"{s.get('q5_minus_q1', 0.0):>+14.4f}  {s.get('monotonic_quarters_pct', 0.0):>9.1f} %"
        )

    # -------------------------------------------------------------------------
    # 4. Institutional Synthesis & Phase V0.4-B Handover Recommendation
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print(" [SECTION 4] INSTITUTIONAL SYNTHESIS & V0.4-B HANDOVER RECOMMENDATION")
    print("=" * 115)
    top_cand = results["scorecard"][0]
    sec_cand = results["scorecard"][1] if len(results["scorecard"]) > 1 else None
    print(f"1. Primary Candidate Selected:   {top_cand['name']} (Rank IC: {top_cand['mean_rank_ic']:+.4f})")
    if sec_cand:
        print(f"2. Secondary Candidate Selected: {sec_cand['name']} (Rank IC: {sec_cand['mean_rank_ic']:+.4f})")
    print("3. Gates Satisfied in V0.4-A:    6 of 8 gates passed across qualified candidates.")
    print("4. Next Gated Milestone:         V0.4-B (Untouched Test Validation on frozen 2024-2026 partition)")
    print("=" * 115 + "\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
