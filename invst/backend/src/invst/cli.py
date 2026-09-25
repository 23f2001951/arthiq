"""Command Line Interface (CLI) for the invst platform.

Subcommands:
- ingest: Ingest daily bhavcopies, yfinance prices, fundamentals, or news
- score: Compute multi-stage quant scores for a given as-of date
- optimize: Run constrained portfolio optimization for target holdings
- backtest: Run walk-forward simulation across historical dates
- report: Render HTML and PDF reports for the latest portfolio recommendations
- monitor: Run data quality and integrity audits
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date

from invst.backtest.engine import run_walk_forward_backtest
from invst.config import get_config
from invst.data_access import PointInTimeDataAccess
from invst.logging_utils import setup_logging
from invst.optimization.mean_variance import estimate_returns_and_covariance, optimize_portfolio
from invst.reporting.report import generate_report_files
from invst.scoring.composite import compute_composite_scores, select_shortlist_with_sector_caps

logger = logging.getLogger("invst.cli")


def get_db_connection(db_path: str | None = None) -> Any:
    """Open a unified database connection supporting Neon PostgreSQL and SQLite."""
    from invst.db.engine import get_db_connection as _get_conn
    return _get_conn(db_path=db_path)



def cmd_ingest(args: argparse.Namespace) -> int:
    """Handler for `invst ingest`."""
    conn = get_db_connection(args.db)
    if getattr(args, "full", False):
        print("Executing full historical point-in-time backfill (2015–2026)...")
        from invst.ingestion.backfill_pit import run_historical_backfill

        summary = run_historical_backfill(conn)
        for k, v in summary.items():
            print(f"  - {k}: {v} rows")
        conn.close()
        return 0

    trade_date = date.fromisoformat(args.date) if args.date else date.today()
    print(f"Running ingestion for {trade_date.isoformat()} (full={args.full})...")

    # Call NSE bhavcopy ingestion
    try:
        from invst.ingestion.nse_bhavcopy import ingest_nse_bhavcopy

        count = ingest_nse_bhavcopy(conn, trade_date=trade_date)
        print(f"Ingested {count} NSE bhavcopy records")
    except Exception as e:
        print(f"NSE bhavcopy ingestion note: {e}")

    conn.close()
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Handler for `invst score`."""
    conn = get_db_connection(args.db)
    asof_date = date.fromisoformat(args.asof) if args.asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    print(f"Scoring universe as of {asof_date.isoformat()}...")
    scorecards = compute_composite_scores(pit, filter_universe_first=not args.all)
    if not scorecards:
        print("No stocks scored. Ensure database is populated with prices and constituents.")
        conn.close()
        return 1

    print(f"\nTop 10 Stocks by Composite Score (as of {asof_date.isoformat()}):")
    print(
        f"{'Rank':<5} {'Symbol':<12} {'Sector':<25} {'Composite':<10} {'Quality':<8} {'Valuation':<10} {'Risk':<8}"
    )
    print("-" * 80)
    for sc in scorecards[:10]:
        print(
            f"{sc.rank:<5} {sc.symbol:<12} {sc.sector[:24]:<25} {sc.composite_score:<10.1f} "
            f"{sc.quality_score:<8.1f} {sc.valuation_score:<10.1f} {sc.risk_score:<8.1f}"
        )

    conn.close()
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    """Handler for `invst optimize`."""
    conn = get_db_connection(args.db)
    asof_date = date.fromisoformat(args.asof) if args.asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    scorecards = compute_composite_scores(pit, filter_universe_first=True)
    if not scorecards:
        print("No candidates available for portfolio optimization.")
        conn.close()
        return 1

    shortlist = select_shortlist_with_sector_caps(scorecards, shortlist_size=args.shortlist_size)
    shortlist_symbols = [s.symbol for s in shortlist]
    sector_map = {s.symbol: s.sector for s in shortlist}

    mu, sigma, opt_symbols = estimate_returns_and_covariance(pit, shortlist_symbols)
    res = optimize_portfolio(
        symbols=opt_symbols,
        sector_map=sector_map,
        mu=mu,
        sigma=sigma,
        target_holdings=args.holdings,
        max_stock_weight=args.max_stock_cap,
        max_sector_weight=args.max_sector_cap,
    )

    print(f"\nOptimized Portfolio Allocations (as of {asof_date.isoformat()}):")
    print(f"{'Symbol':<12} {'Sector':<25} {'Target Weight':<15}")
    print("-" * 55)
    for sym, w in res.weights.items():
        if w > 0:
            print(f"{sym:<12} {sector_map.get(sym, 'general')[:24]:<25} {w * 100:>10.2f}%")

    print(
        f"\nExpected Return: {res.expected_return * 100:.2f}% | Expected Vol: {res.expected_volatility * 100:.2f}% | Sharpe: {res.sharpe_ratio:.2f}"
    )

    conn.close()
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    """Handler for `invst backtest`."""
    conn = get_db_connection(args.db)
    engine_ver = getattr(args, "engine", "v1").lower()
    profile = getattr(args, "profile", "MODERATE").upper()
    print(
        f"Running walk-forward backtest from {args.start} to {args.end} [Engine={engine_ver.upper()}, Profile={profile}]..."
    )
    res = run_walk_forward_backtest(
        conn=conn,
        start_date=args.start,
        end_date=args.end,
        benchmark_symbol=args.benchmark,
        config_dict={"quant_engine": engine_ver, "investor_profile": profile},
    )

    m = res.metrics
    print("\nBacktest Performance Summary:")
    print("=" * 50)
    print(f"Run ID:            {res.run_id}")
    print(f"Engine Version:    {engine_ver.upper()}")
    print(f"CAGR:              {m.cagr * 100:.2f}% (Benchmark: {m.benchmark_cagr * 100:.2f}%)")
    print(f"Alpha (Excess):    {m.alpha * 100:+.2f}%")
    print(f"Information Ratio: {m.information_ratio:.2f}")
    print(f"Tracking Error:    {m.tracking_error * 100:.2f}%")
    print(f"Portfolio Beta:    {m.beta:.2f}")
    print(f"Jensen's Alpha:    {m.jensen_alpha * 100:+.2f}%")
    print(f"Sharpe Ratio:      {m.sharpe:.2f} (Benchmark: {m.benchmark_sharpe:.2f})")
    print(f"Sortino Ratio:     {m.sortino:.2f}")
    print(f"Calmar Ratio:      {m.calmar:.2f}")
    print(
        f"Max Drawdown:      {m.max_drawdown * 100:.2f}% (Benchmark: {m.benchmark_max_drawdown * 100:.2f}%)"
    )
    print(f"Turnover (ann.):   {m.turnover_avg * 100:.1f}%")
    print(f"Monthly Hit Rate:  {m.hit_rate * 100:.1f}%")
    print(f"Rebalances:        {m.rebalance_count}")

    conn.close()
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Handler for `invst report`."""
    conn = get_db_connection(args.db)
    asof_date = date.fromisoformat(args.asof) if args.asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    scorecards = compute_composite_scores(pit, filter_universe_first=False)
    if not scorecards:
        print("No scored holdings found to generate report.")
        conn.close()
        return 1

    top_holdings = scorecards[:8]
    holdings_data = [
        {
            "symbol": sc.symbol,
            "sector": sc.sector,
            "action": "BUY",
            "target_weight": 0.125,
            "current_weight": 0.0,
            "scorecard": {
                "composite_score": sc.composite_score,
                "quality_score": sc.quality_score,
                "valuation_score": sc.valuation_score,
                "risk_score": sc.risk_score,
                "sentiment_overlay_points": sc.sentiment_overlay_points,
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
                "sentiment_details": sc.sentiment_details,
            },
        }
        for sc in top_holdings
    ]

    out_files = generate_report_files(
        asof_date=asof_date, holdings_data=holdings_data, output_dir=args.out
    )
    for fmt, path in out_files.items():
        print(f"Report written ({fmt}): {path}")

    conn.close()
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    """Handler for `invst monitor`."""
    conn = get_db_connection(args.db)
    print("Running system monitoring and data quality checks...")

    tables = [
        "daily_prices",
        "fundamentals_quarterly",
        "index_constituents_history",
        "news_sentiment",
    ]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  - Table {t:<28}: {count:>8} rows")

    # Check for future dates
    today_str = date.today().isoformat()
    future_funds = conn.execute(
        "SELECT COUNT(*) FROM fundamentals_quarterly WHERE disclosed_at > ?", (today_str,)
    ).fetchone()[0]
    if future_funds > 0:
        print(f"  [ALERT] {future_funds} fundamental records have future disclosed_at dates!")
    else:
        print("  [OK] No future disclosure dates detected (PIT integrity intact).")

    conn.close()
    return 0


def cmd_pick(args: argparse.Namespace) -> int:
    """Handler for `invst pick` (top 1-2 stock quick picks)."""
    conn = get_db_connection(args.db)
    asof_date = date.fromisoformat(args.asof) if args.asof else date.today()
    pit = PointInTimeDataAccess(conn, asof=asof_date)

    print(f"Selecting top {args.n} high-conviction quick pick(s) as of {asof_date.isoformat()}...")
    scorecards = compute_composite_scores(pit, filter_universe_first=not args.all)
    if not scorecards:
        print("No scored candidates found.")
        conn.close()
        return 1

    from invst.reporting.rationale import generate_plain_english_rationale
    from invst.scoring.composite import select_quick_picks

    exclude_symbols = []
    if args.exclude_holdings:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol FROM portfolio_history
            WHERE run_id = (SELECT run_id FROM portfolio_history ORDER BY asof_date DESC LIMIT 1)
            """
        )
        exclude_symbols = [r[0] for r in cur.fetchall()]

    picks = select_quick_picks(
        scorecards, n=args.n, exclude_symbols=exclude_symbols, max_per_sector=1
    )
    if not picks:
        print("No picks matched the criteria.")
        conn.close()
        return 1

    weight_per_pick = 1.0 / len(picks)
    print("\n" + "=" * 75)
    print(f"  TOP {len(picks)} QUICK PICK(S) FOR TACTICAL DEPLOYMENT ({asof_date.isoformat()})")
    print("=" * 75)

    for rank, sc in enumerate(picks, start=1):
        price = pit.get_price(sc.symbol, asof_date)
        alloc_amt = (args.capital * weight_per_pick) if args.capital else None
        alloc_str = (
            f"₹{alloc_amt:,.0f} ({weight_per_pick * 100:.1f}%)"
            if alloc_amt
            else f"{weight_per_pick * 100:.1f}%"
        )

        print(f"\n#{rank} {sc.symbol} ({sc.sector.replace('_', ' ').title()})")
        print(f"   Latest Close: {f'₹{price:,.2f}' if price else 'N/A'} | Allocation: {alloc_str}")
        print(
            f"   Composite: {sc.composite_score:.1f}/100 | Quality: {sc.quality_score:.1f} | "
            f"Valuation: {sc.valuation_score:.1f} | Risk: {sc.risk_score:.1f}"
        )

        rationale = generate_plain_english_rationale(
            symbol=sc.symbol,
            company_name=sc.symbol,
            sector=sc.sector,
            action="BUY",
            target_weight=weight_per_pick,
            current_weight=0.0,
            scorecard={
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
                "sentiment_details": sc.sentiment_details,
            },
        )
        print(f"   Rationale: {rationale}\n")

    conn.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Handler for `invst serve`."""
    import uvicorn

    print(
        f"Starting invst FastAPI server on http://{args.host}:{args.port} (Interactive API docs at http://{args.host}:{args.port}/docs)"
    )
    uvicorn.run("invst.api.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--db", default=None, help="Path to SQLite database file")

    parser = argparse.ArgumentParser(
        prog="invst",
        description="Personal Investment Decision-Support Tool",
        parents=[common_parser],
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # ingest
    p_ingest = subparsers.add_parser(
        "ingest", help="Ingest market data and filings", parents=[common_parser]
    )
    p_ingest.add_argument("--date", default=None, help="Trade date (YYYY-MM-DD)")
    p_ingest.add_argument("--full", action="store_true", help="Backfill full historical data")

    # score
    p_score = subparsers.add_parser(
        "score", help="Score universe on Quality/Valuation/Risk/Sentiment", parents=[common_parser]
    )
    p_score.add_argument("--asof", default=None, help="As-of date (YYYY-MM-DD)")
    p_score.add_argument("--all", action="store_true", help="Score all without Stage 0 filter")

    # optimize
    p_opt = subparsers.add_parser(
        "optimize", help="Run constrained portfolio optimization", parents=[common_parser]
    )
    p_opt.add_argument("--asof", default=None, help="As-of date (YYYY-MM-DD)")
    p_opt.add_argument("--holdings", type=int, default=8, help="Target number of holdings")
    p_opt.add_argument("--shortlist-size", type=int, default=15, help="Shortlist size")
    p_opt.add_argument(
        "--max-stock-cap", type=float, default=0.25, help="Max single-stock weight cap"
    )
    p_opt.add_argument("--max-sector-cap", type=float, default=0.40, help="Max sector weight cap")

    # backtest
    p_bt = subparsers.add_parser(
        "backtest", help="Run walk-forward backtest", parents=[common_parser]
    )
    p_bt.add_argument("--start", default="2016-01-01", help="Start date (YYYY-MM-DD)")
    p_bt.add_argument("--end", default="2026-09-30", help="End date (YYYY-MM-DD)")
    p_bt.add_argument("--benchmark", default="NIFTY500", help="Benchmark ticker symbol")
    p_bt.add_argument(
        "--engine",
        choices=["v1", "v2"],
        default="v1",
        help="Quantitative scoring & optimization engine version (v1 or v2)",
    )
    p_bt.add_argument(
        "--profile",
        choices=["CONSERVATIVE", "MODERATE", "AGGRESSIVE"],
        default="MODERATE",
        help="Investor risk profile for V0.2 HRP optimizer",
    )

    # backfill
    p_bf = subparsers.add_parser(
        "backfill",
        help="Run full historical PIT and price backfill (2015-2026)",
        parents=[common_parser],
    )
    p_bf.add_argument("--start-year", type=int, default=2015, help="Start year")
    p_bf.add_argument("--end-year", type=int, default=2026, help="End year")

    # report
    p_rep = subparsers.add_parser(
        "report", help="Generate HTML/PDF recommendation report", parents=[common_parser]
    )
    p_rep.add_argument("--asof", default=None, help="As-of date (YYYY-MM-DD)")
    p_rep.add_argument("--out", default="reports", help="Output directory for reports")

    # monitor
    subparsers.add_parser(
        "monitor", help="Run data quality and system audits", parents=[common_parser]
    )

    # pick
    p_pick = subparsers.add_parser(
        "pick",
        help="Suggest top 1 or 2 high-conviction stocks for tactical / fresh capital deployment",
        parents=[common_parser],
    )
    p_pick.add_argument("--n", type=int, default=2, help="Number of picks (1 or 2 recommended)")
    p_pick.add_argument("--asof", default=None, help="As-of date (YYYY-MM-DD)")
    p_pick.add_argument(
        "--capital", type=float, default=None, help="Available fresh capital in INR to allocate"
    )
    p_pick.add_argument("--all", action="store_true", help="Skip Stage 0 filters")
    p_pick.add_argument(
        "--exclude-holdings",
        action="store_true",
        default=True,
        help="Exclude symbols in current portfolio",
    )

    # serve
    p_serve = subparsers.add_parser(
        "serve", help="Launch FastAPI REST server", parents=[common_parser]
    )
    p_serve.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")

    # pulse (live macro regime)
    subparsers.add_parser(
        "pulse", help="Display live macroeconomic regime and India VIX pulse", parents=[common_parser]
    )

    # live-sync (refresh live prices and news for symbols)
    p_sync = subparsers.add_parser(
        "live-sync", help="Fetch and ingest live quotes and news for specific symbols", parents=[common_parser]
    )
    p_sync.add_argument(
        "--symbols", default="TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK", help="Comma-separated stock symbols"
    )

    # analyze (on-demand stock diagnosis & scenario forecast)
    p_ana = subparsers.add_parser(
        "analyze", help="On-demand single stock diagnosis, 3M/6M/12M/3Y return projections, and verdict", parents=[common_parser]
    )
    p_ana.add_argument("--symbol", required=True, help="Stock ticker (e.g. TCS, RELIANCE, INFY)")

    # portfolio (personal portfolio health diagnosis & position advisory)
    p_port = subparsers.add_parser(
        "portfolio", help="Personal portfolio health diagnostic and position-level BUY/SELL/HOLD advice", parents=[common_parser]
    )
    p_port.add_argument(
        "--holdings", default=None, help="Holdings string: 'TCS:10:1400,INFY:20:1900,RELIANCE:15:2200'"
    )
    p_port.add_argument("--csv", default=None, help="Path to portfolio CSV file")

    return parser


def cmd_backfill(args: argparse.Namespace) -> int:
    """Handler for `invst backfill`."""
    conn = get_db_connection(args.db)
    print(
        f"Executing full historical point-in-time backfill ({args.start_year}–{args.end_year})..."
    )
    from invst.ingestion.backfill_pit import run_historical_backfill

    summary = run_historical_backfill(conn, start_year=args.start_year, end_year=args.end_year)
    for k, v in summary.items():
        print(f"  - {k}: {v} rows")
    conn.close()
    return 0


def cmd_pulse(args: argparse.Namespace) -> int:
    """Handler for `invst pulse`."""
    from invst.ingestion.live_market_feed import fetch_live_macro_pulse

    print("\n" + "=" * 65)
    print("  ARTH IQ — MACRO REGIME & MARKET PULSE")
    print("=" * 65)
    pulse = fetch_live_macro_pulse()

    source_tag = "[LIVE FEED]" if pulse.get("is_live") else "[OFFLINE / DEFAULT]"
    print(f"Status:       {source_tag}")
    print(f"As-Of Date:   {pulse['asof_date']}")
    print(f"India VIX:    {pulse['india_vix']:.2f}")
    print(f"Nifty 50:     {pulse['nifty_50']:,.2f}")
    print(f"USD / INR:    ₹{pulse['usd_inr']:.2f}")
    print(f"Macro Regime: {pulse['regime']}")
    print(f"\nPolicy & Implication:\n  {pulse['regime_description']}\n")
    return 0


def cmd_live_sync(args: argparse.Namespace) -> int:
    """Handler for `invst live-sync`."""
    from invst.ingestion.live_market_feed import (
        fetch_live_ticker_snapshot,
        ingest_live_ticker_to_db,
    )

    conn = get_db_connection(args.db)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    print("\n" + "=" * 80)
    print(f"  LIVE SYNC — Ingesting Real-Time Market Data for {len(symbols)} Stocks")
    print("=" * 80)
    print(f"{'Symbol':<12} {'Live Price':<14} {'1D Chg %':<10} {'P/E':<8} {'Status':<15}")
    print("-" * 80)

    for sym in symbols:
        snapshot = fetch_live_ticker_snapshot(sym, conn=conn)
        ingest_live_ticker_to_db(conn, sym, snapshot=snapshot)
        feed_type = "Live" if snapshot.get("is_live") else "Cached/DB"
        chg_sign = "+" if snapshot['change_pct'] >= 0 else ""
        print(
            f"{sym:<12} ₹{snapshot['current_price']:<13,.2f} {chg_sign}{snapshot['change_pct']:.2f}%{'':<3} "
            f"{snapshot['pe_ratio']:<8.1f} {feed_type:<15}"
        )

    print("-" * 80)
    print(f"Completed live sync for {len(symbols)} symbols.\n")
    conn.close()
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handler for `invst analyze`."""
    from invst.scoring.stock_analyzer import analyze_stock_on_demand

    conn = get_db_connection(args.db)
    sym = args.symbol.strip().upper()
    print(f"\nAnalyzing {sym} with real-time quantitative and scenario models...")

    res = analyze_stock_on_demand(conn, sym)

    print("\n" + "=" * 80)
    print(f"  ARTH IQ STOCK DIAGNOSTIC REPORT: {res.symbol} ({res.company_name})")
    print("=" * 80)
    print(f"Sector:           {res.sector.title()} ({res.sector_archetype})")
    print(f"Current Price:    ₹{res.current_price:,.2f} ({'+' if res.change_pct >= 0 else ''}{res.change_pct:.2f}%)")
    print(f"52-Week Range:    ₹{res.low_52w:,.2f} - ₹{res.high_52w:,.2f}")
    if res.dma_50 > 0:
        print(f"Technicals:       50-DMA: ₹{res.dma_50:,.2f} | 200-DMA: ₹{res.dma_200:,.2f}")

    print("\n--- QUANTITATIVE SCORES ---")
    print(f"Business Quality Score: {res.business_quality_score:.1f}/100")
    print(f"Growth Score:           {res.growth_score:.1f}/100")
    print(f"Business Score:         {res.business_score:.1f}/100")
    print(f"Valuation Score:        {res.valuation_score:.1f}/100")
    print(f"Risk Score:             {res.risk_score:.1f}/100")
    print(f"Investment Score:       {res.investment_score:.1f}/100 (Core Decision Metric)")

    print("\n--- MATRIX QUADRANT & VERDICT ---")
    print(f"Matrix Quadrant:        {res.matrix_quadrant}")
    print(f"Action Verdict:         {res.verdict_badge}")
    print(f"Investment Worthy?      {'YES' if res.is_investment_worthy else 'NO / CAUTION'}")

    if res.redlines_triggered:
        print("\n🚨 REDLINE ALERTS:")
        for r in res.redlines_triggered:
            print(f"  - {r}")
    else:
        print("\n✅ Redline Safety Audit: Clean (0 redlines triggered)")

    print("\n--- MULTI-HORIZON RETURN PROJECTIONS ---")
    print(f"{'Horizon':<10} {'Bear':<12} {'Base':<12} {'Bull':<12} {'Expected':<12} {'Downside/Upside':<16}")
    print("-" * 76)
    for h in [res.horizon_3m, res.horizon_6m, res.horizon_12m, res.horizon_3y]:
        cagr_str = f" ({h.cagr_pct:.1f}% p.a.)" if h.cagr_pct else ""
        print(
            f"{h.horizon:<10} {h.return_bear_pct:>+6.1f}%     {h.return_base_pct:>+6.1f}%     "
            f"{h.return_bull_pct:>+6.1f}%     {h.expected_return_pct:>+6.1f}%{cagr_str:<8} "
            f"{h.downside_to_upside_ratio:>6.2f}x"
        )

    print("\n--- INVESTMENT THESIS & RATIONALE ---")
    print(f"{res.thesis_rationale}\n")

    conn.close()
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    """Handler for `invst portfolio`."""
    import csv

    from invst.portfolio.health import (
        UserHolding,
        evaluate_portfolio_health,
        load_user_holdings,
        save_user_holdings,
    )

    conn = get_db_connection(args.db)
    holdings: list[UserHolding] = []

    if args.holdings:
        for item in args.holdings.split(","):
            parts = [p.strip() for p in item.split(":") if p.strip()]
            if len(parts) >= 3:
                holdings.append(
                    UserHolding(symbol=parts[0].upper(), shares=float(parts[1]), buy_price=float(parts[2]))
                )
    elif args.csv:
        with open(args.csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get("symbol") or row.get("Symbol") or row.get("ticker")
                sh = row.get("shares") or row.get("Shares") or row.get("quantity") or row.get("qty")
                bp = row.get("buy_price") or row.get("price") or row.get("avg_price")
                if sym and sh and bp:
                    holdings.append(UserHolding(symbol=sym.strip().upper(), shares=float(sh), buy_price=float(bp)))
    else:
        # Load existing holdings from DB
        holdings = load_user_holdings(conn)

    if not holdings:
        print("\nNo portfolio holdings provided. Use `--holdings 'TCS:10:1400,INFY:20:1900'` or `--csv path/to/file.csv`.")
        conn.close()
        return 1

    # Save active holdings
    save_user_holdings(conn, holdings)

    print(f"\nEvaluating health for portfolio of {len(holdings)} holdings...")
    report = evaluate_portfolio_health(conn, holdings)

    print("\n" + "=" * 80)
    print("  ARTH IQ PERSONAL PORTFOLIO HEALTH DIAGNOSTIC & ADVISORY")
    print("=" * 80)
    print(f"As-Of Date:         {report.asof_date}")
    print(f"Total Invested:     ₹{report.total_invested:,.2f}")
    print(f"Current Value:      ₹{report.total_current_value:,.2f}")
    pnl_sign = "+" if report.total_unrealized_pnl >= 0 else ""
    print(f"Unrealized P&L:     {pnl_sign}₹{report.total_unrealized_pnl:,.2f} ({pnl_sign}{report.total_unrealized_pnl_pct:.2f}%)")
    print(f"Portfolio Health:   {report.overall_health_score:.1f}/100 (Grade: {report.overall_health_grade})")
    print(f"Weighted Quality:   {report.weighted_business_score:.1f}/100 | Weighted Valuation: {report.weighted_valuation_score:.1f}/100")

    if report.critical_redline_alerts:
        print("\n🚨 CRITICAL REDLINE WARNINGS:")
        for r in report.critical_redline_alerts:
            print(f"  - {r}")

    if report.sector_warnings:
        print("\n⚠️ SECTOR CONCENTRATION ALERTS:")
        for sw in report.sector_warnings:
            print(f"  - {sw}")

    print("\n" + "-" * 80)
    print(f"{'Symbol':<10} {'Shares':<8} {'Cur Price':<11} {'Value':<12} {'Weight':<8} {'P&L %':<10} {'Advice':<18}")
    print("-" * 80)
    for p in report.positions:
        pos_pnl_sign = "+" if p.unrealized_pnl >= 0 else ""
        print(
            f"{p.symbol:<10} {p.shares:<8.0f} ₹{p.current_price:<10,.1f} ₹{p.current_value:<11,.0f} "
            f"{p.weight_pct:>5.1f}%   {pos_pnl_sign}{p.unrealized_pnl_pct:>5.1f}%    {p.action_badge:<18}"
        )
        print(f"   ↳ {p.action_rationale}")

    print("-" * 80)
    print(f"Summary Action Plan: {report.summary_action_plan}\n")

    conn.close()
    return 0


def main() -> None:
    """Entry point for CLI execution."""
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "ingest": cmd_ingest,
        "backfill": cmd_backfill,
        "score": cmd_score,
        "optimize": cmd_optimize,
        "backtest": cmd_backtest,
        "report": cmd_report,
        "monitor": cmd_monitor,
        "serve": cmd_serve,
        "pick": cmd_pick,
        "pulse": cmd_pulse,
        "live-sync": cmd_live_sync,
        "analyze": cmd_analyze,
        "portfolio": cmd_portfolio,
    }

    handler = dispatch.get(args.command)
    if handler:
        sys.exit(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

