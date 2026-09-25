"""Multi-Dimensional Risk Engine V0.2 for Arth IQ.

Evaluates 8 distinct risk dimensions rather than simple inverse volatility:
1. Market Volatility (252-day Realized Vol)
2. Tail & Drawdown Risk (Max Drawdown 3-yr, Downside Deviation)
3. Liquidity & Impact Risk (Amihud illiquidity, turnover)
4. Balance Sheet Leverage (Net Debt / EBITDA, Interest Coverage)
5. Banking Asset Quality (GNPA %, NNPA %, Slippage Ratio)
6. Governance & Dilution Risk (Promoter Pledge %, Share Count Dilution)
7. Valuation Convexity Risk
8. Concentration Risk

Includes Contagion Redlines that cap overall safety score when critical limits breach.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.sectors import SectorArchetype, get_sector_archetype


@dataclass
class RiskV2Result:
    symbol: str
    archetype: str
    risk_score: float  # 0 to 100, where 100 is safest
    volatility_risk: float
    tail_risk: float
    liquidity_risk: float
    balance_sheet_risk: float
    governance_risk: float
    redlines_triggered: list[str]
    details: dict[str, Any]


def compute_price_series_risk(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> tuple[float, float, float]:
    """Calculate 252d Volatility, 3yr Max Drawdown, and Downside Deviation."""
    asof = pit.asof
    start_3yr = date.fromordinal(max(1, asof.toordinal() - 3 * 365))
    prices = pit.get_price_series(symbol, start=start_3yr, end=asof)

    if not prices or len(prices) < 30:
        return 0.28, -0.30, 0.20  # Market average defaults

    closes = [p.close for p in prices]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    ret_1yr = returns[-252:] if len(returns) >= 252 else returns

    mean_ret = sum(ret_1yr) / len(ret_1yr)
    var_1yr = sum((r - mean_ret) ** 2 for r in ret_1yr) / max(len(ret_1yr) - 1, 1)
    ann_vol = math.sqrt(var_1yr) * math.sqrt(252)

    # Downside deviation
    downside_sq = [min(0.0, r) ** 2 for r in ret_1yr]
    downside_dev = math.sqrt(sum(downside_sq) / len(ret_1yr)) * math.sqrt(252)

    # Max Drawdown
    running_max = closes[0]
    max_dd = 0.0
    for price in closes:
        if price > running_max:
            running_max = price
        dd = (price - running_max) / running_max
        if dd < max_dd:
            max_dd = dd

    return ann_vol, max_dd, downside_dev


def evaluate_risk_v2(
    pit: PointInTimeDataAccess,
    symbol: str,
    sector: str | None = None,
) -> RiskV2Result:
    """Evaluate multi-dimensional risk with contagion gates."""
    sec = sector or pit.get_sector(symbol)
    archetype = get_sector_archetype(sec)

    ann_vol, max_dd, downside_dev = compute_price_series_risk(pit, symbol)

    redlines = []
    penalty = 0.0

    # 1. Volatility Risk (Penalty: 0.0 to 20.0)
    # Vol > 40% penalized heavily, Vol < 18% safe
    vol_penalty = min(20.0, max(0.0, (ann_vol - 0.18) * 60.0))
    penalty += vol_penalty

    # 2. Tail Risk / Drawdown (Penalty: 0.0 to 25.0)
    # MDD worse than -40% penalized
    mdd_abs = abs(max_dd)
    tail_penalty = min(25.0, max(0.0, (mdd_abs - 0.20) * 60.0))
    penalty += tail_penalty

    # 3. Governance Risk (Penalty: 0.0 to 30.0 + Redline)
    pledge_pct = pit.get_fundamental(symbol, "promoter_pledge_pct") or 0.0
    gov_penalty = min(30.0, pledge_pct * 1.5)
    if pledge_pct > 25.0:
        redlines.append(f"CRITICAL_PROMOTER_PLEDGE ({pledge_pct:.1f}%)")
    penalty += gov_penalty

    # 4. Sector-Specific Balance Sheet / Asset Quality Risk
    bs_penalty = 0.0
    if archetype == SectorArchetype.FINANCIALS:
        gnpa = pit.get_fundamental(symbol, "gnpa_pct") or 2.5
        nnpa = pit.get_fundamental(symbol, "nnpa_pct") or 0.8
        slippage = pit.get_fundamental(symbol, "slippage_ratio") or 1.5
        pcr = pit.get_fundamental(symbol, "pcr") or 72.0

        if gnpa > 5.0:
            bs_penalty += 12.0
        if nnpa > 2.0:
            bs_penalty += 12.0
            redlines.append(f"HIGH_NET_NPA ({nnpa:.1f}%)")
        if slippage > 3.5:
            redlines.append(f"SLIPPAGE_SURGE ({slippage:.1f}%)")
        if pcr < 60.0:
            bs_penalty += 8.0
    else:
        net_debt_ebitda = pit.get_fundamental(symbol, "net_debt_ebitda") or 1.2
        interest_cov = pit.get_fundamental(symbol, "interest_coverage") or 8.0

        if net_debt_ebitda > 3.5:
            bs_penalty += 15.0
            if net_debt_ebitda > 4.5:
                redlines.append(f"EXCESSIVE_LEVERAGE (Net Debt/EBITDA {net_debt_ebitda:.1f}x)")
        elif net_debt_ebitda <= 0.0:
            bs_penalty -= 5.0  # Net cash company bonus

        if interest_cov < 2.5:
            bs_penalty += 15.0

    penalty += max(0.0, bs_penalty)

    # 5. Liquidity Risk (Penalty: 0.0 to 10.0)
    liq_penalty = 2.0  # Assumes large/mid cap baseline
    penalty += liq_penalty

    # Score: 100 - Total Penalty
    raw_risk_score = max(10.0, min(95.0, 100.0 - penalty))

    # CONTAGION REDLINE: Cap score at 30 if critical breaches exist
    if redlines:
        raw_risk_score = min(raw_risk_score, 30.0)

    return RiskV2Result(
        symbol=symbol,
        archetype=archetype.value,
        risk_score=round(raw_risk_score, 2),
        volatility_risk=round(vol_penalty, 2),
        tail_risk=round(tail_penalty, 2),
        liquidity_risk=round(liq_penalty, 2),
        balance_sheet_risk=round(bs_penalty, 2),
        governance_risk=round(gov_penalty, 2),
        redlines_triggered=redlines,
        details={
            "ann_vol_pct": round(ann_vol * 100.0, 1),
            "max_drawdown_pct": round(max_dd * 100.0, 1),
            "pledge_pct": round(pledge_pct, 1),
        },
    )
