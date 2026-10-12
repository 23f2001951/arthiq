"""
Run Entry Feature Study across 18 NSE F&O Stocks.

Evaluates raw forward returns (2, 4, 8, 16 bars) for:
  1. ORB Breakout (9:15–9:45 Range) + Above Average Volume
  2. Previous Day High / Low Breakout
  3. VWAP Pullback / Bounce
  4. Gap & Go Momentum (Gap >= 0.75% with trend continuation)
"""

import sys
sys.path.insert(0, './invst/backend/src')
import yfinance as yf
import pandas as pd
import numpy as np

from invst.intraday.entry_study import (
    IndianIntradayCostModel,
    analyze_feature_forward_returns,
)
from invst.intraday.indicators import apply_all_indicators

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "SBIN.NS", "KOTAKBANK.NS", "LT.NS", "BAJFINANCE.NS",
    "AXISBANK.NS", "SUNPHARMA.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "TATASTEEL.NS", "HINDALCO.NS"
]

print("Fetching 60 days of 15m data for feature evaluation...")
stock_dfs = {}
for sym in SYMBOLS:
    df = yf.download(sym, period="60d", interval="15m", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0].lower() for c in df.columns]
    df = apply_all_indicators(df)
    
    # Calculate TODVOL
    df['slot'] = df.index.strftime('%H:%M')
    slot_vol = df.groupby('slot')['volume'].mean()
    df['todvol_ratio'] = df.apply(lambda r: r['volume'] / slot_vol[r['slot']] if slot_vol[r['slot']] > 0 else 1.0, axis=1)
    df['date'] = df.index.date
    stock_dfs[sym] = df

cost_model = IndianIntradayCostModel()
hurdle_bps = cost_model.calculate_round_trip_cost_bps(100000.0)
print(f"Realistic Cost Hurdle: {hurdle_bps:.1f} bps (brokerage + STT + turnover + slippage)\n")

# ---------------------------------------------------------------------------
# Build Observation Dataset across all symbols
# ---------------------------------------------------------------------------
horizons = [2, 4, 8, 16] # 30m, 1h, 2h, 4h
records = []

for sym, df in stock_dfs.items():
    dates = sorted(df['date'].unique())
    for d_idx, d in enumerate(dates[1:], 1):
        prev_d = dates[d_idx - 1]
        prev_day = df[df['date'] == prev_d]
        if prev_day.empty: continue
        pdh = float(prev_day['high'].max())
        pdl = float(prev_day['low'].min())
        pdclose = float(prev_day['close'].iloc[-1])
        
        day_df = df[df['date'] == d]
        if len(day_df) < 8: continue
        
        orb_bars = day_df[day_df.index.map(lambda t: t.time() < pd.to_datetime("09:45").time())]
        orb_h = float(orb_bars['high'].max()) if not orb_bars.empty else None
        orb_l = float(orb_bars['low'].min()) if not orb_bars.empty else None
        day_open = float(day_df.iloc[0]['open'])
        
        for i in range(len(day_df)):
            ts = day_df.index[i]
            t = ts.time()
            if t < pd.to_datetime("09:45").time() or t >= pd.to_datetime("14:30").time():
                continue
                
            cur = day_df.iloc[i]
            close = float(cur['close'])
            low = float(cur['low'])
            high = float(cur['high'])
            vwap = float(cur['vwap'])
            todvol = float(cur['todvol_ratio'])
            
            if i + 1 >= len(day_df): continue
            next_open = float(day_df.iloc[i+1]['open'])
            
            fwd_rets = {}
            for h in horizons:
                exit_idx = min(i + 1 + h, len(day_df) - 1)
                exit_price = float(day_df.iloc[exit_idx]['open'])
                fwd_rets[h] = (exit_price - next_open) / next_open

            # 1. ORB Long / Short
            feat_orb_long = (orb_h is not None) and (close > orb_h) and (close > vwap) and (todvol >= 1.4)
            feat_orb_short = (orb_l is not None) and (close < orb_l) and (close < vwap) and (todvol >= 1.4)
            
            # 2. PDH / PDL Breakout
            feat_pdh_long = (close > pdh) and (close > vwap) and (todvol >= 1.3)
            feat_pdl_short = (close < pdl) and (close < vwap) and (todvol >= 1.3)
            
            # 3. VWAP Pullback Bounce
            feat_vwap_pb_long = (close > vwap) and (low <= vwap * 1.002) and (todvol >= 1.2)
            feat_vwap_pb_short = (close < vwap) and (high >= vwap * 0.998) and (todvol >= 1.2)
            
            # 4. Morning Gap & Go (Gap >= 0.75%)
            gap_pct = (day_open - pdclose) / pdclose
            feat_gap_go_long = (gap_pct >= 0.0075) and (close > day_open) and (close > vwap)
            feat_gap_go_short = (gap_pct <= -0.0075) and (close < day_open) and (close < vwap)

            base_row = {
                "symbol": sym, "date": d, "timestamp": ts, "close": close, "next_open": next_open
            }
            for h in horizons:
                base_row[f"fwd_ret_{h}"] = fwd_rets[h]
                
            base_row["feat_orb_long"] = feat_orb_long
            base_row["feat_orb_short"] = feat_orb_short
            base_row["feat_pdh_long"] = feat_pdh_long
            base_row["feat_pdl_short"] = feat_pdl_short
            base_row["feat_vwap_pb_long"] = feat_vwap_pb_long
            base_row["feat_vwap_pb_short"] = feat_vwap_pb_short
            base_row["feat_gap_go_long"] = feat_gap_go_long
            base_row["feat_gap_go_short"] = feat_gap_go_short

            records.append(base_row)

