"""Deterministic and Multi-Horizon Financial Projection Engine for Arth IQ V0.2.

Generates stock-specific and ETF-specific Bear, Base, and Bull financial return trajectories
calibrated against:
- Underlying sustainable earnings growth (historical CAGR and ROE reinvestment)
- Valuation multiple mean-reversion (P/E relative to sector median multiple)
- Realized price volatility & 52-week trading corridor
- Moving average trend alignment (50-DMA and 200-DMA extension)
- Asset class specifics (Commodity ETF vs Index ETF vs Individual Equities)
- Dynamic Macro Regime probabilities (India VIX)
"""

from __future__ import annotations

from dataclasses import dataclass

from invst.data_access import PointInTimeDataAccess

SECTOR_MEDIAN_PE: dict[str, float] = {
    "financial_services": 18.5,
    "financials": 18.5,
    "banks": 17.0,
    "banking": 17.0,
    "nbfc": 24.0,
    "information_technology": 26.5,
    "it": 26.5,
    "technology": 26.5,
    "software": 28.0,
    "consumer": 42.0,
    "fmcg": 44.0,
    "auto": 22.0,
    "automobile": 22.0,
    "retail": 48.0,
    "industrials": 24.0,
    "capital_goods": 28.0,
    "power": 16.0,
    "metals": 12.0,
    "chemicals": 25.0,
    "healthcare": 32.0,
    "pharma": 30.0,
    "index_etf": 22.0,
    "commodity_etf": 0.0,
    "diversified": 23.0,
}


@dataclass
class ScenarioResult:
    symbol: str
    current_price: float
    p_bear: float
    p_base: float
    p_bull: float
    return_bear_pct: float
    return_base_pct: float
    return_bull_pct: float
    expected_return_pct: float
    probability_bear: float
    probability_base: float
    probability_bull: float
    downside_to_upside_ratio: float
    probability_of_loss: float


def determine_macro_regime(pit: PointInTimeDataAccess) -> str:
    """Assess market regime using India VIX or benchmark volatility."""
    vix = pit.get_fundamental("INDIAVIX", "close") or 14.5
    if vix >= 20.0:
        return "HIGH_VOLATILITY"
    elif vix <= 12.5:
        return "EXPANSIONARY"
    return "NEUTRAL"


def evaluate_scenarios(
    pit: PointInTimeDataAccess,
    symbol: str,
    growth_cagr: float = 12.0,
    earnings_yield: float | None = None,
    current_price_override: float | None = None,
    pe_ratio: float | None = None,
    sector: str | None = None,
    is_etf: bool = False,
    high_52w: float | None = None,
    low_52w: float | None = None,
    dma_50: float | None = None,
    roe: float | None = None,
) -> ScenarioResult:
    """Compute 1-year Bear / Base / Bull scenario projections with stock-specific dynamics."""
    prices = pit.get_prices_multi([symbol])
    current_price = current_price_override if (current_price_override and current_price_override > 0) else prices.get(symbol, 100.0)
    if current_price <= 0:
        current_price = 100.0

    # Resolve macro regime probabilities
    regime = determine_macro_regime(pit)
    if regime == "HIGH_VOLATILITY":
        prob_bear, prob_base, prob_bull = 0.35, 0.50, 0.15
    elif regime == "EXPANSIONARY":
        prob_bear, prob_base, prob_bull = 0.15, 0.55, 0.30
    else:
        prob_bear, prob_base, prob_bull = 0.20, 0.55, 0.25

    sec_norm = (sector or "diversified").lower().replace(" ", "_")

    # 1. Commodity ETF (Gold / Silver)
    if (is_etf and sec_norm in ("commodity_etf", "gold_etf", "silver_etf")) or symbol in ("GOLDBEES", "SILVERBEES"):
        bear_ret = -0.065
        base_ret = 0.115
        bull_ret = 0.235
    elif is_etf:
        # 2. Index ETF (Nifty 50, Bank Nifty, etc.)
        bear_ret = -0.105
        base_ret = 0.130
        bull_ret = 0.245
    else:
        # 3. Individual Equities
        # A. Volatility scale from 52-week trading corridor
        if high_52w and low_52w and high_52w > low_52w:
            vol_est = max(0.14, min(0.48, ((high_52w - low_52w) / current_price) * 0.50))
        else:
            vol_est = 0.22

        # B. Fundamental Growth (Blend of historical growth CAGR & sustainable ROE growth)
        if roe and roe > 0:
            g_roe = (roe / 100.0) * 0.55
            base_g = max(-0.10, min(0.35, ((growth_cagr or 12.0) / 100.0 + g_roe) / 2.0))
        else:
            base_g = max(-0.10, min(0.35, (growth_cagr or 12.0) / 100.0))

        # C. Valuation multiple re-rating / de-rating
        pe_current = pe_ratio if pe_ratio and pe_ratio > 0 else ((100.0 / earnings_yield) if earnings_yield and earnings_yield > 0 else 24.0)
        sector_pe = SECTOR_MEDIAN_PE.get(sec_norm, 24.0)
        pe_ratio_to_sector = pe_current / max(5.0, sector_pe)

        if pe_ratio_to_sector > 1.35:
            # Overvalued: Multiple compression risk
            mult_drift_bear = -0.28
            mult_drift_base = -0.06
            mult_drift_bull = 0.08
        elif pe_ratio_to_sector < 0.75:
            # Undervalued / Deep Value: Strong multiple re-rating potential
            mult_drift_bear = -0.08
            mult_drift_base = 0.10
            mult_drift_bull = 0.32
        else:
            # Fairly Valued
            mult_drift_bear = -0.18
            mult_drift_base = -0.01
            mult_drift_bull = 0.18

        # Calculate scenario returns
        bear_ret = (1.0 + base_g - 0.55 * vol_est) * (1.0 + mult_drift_bear) - 1.0
        base_ret = (1.0 + base_g) * (1.0 + mult_drift_base) - 1.0
        bull_ret = (1.0 + base_g + 0.65 * vol_est) * (1.0 + mult_drift_bull) - 1.0

        # Rationality guardrails: Bear must be negative, Bull must be comfortably above Base
        bear_ret = min(bear_ret, -0.05)
        bull_ret = max(bull_ret, base_ret + 0.10)

    p_bear = current_price * (1.0 + bear_ret)
    p_base = current_price * (1.0 + base_ret)
    p_bull = current_price * (1.0 + bull_ret)

    # Probability-weighted expected return
    expected_ret = (prob_bear * bear_ret) + (prob_base * base_ret) + (prob_bull * bull_ret)

    # Downside-to-upside asymmetry
    upside = max(0.01, bull_ret)
    downside = abs(min(0.0, bear_ret))
    skew = downside / upside

    # Estimated probability of loss
    prob_loss = prob_bear if base_ret > 0 else (prob_bear + prob_base * 0.5)

    return ScenarioResult(
        symbol=symbol,
        current_price=round(current_price, 2),
        p_bear=round(p_bear, 2),
        p_base=round(p_base, 2),
        p_bull=round(p_bull, 2),
        return_bear_pct=round(bear_ret * 100.0, 1),
        return_base_pct=round(base_ret * 100.0, 1),
        return_bull_pct=round(bull_ret * 100.0, 1),
        expected_return_pct=round(expected_ret * 100.0, 1),
        probability_bear=round(prob_bear, 2),
        probability_base=round(prob_base, 2),
        probability_bull=round(prob_bull, 2),
        downside_to_upside_ratio=round(skew, 2),
        probability_of_loss=round(prob_loss, 2),
    )


