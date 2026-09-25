"""Tests for all Quant Framework scoring modules (Stages 0–4 and Composite)."""

import sqlite3
from datetime import date

from invst.data_access import PointInTimeDataAccess
from invst.scoring.composite import (
    StockScorecard,
    compute_composite_scores,
    select_shortlist_with_sector_caps,
)
from invst.scoring.filters import evaluate_symbol_filters, filter_universe
from invst.scoring.quality import score_quality_universe
from invst.scoring.risk import score_risk_universe
from invst.scoring.sentiment_overlay import (
    compute_sentiment_overlay,
)
from invst.scoring.valuation import score_valuation_universe

# ── Stage 0 Filter Tests ──────────────────────────────────────────────


def test_stage_0_filters(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))

    # Evaluate STOCK_A (should pass all criteria)
    res_a = evaluate_symbol_filters(pit, "STOCK_A")
    assert res_a.passed is True
    assert len(res_a.reasons) == 0

    # Evaluate PENNY_STOCK (fails price < 10 and mcap < 1000)
    res_penny = evaluate_symbol_filters(pit, "PENNY_STOCK")
    assert res_penny.passed is False
    assert any("penny stock" in r for r in res_penny.reasons)
    assert any("Market cap" in r for r in res_penny.reasons)

    # Evaluate STOCK_B (fails promoter holding 82% > 75%)
    res_b = evaluate_symbol_filters(pit, "STOCK_B")
    assert res_b.passed is False
    assert any("Promoter holding" in r for r in res_b.reasons)

    # Universe filter
    passed_symbols, _ = filter_universe(pit)
    assert "STOCK_A" in passed_symbols
    assert "PENNY_STOCK" not in passed_symbols
    assert "STOCK_B" not in passed_symbols


# ── Stage 1 Quality Scoring Tests ────────────────────────────────────


def test_stage_1_quality_scoring(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    results = score_quality_universe(pit, ["STOCK_A", "STOCK_B"])

    assert "STOCK_A" in results
    assert "STOCK_B" in results
    # STOCK_A has higher ROE/ROCE and lower D/E, so its quality score should exceed STOCK_B
    assert results["STOCK_A"]["quality_score"] > results["STOCK_B"]["quality_score"]
    assert 0.0 <= results["STOCK_A"]["quality_score"] <= 100.0


# ── Stage 2 Valuation Scoring Tests ──────────────────────────────────


def test_stage_2_valuation_scoring(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    results = score_valuation_universe(pit, ["STOCK_A", "STOCK_B"])

    # STOCK_A has PE 22 vs STOCK_B PE 45. Lower PE should give higher valuation score
    assert results["STOCK_A"]["valuation_score"] > results["STOCK_B"]["valuation_score"]
    assert 0.0 <= results["STOCK_A"]["valuation_score"] <= 100.0


# ── Stage 3 Risk Scoring Tests ───────────────────────────────────────


def test_stage_3_risk_scoring(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    results = score_risk_universe(pit, ["STOCK_A", "STOCK_B"])

    assert "STOCK_A" in results
    assert "STOCK_B" in results
    # Both scores are in [0, 100]
    assert 0.0 <= results["STOCK_A"]["risk_score"] <= 100.0
    assert 0.0 <= results["STOCK_B"]["risk_score"] <= 100.0


# ── Stage 4 Sentiment Overlay Tests ──────────────────────────────────


def test_stage_4_sentiment_overlay(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    res_a = compute_sentiment_overlay(pit, "STOCK_A")
    res_b = compute_sentiment_overlay(pit, "STOCK_B")

    # STOCK_A had positive news (+0.7) and price went up (positive momentum)
    assert res_a["overlay_points"] > 0
    assert res_a["sentiment_score"] == 0.7
    # Overlay is capped at 10.0
    assert -10.0 <= res_a["overlay_points"] <= 10.0

    # STOCK_B had negative news (-0.4)
    assert res_b["sentiment_score"] == -0.4


# ── Composite Scoring & Funnel Tests ─────────────────────────────────


def test_composite_scoring_and_shortlisting(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    # Run composite without Stage 0 filter to score both STOCK_A and STOCK_B
    scorecards = compute_composite_scores(
        pit, symbols=["STOCK_A", "STOCK_B"], filter_universe_first=False
    )

    assert len(scorecards) == 2
    top_stock = scorecards[0]
    assert top_stock.symbol == "STOCK_A"
    assert top_stock.rank == 1
    assert top_stock.composite_score > scorecards[1].composite_score

    # Sector capping test
    mock_cards = [
        StockScorecard("S1", "tech", 90.0, 90.0, 90.0, 90.0, 0.0, 1, {}, {}, {}, {}),
        StockScorecard("S2", "tech", 88.0, 88.0, 88.0, 88.0, 0.0, 2, {}, {}, {}, {}),
        StockScorecard("S3", "tech", 87.0, 87.0, 87.0, 87.0, 0.0, 3, {}, {}, {}, {}),
        StockScorecard("S4", "finance", 85.0, 85.0, 85.0, 85.0, 0.0, 4, {}, {}, {}, {}),
        StockScorecard("S5", "auto", 80.0, 80.0, 80.0, 80.0, 0.0, 5, {}, {}, {}, {}),
    ]
    # Set max sector weight = 40% of 5 = 2 max per sector
    shortlist = select_shortlist_with_sector_caps(
        mock_cards, top_n_initial=5, max_sector_pct=0.40, shortlist_size=3
    )
    # Tech should have at most 2 stocks, so S1, S2, and S4 (finance) make it
    tech_count = sum(1 for c in shortlist if c.sector == "tech")
    assert tech_count <= 2
    assert len(shortlist) == 3
