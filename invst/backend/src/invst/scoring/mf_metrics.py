"""Mutual Fund Quantitative Metrics, Rolling Returns, and XIRR Engine.

Provides institutional-grade calculations for Indian Mutual Funds:
- CAGR (1Y, 3Y, 5Y, Since Inception)
- Rolling Returns distributions (Mean, Median, p25, p75, Min, Max, Negative Prob)
- Volatility (Annualized standard deviation & downside deviation)
- Risk-Adjusted Performance (Sharpe, Sortino, Treynor, Jensen's Alpha, Beta)
- Upside & Downside Capture Ratios
- Robust Cashflow-based XIRR (Newton-Raphson with Bisection fallback)
- Cross-Fund Portfolio Stock Overlap Matrix
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy import optimize

logger = logging.getLogger(__name__)

DEFAULT_RISK_FREE_RATE = 0.065  # 6.5% p.a. (Indian 91-day T-Bill benchmark)
TRADING_DAYS_PER_YEAR = 252


# -----------------------------------------------------------------------------
# 1. CAGR and Trailing Returns
# -----------------------------------------------------------------------------
def calculate_cagr(start_nav: float, end_nav: float, years: float) -> float:
    """Calculate annualized Compound Annual Growth Rate.

    Args:
        start_nav: Beginning NAV.
        end_nav: Ending NAV.
        years: Fractional or integer years elapsed.

    Returns:
        CAGR as a decimal (e.g., 0.152 for 15.2%). Returns 0.0 if invalid inputs.
    """
    if start_nav <= 0 or end_nav <= 0 or years <= 0:
        return 0.0
    return float((end_nav / start_nav) ** (1.0 / years) - 1.0)


def calculate_trailing_returns(
    nav_series: pd.Series,
) -> dict[str, float | None]:
    """Calculate standard trailing returns (1M, 3M, 6M, 1Y, 3Y, 5Y, Max).

    Args:
        nav_series: Series indexed by datetime with float NAV values, sorted ascending by date.

    Returns:
        Dictionary mapping period labels to annualized returns (or absolute return for < 1Y).
    """
    if nav_series.empty or len(nav_series) < 2:
        return {
            "1m": None, "3m": None, "6m": None,
            "1y": None, "3y": None, "5y": None, "inception": None,
        }

    latest_date = nav_series.index[-1]
    latest_nav = float(nav_series.iloc[-1])

    first_date = nav_series.index[0]
    total_years = (latest_date - first_date).days / 365.25

    def _get_return(target_date: pd.Timestamp, is_annualized: bool) -> float | None:
        subset = nav_series.loc[:target_date]
        if subset.empty:
            return None
        past_nav = float(subset.iloc[-1])
        if past_nav <= 0:
            return None
        years = (latest_date - subset.index[-1]).days / 365.25
        if years <= 0:
            return None
        if is_annualized and years >= 0.95:
            return calculate_cagr(past_nav, latest_nav, years)
        return float((latest_nav - past_nav) / past_nav)

    return {
        "1m": _get_return(latest_date - pd.DateOffset(months=1), False),
        "3m": _get_return(latest_date - pd.DateOffset(months=3), False),
        "6m": _get_return(latest_date - pd.DateOffset(months=6), False),
        "1y": _get_return(latest_date - pd.DateOffset(years=1), True),
        "3y": _get_return(latest_date - pd.DateOffset(years=3), True),
        "5y": _get_return(latest_date - pd.DateOffset(years=5), True),
        "inception": calculate_cagr(float(nav_series.iloc[0]), latest_nav, total_years) if total_years > 0.5 else None,
    }


# -----------------------------------------------------------------------------
# 2. Rolling Returns Analysis
# -----------------------------------------------------------------------------
def calculate_rolling_returns(
    nav_series: pd.Series,
    window_years: int = 3,
    benchmark_series: pd.Series | None = None,
) -> dict[str, Any]:
    """Compute rolling annualized returns distribution over a specified window.

    Rolling returns eliminate point-to-point recency bias by measuring the CAGR
    an investor would have received starting on every single calendar day.

    Args:
        nav_series: Daily NAV series with pd.DatetimeIndex, sorted ascending.
        window_years: Window duration in years (e.g., 1, 3, 5).
        benchmark_series: Optional benchmark NAV/index price series on identical dates.

    Returns:
        Dict containing statistical summary (mean, median, p25, p75, min, max,
        negative_prob, outperformance_pct) and the rolling time series.
    """
    if nav_series.empty or len(nav_series) < 20:
        return {"error": "Insufficient historical data for rolling returns"}

    window_days = int(window_years * 365.25)
    start_date = nav_series.index[0]
    end_date = nav_series.index[-1]

    total_span_days = (end_date - start_date).days
    if total_span_days < window_days:
        return {
            "error": f"Data span ({total_span_days} days) is less than rolling window ({window_days} days)",
            "available_years": round(total_span_days / 365.25, 2),
        }

    # Resample or align to daily timeline
    rolling_records: list[dict[str, Any]] = []
    fund_returns: list[float] = []
    bench_returns: list[float] = []

    # Map dates to fast index lookup
    dates = nav_series.index
    navs = nav_series.values

    # Step through dates where end_date = start_date + window_days
    for i in range(len(dates)):
        t_start = dates[i]
        t_target = t_start + pd.Timedelta(days=window_days)
        if t_target > end_date:
            break

        # Find closest date on or after target
        idx_target = dates.searchsorted(t_target)
        if idx_target >= len(dates):
            break

        actual_end_date = dates[idx_target]
        actual_years = (actual_end_date - t_start).days / 365.25

        start_nav = float(navs[i])
        end_nav = float(navs[idx_target])
        fund_cagr = calculate_cagr(start_nav, end_nav, actual_years)
        fund_returns.append(fund_cagr)

        bench_cagr: float | None = None
        if benchmark_series is not None and not benchmark_series.empty:
            try:
                b_start = float(benchmark_series.asof(t_start))
                b_end = float(benchmark_series.asof(actual_end_date))
                bench_cagr = calculate_cagr(b_start, b_end, actual_years)
                bench_returns.append(bench_cagr)
            except Exception:
                pass

        rolling_records.append({
            "start_date": t_start.strftime("%Y-%m-%d"),
            "end_date": actual_end_date.strftime("%Y-%m-%d"),
            "fund_return": round(fund_cagr * 100, 2),
            "benchmark_return": round(bench_cagr * 100, 2) if bench_cagr is not None else None,
        })

    if not fund_returns:
        return {"error": "Could not compute rolling returns"}

    arr = np.array(fund_returns)
    outperform_pct: float | None = None
    if bench_returns and len(bench_returns) == len(fund_returns):
        b_arr = np.array(bench_returns)
        outperform_pct = float(np.mean(arr > b_arr) * 100.0)

    # Subsample time series for clean charts (max 150 points)
    sample_step = max(1, len(rolling_records) // 120)
    sampled_series = rolling_records[::sample_step]

    return {
        "window_years": window_years,
        "sample_count": len(fund_returns),
        "mean_return_pct": round(float(np.mean(arr)) * 100, 2),
        "median_return_pct": round(float(np.median(arr)) * 100, 2),
        "p25_return_pct": round(float(np.percentile(arr, 25)) * 100, 2),
        "p75_return_pct": round(float(np.percentile(arr, 75)) * 100, 2),
        "min_return_pct": round(float(np.min(arr)) * 100, 2),
        "max_return_pct": round(float(np.max(arr)) * 100, 2),
        "negative_return_prob_pct": round(float(np.mean(arr < 0.0)) * 100, 2),
        "outperformance_pct": round(outperform_pct, 2) if outperform_pct is not None else None,
        "series": sampled_series,
    }


# -----------------------------------------------------------------------------
# 3. Volatility, Sharpe, Sortino, Alpha, and Beta
# -----------------------------------------------------------------------------
def calculate_risk_metrics(
    fund_nav_series: pd.Series,
    benchmark_nav_series: pd.Series | None = None,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> dict[str, float | None]:
    """Calculate institutional risk and return ratios over trailing 3-year history.

    Computes:
    - Annualized Volatility (Std Dev)
    - Downside Deviation
    - Sharpe Ratio
    - Sortino Ratio
    - Beta (against benchmark)
    - Jensen's Alpha
    - Upside / Downside Capture Ratio
    """
    if fund_nav_series.empty or len(fund_nav_series) < 60:
        return {
            "volatility": None, "downside_deviation": None,
            "sharpe_ratio": None, "sortino_ratio": None,
            "beta": None, "alpha": None,
            "upside_capture": None, "downside_capture": None,
        }

    # Daily percentage returns
    fund_daily = fund_nav_series.pct_change().dropna()
    if fund_daily.empty:
        return {
            "volatility": None, "downside_deviation": None,
            "sharpe_ratio": None, "sortino_ratio": None,
            "beta": None, "alpha": None,
            "upside_capture": None, "downside_capture": None,
        }

    # Annualized volatility
    daily_std = float(fund_daily.std())
    ann_volatility = daily_std * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Fund annualized return (CAGR)
    years = (fund_nav_series.index[-1] - fund_nav_series.index[0]).days / 365.25
    cagr = calculate_cagr(float(fund_nav_series.iloc[0]), float(fund_nav_series.iloc[-1]), years)

    # Sharpe ratio
    sharpe = (cagr - risk_free_rate) / ann_volatility if ann_volatility > 1e-6 else 0.0

    # Downside deviation (returns below daily risk-free rate)
    daily_rf = (1.0 + risk_free_rate) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    downside_diff = np.minimum(fund_daily.values - daily_rf, 0.0)
    downside_dev = float(np.sqrt(np.mean(downside_diff ** 2)) * np.sqrt(TRADING_DAYS_PER_YEAR))
    sortino = (cagr - risk_free_rate) / downside_dev if downside_dev > 1e-6 else 0.0

    # Benchmark comparisons
    beta: float | None = None
    alpha: float | None = None
    up_capture: float | None = None
    down_capture: float | None = None

    if benchmark_nav_series is not None and not benchmark_nav_series.empty:
        # Align on common trading days
        df = pd.DataFrame({"fund": fund_nav_series, "bench": benchmark_nav_series}).dropna()
        if len(df) > 60:
            returns_df = df.pct_change().dropna()
            f_ret = returns_df["fund"].values
            b_ret = returns_df["bench"].values

            var_b = float(np.var(b_ret, ddof=1))
            if var_b > 1e-8:
                cov_fb = float(np.cov(f_ret, b_ret)[0, 1])
                beta = cov_fb / var_b

                # Bench CAGR
                b_years = (df.index[-1] - df.index[0]).days / 365.25
                b_cagr = calculate_cagr(float(df["bench"].iloc[0]), float(df["bench"].iloc[-1]), b_years)
                # Jensen's Alpha: (R_f - Rf) - beta * (R_m - Rf)
                alpha = (cagr - risk_free_rate) - beta * (b_cagr - risk_free_rate)

            # Capture Ratios (monthly aggregation for stability)
            monthly_f = df["fund"].resample("ME").last().pct_change().dropna()
            monthly_b = df["bench"].resample("ME").last().pct_change().dropna()
            m_df = pd.DataFrame({"fund": monthly_f, "bench": monthly_b}).dropna()

            if len(m_df) >= 12:
                up_months = m_df[m_df["bench"] > 0]
                if not up_months.empty and up_months["bench"].mean() > 0:
                    up_capture = float((up_months["fund"].mean() / up_months["bench"].mean()) * 100.0)

                down_months = m_df[m_df["bench"] < 0]
                if not down_months.empty and down_months["bench"].mean() < 0:
                    down_capture = float((down_months["fund"].mean() / down_months["bench"].mean()) * 100.0)

    return {
        "cagr": round(float(cagr) * 100, 2),
        "volatility": round(float(ann_volatility) * 100, 2),
        "downside_deviation": round(float(downside_dev) * 100, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "sortino_ratio": round(float(sortino), 2),
        "beta": round(float(beta), 2) if beta is not None else 1.0,
        "alpha": round(float(alpha) * 100, 2) if alpha is not None else 0.0,
        "upside_capture": round(float(up_capture), 1) if up_capture is not None else None,
        "downside_capture": round(float(down_capture), 1) if down_capture is not None else None,
    }


# -----------------------------------------------------------------------------
# 4. Cashflow XIRR Solver (Extended Internal Rate of Return)
# -----------------------------------------------------------------------------
def calculate_xirr(
    cashflows: Sequence[tuple[datetime.date | str, float]],
    guess: float = 0.12,
) -> float | None:
    """Calculate the Extended Internal Rate of Return (XIRR) for cash flows.

    Cash flow convention:
    - Outflows (investments/purchases/SIP installments) are negative.
    - Inflows (dividends, redemptions, or current portfolio value) are positive.

    Args:
        cashflows: List of (date, amount) tuples.
        guess: Initial return guess (default 12%).

    Returns:
        Annualized XIRR as a percentage (e.g., 14.85 for 14.85%), or None if computation fails.
    """
    if len(cashflows) < 2:
        return None

    # Parse and sort by date
    parsed: list[tuple[datetime.date, float]] = []
    for dt, amt in cashflows:
        if isinstance(dt, str):
            parsed_dt = datetime.datetime.strptime(dt[:10], "%Y-%m-%d").date()
        elif isinstance(dt, datetime.datetime):
            parsed_dt = dt.date()
        else:
            parsed_dt = dt
        parsed.append((parsed_dt, float(amt)))

    parsed.sort(key=lambda x: x[0])
    dates, amounts = zip(*parsed)

    # Must contain both positive and negative cashflows
    has_pos = any(a > 0 for a in amounts)
    has_neg = any(a < 0 for a in amounts)
    if not (has_pos and has_neg):
        return None

    t0 = dates[0]
    year_fractions = np.array([(d - t0).days / 365.25 for d in dates], dtype=np.float64)
    amt_arr = np.array(amounts, dtype=np.float64)

    def npv(r: float) -> float:
        if r <= -0.9999:
            return 1e12
        return float(np.sum(amt_arr / ((1.0 + r) ** year_fractions)))

    def npv_prime(r: float) -> float:
        if r <= -0.9999:
            return -1e12
        return float(np.sum(-year_fractions * amt_arr / ((1.0 + r) ** (year_fractions + 1.0))))

    # 1. Try Newton-Raphson
    try:
        sol = optimize.newton(npv, guess, fprime=npv_prime, maxiter=100, tol=1e-6)
        if -0.99 < sol < 50.0:  # reasonable range: -99% to +5000%
            return round(float(sol) * 100.0, 2)
    except Exception:
        pass

    # 2. Robust Bisection / Brent fallback
    try:
        # Search brackets
        brackets = [(-0.95, 0.5), (0.0, 2.0), (1.0, 10.0), (-0.99, 0.0)]
        for low, high in brackets:
            f_low = npv(low)
            f_high = npv(high)
            if f_low * f_high <= 0:
                sol = optimize.brentq(npv, low, high, maxiter=200, xtol=1e-6)
                return round(float(sol) * 100.0, 2)
    except Exception as e:
        logger.debug("Brentq fallback failed for XIRR: %s", e)

    return None


# -----------------------------------------------------------------------------
# 5. Cross-Fund Portfolio Stock Overlap Matrix
# -----------------------------------------------------------------------------
def calculate_portfolio_overlap(
    holdings_by_scheme: dict[int | str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Calculate pairwise and portfolio-wide stock overlap across mutual funds.

    Formula:
        Pairwise Overlap(Fund A, Fund B) = Sum(min(Weight_A(s), Weight_B(s))) for all s in A ∩ B

    Args:
        holdings_by_scheme: Dict mapping scheme_code/name to list of holdings:
            [{"company_name": "...", "symbol": "...", "weight_pct": 8.5}, ...]

    Returns:
        Dict with pairwise matrix, common stocks with aggregated weight, and redundancy score.
    """
    schemes = list(holdings_by_scheme.keys())
    matrix: dict[str, dict[str, float]] = {str(s): {} for s in schemes}

    # Normalize holdings into dict {norm_company_name: weight}
    norm_holdings: dict[str, dict[str, float]] = {}
    for s, h_list in holdings_by_scheme.items():
        s_key = str(s)
        norm_holdings[s_key] = {}
        for item in h_list:
            comp = (item.get("symbol") or item.get("company_name") or "").strip().upper()
            wt = float(item.get("weight_pct") or 0.0)
            if comp and wt > 0:
                norm_holdings[s_key][comp] = norm_holdings[s_key].get(comp, 0.0) + wt

    # Compute pairwise overlap
    for s1 in schemes:
        k1 = str(s1)
        h1 = norm_holdings[k1]
        for s2 in schemes:
            k2 = str(s2)
            if k1 == k2:
                matrix[k1][k2] = 100.0
                continue
            h2 = norm_holdings[k2]
            common_keys = set(h1.keys()) & set(h2.keys())
            overlap_pct = sum(min(h1[k], h2[k]) for k in common_keys)
            matrix[k1][k2] = round(overlap_pct, 1)

    # Find top common stocks across all funds
    stock_counts: dict[str, dict[str, Any]] = {}
    for s_key, h_map in norm_holdings.items():
        for comp, wt in h_map.items():
            if comp not in stock_counts:
                stock_counts[comp] = {"funds_holding": 0, "weights": {}}
            stock_counts[comp]["funds_holding"] += 1
            stock_counts[comp]["weights"][s_key] = wt

    multi_fund_stocks = [
        {
            "stock": comp,
            "funds_holding_count": data["funds_holding"],
            "fund_weights": data["weights"],
            "avg_weight_pct": round(sum(data["weights"].values()) / len(schemes), 2),
        }
        for comp, data in stock_counts.items()
        if data["funds_holding"] > 1
    ]
    multi_fund_stocks.sort(key=lambda x: (x["funds_holding_count"], x["avg_weight_pct"]), reverse=True)

    # Average non-self pairwise overlap
    pairwise_overlaps: list[float] = []
    for k1 in matrix:
        for k2 in matrix[k1]:
            if k1 != k2:
                pairwise_overlaps.append(matrix[k1][k2])

    avg_overlap = round(sum(pairwise_overlaps) / len(pairwise_overlaps), 1) if pairwise_overlaps else 0.0

    return {
        "schemes": [str(s) for s in schemes],
        "pairwise_overlap_matrix": matrix,
        "average_overlap_pct": avg_overlap,
        "high_overlap_warning": avg_overlap > 35.0,
        "common_holdings": multi_fund_stocks[:15],
    }


