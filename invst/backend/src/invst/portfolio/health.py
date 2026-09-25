"""Personal Portfolio Health Diagnosis & Position Advisory Engine for Arth IQ.

Analyzes user-provided stock holdings against live quantitative scores,
evaluates sector concentration risks, scans for redlines, and generates
actionable position-level advice (BUY MORE / HOLD / TRIM / EXIT SELL) with
exact share adjustments, multi-horizon scenario forecasts, and institutional factor tiers.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.composite import compute_composite_scores
from invst.scoring.stock_analyzer import analyze_stock_on_demand

logger = logging.getLogger(__name__)


@dataclass
class UserHolding:
    symbol: str
    shares: float
    buy_price: float
    target_price: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "buy_price": self.buy_price,
            "target_price": self.target_price,
            "notes": self.notes,
        }


@dataclass
class UserPortfolio:
    id: str
    name: str
    description: str = ""
    portfolio_type: str = "PORTFOLIO"  # 'PORTFOLIO' or 'TARGETLIST'
    holdings: list[UserHolding] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PositionHealth:
    symbol: str
    shares: float
    buy_price: float
    current_price: float
    current_value: float
    weight_pct: float
    target_weight_pct: float
    shares_to_adjust: float  # Negative to trim/sell, positive to add, 0 to hold
    capital_delta: float  # Cash unlocked (positive) or cash required (negative)
    unrealized_pnl: float
    unrealized_pnl_pct: float
    business_quality_score: float
    valuation_score: float
    risk_score: float
    investment_score: float
    quality_tier: str
    action_verdict: str  # BUY_MORE, HOLD, TRIM, EXIT_SELL
    action_badge: str
    action_rationale: str
    dip_target_price: float
    dip_discount_pct: float
    stop_loss_level: float
    technical_trend: str
    is_etf: bool
    redlines_triggered: list[str]
    expected_return_12m: float
    sector: str
    target_price: float | None = None
    notes: str = ""


@dataclass
class PortfolioHorizonSummary:
    horizon_name: str
    expected_return_pct: float
    bull_return_pct: float
    bear_return_pct: float
    projected_portfolio_value: float
    cagr_pct: float | None = None


@dataclass
class PortfolioFactorHealth:
    score: float
    tier: str
    interpretation: str
    summary_metric: str


@dataclass
class PortfolioDiversification:
    hhi_score: float
    diversification_tier: str  # OPTIMAL_DIVERSIFICATION, MODERATE_CONCENTRATION, HIGH_CONCENTRATION
    equity_weight_pct: float
    etf_weight_pct: float
    top_3_concentration_pct: float
    total_positions: int
    sector_count: int


@dataclass
class RebalanceOrder:
    symbol: str
    action: str  # SELL, TRIM, ACCUMULATE
    shares: float
    estimated_price: float
    capital_impact: float  # Cash freed up (positive) or cash needed (negative)
    target_weight_pct: float
    rationale: str


@dataclass
class RebalancingBlueprint:
    total_capital_unlocked: float
    total_capital_needed: float
    net_cash_flow: float
    rebalance_urgency: str  # LOW, MODERATE, HIGH, CRITICAL
    orders: list[RebalanceOrder] = field(default_factory=list)
    strategic_summary: str = ""


@dataclass
class PortfolioHealthReport:
    asof_date: str
    total_invested: float
    total_current_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    weighted_business_score: float
    weighted_valuation_score: float
    weighted_risk_score: float
    weighted_investment_score: float
    overall_health_score: float
    overall_health_grade: str  # EXCELLENT, GOOD, ATTENTION_REQUIRED, HIGH_RISK
    positions: list[PositionHealth]
    sector_exposures: dict[str, float]
    sector_warnings: list[str]
    critical_redline_alerts: list[str]
    suggested_replacements: list[dict[str, Any]]
    summary_action_plan: str
    portfolio_horizons: dict[str, PortfolioHorizonSummary] = field(default_factory=dict)
    factor_health: dict[str, PortfolioFactorHealth] = field(default_factory=dict)
    diversification: PortfolioDiversification | None = None
    rebalancing_blueprint: RebalancingBlueprint | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert report to serializable dictionary."""
        return asdict(self)


def init_portfolio_db(conn: sqlite3.Connection) -> None:
    """Ensure user_portfolio_holdings, user_portfolios, and portfolio_holdings tables exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_portfolio_holdings (
            symbol TEXT PRIMARY KEY,
            shares REAL NOT NULL,
            buy_price REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            portfolio_type TEXT DEFAULT 'PORTFOLIO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            portfolio_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            shares REAL NOT NULL,
            buy_price REAL NOT NULL,
            target_price REAL,
            notes TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (portfolio_id, symbol),
            FOREIGN KEY (portfolio_id) REFERENCES user_portfolios(id) ON DELETE CASCADE
        );
        """
    )

    # Ensure default portfolio exists
    cur = conn.cursor()
    cur.execute("SELECT id FROM user_portfolios WHERE id = 'default'")
    if not cur.fetchone():
        cur.execute(
            """
            INSERT INTO user_portfolios (id, name, description, portfolio_type)
            VALUES ('default', 'Main Portfolio', 'Primary core investment portfolio', 'PORTFOLIO')
            """
        )
        cur.execute("SELECT symbol, shares, buy_price FROM user_portfolio_holdings")
        rows = cur.fetchall()
        for r in rows:
            cur.execute(
                """
                INSERT OR IGNORE INTO portfolio_holdings (portfolio_id, symbol, shares, buy_price)
                VALUES ('default', ?, ?, ?)
                """,
                (r[0], r[1], r[2]),
            )

    # Ensure default target list exists
    cur.execute("SELECT id FROM user_portfolios WHERE portfolio_type = 'TARGETLIST'")
    if not cur.fetchone():
        cur.execute(
            """
            INSERT OR IGNORE INTO user_portfolios (id, name, description, portfolio_type)
            VALUES ('targetlist_dips', 'Tactical Dip Target List', 'High-conviction ideas waiting for dip accumulation limit', 'TARGETLIST')
            """
        )
    conn.commit()