df_all = pd.DataFrame(records)
print(f"Total bar observations collected: {len(df_all)}\n")

# ---------------------------------------------------------------------------
# Evaluate Each Feature Family across Horizons
# ---------------------------------------------------------------------------

feature_families = [
    ("Opening Range Breakout (ORB + Vol)", "feat_orb_long", "feat_orb_short"),
    ("Previous Day High/Low Breakout", "feat_pdh_long", "feat_pdl_short"),
    ("VWAP Pullback / Support Test", "feat_vwap_pb_long", "feat_vwap_pb_short"),
    ("Gap & Go Momentum (Gap >= 0.75%)", "feat_gap_go_long", "feat_gap_go_short"),
]

print("=" * 86)
print(f"{'Feature Family':<34} {'Horizon':<8} {'n':<6} {'Days':<6} {'Gross bps':<11} {'Net bps':<9} {'t-stat':<8} {'p-val':<7} {'Verdict'}")
print("=" * 86)

for family_name, long_col, short_col in feature_families:
    for h in horizons:
        df_long = df_all[df_all[long_col] == True].copy()
        df_long["signal"] = True
        df_long["direction"] = 1
        df_long["forward_ret"] = df_long[f"fwd_ret_{h}"]

        df_short = df_all[df_all[short_col] == True].copy()
        df_short["signal"] = True
        df_short["direction"] = -1
        df_short["forward_ret"] = df_short[f"fwd_ret_{h}"]

        combined = pd.concat([df_long, df_short], ignore_index=True)
        res = analyze_feature_forward_returns(
            df_signals=combined,
            feature_name=f"{family_name}",
            horizon_bars=h,
            cost_model=cost_model,
        )
        verdict = "✅ EDGE" if res.edge_detected else ("⚠️ WEAK" if res.net_mean_return_bps > 0 else "❌ NO EDGE")
        print(f"{family_name:<34} {h*15}m     {res.sample_size:<6d} {res.unique_days:<6d} {res.mean_return_bps:>+7.1f} bps  {res.net_mean_return_bps:>+6.1f} bps  {res.t_statistic:>6.2f}  {res.p_value:>6.4f}  {verdict}")
    print("-" * 86)
