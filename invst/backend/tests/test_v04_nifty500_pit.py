"""Tests for V0.4-C Nifty 500 PIT Universe & Sector Normalization."""

import numpy as np
import pytest

from invst.ingestion.nifty500_universe import CORE_20_STOCKS, build_full_nifty500_roster
from invst.scoring.sectors.archetypes import SectorArchetype
from invst.scoring.sectors.normalization import normalize_cross_sectional_features_by_sector


class TestSectorNormalization:
    """Test sector and archetype-relative feature standardization."""

    def test_empty_matrix(self):
        mat = np.zeros((0, 3))
        res = normalize_cross_sectional_features_by_sector(mat, [], {})
        assert res.shape == (0, 3)

    def test_sector_standardization_shape_and_scale(self):
        # 6 stocks across 2 sectors
        symbols = ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "TCS", "INFY", "HCLTECH"]
        sector_map = {
            "HDFCBANK": "financial_services",
            "ICICIBANK": "financial_services",
            "KOTAKBANK": "financial_services",
            "TCS": "information_technology",
            "INFY": "information_technology",
            "HCLTECH": "information_technology",
        }
        # Column 0: RoE (Banks: ~15, Tech: ~35)
        # Column 1: D/E (Banks: ~6.0, Tech: ~0.0)
        raw_matrix = np.array([
            [14.0, 6.0],
            [15.0, 6.5],
            [16.0, 5.5],
            [30.0, 0.0],
            [35.0, 0.1],
            [40.0, 0.0],
        ], dtype=float)

        norm = normalize_cross_sectional_features_by_sector(raw_matrix, symbols, sector_map)
        assert norm.shape == raw_matrix.shape

        # Within banks (rows 0, 1, 2), RoE mean was 15.0 -> row 1 should be approx 0.0
        assert norm[1, 0] == pytest.approx(0.0, abs=1e-2)
        # Within tech (rows 3, 4, 5), RoE mean was 35.0 -> row 4 should be approx 0.0
        assert norm[4, 0] == pytest.approx(0.0, abs=1e-2)

        # All values clipped within [-3, 3]
        assert np.all(norm >= -3.0)
        assert np.all(norm <= 3.0)


class TestNifty500RosterStructure:
    """Test full institutional universe roster integrity."""

    def test_roster_breadth_and_core_preservation(self):
        roster = build_full_nifty500_roster()
        assert len(roster) == 500

        # Core 20 must be preserved
        core_syms = {s.symbol for s in CORE_20_STOCKS}
        top_20_syms = {s.symbol for s in roster[:20]}
        assert core_syms == top_20_syms

    def test_all_archetypes_represented(self):
        roster = build_full_nifty500_roster()
        archetypes = {s.archetype for s in roster}
        assert SectorArchetype.FINANCIALS in archetypes
        assert SectorArchetype.TECH_SERVICES in archetypes
        assert SectorArchetype.INDUSTRIALS_CAPEX in archetypes
        assert SectorArchetype.CONSUMER_MOATS in archetypes
        assert SectorArchetype.HEALTHCARE_PHARMA in archetypes
