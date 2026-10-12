"""
IIM Phase 0 Backtest Script.

Downloads 60 days of 15m data for a representative set of NSE F&O stocks,
runs both strategies through the signal engine, and prints the gate report.

Usage:
    python run_backtest.py

Gate requirements (ALL must pass before live use):
  GATE A: E_net > +0.15R after costs
  GATE B: 90% CI lower bound > 0.0R
  GATE C: Profit Factor > 1.4
  GATE D: Max consecutive R drawdown < 6R
  GATE E: Sample ≥ 200 closed trades
"""

import sys
import logging
import time
from datetime import timezone, timedelta

import pandas as pd
import yfinance as yf

sys.path.insert(0, './invst/backend/src')

logging.basicConfig(
    level=logging.WARNING,  # suppress debug noise during backtest
    format='%(levelname)s  %(name)s: %(message)s',
)
logger = logging.getLogger("backtest")

from invst.intraday.indicators import apply_all_indicators
from invst.intraday.backtest_runner import run_backtest, BacktestResults, TradeResult

IST = timezone(timedelta(hours=5, minutes=30))

# ── Symbols to backtest ─────────────────────────────────────────────────────
# Representative cross-sector F&O basket
SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "BHARTIARTL", "SBIN", "KOTAKBANK", "LT", "BAJFINANCE",
    "AXISBANK", "MARUTI", "TATAMOTORS", "SUNPHARMA", "WIPRO",
    "HCLTECH", "NTPC", "ONGC", "TATASTEEL", "HINDALCO",
]
NIFTY_SYMBOL = "^NSEI"
PERIOD = "60d"
INTERVAL = "15m"