# -----------------------------------------------------------------------------
# 6. Goal & Step-Up SIP Projections
# -----------------------------------------------------------------------------
def calculate_sip_projection(
    monthly_sip: float,
    expected_cagr_pct: float,
    years: int,
    step_up_pct: float = 0.0,
    inflation_pct: float = 0.0,
) -> dict[str, Any]:
    """Calculate compound wealth trajectory with annual step-up and inflation adjustments.

    Args:
        monthly_sip: Starting monthly SIP amount in INR.
        expected_cagr_pct: Expected annual compound rate of return (e.g. 13.5).
        years: Investment duration in years.
        step_up_pct: Annual percentage increase in monthly SIP (e.g. 10.0 for 10% annual top-up).
        inflation_pct: Annual inflation rate (e.g. 6.0) to compute real purchasing power.

    Returns:
        Summary dict containing total invested, future nominal value, real value,
        wealth multiplier, and year-by-year trajectory table.
    """
    monthly_rate = (1.0 + (expected_cagr_pct / 100.0)) ** (1.0 / 12.0) - 1.0
    current_sip = float(monthly_sip)
    total_invested = 0.0
    corpus = 0.0

    trajectory: list[dict[str, Any]] = []

    for y in range(1, years + 1):
        for _m in range(12):
            total_invested += current_sip
            corpus = (corpus + current_sip) * (1.0 + monthly_rate)

        # Apply inflation discount to corpus for real value
        real_corpus = corpus / ((1.0 + (inflation_pct / 100.0)) ** y) if inflation_pct > 0 else corpus

        trajectory.append({
            "year": y,
            "monthly_sip": round(current_sip, 0),
            "total_invested": round(total_invested, 0),
            "estimated_corpus": round(corpus, 0),
            "wealth_gain": round(corpus - total_invested, 0),
            "real_purchasing_power": round(real_corpus, 0),
        })

        if step_up_pct > 0:
            current_sip = current_sip * (1.0 + (step_up_pct / 100.0))

    gain = corpus - total_invested
    multiplier = round(corpus / total_invested, 2) if total_invested > 0 else 1.0

    return {
        "monthly_sip": monthly_sip,
        "expected_cagr_pct": expected_cagr_pct,
        "years": years,
        "step_up_pct": step_up_pct,
        "inflation_pct": inflation_pct,
        "total_invested": round(total_invested, 0),
        "estimated_corpus": round(corpus, 0),
        "estimated_gain": round(gain, 0),
        "wealth_multiplier": multiplier,
        "trajectory": trajectory,
    }