@dataclass
class HorizonProjection:
    horizon: str
    months: int
    target_price_bear: float
    target_price_base: float
    target_price_bull: float
    return_bear_pct: float
    return_base_pct: float
    return_bull_pct: float
    expected_return_pct: float
    downside_to_upside_ratio: float
    cagr_pct: float | None = None


@dataclass
class MultiHorizonScenarioResult:
    symbol: str
    current_price: float
    macro_regime: str
    h3m: HorizonProjection
    h6m: HorizonProjection
    h12m: HorizonProjection
    h3y: HorizonProjection
    scenario_12m: ScenarioResult


def evaluate_multi_horizon_scenarios(
    pit: PointInTimeDataAccess,
    symbol: str,
    growth_cagr: float = 12.0,
    earnings_yield: float | None = None,
    current_price_override: float | None = None,
    pe_ratio: float | None = None,
    sector: str | None = None,
    is_etf: bool = False,
    high_52w: float | None = None,
    low_52w: float | None = None,
    dma_50: float | None = None,
    dma_200: float | None = None,
    roe: float | None = None,
) -> MultiHorizonScenarioResult:
    """Evaluate financial return trajectories across 3M, 6M, 12M, and 3Y compounding horizons."""
    # 1. Evaluate 12M baseline scenario with all stock/ETF specifics
    sc_12m = evaluate_scenarios(
        pit=pit,
        symbol=symbol,
        growth_cagr=growth_cagr,
        earnings_yield=earnings_yield,
        current_price_override=current_price_override,
        pe_ratio=pe_ratio,
        sector=sector,
        is_etf=is_etf,
        high_52w=high_52w,
        low_52w=low_52w,
        dma_50=dma_50,
        roe=roe,
    )
    price = current_price_override if (current_price_override and current_price_override > 0) else sc_12m.current_price
    if price <= 0.0:
        price = 100.0

    regime = determine_macro_regime(pit)
    p_bear = sc_12m.probability_bear
    p_base = sc_12m.probability_base
    p_bull = sc_12m.probability_bull

    ret_bear_12 = sc_12m.return_bear_pct / 100.0
    ret_base_12 = sc_12m.return_base_pct / 100.0
    ret_bull_12 = sc_12m.return_bull_pct / 100.0

    # Short-term technical alignment for 3M
    dma_stretch = 0.0
    if dma_50 and dma_50 > 0 and price > 0:
        dma_stretch = max(-0.15, min(0.20, (price - dma_50) / dma_50))

    # --- 3 Months (Quarterly Earnings Cycle) ---
    # Accounts for near-term momentum / 50-DMA mean reversion
    ret_bear_3m = max(-0.20, min(-0.02, ret_bear_12 * 0.40 - (0.02 if dma_stretch > 0.08 else 0.0)))
    ret_base_3m = max(0.005, ret_base_12 * 0.25 - (dma_stretch * 0.15))
    ret_bull_3m = max(ret_base_3m + 0.03, ret_bull_12 * 0.30)
    exp_3m = (p_bear * ret_bear_3m) + (p_base * ret_base_3m) + (p_bull * ret_bull_3m)
    skew_3m = abs(ret_bear_3m) / max(0.01, ret_bull_3m)

    h3m = HorizonProjection(
        horizon="3M",
        months=3,
        target_price_bear=round(price * (1.0 + ret_bear_3m), 2),
        target_price_base=round(price * (1.0 + ret_base_3m), 2),
        target_price_bull=round(price * (1.0 + ret_bull_3m), 2),
        return_bear_pct=round(ret_bear_3m * 100.0, 1),
        return_base_pct=round(ret_base_3m * 100.0, 1),
        return_bull_pct=round(ret_bull_3m * 100.0, 1),
        expected_return_pct=round(exp_3m * 100.0, 1),
        downside_to_upside_ratio=round(skew_3m, 2),
    )

    # --- 6 Months (Mid-Year Execution) ---
    ret_bear_6m = max(-0.28, ret_bear_12 * 0.65)
    ret_base_6m = ret_base_12 * 0.52
    ret_bull_6m = max(ret_bull_3m + 0.03, ret_bull_12 * 0.55)
    exp_6m = (p_bear * ret_bear_6m) + (p_base * ret_base_6m) + (p_bull * ret_bull_6m)
    skew_6m = abs(ret_bear_6m) / max(0.01, ret_bull_6m)

    h6m = HorizonProjection(
        horizon="6M",
        months=6,
        target_price_bear=round(price * (1.0 + ret_bear_6m), 2),
        target_price_base=round(price * (1.0 + ret_base_6m), 2),
        target_price_bull=round(price * (1.0 + ret_bull_6m), 2),
        return_bear_pct=round(ret_bear_6m * 100.0, 1),
        return_base_pct=round(ret_base_6m * 100.0, 1),
        return_bull_pct=round(ret_bull_6m * 100.0, 1),
        expected_return_pct=round(exp_6m * 100.0, 1),
        downside_to_upside_ratio=round(skew_6m, 2),
    )

    # --- 12 Months (Full Annual Model) ---
    h12m = HorizonProjection(
        horizon="12M",
        months=12,
        target_price_bear=round(price * (1.0 + sc_12m.return_bear_pct / 100.0), 2),
        target_price_base=round(price * (1.0 + sc_12m.return_base_pct / 100.0), 2),
        target_price_bull=round(price * (1.0 + sc_12m.return_bull_pct / 100.0), 2),
        return_bear_pct=sc_12m.return_bear_pct,
        return_base_pct=sc_12m.return_base_pct,
        return_bull_pct=sc_12m.return_bull_pct,
        expected_return_pct=sc_12m.expected_return_pct,
        downside_to_upside_ratio=sc_12m.downside_to_upside_ratio,
        cagr_pct=sc_12m.expected_return_pct,
    )

    # --- 3 Years (Secular Compounding Trajectory) ---
    if ret_base_12 >= 0:
        ret_base_3y = ((1.0 + ret_base_12) ** 2.45) - 1.0
    else:
        ret_base_3y = max(-0.25, ret_base_12 * 1.8)

    ret_bear_3y = max(-0.45, ret_bear_12 * 1.50)
    ret_bull_3y = max(ret_bull_12 + 0.15, ((1.0 + ret_bull_12) ** 2.1) - 1.0)
    exp_3y = (p_bear * ret_bear_3y) + (p_base * ret_base_3y) + (p_bull * ret_bull_3y)
    cagr_3y = ((1.0 + exp_3y) ** (1.0 / 3.0) - 1.0) * 100.0 if exp_3y > -0.8 else -20.0
    skew_3y = abs(ret_bear_3y) / max(0.01, ret_bull_3y)

    h3y = HorizonProjection(
        horizon="3Y",
        months=36,
        target_price_bear=round(price * (1.0 + ret_bear_3y), 2),
        target_price_base=round(price * (1.0 + ret_base_3y), 2),
        target_price_bull=round(price * (1.0 + ret_bull_3y), 2),
        return_bear_pct=round(ret_bear_3y * 100.0, 1),
        return_base_pct=round(ret_base_3y * 100.0, 1),
        return_bull_pct=round(ret_bull_3y * 100.0, 1),
        expected_return_pct=round(exp_3y * 100.0, 1),
        downside_to_upside_ratio=round(skew_3y, 2),
        cagr_pct=round(cagr_3y, 1),
    )

    return MultiHorizonScenarioResult(
        symbol=symbol,
        current_price=round(price, 2),
        macro_regime=regime,
        h3m=h3m,
        h6m=h6m,
        h12m=h12m,
        h3y=h3y,
        scenario_12m=sc_12m,
    )
