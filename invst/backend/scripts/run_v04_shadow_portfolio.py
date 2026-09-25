#!/usr/bin/env python3
"""Arth IQ V0.4-E: Forward Paper / Shadow Portfolio Operational Harness Runner.

Tracks dual forward shadow portfolios:
1. Production Shadow Portfolio: Deterministic Baseline Engine V0.2.1
2. Experimental Research Shadow: V0.4-D Normalized Additive Engine (ArthScore)

Generates live tracking error, turnover, and operational telemetry.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.config import get_config
from invst.execution.v04_shadow_portfolio import run_shadow_tracking_simulation
from invst.logging_utils import setup_logging

logger = logging.getLogger("invst.v04_shadow_portfolio")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.4-E Shadow Portfolio Operational Harness Runner"
    )
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--start", default="2024-01-01", help="Shadow tracking start date (YYYY-MM-DD)")
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
    print("        ARTH IQ V0.4-E — FORWARD PAPER / SHADOW PORTFOLIO OPERATIONAL TRACKING HARNESS")
    print("=" * 115)
    print(f"Database:              {db_path}")
    print(f"Shadow Tracking Epoch: {args.start} to {end_date} (Clamped to Current Date: {today_str})")
    print(f"Benchmark:             {args.benchmark} (Nifty 500 TRI)")
    print("Initial Shadow Capital:₹1,000,000.00")
    print("-" * 115)

    res = run_shadow_tracking_simulation(
        conn=conn,
        benchmark_symbol=args.benchmark,
        start_date=args.start,
        end_date=end_date,
    )

    prod = res["production"]
    res_eng = res["research"]

    # 1. Performance Overview Table
    print("\n" + "=" * 115)
    print(" [SECTION 1] SHADOW PORTFOLIO CAPITAL ACCOUNTING & MARK-TO-MARKET VALUATION")
    print("=" * 115)
    header = f"{'Metric Description':<35} {'Production Shadow (V0.2.1)':<32} {'Research Shadow (V0.4-D)':<30}"
    print(header)
    print("-" * 115)
    print(f"{'Initial Capital':<35} ₹1,000,000.00                     ₹1,000,000.00")
    print(f"{'Current Portfolio Equity':<35} ₹{prod['final_equity']:,.2f}                     ₹{res_eng['final_equity']:,.2f}")
    print(f"{'Annualized CAGR %':<35} {prod['cagr']:>6.2f} %                         {res_eng['cagr']:>6.2f} %")
    print(f"{'Active Alpha vs Nifty 500':<35} {prod['alpha']:>+6.2f} %                         {res_eng['alpha']:>+6.2f} %")
    print(f"{'Sharpe Ratio':<35} {prod['sharpe']:>6.2f}                           {res_eng['sharpe']:>6.2f}")
    print(f"{'Max Peak-to-Trough Drawdown':<35} {prod['max_drawdown']:>6.2f} %                         {res_eng['max_drawdown']:>6.2f} %")
    print(f"{'Annualized Volatility':<35} {prod['volatility']:>6.2f} %                         {res_eng['volatility']:>6.2f} %")
    print(f"{'Average Quarterly Turnover':<35} {prod['turnover_avg']:>6.1f} %                         {res_eng['turnover_avg']:>6.1f} %")
    print(f"{'Monthly Benchmark Win Rate':<35} {prod['hit_rate']:>6.1f} %                         {res_eng['hit_rate']:>6.1f} %")

    # 2. Operational Comparison & Tracking Spread
    print("\n" + "=" * 115)
    print(" [SECTION 2] ACTIVE TRACKING SPREAD & OPERATIONAL SLIPPAGE")
    print("=" * 115)
    print(f"Equity Spread (Research - Production): ₹{res_eng['final_equity'] - prod['final_equity']:+,.2f}")
    print(f"Annualized CAGR Spread:                {res['delta_cagr']:+.2f}% CAGR")
    print("Execution Friction Modeling:           30 bps buy commission + 20 bps sell commission + 5 bps slippage")

    # 3. Institutional Fiduciary Verdict
    print("\n" + "=" * 115)
    print(" [SECTION 3] INSTITUTIONAL FIDUCIARY VERDICT & PRODUCTION STATUS")
    print("=" * 115)
    print(f"Operational Verdict: {res['fiduciary_verdict']}")
    print("Production Allocation: 100% Real Capital remains exclusively anchored on Deterministic Baseline V0.2.1.")
    print("Research Allocation:   0% Real Capital; forward telemetry logged daily in shadow ledger.")
    print("=" * 115 + "\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