def calculate_required_sip_for_goal(
    target_corpus_today: float,
    years: int,
    expected_cagr_pct: float = 12.0,
    inflation_pct: float = 6.0,
    step_up_pct: float = 10.0,
) -> dict[str, Any]:
    """Calculate the required monthly SIP to achieve a target financial goal.

    Adjusts target corpus for future inflation and solves for starting monthly SIP
    with and without step-up.
    """
    # Future inflated target
    future_target = target_corpus_today * ((1.0 + (inflation_pct / 100.0)) ** years)
    months = years * 12
    monthly_r = (1.0 + (expected_cagr_pct / 100.0)) ** (1.0 / 12.0) - 1.0

    # Flat SIP PMT formula: FV = PMT * ((1+r)^n - 1)/r * (1+r)
    flat_pmt = future_target * monthly_r / (((1.0 + monthly_r) ** months - 1.0) * (1.0 + monthly_r))

    # Binary search for step-up SIP starting amount
    low = 100.0
    high = flat_pmt * 1.5
    step_up_pmt = flat_pmt
    for _ in range(50):
        mid = (low + high) / 2.0
        proj = calculate_sip_projection(mid, expected_cagr_pct, years, step_up_pct=step_up_pct)
        c = proj["estimated_corpus"]
        if abs(c - future_target) < 1000:
            step_up_pmt = mid
            break
        elif c < future_target:
            low = mid
        else:
            high = mid
            step_up_pmt = mid

    savings_pct = round(((flat_pmt - step_up_pmt) / flat_pmt) * 100.0, 1) if flat_pmt > 0 else 0.0

    return {
        "target_corpus_today": target_corpus_today,
        "years": years,
        "inflation_adjusted_target": round(future_target, 0),
        "flat_monthly_sip": round(flat_pmt, 0),
        "step_up_starting_monthly_sip": round(step_up_pmt, 0),
        "step_up_annual_pct": step_up_pct,
        "initial_savings_pct": savings_pct,
    }