def list_portfolios(conn: sqlite3.Connection, portfolio_type: str | None = None) -> list[dict[str, Any]]:
    """List all portfolios and target lists with holdings count, optionally filtered by portfolio_type."""
    init_portfolio_db(conn)
    cur = conn.cursor()
    query = """
        SELECT p.id, p.name, p.description, p.portfolio_type, p.created_at, p.updated_at,
               COUNT(h.symbol) as holdings_count
        FROM user_portfolios p
        LEFT JOIN portfolio_holdings h ON p.id = h.portfolio_id
    """
    params = []
    if portfolio_type:
        query += " WHERE UPPER(p.portfolio_type) = ?"
        params.append(portfolio_type.strip().upper())
    query += """
        GROUP BY p.id
        ORDER BY CASE WHEN p.id = 'default' THEN 0 ELSE 1 END, p.created_at ASC
    """
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2] or "",
            "portfolio_type": r[3] or "PORTFOLIO",
            "created_at": str(r[4] or ""),
            "updated_at": str(r[5] or ""),
            "holdings_count": int(r[6] or 0),
        }
        for r in rows
    ]


def get_portfolio(conn: sqlite3.Connection, portfolio_id: str) -> UserPortfolio | None:
    """Retrieve portfolio metadata and holdings."""
    init_portfolio_db(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, portfolio_type, created_at, updated_at FROM user_portfolios WHERE id = ?",
        (portfolio_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    cur.execute(
        """
        SELECT symbol, shares, buy_price, target_price, notes
        FROM portfolio_holdings
        WHERE portfolio_id = ?
        ORDER BY symbol ASC
        """,
        (portfolio_id,),
    )
    h_rows = cur.fetchall()
    holdings = [
        UserHolding(
            symbol=hr[0],
            shares=float(hr[1]),
            buy_price=float(hr[2]),
            target_price=float(hr[3]) if hr[3] is not None else None,
            notes=hr[4] or "",
        )
        for hr in h_rows
    ]
    return UserPortfolio(
        id=row[0],
        name=row[1],
        description=row[2] or "",
        portfolio_type=row[3] or "PORTFOLIO",
        holdings=holdings,
        created_at=str(row[4] or ""),
        updated_at=str(row[5] or ""),
    )


def create_portfolio(
    conn: sqlite3.Connection,
    name: str,
    description: str = "",
    portfolio_type: str = "PORTFOLIO",
    initial_holdings: list[UserHolding] | None = None,
) -> UserPortfolio:
    """Create a new portfolio or target list."""
    import re
    import uuid

    init_portfolio_db(conn)
    base_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
    portfolio_id = f"{base_slug}_{uuid.uuid4().hex[:6]}" if base_slug else f"port_{uuid.uuid4().hex[:8]}"

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_portfolios (id, name, description, portfolio_type, created_at, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (portfolio_id, name.strip(), description.strip(), portfolio_type.upper()),
    )
    if initial_holdings:
        cur.executemany(
            """
            INSERT OR REPLACE INTO portfolio_holdings (portfolio_id, symbol, shares, buy_price, target_price, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                (portfolio_id, h.symbol.strip().upper(), h.shares, h.buy_price, h.target_price, h.notes)
                for h in initial_holdings
            ],
        )
    conn.commit()
    res = get_portfolio(conn, portfolio_id)
    assert res is not None
    return res


def update_portfolio(
    conn: sqlite3.Connection,
    portfolio_id: str,
    name: str | None = None,
    description: str | None = None,
    portfolio_type: str | None = None,
    holdings: list[UserHolding] | None = None,
) -> UserPortfolio | None:
    """Update portfolio metadata and/or replace holdings."""
    init_portfolio_db(conn)
    p = get_portfolio(conn, portfolio_id)
    if not p:
        return None

    cur = conn.cursor()
    new_name = name.strip() if name is not None else p.name
    new_desc = description.strip() if description is not None else p.description
    new_type = portfolio_type.upper() if portfolio_type is not None else p.portfolio_type

    cur.execute(
        """
        UPDATE user_portfolios
        SET name = ?, description = ?, portfolio_type = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_name, new_desc, new_type, portfolio_id),
    )
    if holdings is not None:
        cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = ?", (portfolio_id,))
        cur.executemany(
            """
            INSERT INTO portfolio_holdings (portfolio_id, symbol, shares, buy_price, target_price, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                (portfolio_id, h.symbol.strip().upper(), h.shares, h.buy_price, h.target_price, h.notes)
                for h in holdings
            ],
        )
        if portfolio_id == "default":
            cur.execute("DELETE FROM user_portfolio_holdings")
            cur.executemany(
                """
                INSERT INTO user_portfolio_holdings (symbol, shares, buy_price, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [(h.symbol.strip().upper(), h.shares, h.buy_price) for h in holdings],
            )
    conn.commit()
    return get_portfolio(conn, portfolio_id)


def delete_portfolio(conn: sqlite3.Connection, portfolio_id: str) -> bool:
    """Delete a portfolio by ID. Default portfolio is cleared rather than dropped."""
    init_portfolio_db(conn)
    cur = conn.cursor()
    if portfolio_id == "default":
        cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = 'default'")
        cur.execute("DELETE FROM user_portfolio_holdings")
        cur.execute("UPDATE user_portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = 'default'")
        conn.commit()
        return True

    cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = ?", (portfolio_id,))
    cur.execute("DELETE FROM user_portfolios WHERE id = ?", (portfolio_id,))
    conn.commit()
    return cur.rowcount > 0


def add_or_update_holding_in_portfolio(
    conn: sqlite3.Connection,
    portfolio_id: str,
    holding: UserHolding,
) -> None:
    """Add or update an individual stock in a specific portfolio or target list."""
    init_portfolio_db(conn)
    cur = conn.cursor()
    cur.execute("SELECT id FROM user_portfolios WHERE id = ?", (portfolio_id,))
    if not cur.fetchone():
        create_portfolio(conn, name=portfolio_id.replace("_", " ").title())

    sym = holding.symbol.strip().upper()
    cur.execute(
        """
        INSERT INTO portfolio_holdings (portfolio_id, symbol, shares, buy_price, target_price, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
            shares = excluded.shares,
            buy_price = excluded.buy_price,
            target_price = excluded.target_price,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """,
        (portfolio_id, sym, holding.shares, holding.buy_price, holding.target_price, holding.notes),
    )
    if portfolio_id == "default":
        cur.execute(
            """
            INSERT INTO user_portfolio_holdings (symbol, shares, buy_price, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                shares = excluded.shares,
                buy_price = excluded.buy_price,
                updated_at = CURRENT_TIMESTAMP
            """,
            (sym, holding.shares, holding.buy_price),
        )
    cur.execute("UPDATE user_portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (portfolio_id,))
    conn.commit()


def remove_holding_from_portfolio(
    conn: sqlite3.Connection,
    portfolio_id: str,
    symbol: str,
) -> None:
    """Remove a stock from a specific portfolio."""
    init_portfolio_db(conn)
    cur = conn.cursor()
    sym = symbol.strip().upper()
    cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = ? AND symbol = ?", (portfolio_id, sym))
    if portfolio_id == "default":
        cur.execute("DELETE FROM user_portfolio_holdings WHERE symbol = ?", (sym,))
    cur.execute("UPDATE user_portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (portfolio_id,))
    conn.commit()


def save_user_holdings(
    conn: sqlite3.Connection,
    holdings: list[UserHolding],
    portfolio_id: str = "default",
) -> None:
    """Persist active user holdings to database for given portfolio (default='default')."""
    init_portfolio_db(conn)
    update_portfolio(conn, portfolio_id=portfolio_id, holdings=holdings)


def load_user_holdings(
    conn: sqlite3.Connection,
    portfolio_id: str = "default",
) -> list[UserHolding]:
    """Retrieve saved user holdings from database for given portfolio (default='default')."""
    p = get_portfolio(conn, portfolio_id)
    if p is not None:
        return p.holdings
    init_portfolio_db(conn)
    cur = conn.cursor()
    cur.execute("SELECT symbol, shares, buy_price FROM user_portfolio_holdings ORDER BY symbol ASC")
    rows = cur.fetchall()
    return [UserHolding(symbol=r[0], shares=float(r[1]), buy_price=float(r[2])) for r in rows]


def _determine_factor_tiers(
    bqs: float, val: float, risk: float
) -> dict[str, PortfolioFactorHealth]:
    """Classify weighted scores into institutional tiers with plain-English rationales."""
    # 1. Quality
    if bqs >= 80.0:
        q_tier = "TIER_1_MONOPOLISTIC_MOAT"
        q_interp = (
            "Outstanding portfolio pricing power, superior capital returns (ROIC > 20%), and clean balance sheets."
        )
    elif bqs >= 65.0:
        q_tier = "TIER_2_STABLE_COMPOUNDER"
        q_interp = (
            "Resilient business franchises with predictable earnings visibility and disciplined capital reinvestment."
        )
    elif bqs >= 50.0:
        q_tier = "TIER_3_CYCLICAL_AVERAGE"
        q_interp = (
            "Average competitive moats susceptible to cyclical margin pressure or elevated working capital intensity."
        )
    else:
        q_tier = "TIER_4_WEAK_GOVERNANCE"
        q_interp = "Sub-par return on capital or elevated accrual drag. High exposure to structural sector disruption."

    # 2. Valuation
    if val >= 70.0:
        v_tier = "DEEP_MARGIN_OF_SAFETY"
        v_interp = "Substantial margin of safety. Portfolio trades at attractive discounts to normalized earnings."
    elif val >= 50.0:
        v_tier = "FAIR_VALUE_CORRIDOR"
        v_interp = "Balanced multiples. Portfolio pricing aligns reasonably with cash generation and growth prospects."
    elif val >= 35.0:
        v_tier = "GROWTH_PREMIUM_ELEVATED"
        v_interp = "Priced for strong execution. Valuation multiples leave little room for quarterly earnings misses."
    else:
        v_tier = "OVERVALUED_EXTREME"
        v_interp = "Stretched valuations across key holdings. Asymmetric downside risk to multiple contraction."

    # 3. Solvency & Risk
    if risk >= 70.0:
        r_tier = "LOW_RISK_FORTRESS"
        r_interp = "Fortress balance sheets with low financial gearing, strong interest coverage, and low default risk."
    elif risk >= 50.0:
        r_tier = "MODERATE_SOLVENCY"
        r_interp = "Healthy solvency with manageable debt loads supported by predictable operating cash flows."
    else:
        r_tier = "ELEVATED_FINANCIAL_RISK"
        r_interp = "High financial leverage or elevated beta volatility across top portfolio positions."

    return {
        "business_quality": PortfolioFactorHealth(
            score=round(bqs, 1),
            tier=q_tier,
            interpretation=q_interp,
            summary_metric=f"Weighted Quality Moat: {bqs:.1f}/100",
        ),
        "valuation": PortfolioFactorHealth(
            score=round(val, 1),
            tier=v_tier,
            interpretation=v_interp,
            summary_metric=f"Weighted Safety Margin: {val:.1f}/100",
        ),
        "risk_solvency": PortfolioFactorHealth(
            score=round(risk, 1),
            tier=r_tier,
            interpretation=r_interp,
            summary_metric=f"Weighted Solvency Strength: {risk:.1f}/100",
        ),
    }


def evaluate_portfolio_health(
    conn: sqlite3.Connection,
    holdings: list[UserHolding],
    max_sector_cap_pct: float = 35.0,
    max_stock_cap_pct: float = 20.0,
    fetch_live: bool = True,
) -> PortfolioHealthReport:
    """Perform comprehensive health diagnosis and generate actionable BUY/SELL/HOLD/TRIM advice."""
    today_str = date.today().isoformat()
    if not holdings:
        default_diversification = PortfolioDiversification(
            hhi_score=0.0,
            diversification_tier="N/A",
            equity_weight_pct=0.0,
            etf_weight_pct=0.0,
            top_3_concentration_pct=0.0,
            total_positions=0,
            sector_count=0,
        )
        default_blueprint = RebalancingBlueprint(
            total_capital_unlocked=0.0,
            total_capital_needed=0.0,
            net_cash_flow=0.0,
            rebalance_urgency="LOW",
            orders=[],
            strategic_summary="No active holdings to rebalance.",
        )
        return PortfolioHealthReport(
            asof_date=today_str,
            total_invested=0.0,
            total_current_value=0.0,
            total_unrealized_pnl=0.0,
            total_unrealized_pnl_pct=0.0,
            weighted_business_score=0.0,
            weighted_valuation_score=0.0,
            weighted_risk_score=0.0,
            weighted_investment_score=0.0,
            overall_health_score=0.0,
            overall_health_grade="N/A",
            positions=[],
            sector_exposures={},
            sector_warnings=[],
            critical_redline_alerts=[],
            suggested_replacements=[],
            summary_action_plan="No active holdings to diagnose.",
            portfolio_horizons={},
            factor_health={},
            diversification=default_diversification,
            rebalancing_blueprint=default_blueprint,
        )

    # 1. Analyze each holding individually
    total_val = 0.0
    total_cost = 0.0
    analyses_map = {}
    for h in holdings:
        sym = h.symbol.strip().upper()
        try:
            res = analyze_stock_on_demand(conn, sym, fetch_live=fetch_live)
        except ValueError:
            # If stock cannot be found in live feed or DB, handle gracefully for manual portfolio holding:
            # use holding's buy_price as price rather than arbitrary 100.0, and mark unverified
            from invst.scoring.stock_analyzer import (
                FullStockAnalysis,
                ScoreBreakdowns,
                FactorTierBreakdown,
                TacticalActionPlan,
                ResearchReport,
                MultiHorizonReturn,
            )

            neutral_tier = FactorTierBreakdown(
                score=50.0,
                tier="UNVERIFIED",
                interpretation="Ticker not found in live feed or database.",
                summary_metric="N/A",
            )
            res = FullStockAnalysis(
                symbol=sym,
                company_name=f"{sym} (Unrecognized Ticker)",
                sector="diversified",
                sector_archetype="DIVERSIFIED",
                is_etf=False,
                current_price=h.buy_price,
                change_pct=0.0,
                business_score=50.0,
                valuation_score=50.0,
                risk_score=50.0,
                investment_score=50.0,
                action_verdict="HOLD",
                action_badge="❓ UNVERIFIED",
                action_rationale=f"Ticker '{sym}' could not be identified or found on NSE/BSE. Valued at buy price (₹{h.buy_price:,.2f}).",
                matrix_quadrant="Unverified Asset",
                quality_tier="Unverified",
                valuation_band="Fair Value",
                score_breakdowns=ScoreBreakdowns(
                    business_quality=neutral_tier,
                    valuation=neutral_tier,
                    risk_solvency=neutral_tier,
                ),
                tactical_action=TacticalActionPlan(
                    dip_target_price=h.buy_price,
                    dip_discount_pct=0.0,
                    stop_loss_level=round(h.buy_price * 0.9, 2),
                    technical_trend="NEUTRAL",
                    verdict_reasoning=f"Unrecognized symbol '{sym}'. Invalidation level estimated at 10% below cost.",
                ),
                research_report=ResearchReport(
                    executive_summary=f"Symbol '{sym}' could not be found on NSE/BSE or local database.",
                    fundamental_moat="No financial data available.",
                    valuation_context="Tracked at purchase cost.",
                    technical_momentum="No market feed available.",
                    scenario_analysis="N/A",
                ),
                horizon_3m=MultiHorizonReturn(
                    horizon_name="3M",
                    expected_return_pct=0.0,
                    bull_return_pct=0.0,
                    bear_return_pct=0.0,
                    projected_price=h.buy_price,
                ),
                horizon_6m=MultiHorizonReturn(
                    horizon_name="6M",
                    expected_return_pct=0.0,
                    bull_return_pct=0.0,
                    bear_return_pct=0.0,
                    projected_price=h.buy_price,
                ),
                horizon_12m=MultiHorizonReturn(
                    horizon_name="12M",
                    expected_return_pct=0.0,
                    bull_return_pct=0.0,
                    bear_return_pct=0.0,
                    projected_price=h.buy_price,
                ),
                horizon_3y=MultiHorizonReturn(
                    horizon_name="3Y",
                    expected_return_pct=0.0,
                    bull_return_pct=0.0,
                    bear_return_pct=0.0,
                    projected_price=h.buy_price,
                ),
                reverse_dcf_implied_growth=None,
                reverse_dcf_assessment="N/A",
                is_investment_worthy=False,
                asof_date=today_str,
                is_live_data=False,
                headlines=[],
            )
        analyses_map[sym] = res

        pos_val = round(h.shares * res.current_price, 2)
        pos_cost = round(h.shares * h.buy_price, 2)
        total_val += pos_val
        total_cost += pos_cost

    # 2. Sector allocations & weights
    sector_values: dict[str, float] = {}
    equity_val = 0.0
    etf_val = 0.0

    for h in holdings:
        sym = h.symbol.strip().upper()
        res = analyses_map[sym]
        pos_val = h.shares * res.current_price
        sec = res.sector
        sector_values[sec] = sector_values.get(sec, 0.0) + pos_val
        if getattr(res, "is_etf", False):
            etf_val += pos_val
        else:
            equity_val += pos_val

    sector_exposures = {
        sec: round((val / total_val) * 100.0, 1) if total_val > 0 else 0.0
        for sec, val in sector_values.items()
    }

    sector_warnings = []
    for sec, exp in sector_exposures.items():
        if exp > max_sector_cap_pct:
            sector_warnings.append(
                f"Sector '{sec.title()}' represents {exp:.1f}% of portfolio, exceeding maximum {max_sector_cap_pct:.0f}% cap."
            )

    # 3. Position-by-Position Health and Tactical Advisory
    positions: list[PositionHealth] = []
    rebalance_orders: list[RebalanceOrder] = []
    weighted_bqs = 0.0
    weighted_val = 0.0
    weighted_risk = 0.0
    weighted_inv = 0.0
    critical_redlines = []

    # Sort holdings by position value descending to determine top-3 concentration
    sorted_holdings = sorted(
        holdings,
        key=lambda h: h.shares * analyses_map[h.symbol.strip().upper()].current_price,
        reverse=True,
    )

    for h in sorted_holdings:
        sym = h.symbol.strip().upper()
        res = analyses_map[sym]
        pos_val = round(h.shares * res.current_price, 2)
        pos_cost = round(h.shares * h.buy_price, 2)
        pnl = round(pos_val - pos_cost, 2)
        pnl_pct = round((pnl / pos_cost) * 100.0, 2) if pos_cost > 0 else 0.0
        weight_pct = round((pos_val / total_val) * 100.0, 2) if total_val > 0 else 0.0

        # Weighted scores
        weighted_bqs += res.business_score * (weight_pct / 100.0)
        weighted_val += res.valuation_score * (weight_pct / 100.0)
        weighted_risk += getattr(res, "risk_score", 50.0) * (weight_pct / 100.0)
        weighted_inv += res.investment_score * (weight_pct / 100.0)

        is_etf = getattr(res, "is_etf", False)

        # Extract tactical metadata from FullStockAnalysis
        tactical = getattr(res, "tactical_action", None)
        dip_target = getattr(tactical, "dip_target_price", round(res.current_price * 0.95, 1))
        dip_discount = getattr(tactical, "dip_discount_pct", 5.0)
        stop_loss = getattr(tactical, "stop_loss_level", round(res.current_price * 0.88, 1))

        tech = getattr(res, "technical_overview", None)
        trend_phase = getattr(tech, "trend_phase", "Neutral Consolidation")

        score_b = getattr(res, "score_breakdowns", None)
        if score_b and hasattr(score_b, "business_quality"):
            q_tier = score_b.business_quality.tier
        elif is_etf:
            q_tier = "INDEX_BENCHMARK_STABILIZER"
        elif res.business_score >= 80:
            q_tier = "TIER_1_MONOPOLISTIC_MOAT"
        elif res.business_score >= 65:
            q_tier = "TIER_2_STABLE_COMPOUNDER"
        else:
            q_tier = "TIER_3_CYCLICAL_AVERAGE"

        # Determine Position Action (BUY_MORE / HOLD / TRIM / EXIT_SELL) & exact share adjustment
        action_verdict = "HOLD"
        action_badge = "🟡 HOLD"
        action_rationale = ""
        target_weight_pct = weight_pct
        shares_to_adjust = 0.0
        capital_delta = 0.0

        # ETF exemption: ETFs can hold up to 35% without single-stock trim penalty
        stock_cap = 35.0 if is_etf else max_stock_cap_pct

        if res.redlines_triggered:
            action_verdict = "EXIT_SELL"
            action_badge = "🚨 EXIT / SELL"
            reasons = "; ".join(res.redlines_triggered)
            target_weight_pct = 0.0
            shares_to_adjust = -h.shares
            capital_delta = pos_val
            action_rationale = (
                f"Disqualified: {reasons}. Invalidate position immediately and harvest ₹{pos_val:,.0f}."
            )
            critical_redlines.append(f"{sym}: {reasons}")
            rebalance_orders.append(
                RebalanceOrder(
                    symbol=sym,
                    action="SELL",
                    shares=h.shares,
                    estimated_price=res.current_price,
                    capital_impact=pos_val,
                    target_weight_pct=0.0,
                    rationale=f"Violates governance / solvency redlines ({reasons}). Full exit required.",
                )
            )
        elif res.action_verdict == "AVOID" and not is_etf:
            action_verdict = "EXIT_SELL"
            action_badge = "🔴 EXIT / SELL"
            target_weight_pct = 0.0
            shares_to_adjust = -h.shares
            capital_delta = pos_val
            action_rationale = (
                f"Sub-par business quality ({res.business_score:.1f}/100) and negative risk-reward. "
                f"Classified as Value Trap. Reallocate ₹{pos_val:,.0f} into core compounders."
            )
            rebalance_orders.append(
                RebalanceOrder(
                    symbol=sym,
                    action="SELL",
                    shares=h.shares,
                    estimated_price=res.current_price,
                    capital_impact=pos_val,
                    target_weight_pct=0.0,
                    rationale="Value Trap profile. Sell all shares to preserve capital.",
                )
            )
        elif weight_pct > stock_cap:
            action_verdict = "TRIM"
            action_badge = "✂️ TRIM"
            target_weight_pct = stock_cap
            excess_pct = weight_pct - stock_cap
            excess_val = (excess_pct / 100.0) * total_val
            trim_shares = max(1.0, math.floor(excess_val / res.current_price))
            trim_capital = round(trim_shares * res.current_price, 2)
            shares_to_adjust = -trim_shares
            capital_delta = trim_capital
            action_rationale = (
                f"Over-concentrated ({weight_pct:.1f}% vs {stock_cap:.0f}% cap). "
                f"Trim {trim_shares:.0f} shares at ~₹{res.current_price:,.1f} to release ₹{trim_capital:,.0f}."
            )
            rebalance_orders.append(
                RebalanceOrder(
                    symbol=sym,
                    action="TRIM",
                    shares=trim_shares,
                    estimated_price=res.current_price,
                    capital_impact=trim_capital,
                    target_weight_pct=target_weight_pct,
                    rationale=f"Trim {excess_pct:.1f}% excess concentration above {stock_cap:.0f}% single-holding cap.",
                )
            )
        elif sector_exposures.get(res.sector, 0.0) > max_sector_cap_pct and weight_pct > 15.0 and not is_etf:
            action_verdict = "TRIM"
            action_badge = "✂️ TRIM"
            target_weight_pct = 12.0
            trim_pct = max(0.0, weight_pct - target_weight_pct)
            excess_val = (trim_pct / 100.0) * total_val
            trim_shares = max(1.0, math.floor(excess_val / res.current_price))
            trim_capital = round(trim_shares * res.current_price, 2)
            shares_to_adjust = -trim_shares
            capital_delta = trim_capital
            action_rationale = (
                f"Sector '{res.sector.title()}' over-weight ({sector_exposures[res.sector]:.1f}%). "
                f"Trim {trim_shares:.0f} shares to mitigate cluster correlation risk."
            )
            rebalance_orders.append(
                RebalanceOrder(
                    symbol=sym,
                    action="TRIM",
                    shares=trim_shares,
                    estimated_price=res.current_price,
                    capital_impact=trim_capital,
                    target_weight_pct=target_weight_pct,
                    rationale=f"Reduce sector exposure in '{res.sector.title()}' towards target 12%.",
                )
            )
        elif res.action_verdict in ["STRONG_BUY", "TACTICAL_BUY"] and weight_pct < 15.0:
            action_verdict = "BUY_MORE"
            action_badge = "🟢 BUY / ACCUMULATE"
            target_weight_pct = min(18.0, weight_pct + 5.0)
            add_pct = target_weight_pct - weight_pct
            add_val = (add_pct / 100.0) * total_val
            add_shares = max(1.0, math.floor(add_val / res.current_price))
            add_capital = round(add_shares * res.current_price, 2)
            shares_to_adjust = add_shares
            capital_delta = -add_capital
            action_rationale = (
                f"High-conviction idea ({res.investment_score:.1f}/100). "
                f"Accumulate up to {add_shares:.0f} shares on pullbacks towards ₹{dip_target:,.1f} (-{dip_discount:.1f}% dip)."
            )
            rebalance_orders.append(
                RebalanceOrder(
                    symbol=sym,
                    action="ACCUMULATE",
                    shares=add_shares,
                    estimated_price=dip_target,
                    capital_impact=-add_capital,
                    target_weight_pct=target_weight_pct,
                    rationale=f"Scale conviction weight from {weight_pct:.1f}% to {target_weight_pct:.1f}% on market pullbacks.",
                )
            )
        elif res.action_verdict == "HOLD_WAIT":
            action_verdict = "HOLD"
            action_badge = "🟡 HOLD"
            target_weight_pct = weight_pct
            shares_to_adjust = 0.0
            capital_delta = 0.0
            action_rationale = (
                f"Solid business moat ({res.business_score:.1f}/100), but valuation is currently rich. "
                f"Hold existing position; patient buy limit is ₹{dip_target:,.1f}."
            )
        else:
            action_verdict = "HOLD"
            action_badge = "🟡 HOLD"
            target_weight_pct = weight_pct
            shares_to_adjust = 0.0
            capital_delta = 0.0
            ret_12m = res.horizon_12m.expected_return_pct
            action_rationale = (
                f"Healthy holding within risk limits. 12M expected return is {ret_12m:+.1f}%. "
                f"Invalidation stop-loss is ₹{stop_loss:,.1f}."
            )

        positions.append(
            PositionHealth(
                symbol=sym,
                shares=h.shares,
                buy_price=h.buy_price,
                current_price=res.current_price,
                current_value=pos_val,
                weight_pct=weight_pct,
                target_weight_pct=target_weight_pct,
                shares_to_adjust=shares_to_adjust,
                capital_delta=capital_delta,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                business_quality_score=res.business_score,
                valuation_score=res.valuation_score,
                risk_score=getattr(res, "risk_score", 50.0),
                investment_score=res.investment_score,
                quality_tier=q_tier,
                action_verdict=action_verdict,
                action_badge=action_badge,
                action_rationale=action_rationale,
                dip_target_price=dip_target,
                dip_discount_pct=dip_discount,
                stop_loss_level=stop_loss,
                technical_trend=trend_phase,
                is_etf=is_etf,
                redlines_triggered=res.redlines_triggered,
                expected_return_12m=res.horizon_12m.expected_return_pct,
                sector=res.sector,
                target_price=getattr(h, "target_price", None),
                notes=getattr(h, "notes", ""),
            )
        )

    # 4. Overall Health Score Calculation (0 - 100)
    health_score = 0.60 * weighted_bqs + 0.40 * weighted_val
    if critical_redlines:
        health_score -= len(critical_redlines) * 15.0
    if sector_warnings:
        health_score -= len(sector_warnings) * 10.0
    health_score = max(0.0, min(100.0, health_score))

    if health_score >= 75.0:
        grade = "EXCELLENT"
    elif health_score >= 60.0:
        grade = "GOOD"
    elif health_score >= 45.0:
        grade = "NEEDS_ATTENTION"
    else:
        grade = "HIGH_RISK"

    # 5. Multi-Horizon Portfolio Aggregate Projections (3M, 6M, 12M, 3Y)
    horizons: dict[str, PortfolioHorizonSummary] = {}
    for h_code, h_name, years in [
        ("3m", "3-Month Tactical Horizon", 0.25),
        ("6m", "6-Month Intermediate Horizon", 0.5),
        ("12m", "12-Month Annual Horizon", 1.0),
        ("3y", "3-Year Compounding Horizon", 3.0),
    ]:
        w_exp = 0.0
        w_bull = 0.0
        w_bear = 0.0
        for p in positions:
            res = analyses_map[p.symbol]
            h_obj = getattr(res, f"horizon_{h_code}", None)
            if h_obj:
                w_frac = p.weight_pct / 100.0
                w_exp += h_obj.expected_return_pct * w_frac
                w_bull += h_obj.return_bull_pct * w_frac
                w_bear += h_obj.return_bear_pct * w_frac

        proj_val = round(total_val * (1.0 + w_exp / 100.0), 2)
        cagr = None
        if h_code == "3y" and total_val > 0:
            cagr = round(((proj_val / total_val) ** (1.0 / 3.0) - 1.0) * 100.0, 2)

        horizons[h_code] = PortfolioHorizonSummary(
            horizon_name=h_name,
            expected_return_pct=round(w_exp, 1),
            bull_return_pct=round(w_bull, 1),
            bear_return_pct=round(w_bear, 1),
            projected_portfolio_value=proj_val,
            cagr_pct=cagr,
        )

    # 6. Factor Health Explanations
    factor_health = _determine_factor_tiers(weighted_bqs, weighted_val, weighted_risk)

    # 7. Diversification & Concentration Metrics
    # HHI = sum of (weight_pct)^2
    hhi = round(sum(p.weight_pct**2 for p in positions), 1)
    if hhi < 1500:
        div_tier = "OPTIMAL_DIVERSIFICATION"
    elif hhi <= 2500:
        div_tier = "MODERATE_CONCENTRATION"
    else:
        div_tier = "HIGH_CONCENTRATION"

    top_3_pct = round(sum(p.weight_pct for p in positions[:3]), 1)
    equity_pct = round((equity_val / total_val) * 100.0, 1) if total_val > 0 else 0.0
    etf_pct = round((etf_val / total_val) * 100.0, 1) if total_val > 0 else 0.0

    diversification = PortfolioDiversification(
        hhi_score=hhi,
        diversification_tier=div_tier,
        equity_weight_pct=equity_pct,
        etf_weight_pct=etf_pct,
        top_3_concentration_pct=top_3_pct,
        total_positions=len(positions),
        sector_count=len(sector_exposures),
    )

    # 8. Rebalancing Blueprint
    total_unlocked = sum(o.capital_impact for o in rebalance_orders if o.capital_impact > 0)
    total_needed = sum(abs(o.capital_impact) for o in rebalance_orders if o.capital_impact < 0)
    net_cash = round(total_unlocked - total_needed, 2)

    if critical_redlines:
        urgency = "CRITICAL"
    elif any(o.action in ["SELL", "TRIM"] for o in rebalance_orders):
        urgency = "HIGH"
    elif any(o.action == "ACCUMULATE" for o in rebalance_orders):
        urgency = "MODERATE"
    else:
        urgency = "LOW"

    if total_unlocked > 0:
        rebalance_summary = (
            f"Executing recommended trims/exits frees up ₹{total_unlocked:,.0f} in cash, "
            f"reducing HHI concentration and eliminating redline liabilities."
        )
    else:
        rebalance_summary = "Portfolio is well-aligned with risk caps. No immediate trims required."

    rebalancing_blueprint = RebalancingBlueprint(
        total_capital_unlocked=round(total_unlocked, 2),
        total_capital_needed=round(total_needed, 2),
        net_cash_flow=net_cash,
        rebalance_urgency=urgency,
        orders=rebalance_orders,
        strategic_summary=rebalance_summary,
    )

    # 9. Suggest Replacements from Top Arth IQ Ideas
    pit = PointInTimeDataAccess(conn, asof=date.today())
    scorecards = compute_composite_scores(pit, filter_universe_first=False)
    held_symbols = {h.symbol.strip().upper() for h in holdings}
    candidate_picks = [sc for sc in scorecards if sc.symbol not in held_symbols][:3]

    replacements = []
    for sc in candidate_picks:
        replacements.append(
            {
                "symbol": sc.symbol,
                "sector": sc.sector.title(),
                "composite_score": sc.composite_score,
                "quality_score": sc.quality_score,
                "valuation_score": sc.valuation_score,
                "suggested_role": "Core Compounding Alpha Allocation",
            }
        )

    # 10. Action Plan Summary
    sells = [p.symbol for p in positions if p.action_verdict == "EXIT_SELL"]
    trims = [p.symbol for p in positions if p.action_verdict == "TRIM"]
    adds = [p.symbol for p in positions if p.action_verdict == "BUY_MORE"]

    action_summary_parts = []
    if sells:
        action_summary_parts.append(f"Exit {len(sells)} position(s): {', '.join(sells)}")
    if trims:
        action_summary_parts.append(f"Trim {len(trims)} over-concentrated stock(s): {', '.join(trims)}")
    if adds:
        action_summary_parts.append(f"Accumulate {len(adds)} high-conviction idea(s): {', '.join(adds)}")
    if not action_summary_parts:
        action_summary_parts.append("Portfolio is well-balanced. Continue holding current positions.")

    summary_action_plan = " | ".join(action_summary_parts)
    unrealized_pnl = round(total_val - total_cost, 2)
    unrealized_pnl_pct = round((unrealized_pnl / total_cost) * 100.0, 2) if total_cost > 0 else 0.0

    return PortfolioHealthReport(
        asof_date=today_str,
        total_invested=round(total_cost, 2),
        total_current_value=round(total_val, 2),
        total_unrealized_pnl=unrealized_pnl,
        total_unrealized_pnl_pct=unrealized_pnl_pct,
        weighted_business_score=round(weighted_bqs, 1),
        weighted_valuation_score=round(weighted_val, 1),
        weighted_risk_score=round(weighted_risk, 1),
        weighted_investment_score=round(weighted_inv, 1),
        overall_health_score=round(health_score, 1),
        overall_health_grade=grade,
        positions=positions,
        sector_exposures=sector_exposures,
        sector_warnings=sector_warnings,
        critical_redline_alerts=critical_redlines,
        suggested_replacements=replacements,
        summary_action_plan=summary_action_plan,
        portfolio_horizons=horizons,
        factor_health=factor_health,
        diversification=diversification,
        rebalancing_blueprint=rebalancing_blueprint,
    )
