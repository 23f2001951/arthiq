#!/usr/bin/env python3
"""Arth IQ V0.4-B: Untouched Out-of-Sample Test Validation Runner.

Evaluates surviving candidate models on the permanently frozen 2024-2026 test
partition against the deterministic baseline to test Gate 5 (Untouched Test Delta > 0).
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.config import get_config
from invst.logging_utils import setup_logging
from invst.ml.v04_untouched_validation import (
    UNTOUCHED_TEST_START,
    run_untouched_test_portfolio_backtests,
    run_untouched_test_predictive_ranking,
)

logger = logging.getLogger("invst.v04_untouched_validation")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.4-B Untouched Test Validation Runner"
    )
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--test-start", default=UNTOUCHED_TEST_START, help="Test start date (YYYY-MM-DD)")
    parser.add_argument("--test-end", default="2026-09-21", help="Test end date (clamped to today)")
    parser.add_argument("--benchmark", default="NIFTY500", help="Benchmark ticker")
    parser.add_argument("--gamma", type=float, default=0.50, help="ML conviction gamma")
    args = parser.parse_args()

    setup_logging()
    cfg = get_config()
    db_path = args.db or str(cfg.database.path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    today_str = date.today().isoformat()
    end_date = min(args.test_end, today_str)

    print("=" * 115)
    print("        ARTH IQ V0.4-B — UNTOUCHED OUT-OF-SAMPLE TEST VALIDATION (2024-2026 PARTITION)")
    print("=" * 115)
    print(f"Database:         {db_path}")
    print(f"Test Partition:   {args.test_start} to {end_date} (Clamped to Current Date: {today_str})")
    print(f"Benchmark:        {args.benchmark} (Nifty 500 TRI)")
    print(f"Conviction Gamma: {args.gamma}")
    print("-" * 115)

    # 1. Run Portfolio Backtests on Frozen Partition
    print("\n" + "=" * 115)
    print(" [SECTION 1] FROZEN TEST PARTITION PORTFOLIO BACKTEST & GATE 5 VERDICT")
    print("=" * 115)
    port_results = run_untouched_test_portfolio_backtests(
        conn=conn,
        benchmark_symbol=args.benchmark,
        gamma=args.gamma,
        test_start=args.test_start,
        test_end=end_date,
    )

    header_port = (
        f"{'Model Configuration':<36} {'CAGR %':<10} {'Δ Baseline':<12} {'Alpha %':<10} "
        f"{'Sharpe':<8} {'Max DD %':<10} {'Vol %':<8} {'Hit Rate':<10} {'Gate 5':<10}"
    )
    print(header_port)
    print("-" * 115)
    for r in port_results:
        delta_str = f"{r['cagr_delta_vs_baseline']:>+6.2f} %" if not r["is_baseline"] else "---"
        print(
            f"{r['name']:<36} {r['cagr']:>6.2f} %   {delta_str:<12} {r['alpha']:>6.2f} %   "
            f"{r['sharpe']:>6.2f}  {r['max_drawdown']:>7.2f} %  {r['annualized_vol']:>6.2f} %  "
            f"{r['hit_rate']:>6.1f} %  {r['gate_5_verdict']:<10}"
        )

    # 2. Run Predictive Ranking on Test Partition
    print("\n" + "=" * 115)
    print(" [SECTION 2] OUT-OF-SAMPLE PREDICTIVE RANKING METRICS (2024-2026 TEST REBALANCES)")
    print("=" * 115)
    rank_results = run_untouched_test_predictive_ranking(
        conn=conn,
        benchmark_symbol=args.benchmark,
        test_start=args.test_start,
        test_end=end_date,
    )

    header_rank = (
        f"{'Model Configuration':<38} {'Quarters':<10} {'Rank IC':<10} {'IC IR':<8} "
        f"{'% Pos IC':<10} {'L/S Ann %':<11} {'Q5-Q1 Spread':<14}"
    )
    print(header_rank)
    print("-" * 115)
    for rk in rank_results:
        print(
            f"{rk['name']:<38} {rk['test_quarters_count']:<10} {rk['mean_rank_ic']:>+8.4f}  "
            f"{rk['rank_ic_ir']:>+6.2f}  {rk['pct_positive_ic']:>6.1f} %  "
            f"{rk['annualized_ls_return']:>+8.2f} %  {rk['q5_minus_q1']:>+10.4f}"
        )

    # 3. Institutional Gate 5 Summary
    print("\n" + "=" * 115)
    print(" [SECTION 3] INSTITUTIONAL GATE 5 EVALUATION & V0.4-C HANDOVER SUMMARY")
    print("=" * 115)
    surviving_candidates = [r for r in port_results if not r["is_baseline"] and r["gate_5_verdict"] == "PASS"]
    if surviving_candidates:
        print(f"Qualified Candidates Passing Gate 5 ({len(surviving_candidates)}):")
        for sc in surviving_candidates:
            print(f"  ★ {sc['name']}: Untouched Test Delta = {sc['cagr_delta_vs_baseline']:+.2f}% | Sharpe = {sc['sharpe']}")
        print("\nHandover Verdict: PROCEED TO PHASE V0.4-C (Nifty 500 PIT Validation)")
    else:
        print("ALERT: No ML candidate achieved positive alpha delta over deterministic baseline on untouched test.")
        print("Verdict: Retain Deterministic Engine V0.2.1 as production anchor.")
    print("=" * 115 + "\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