# -----------------------------------------------------------------------------
# 7. Seasoned Quant Analyst Conviction Scoring Engine
# -----------------------------------------------------------------------------
def compute_analyst_conviction_score(
    cagr_3y: float | None,
    sharpe: float | None,
    sortino: float | None,
    expense_ratio: float | None,
    aum_cr: float | None,
    crisil_rating: int | None,
    category: str = "",
    scheme_name: str = "",
) -> dict[str, Any]:
    """Compute institutional Seasoned Analyst Conviction Score (0-100) and qualitative memo."""
    # 1. Alpha Pillar (30 pts)
    ret_score = 15.0
    if cagr_3y is not None:
        if cagr_3y >= 20.0:
            ret_score = 30.0
        elif cagr_3y >= 15.0:
            ret_score = 25.0
        elif cagr_3y >= 12.0:
            ret_score = 20.0
        elif cagr_3y >= 9.0:
            ret_score = 14.0
        else:
            ret_score = 8.0

    # 2. Downside Shield & Sortino Pillar (25 pts)
    sort_score = 12.0
    if sortino is not None:
        if sortino >= 1.4:
            sort_score = 25.0
        elif sortino >= 1.0:
            sort_score = 20.0
        elif sortino >= 0.7:
            sort_score = 15.0
        elif sortino >= 0.4:
            sort_score = 10.0
        else:
            sort_score = 5.0

    # 3. Cost Drag & TER Efficiency (15 pts)
    ter_score = 10.0
    if expense_ratio is not None:
        if expense_ratio <= 0.40:
            ter_score = 15.0
        elif expense_ratio <= 0.65:
            ter_score = 12.0
        elif expense_ratio <= 0.90:
            ter_score = 9.0
        else:
            ter_score = 5.0

    # 4. AUM Sweet-Spot & Liquidity (15 pts)
    aum_score = 12.0
    if aum_cr is not None:
        if "Small Cap" in category and aum_cr > 40000:
            aum_score = 8.0  # Liquidity drag penalty on giant small-cap AUM
        elif "Large Cap" in category and aum_cr >= 15000:
            aum_score = 15.0
        elif aum_cr >= 3000:
            aum_score = 14.0
        else:
            aum_score = 10.0

    # 5. Rating & Governance (15 pts)
    rating_score = 12.0
    if crisil_rating == 5:
        rating_score = 15.0
    elif crisil_rating == 4:
        rating_score = 12.0
    elif crisil_rating == 3:
        rating_score = 9.0
    else:
        rating_score = 6.0

    total_conviction = int(round(ret_score + sort_score + ter_score + aum_score + rating_score))
    total_conviction = min(100, max(10, total_conviction))

    if total_conviction >= 85:
        verdict = "STRONG BUY"
        role = "Core Compounding Anchor"
        conviction_badge = "Institutional High Conviction"
    elif total_conviction >= 72:
        verdict = "BUY"
        role = "Alpha Growth Compounder"
        conviction_badge = "Top Quartile Compounder"
    elif total_conviction >= 58:
        verdict = "ACCUMULATE ON DIPS"
        role = "Satellite Allocation"
        conviction_badge = "Selective Dip Buy"
    elif total_conviction >= 45:
        verdict = "HOLD"
        role = "Under Review"
        conviction_badge = "Average Category Performer"
    else:
        verdict = "UNDERPERFORM"
        role = "Candidate for Reallocation"
        conviction_badge = "Sub-Par Risk Adjusted Returns"

    # Bull & Bear Narrative
    bull_case = (
        f"Consistently demonstrates top-tier downside protection with a Sortino of {sortino or 1.2}. "
        f"Unconstrained allocation freedom allows the manager to pivot during market overvaluations."
    )
    bear_case = (
        f"May underperform hyper-momentum bull phases due to conservative cash or value orientation. "
        f"AUM scale of ₹{int(aum_cr or 10000):,} Cr requires active liquidity monitoring."
    )

    if "Small" in category:
        bull_case = "Capitalizes on high-operating-leverage emerging market leaders with explosive multi-bagger earnings potential."
        bear_case = "Vulnerable to sharp liquidity contraction and steep drawdowns during broad market risk-off cycles."
    elif "Mid" in category:
        bull_case = "Hits the sweet-spot between institutional governance and high revenue growth in India's domestic capex cycle."
        bear_case = "Valuation multiples can become stretched during speculative liquidity expansions."
    elif "Balanced" in category:
        bull_case = "Dynamic equity-debt derivative hedging cushions drawdowns, preserving investor peace of mind and dry powder."
        bear_case = "Capped upside during one-way bull markets due to mandatory debt/cash holding buffers."

    return {
        "conviction_score": total_conviction,
        "verdict": verdict,
        "conviction_badge": conviction_badge,
        "portfolio_role": role,
        "pillars": {
            "alpha_consistency": {"score": ret_score, "max": 30},
            "downside_protection": {"score": sort_score, "max": 25},
            "cost_efficiency": {"score": ter_score, "max": 15},
            "aum_liquidity": {"score": aum_score, "max": 15},
            "rating_governance": {"score": rating_score, "max": 15},
        },
        "analyst_memo": {
            "bull_case": bull_case,
            "bear_risks": bear_case,
            "recommendation_summary": f"{verdict}: Assigned {total_conviction}/100 conviction score. Ideal as a {role} in diversified long-term wealth portfolios.",
        },
    }
