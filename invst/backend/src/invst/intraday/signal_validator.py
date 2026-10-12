"""
IIM — Signal Validator.

Applies the portfolio-level risk controls and multi-timeframe (MTA) confirmation
AFTER the core signal engine has fired a signal candidate. These checks are the
final layer before a signal is committed to the database and displayed to the user.

Portfolio-level controls (from V2 spec, all hard):
  1. Max 3 concurrent active signals.
  2. Max 2 signals per NSE sector active at the same time.
  3. Daily loss halt: if realized + unrealized P&L ≤ -2% of capital, pause engine.
  4. MTA check: 1H EMA21 must agree with signal direction.
  5. Minimum R:R of 1:1.8 (enforced via feasibility gate in sl_target_engine).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from invst.intraday.indicators import add_ema, resample_to_1h
from invst.intraday.signal_engine import SignalResult
from invst.intraday.sl_target_engine import SLTargetResult

logger = logging.getLogger("invst.intraday.signal_validator")

# ---------------------------------------------------------------------------
# Multi-Timeframe Confirmation (MTA)
# ---------------------------------------------------------------------------

def validate_mta(
    signal: SignalResult,
    df_15m: pd.DataFrame,
) -> tuple[bool, str]:
    """
    Confirm signal direction using the 1H EMA21.

    The 1H timeframe must agree with the 15m signal direction:
      LONG: 1H EMA21 must be sloping upward.
      SHORT: 1H EMA21 must be sloping downward.

    Args:
        signal: Candidate signal from the signal engine.
        df_15m: Full 15m DataFrame including warmup bars.

    Returns:
        (valid, reason)
    """
    if df_15m.empty:
        return False, "No 15m data for MTA."

    try:
        df_1h = resample_to_1h(df_15m)
        if len(df_1h) < 3:
            return False, "Insufficient 1H bars for MTA."

        df_1h = add_ema(df_1h, period=21)

        ema21_cur = float(df_1h["ema21"].iloc[-1])
        ema21_prev = float(df_1h["ema21"].iloc[-2])
        slope = ema21_cur - ema21_prev

        if signal.signal_type == "LONG" and slope <= 0:
            return False, f"MTA fail: 1H EMA21 slope={slope:.4f} (not rising for LONG)."
        if signal.signal_type == "SHORT" and slope >= 0:
            return False, f"MTA fail: 1H EMA21 slope={slope:.4f} (not falling for SHORT)."

        return True, f"MTA OK: 1H EMA21 slope={slope:+.4f} agrees with {signal.signal_type}."
    except Exception as exc:
        logger.exception("MTA check error for %s: %s", signal.symbol, exc)
        return False, f"MTA error: {exc}"


# ---------------------------------------------------------------------------
# Portfolio-Level Controls
# ---------------------------------------------------------------------------

def check_portfolio_limits(
    signal: SignalResult,
    active_signals: list[dict[str, Any]],
    sector_map: dict[str, str],
    account_capital: float,
    current_day_pnl_r: float,
    account_atr_size: float,
) -> tuple[bool, str]:
    """
    Enforce all portfolio-level risk controls.

    Args:
        signal: Candidate signal.
        active_signals: List of currently active signal dicts (from DB).
        sector_map: Dict mapping symbol → NSE sector name.
        account_capital: User's configured account capital (₹).
        current_day_pnl_r: Today's realized + unrealized P&L in R-units (negative = loss).
        account_atr_size: Current risk per trade in ₹ (used to convert R to ₹).

    Returns:
        (allowed, reason)
    """
    # Control 1: Max concurrent signals
    if len(active_signals) >= 3:
        return False, f"Max concurrent signals (3) reached. Active: {len(active_signals)}."

    # Control 2: Sector concentration cap
    signal_sector = sector_map.get(signal.symbol, "UNKNOWN")
    sector_count = sum(
        1 for s in active_signals
        if sector_map.get(s.get("symbol", ""), "UNKNOWN") == signal_sector
    )
    if sector_count >= 2:
        return False, (
            f"Sector cap reached: {sector_count} active signals in '{signal_sector}'. "
            f"Max 2 per sector."
        )

    # Control 3: Daily loss halt
    # current_day_pnl_r in R; convert to ₹ using account_atr_size
    daily_loss_pct = (-current_day_pnl_r * account_atr_size) / account_capital
    if daily_loss_pct >= 0.02:
        return False, (
            f"Daily loss halt: P&L={current_day_pnl_r:.2f}R = "
            f"{daily_loss_pct*100:.1f}% of capital ≥ 2%. Engine paused."
        )

    return True, "Portfolio limits OK."


# ---------------------------------------------------------------------------
# Position Sizing
# ---------------------------------------------------------------------------

def compute_position_size(
    account_capital: float,
    sl_distance: float,
    risk_pct: float = 0.005,
) -> dict[str, Any]:
    """
    Compute suggested position size based on account capital and SL distance.

    Args:
        account_capital: Total account capital in ₹.
        sl_distance: SL distance in ₹ per share.
        risk_pct: Risk per trade as fraction of capital (default 0.5%).

    Returns:
        Dict with: shares, capital_at_risk, risk_pct, max_loss_inr.
    """
    if sl_distance <= 0 or account_capital <= 0:
        return {"shares": 0, "capital_at_risk": 0.0, "risk_pct": risk_pct, "max_loss_inr": 0.0}

    risk_amount = account_capital * risk_pct
    shares = int(risk_amount / sl_distance)
    actual_risk = shares * sl_distance

    return {
        "shares": shares,
        "capital_at_risk": round(actual_risk, 2),
        "risk_pct": risk_pct,
        "max_loss_inr": round(actual_risk, 2),
    }


# ---------------------------------------------------------------------------
# Full Validation Pipeline
# ---------------------------------------------------------------------------

def validate_signal(
    signal: SignalResult,
    sl_result: SLTargetResult,
    df_15m: pd.DataFrame,
    active_signals: list[dict[str, Any]],
    sector_map: dict[str, str],
    account_capital: float,
    current_day_pnl_r: float,
) -> tuple[bool, list[str]]:
    """
    Run all validation checks in order. Returns (is_valid, rejection_reasons).

    Order (fail-fast):
      1. Feasibility gate (from sl_target_engine)
      2. MTA confirmation (1H EMA21)
      3. Portfolio limits (concurrent, sector, daily halt)
    """
    reasons: list[str] = []

    # 1. Feasibility gate
    if not sl_result.feasible:
        reasons.append(f"Feasibility: {sl_result.feasibility_reason}")
        return False, reasons

    # 2. MTA
    mta_ok, mta_msg = validate_mta(signal, df_15m)
    if not mta_ok:
        reasons.append(mta_msg)
        return False, reasons

    # 3. Portfolio limits
    portfolio_ok, port_msg = check_portfolio_limits(
        signal=signal,
        active_signals=active_signals,
        sector_map=sector_map,
        account_capital=account_capital,
        current_day_pnl_r=current_day_pnl_r,
        account_atr_size=sl_result.sl_distance,
    )
    if not portfolio_ok:
        reasons.append(port_msg)
        return False, reasons

    return True, []
