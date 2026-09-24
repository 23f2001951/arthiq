#!/usr/bin/env python3
"""Run 40-Quarter Out-of-Sample Walk-Forward Validation (2016-2026) for Arth IQ V0.2 Engine.

Quantifies Alpha, Information Ratio, Tracking Error, Beta, and Sharpe vs Nifty 500 TRI.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from invst.backtest.engine import run_walk_forward_backtest
from invst.config import get_config
from invst.ingestion.backfill_pit import run_historical_backfill
from invst.logging_utils import setup_logging

logger = logging.getLogger("invst.backtest_v2")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arth IQ V0.2 40-Quarter Walk-Forward Out-of-Sample Validation"
    )
    parser.add_argument("--db", default=None, help="Path to SQLite database")
    parser.add_argument("--start", default="2016-01-01", help="Simulation start date")
    parser.add_argument("--end", default="2026-09-30", help="Simulation end date")
    parser.add_argument("--capital", type=float, default=1_000_000.0, help="Initial capital in INR")
    parser.add_argument("--benchmark", default="NIFTY500", help="Benchmark ticker symbol")
    parser.add_argument("--profile", default="MODERATE", choices=["CONSERVATIVE", "MODERATE", "AGGRESSIVE"], help="Investor profile")
    parser.add_argument("--backfill", action="store_true", default=False, help="Run PIT backfill before testing")
    parser.add_argument("--backfill-only", action="store_true", default=False, help="Only run backfill and exit")
    args = parser.parse_args()

    setup_logging()
    cfg = get_config()
    db_path = args.db or str(cfg.database.path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    print("=" * 80)
    print("  ARTH IQ V0.2 — 40-QUARTER OUT-OF-SAMPLE WALK-FORWARD VALIDATION (2016–2026)")
    print("=" * 80)
    print(f"Database:         {db_path}")
    print(f"Simulation Range: {args.start} to {args.end}")
    print(f"Benchmark:        {args.benchmark} (Nifty 500 TRI)")
    print(f"Initial Capital:  ₹{args.capital:,.0f}")
    print(f"Investor Profile: {args.profile}")
    print("-" * 80)

    if args.backfill or args.backfill_only:
        print("\n>>> Executing Bi-Temporal Point-in-Time Historical Data Backfill...")
        summary = run_historical_backfill(conn, start_year=2015, end_year=2026)
        print("Backfill Ingestion Completed:")
        for k, v in summary.items():
            print(f"  • {k:<30}: {v:>8} rows")
        if args.backfill_only:
            conn.close()
            return 0

    print("\n>>> Executing Walk-Forward Simulation across 40 Quarters...")
    res = run_walk_forward_backtest(
        conn=conn,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        benchmark_symbol=args.benchmark,
        config_dict={"quant_engine": "v2", "investor_profile": args.profile},
    )

    m = res.metrics
    p_start = res.portfolio_equity[0] if res.portfolio_equity else args.capital
    p_end = res.portfolio_equity[-1] if res.portfolio_equity else args.capital
    _b_start = res.benchmark_equity[0] if res.benchmark_equity else args.capital
    b_end = res.benchmark_equity[-1] if res.benchmark_equity else args.capital

    print("\n" + "=" * 80)
    print("  INSTITUTIONAL PERFORMANCE & ALPHA VALIDATION REPORT")
    print("=" * 80)
    print(f"Run ID:                      {res.run_id}")
    print(f"Total Rebalance Quarters:    {m.rebalance_count} quarters")
    print(f"Trading Days Modeled:        {len(res.equity_dates)} trading sessions")
    print(f"Initial Portfolio Value:     ₹{p_start:,.2f}")
    print(f"Final Portfolio Value:       ₹{p_end:,.2f}")
    print(f"Final Benchmark Value:       ₹{b_end:,.2f}")
    print("-" * 80)
    print("ALPHA & ACTIVE RISK METRICS:")
    print(f"  ★ Annualized Alpha (Excess):    {m.alpha * 100:>+7.2f} %  (CAGR - Benchmark CAGR)")
    print(f"  ★ Information Ratio (IR):        {m.information_ratio:>7.2f}    (Active Return / Tracking Error)")
    print(f"  ★ Annualized Tracking Error:     {m.tracking_error * 100:>7.2f} %")
    print(f"  ★ Portfolio Beta:                {m.beta:>7.2f}")
    print(f"  ★ Jensen's Alpha:                {m.jensen_alpha * 100:>+7.2f} %")
    print("-" * 80)
    print("ABSOLUTE RETURN & DRAWDOWN METRICS:")
    print(f"  • Strategy CAGR:                 {m.cagr * 100:>7.2f} %  (vs Benchmark: {m.benchmark_cagr * 100:.2f}%)")
    print(f"  • Sharpe Ratio:                  {m.sharpe:>7.2f}    (vs Benchmark: {m.benchmark_sharpe:.2f})")
    print(f"  • Sortino Ratio:                 {m.sortino:>7.2f}")
    print(f"  • Calmar Ratio:                  {m.calmar:>7.2f}")
    print(f"  • Max Drawdown (Peak-to-Trough): {m.max_drawdown * 100:>7.2f} %  (vs Benchmark: {m.benchmark_max_drawdown * 100:.2f}%)")
    print(f"  • Annualized Volatility:         {m.annualized_vol * 100:>7.2f} %")
    print(f"  • Worst 5-Day Rolling Return:    {m.worst_5d_return * 100:>7.2f} %")
    print("-" * 80)
    print("EXECUTION & TURNOVER EFFICIENCY:")
    print(f"  • Average Annualized Turnover:   {m.turnover_avg * 100:>7.1f} %")
    print(f"  • Monthly Win Rate (Hit Rate):   {m.hit_rate * 100:>7.1f} % of months beating index")
    print("=" * 80)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
