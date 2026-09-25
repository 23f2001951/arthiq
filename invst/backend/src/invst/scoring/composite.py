"""Composite Quant Scoring Engine.

Combines Stages 0 to 4 into final rank-ordered scorecards:
1. Stage 0: Universe reduction & safety filters
2. Stage 1: Quality scoring (0–100)
3. Stage 2: Valuation scoring (0–100)
4. Stage 3: Risk scoring (0–100)
5. Stage 4: Sentiment / Momentum overlay (±10 points)

Funnel & Selection:
- Screen investable universe
- Compute Composite = 0.35 * Quality + 0.30 * Valuation + 0.20 * Risk + 0.15 * Sentiment_Mapped
  (or Stage 1-3 composite + Stage 4 overlay points)
- Form Top 50 by composite
- Apply sector cap: no single sector > 35% of Top-50
- Form Top 15 shortlist for final portfolio optimization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.filters import filter_universe
from invst.scoring.quality import score_quality_universe
from invst.scoring.risk import score_risk_universe
from invst.scoring.sentiment_overlay import score_sentiment_universe
from invst.scoring.valuation import score_valuation_universe

logger = logging.getLogger(__name__)


@dataclass
class StockScorecard:
    """Consolidated scorecard containing all metric breakdowns and ranks."""

    symbol: str
    sector: str
    composite_score: float
    quality_score: float
    valuation_score: float
    risk_score: float
    sentiment_overlay_points: float
    rank: int
    quality_details: dict[str, Any]
    valuation_details: dict[str, Any]
    risk_details: dict[str, Any]
    sentiment_details: dict[str, Any]


def compute_composite_scores(
    pit: PointInTimeDataAccess,
    symbols: list[str] | None = None,
    filter_universe_first: bool = True,
    composite_weights: dict[str, float] | None = None,
) -> list[StockScorecard]:
    """Run full Stages 0–4 pipeline and return ordered scorecards."""
    # 1. Universe selection / Stage 0 filtering
    candidate_symbols = symbols or pit.get_universe()
    if filter_universe_first:
        passed_symbols, _ = filter_universe(pit, candidate_symbols)
    else:
        passed_symbols = candidate_symbols

    if not passed_symbols:
        logger.warning("No symbols passed Stage 0 filtering")
        return []

    # Default stage contribution weights
    weights = composite_weights or {
        "quality": 0.35,
        "valuation": 0.30,
        "risk": 0.20,
    }

    # 2. Stage 1 Quality
    quality_res = score_quality_universe(pit, passed_symbols)

    # 3. Stage 2 Valuation
    valuation_res = score_valuation_universe(pit, passed_symbols)

    # 4. Stage 3 Risk
    risk_res = score_risk_universe(pit, passed_symbols)

    # 5. Stage 4 Sentiment Overlay
    sentiment_res = score_sentiment_universe(pit, passed_symbols)

    # 6. Composite synthesis
    scorecards: list[StockScorecard] = []

    for sym in passed_symbols:
        q_item = quality_res.get(sym, {})
        v_item = valuation_res.get(sym, {})
        r_item = risk_res.get(sym, {})
        s_item = sentiment_res.get(sym, {})

        q_score = q_item.get("quality_score", 50.0)
        v_score = v_item.get("valuation_score", 50.0)
        r_score = r_item.get("risk_score", 50.0)
        s_pts = s_item.get("overlay_points", 0.0)
        sector = q_item.get("sector") or pit.get_sector(sym) or "diversified"

        base_composite = (
            weights["quality"] * q_score
            + weights["valuation"] * v_score
            + weights["risk"] * r_score
        )
        # Apply Stage 4 additive overlay
        final_composite = max(0.0, min(100.0, base_composite + s_pts))

        scorecards.append(
            StockScorecard(
                symbol=sym,
                sector=sector,
                composite_score=round(final_composite, 2),
                quality_score=q_score,
                valuation_score=v_score,
                risk_score=r_score,
                sentiment_overlay_points=s_pts,
                rank=0,
                quality_details=q_item,
                valuation_details=v_item,
                risk_details=r_item,
                sentiment_details=s_item,
            )
        )

    # Sort descending by composite score
    scorecards.sort(key=lambda x: x.composite_score, reverse=True)

    # Assign ranks
    for idx, card in enumerate(scorecards, start=1):
        card.rank = idx

    return scorecards


def select_shortlist_with_sector_caps(
    scorecards: list[StockScorecard],
    top_n_initial: int = 50,
    max_sector_pct: float = 0.35,
    shortlist_size: int = 15,
) -> list[StockScorecard]:
    """Apply sector concentration caps and select the final candidate shortlist.

    No single sector can exceed `max_sector_pct` (e.g. 35%) of the pool.
    """
    initial_pool = scorecards[:top_n_initial]
    max_per_sector = max(1, int(top_n_initial * max_sector_pct))

    sector_counts: dict[str, int] = {}
    capped_pool: list[StockScorecard] = []

    for card in initial_pool:
        sec = card.sector
        count = sector_counts.get(sec, 0)
        if count < max_per_sector:
            capped_pool.append(card)
            sector_counts[sec] = count + 1

    # Take Top N for the optimization shortlist
    shortlist = capped_pool[:shortlist_size]
    return shortlist


def select_quick_picks(
    scorecards: list[StockScorecard],
    n: int = 2,
    exclude_symbols: list[str] | None = None,
    max_per_sector: int = 1,
) -> list[StockScorecard]:
    """Select top highest-conviction stocks for tactical / fresh-cash deployment.

    Args:
        scorecards: Sorted list of scored stocks.
        n: Number of picks to return (flexible, user configurable 1 to 50).
        exclude_symbols: Symbols to skip (e.g. existing portfolio holdings).
        max_per_sector: Maximum picks allowed from the same sector (default 1 to ensure diversification).

    Returns:
        List of selected StockScorecards up to length n.
    """
    excluded = set(exclude_symbols or [])
    picks: list[StockScorecard] = []
    sector_counts: dict[str, int] = {}

    # Pass 1: Prioritize cross-sector diversification
    for card in scorecards:
        if card.symbol in excluded:
            continue
        sec = card.sector
        if sector_counts.get(sec, 0) >= max_per_sector:
            continue

        picks.append(card)
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

        if len(picks) >= n:
            return picks

    # Pass 2: If user requested more picks than unique sectors, fill remaining by score
    picked_symbols = {p.symbol for p in picks}
    for card in scorecards:
        if card.symbol in excluded or card.symbol in picked_symbols:
            continue
        picks.append(card)
        if len(picks) >= n:
            break

    return picks
