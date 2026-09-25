"""Arth IQ V0.4-C: Nifty 500 Point-in-Time Universe & Sector Normalization Suite.

Evaluates:
1. Nifty 500 Point-in-Time Constituent Integrity & Zero Lookahead Audit
2. Sector Archetype Representation & Balance across the 500-Stock Universe
3. Controlled Sector-Relative Feature Normalization vs Raw Features:
   - Candidate 2: Fundamentals + Momentum (Raw vs Sector-Normalized)
   - Candidate 1: Fundamentals Only (Raw vs Sector-Normalized)
   - Candidate 3: Fundamentals + Sentiment (Raw vs Sector-Normalized)
"""

from __future__ import annotations

import logging
from typing import Any

from invst.ingestion.nifty500_universe import (
    CORE_20_STOCKS,
    SECTOR_DISTRIBUTION,
    build_full_nifty500_roster,
)
from invst.ml.diagnostics import run_diagnostic_8_zero_lookahead_audit
from invst.ml.ranking import evaluate_walk_forward_ranking

logger = logging.getLogger("invst.ml.v04_nifty500_pit")


def audit_nifty500_pit_universe(conn: Any, rebalance_dates: list[str]) -> dict[str, Any]:
    """Audit Nifty 500 universe structure, archetype representation, and PIT compliance."""
    roster = build_full_nifty500_roster()
    core_symbols = {s.symbol for s in CORE_20_STOCKS}

    # Archetype breakdown of 500 roster
    archetype_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    for s in roster:
        arch_name = s.archetype.value
        archetype_counts[arch_name] = archetype_counts.get(arch_name, 0) + 1
        sector_counts[s.sector] = sector_counts.get(s.sector, 0) + 1

    # Database constituent history check
    cur = conn.execute("SELECT COUNT(DISTINCT symbol), COUNT(DISTINCT effective_date) FROM index_constituents_history")
    db_symbols, db_snapshots = cur.fetchone()

    # Zero lookahead audit across rebalance dates
    lookahead_audit = run_diagnostic_8_zero_lookahead_audit(conn, rebalance_dates)

    return {
        "roster_total": len(roster),
        "core_20_preserved": all(s in {r.symbol for r in roster} for s in core_symbols),
        "archetype_distribution": archetype_counts,
        "sector_distribution_target_count": len(SECTOR_DISTRIBUTION),
        "db_constituent_symbols": db_symbols,
        "db_constituent_snapshots": db_snapshots,
        "lookahead_violations": lookahead_audit["violations_count"],
        "lookahead_verified": lookahead_audit["zero_lookahead_verified"],
    }


def evaluate_sector_normalized_predictive_ranking(
    conn: Any,
    rebalance_dates: list[str],
    benchmark_symbol: str = "NIFTY500",
    horizon_days: int = 90,
) -> list[dict[str, Any]]:
    """Compare Raw Features vs Sector-Normalized Features across candidate models."""
    eval_matrix = [
        ("Candidate 2: Fund + Momentum (Raw)", "pair_fund_mom", False),
        ("Candidate 2: Fund + Momentum (Sector-Normalized)", "pair_fund_mom", True),
        ("Candidate 1: Fundamentals Only (Raw)", "set_a", False),
        ("Candidate 1: Fundamentals Only (Sector-Normalized)", "set_a", True),
        ("Candidate 3: Fund + Sentiment (Raw)", "pair_fund_sent", False),
        ("Candidate 3: Fund + Sentiment (Sector-Normalized)", "pair_fund_sent", True),
    ]

    results: list[dict[str, Any]] = []

    for label, mode_key, use_sector_norm in eval_matrix:
        logger.info(f"Evaluating: {label} (sector_norm={use_sector_norm})")
        res = evaluate_walk_forward_ranking(
            conn=conn,
            rebalance_dates=rebalance_dates,
            benchmark_symbol=benchmark_symbol,
            horizon_days=horizon_days,
            feature_mode=mode_key,
            sector_normalize=use_sector_norm,
        )
        s = res.get("summary", {})
        results.append(
            {
                "label": label,
                "mode_key": mode_key,
                "sector_normalized": use_sector_norm,
                "mean_rank_ic": s.get("mean_rank_ic", 0.0),
                "rank_ic_ir": s.get("rank_ic_ir", 0.0),
                "pct_positive_ic": s.get("pct_positive_ic", 0.0),
                "annualized_ls_return": round(s.get("annualized_ls_return", 0.0) * 100.0, 2),
                "q5_minus_q1": s.get("q5_minus_q1", 0.0),
                "monotonic_quarters_pct": s.get("monotonic_quarters_pct", 0.0),
            }
        )

    return results
