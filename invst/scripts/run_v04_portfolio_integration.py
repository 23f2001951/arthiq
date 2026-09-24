#!/usr/bin/env python3
"""Arth IQ V0.4-D: Portfolio Integration & Normalized Additive Engine Runner.

Executes 10-year walk-forward comparative portfolio backtest evaluating:
- Deterministic Baseline V0.2.1
- V0.4 Candidate 2 Standalone Tilt (Fund + Momentum, γ=0.50)
- V0.4-D Normalized Additive Framework (ArthScore Blend, γ=0.50)

Evaluates Gate 8: Portfolio Value-Add vs Baseline.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.config import get_config
from invst.logging_utils import setup_logging
from invst.ml.v04_portfolio_integration import run_v04_portfolio_integration_comparison

logger = logging.getLogger("invst.v04_portfolio_integration")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.4-D Portfolio Integration Runner"
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
    print("        ARTH IQ V0.4-D — PORTFOLIO INTEGRATION & NORMALIZED ADDITIVE ENGINE BENCHMARK")
    print("=" * 115)
    print(f"Database:         {db_path}")
    print(f"Simulation Range: {args.start} to {end_date} (Clamped to Current Date: {today_str})")
    print(f"Benchmark:        {args.benchmark} (Nifty 500 TRI)")
    print("-" * 115)

    res = run_v04_portfolio_integration_comparison(
        conn=conn,
        start_date=args.start,
        end_date=end_date,
        benchmark_symbol=args.benchmark,
    )

    # 1. Full Period Backtest Results
    print("\n" + "=" * 115)
    print(" [SECTION 1] 10-YEAR FULL SIMULATION BACKTEST (2016 TO PRESENT)")
    print("=" * 115)
    header_full = (
        f"{'Model Configuration':<45} {'CAGR %':<10} {'Δ Baseline':<12} {'Alpha %':<10} "
        f"{'Sharpe':<8} {'Max DD %':<10} {'Vol %':<8} {'Hit Rate':<10} {'Gate 8':<10}"
    )
    print(header_full)
    print("-" * 115)
    for r in res["full_period_results"]:
        delta_str = f"{r['cagr_delta_vs_baseline']:>+6.2f} %" if not r["is_baseline"] else "---"
        print(
            f"{r['name']:<45} {r['cagr']:>6.2f} %   {delta_str:<12} {r['alpha']:>6.2f} %   "
            f"{r['sharpe']:>6.2f}  {r['max_drawdown']:>7.2f} %  {r['annualized_vol']:>6.2f} %  "
            f"{r['hit_rate']:>6.1f} %  {r['gate_8_verdict']:<10}"
        )

    # 2. Partitioned Epoch Breakdown
    print("\n" + "=" * 115)
    print(" [SECTION 2] PARTITIONED EPOCH COMPARISON (BASELINE VS V0.4-D INTEGRATED ENGINE)")
    print("=" * 115)
    header_ep = (
        f"{'Evaluation Epoch':<38} {'Base CAGR':<12} {'V0.4-D CAGR':<14} {'Δ CAGR':<10} "
        f"{'Base Sharpe':<13} {'V0.4-D Sharpe':<14} {'Base MDD':<11} {'V0.4-D MDD':<12}"
    )
    print(header_ep)
    print("-" * 115)
    for p in res["partition_results"]:
        print(
            f"{p['epoch_name']:<38} {p['baseline_cagr']:>7.2f} %   {p['integrated_cagr']:>7.2f} %   "
            f"{p['cagr_delta']:>+6.2f} %   {p['baseline_sharpe']:>8.2f}      {p['integrated_sharpe']:>8.2f}      "
            f"{p['baseline_mdd']:>7.2f} %  {p['integrated_mdd']:>7.2f} %"
        )

    # 3. Institutional Gate 8 Synthesis
    print("\n" + "=" * 115)
    print(" [SECTION 3] INSTITUTIONAL GATE 8 EVALUATION & V0.4-E HANDOVER")
    print("=" * 115)
    int_engine = res["full_period_results"][2]
    print(f"Engine Tested:               {int_engine['name']}")
    print(f"Full-Period Active Delta:    {int_engine['cagr_delta_vs_baseline']:+.2f}% CAGR vs Deterministic Baseline")
    print(f"Max Drawdown Impact:         {int_engine['max_drawdown']:.2f}% (vs Baseline: {res['full_period_results'][0]['max_drawdown']:.2f}%)")
    print(f"Gate 8 Final Verdict:        {int_engine['gate_8_verdict']}")
    if int_engine["cagr_delta_vs_baseline"] >= -0.50:
        print("\nHandover Verdict: PROCEED TO PHASE V0.4-E (Paper / Shadow Portfolio Deployment)")
    else:
        print("\nHandover Verdict: Model fails portfolio usefulness threshold.")
    print("=" * 115 + "\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