def fetch(symbol: str, is_nifty: bool = False) -> pd.DataFrame | None:
    yf_sym = symbol if is_nifty else f"{symbol}.NS"
    try:
        df = yf.download(yf_sym, period=PERIOD, interval=INTERVAL,
                         progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 100:
            return None
        # Flatten MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        df = df.dropna(subset=['close', 'volume'])
        # Remove the current incomplete candle (last bar)
        now_ist = pd.Timestamp.now(tz=IST)
        df = df[df.index < now_ist - pd.Timedelta(minutes=14)]
        return df
    except Exception as e:
        logger.warning("[%s] fetch error: %s", symbol, e)
        return None


def merge_results(results_list: list[BacktestResults]) -> BacktestResults:
    """Merge individual symbol results into a combined portfolio result."""
    from invst.intraday.backtest_runner import BacktestResults
    all_trades = []
    for r in results_list:
        all_trades.extend(r.trades)
    
    if not all_trades:
        merged = BacktestResults(
            strategy_id=results_list[0].strategy_id if results_list else "UNKNOWN",
            symbol="ALL_SYMBOLS",
            start_date="N/A", end_date="N/A",
            trades=[],
        )
        return merged
    
    dates = sorted(set(t.entry_time.date() for t in all_trades if t.entry_time))
    merged = BacktestResults(
        strategy_id=results_list[0].strategy_id,
        symbol=f"ALL ({len(results_list)} symbols)",
        start_date=str(dates[0]) if dates else "N/A",
        end_date=str(dates[-1]) if dates else "N/A",
        trades=all_trades,
        backtest_run_id=results_list[0].backtest_run_id,
    )
    merged.compute_metrics(n_bootstrap=2000)
    return merged


def print_banner(text: str):
    print("\n" + "═" * 68)
    print(f"  {text}")
    print("═" * 68)


# ═══════════════════════════════════════════════════════════════════════════
print_banner("ArthIQ IIM — Phase 0 Backtest (60-day, 15m)")
print(f"  Symbols: {len(SYMBOLS)}")
print(f"  Period: {PERIOD} | Interval: {INTERVAL}")
print(f"  Strategies: TREND_PULLBACK, INTRADAY_BREAKOUT")
print(f"  Cost model: 0.18R per round-trip (brokerage + STT + slippage)")

# ── 1. Fetch Nifty50 ────────────────────────────────────────────────────────
print("\n[1/3] Fetching Nifty50 data for regime detection...")
nifty_raw = fetch(NIFTY_SYMBOL, is_nifty=True)
if nifty_raw is None:
    print("❌ Could not fetch Nifty50 data. Abort.")
    sys.exit(1)
nifty_df = apply_all_indicators(nifty_raw)
print(f"  ✅ Nifty50: {len(nifty_raw)} bars, {nifty_raw.index[0].date()} → {nifty_raw.index[-1].date()}")

# ── 2. Fetch stock data ─────────────────────────────────────────────────────
print(f"\n[2/3] Fetching stock data ({len(SYMBOLS)} symbols)...")
stock_data: dict[str, pd.DataFrame] = {}
for sym in SYMBOLS:
    df = fetch(sym)
    if df is not None:
        stock_data[sym] = df
        print(f"  ✅ {sym:16s} {len(df):5d} bars")
    else:
        print(f"  ⚠️  {sym:16s} skipped (insufficient data)")

print(f"\n  {len(stock_data)}/{len(SYMBOLS)} symbols loaded")

# ── 3. Run backtest ─────────────────────────────────────────────────────────
print(f"\n[3/3] Running backtest...\n")

all_pullback: list[BacktestResults] = []
all_breakout: list[BacktestResults] = []
symbol_summary_rows = []

for sym, df_raw in stock_data.items():
    t0 = time.time()
    for strategy_name, results_list in [
        ("TREND_PULLBACK", all_pullback),
        ("INTRADAY_BREAKOUT", all_breakout),
    ]:
        try:
            result = run_backtest(
                df_15m=df_raw,
                nifty_15m=nifty_raw,
                strategy=strategy_name,
                symbol=sym,
                n_bootstrap=500,  # faster per symbol; final merge uses 2000
            )
            results_list.append(result)
        except Exception as e:
            logger.warning("[%s][%s] backtest error: %s", sym, strategy_name, e)

    elapsed = time.time() - t0
    pb = all_pullback[-1] if all_pullback else None
    bo = all_breakout[-1] if all_breakout else None
    if pb and bo:
        print(f"  {sym:16s}  PB: {pb.total_trades:3d} trades E={pb.expectancy_net:+.3f}R | "
              f"BO: {bo.total_trades:3d} trades E={bo.expectancy_net:+.3f}R  ({elapsed:.1f}s)")
        symbol_summary_rows.append({
            "symbol": sym,
            "pb_trades": pb.total_trades, "pb_enet": pb.expectancy_net, "pb_wr": pb.win_rate,
            "bo_trades": bo.total_trades, "bo_enet": bo.expectancy_net, "bo_wr": bo.win_rate,
        })

# ── 4. Merge and report ─────────────────────────────────────────────────────
print_banner("COMBINED RESULTS — TREND_PULLBACK")
if all_pullback:
    combined_pb = merge_results(all_pullback)
    print(combined_pb.gate_summary())
else:
    print("  No TREND_PULLBACK results.")

print_banner("COMBINED RESULTS — INTRADAY_BREAKOUT")
if all_breakout:
    combined_bo = merge_results(all_breakout)
    print(combined_bo.gate_summary())
else:
    print("  No INTRADAY_BREAKOUT results.")

# ── 5. Per-symbol summary table ─────────────────────────────────────────────
print_banner("PER-SYMBOL SUMMARY")
print(f"{'Symbol':16s} {'PB Trades':>9} {'PB E_net':>8} {'PB WR%':>6} | {'BO Trades':>9} {'BO E_net':>8} {'BO WR%':>6}")
print("-" * 68)
for row in symbol_summary_rows:
    print(f"{row['symbol']:16s} {row['pb_trades']:>9d} {row['pb_enet']:>+8.3f}R {row['pb_wr']*100:>5.1f}% "
          f"| {row['bo_trades']:>9d} {row['bo_enet']:>+8.3f}R {row['bo_wr']*100:>5.1f}%")

# ── 6. Final verdict ─────────────────────────────────────────────────────────
print_banner("PHASE 0 GATE VERDICT")
pb_pass = combined_pb.all_gates_pass() if all_pullback else False
bo_pass = combined_bo.all_gates_pass() if all_breakout else False

if pb_pass and bo_pass:
    print("  🟢 BOTH strategies PASSED Phase 0.")
    print("  ✅ Proceed to paper trading phase.")
elif pb_pass:
    print("  🟡 TREND_PULLBACK passed. INTRADAY_BREAKOUT FAILED.")
    print("  ⚠️  Deploy TREND_PULLBACK only. Investigate breakout signal conditions.")
elif bo_pass:
    print("  🟡 INTRADAY_BREAKOUT passed. TREND_PULLBACK FAILED.")
    print("  ⚠️  Deploy INTRADAY_BREAKOUT only. Investigate pullback signal conditions.")
else:
    print("  🔴 NEITHER strategy passed Phase 0 gates.")
    print("  ❌ Do NOT deploy live signals. Review signal conditions and costs.")
    print("  💡 Typical causes:")
    print("     1. Thresholds too strict → too few trades (n<200)")
    print("     2. TODVOL ratio baseline unavailable → falls back to 20-bar avg (acceptable)")
    print("     3. Market was strongly trending in one direction only")
    print("     4. Review GATE E first — if n<200, loosen filters before assuming alpha failure")

print()
