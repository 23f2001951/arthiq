"""Structured Corporate Event Intelligence Engine for Arth IQ V0.2.

Replaces crude sentiment points with structured event impact propagation.
Classifies corporate disclosures, regulatory notifications, and corporate actions,
computing factor-specific delta adjustments with exponential time decay:

    delta_f(t) = BaseImpact * Materiality * Confidence * exp(-Delta_t / tau)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from invst.data_access import PointInTimeDataAccess

# Event configurations: (Affected Pillar, Base Impact, Half-Life in Days)
EVENT_SPECS: dict[str, tuple[str, float, float]] = {
    "EARNINGS_BEAT": ("GROWTH", 12.0, 45.0),
    "EARNINGS_MISS": ("GROWTH", -15.0, 45.0),
    "GUIDANCE_UPGRADE": ("GROWTH", 15.0, 90.0),
    "GUIDANCE_DOWNGRADE": ("GROWTH", -20.0, 90.0),
    "REGULATORY_ACTION": ("RISK", -25.0, 180.0),
    "REGULATORY_CLEARANCE": ("RISK", 15.0, 120.0),
    "AUDITOR_RESIGNATION": ("GOVERNANCE", -40.0, 180.0),
    "PROMOTER_BUYING": ("GOVERNANCE", 12.0, 60.0),
    "PROMOTER_PLEDGE_INCREASE": ("GOVERNANCE", -25.0, 90.0),
    "MAJOR_CAPEX_ANNOUNCEMENT": ("GROWTH", 10.0, 120.0),
    "LITIGATION_ADVERSE": ("RISK", -20.0, 120.0),
}


@dataclass
class EventImpactSummary:
    symbol: str
    factor_deltas: dict[str, float]  # Pillar -> delta (e.g. {"GOVERNANCE": -15.2, "RISK": -8.4})
    active_events_count: int
    most_material_event: str | None


def compute_event_factor_deltas(
    pit: PointInTimeDataAccess,
    symbol: str,
    lookback_days: int = 180,
) -> EventImpactSummary:
    """Extract structured events and compute decayed factor deltas as of pit.asof."""
    events = pit.get_corporate_events(symbol, lookback_days=lookback_days)
    asof = pit.asof

    deltas: dict[str, float] = {
        "GOVERNANCE": 0.0,
        "RISK": 0.0,
        "GROWTH": 0.0,
        "VALUATION": 0.0,
    }

    most_material = None
    max_materiality = -1.0

    for ev in events:
        spec = EVENT_SPECS.get(ev.event_type)
        if not spec:
            continue

        pillar, base_impact, half_life = spec

        # Compute days elapsed since event
        ev_date = ev.effective_date if isinstance(ev.effective_date, date) else date.fromisoformat(str(ev.effective_date))
        days_elapsed = max(0, (asof - ev_date).days)

        # Direction modifier
        direction_mult = 1.0 if ev.direction.upper() == "POSITIVE" else (-1.0 if ev.direction.upper() == "NEGATIVE" else 0.5)

        # Exponential decay factor
        decay = math.exp(-days_elapsed / half_life)

        # Net impact delta
        impact = abs(base_impact) * direction_mult * ev.materiality_score * ev.confidence_score * decay

        # Accumulate into primary pillar
        deltas[pillar] = deltas.get(pillar, 0.0) + impact

        # Also propagate to secondary affected factors if designated
        for f in ev.affected_factors:
            f_upper = f.upper()
            if f_upper in deltas and f_upper != pillar:
                deltas[f_upper] += impact * 0.5

        if ev.materiality_score > max_materiality:
            max_materiality = ev.materiality_score
            most_material = f"{ev.event_type}: {ev.headline}"

    # Clamp deltas to reasonable factor bounds [-30.0, +20.0]
    clamped_deltas = {
        k: round(max(-30.0, min(20.0, v)), 2) for k, v in deltas.items()
    }

    return EventImpactSummary(
        symbol=symbol,
        factor_deltas=clamped_deltas,
        active_events_count=len(events),
        most_material_event=most_material,
    )
