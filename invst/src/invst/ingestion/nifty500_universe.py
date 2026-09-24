"""Nifty 500 Full Universe Definitions and Sector Archetype Registry.

Provides point-in-time constituent definitions, sector mappings, ISINs, and
baseline financial profiles for both the 20-stock seed prototype and the
scaled 500-stock institutional universe.
"""

from __future__ import annotations

import random
from typing import NamedTuple

from invst.scoring.sectors.archetypes import SectorArchetype


class StockDefinition(NamedTuple):
    symbol: str
    sector: str
    isin: str
    archetype: SectorArchetype
    base_mcap: float  # INR Crore
    base_pe: float
    base_pb: float
    base_roe: float
    base_roce: float
    annual_drift: float
    volatility: float


# The canonical 20-stock audited benchmark universe (Frozen V0.2.1)
CORE_20_STOCKS: list[StockDefinition] = [
    StockDefinition("HDFCBANK", "financial_services", "INE040A01034", SectorArchetype.FINANCIALS, 250000.0, 24.0, 3.8, 19.0, 17.5, 0.155, 0.20),
    StockDefinition("ICICIBANK", "financial_services", "INE090A01021", SectorArchetype.FINANCIALS, 160000.0, 18.0, 2.1, 14.5, 13.0, 0.185, 0.24),
    StockDefinition("KOTAKBANK", "financial_services", "INE237A01028", SectorArchetype.FINANCIALS, 130000.0, 28.0, 4.2, 16.0, 15.0, 0.145, 0.21),
    StockDefinition("BAJFINANCE", "financial_services", "INE296A01024", SectorArchetype.FINANCIALS, 45000.0, 32.0, 6.5, 22.0, 20.0, 0.260, 0.28),
    StockDefinition("AXISBANK", "financial_services", "INE238A01034", SectorArchetype.FINANCIALS, 110000.0, 20.0, 2.3, 13.0, 12.0, 0.130, 0.25),
    StockDefinition("TCS", "information_technology", "INE467B01029", SectorArchetype.TECH_SERVICES, 480000.0, 20.0, 8.5, 38.0, 45.0, 0.150, 0.18),
    StockDefinition("INFY", "information_technology", "INE009A01021", SectorArchetype.TECH_SERVICES, 240000.0, 17.0, 5.2, 25.0, 32.0, 0.140, 0.21),
    StockDefinition("HCLTECH", "information_technology", "INE860A01027", SectorArchetype.TECH_SERVICES, 115000.0, 15.0, 4.1, 26.0, 30.0, 0.170, 0.22),
    StockDefinition("LT", "capital_goods", "INE018A01030", SectorArchetype.INDUSTRIALS_CAPEX, 140000.0, 23.0, 3.1, 14.0, 16.0, 0.165, 0.22),
    StockDefinition("RELIANCE", "oil_gas_consumable_fuels", "INE002A01018", SectorArchetype.INDUSTRIALS_CAPEX, 330000.0, 14.0, 1.6, 13.5, 12.5, 0.190, 0.23),
    StockDefinition("TATAPOWER", "power", "INE245A01021", SectorArchetype.INDUSTRIALS_CAPEX, 20000.0, 16.0, 1.4, 9.5, 10.5, 0.175, 0.27),
    StockDefinition("NTPC", "power", "INE733E01010", SectorArchetype.INDUSTRIALS_CAPEX, 120000.0, 10.5, 1.2, 12.0, 11.5, 0.140, 0.19),
    StockDefinition("HINDUNILVR", "fast_moving_consumer_goods", "INE030A01027", SectorArchetype.CONSUMER_MOATS, 180000.0, 42.0, 24.0, 65.0, 85.0, 0.145, 0.16),
    StockDefinition("ITC", "fast_moving_consumer_goods", "INE154A01025", SectorArchetype.CONSUMER_MOATS, 250000.0, 26.0, 8.0, 28.0, 36.0, 0.115, 0.19),
    StockDefinition("TITAN", "consumer_durables", "INE280A01028", SectorArchetype.CONSUMER_MOATS, 32000.0, 40.0, 9.0, 24.0, 28.0, 0.245, 0.25),
    StockDefinition("TATAMOTORS", "automobile_and_auto_components", "INE155A01022", SectorArchetype.CONSUMER_MOATS, 125000.0, 12.0, 1.8, 11.0, 12.0, 0.140, 0.32),
    StockDefinition("MARUTI", "automobile_and_auto_components", "INE585B01010", SectorArchetype.CONSUMER_MOATS, 145000.0, 28.0, 4.5, 18.0, 24.0, 0.125, 0.22),
    StockDefinition("SUNPHARMA", "healthcare", "INE044A01036", SectorArchetype.HEALTHCARE_PHARMA, 190000.0, 27.0, 5.0, 17.0, 19.0, 0.110, 0.21),
    StockDefinition("CIPLA", "healthcare", "INE059A01026", SectorArchetype.HEALTHCARE_PHARMA, 48000.0, 24.0, 3.6, 14.5, 16.5, 0.120, 0.20),
    StockDefinition("BHARTIARTL", "telecommunication", "INE397D01024", SectorArchetype.TECH_SERVICES, 135000.0, 22.0, 2.2, 9.0, 10.0, 0.175, 0.24),
]

# Sector allocation blueprint for scaling to 500 stocks
SECTOR_DISTRIBUTION: list[tuple[str, SectorArchetype, int, float, float, float, float]] = [
    # (sector_code, archetype, target_count, avg_mcap, avg_pe, avg_roe, avg_drift)
    ("financial_services", SectorArchetype.FINANCIALS, 85, 45000.0, 18.0, 15.0, 0.15),
    ("information_technology", SectorArchetype.TECH_SERVICES, 55, 38000.0, 24.0, 26.0, 0.16),
    ("oil_gas_consumable_fuels", SectorArchetype.INDUSTRIALS_CAPEX, 25, 65000.0, 12.0, 14.0, 0.13),
    ("fast_moving_consumer_goods", SectorArchetype.CONSUMER_MOATS, 40, 35000.0, 38.0, 32.0, 0.13),
    ("automobile_and_auto_components", SectorArchetype.CONSUMER_MOATS, 45, 28000.0, 22.0, 17.0, 0.14),
    ("healthcare", SectorArchetype.HEALTHCARE_PHARMA, 50, 25000.0, 28.0, 16.5, 0.14),
    ("capital_goods", SectorArchetype.INDUSTRIALS_CAPEX, 50, 22000.0, 26.0, 15.5, 0.17),
    ("metals_mining", SectorArchetype.INDUSTRIALS_CAPEX, 30, 35000.0, 10.5, 16.0, 0.15),
    ("power", SectorArchetype.INDUSTRIALS_CAPEX, 20, 28000.0, 14.0, 12.0, 0.14),
    ("chemicals", SectorArchetype.INDUSTRIALS_CAPEX, 35, 18000.0, 30.0, 19.0, 0.16),
    ("consumer_durables", SectorArchetype.CONSUMER_MOATS, 25, 16000.0, 35.0, 20.0, 0.17),
    ("construction_materials", SectorArchetype.INDUSTRIALS_CAPEX, 20, 24000.0, 25.0, 13.5, 0.13),
    ("realty", SectorArchetype.INDUSTRIALS_CAPEX, 20, 15000.0, 28.0, 11.0, 0.16),
]


def build_full_nifty500_roster() -> list[StockDefinition]:
    """Construct the complete 500-stock institutional universe roster.

    Guarantees that CORE_20_STOCKS are preserved exactly at the top of the roster,
    followed by 480 systematically constructed Indian equities spanning all sectors.
    """
    roster: list[StockDefinition] = list(CORE_20_STOCKS)
    existing_symbols = {s.symbol for s in roster}

    rng = random.Random(42)  # Deterministic seed for reproducible testing

    total_added = len(roster)
    target_total = 500

    # Prefix mapping for readable, realistic Indian equity symbols
    sector_prefixes = {
        "financial_services": ["SBIN", "CANBK", "PNB", "BANKBARODA", "FEDERALBNK", "INDUSINDBK", "IDFCFIRSTB", "MUTHOOTFIN", "CHOLAFIN", "SHRIRAMFIN", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "ICICIGI", "BAJAJHLDNG", "HDFCAMC", "BSE", "CDSL", "MCX", "POONAWALLA", "LICHSGFIN", "LICI"],
        "information_technology": ["WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "KPITTECH", "TATAELXSI", "LTTS", "ORCL", "CYIENT", "SONACOMS", "ZENSARTECH", "HAPPSTMNDS", "MASTEK", "BSOFT", "LATENTVIEW", "RATEGAIN"],
        "capital_goods": ["BEL", "HAL", "SIEMENS", "ABB", "CUMMINSIND", "BHARATFORG", "AIAENG", "THERMAX", "POLYCAB", "KEI", "HAVELLS", "VOLTAS", "CGPOWER", "SUZLON", "BHEL", "MAZDOCK", "COCHINSHIP", "GRSE"],
        "healthcare": ["DRREDDY", "DIVISLAB", "APOLLOHOSP", "MANKIND", "TORNTPHARM", "LUPIN", "AUROPHARMA", "ZYDUSLIFE", "ALKEM", "BIOCON", "GLENMARK", "IPCALAB", "MAXHEALTH", "FORTIS", "SYNGENE", "LAURUSLABS"],
        "automobile_and_auto_components": ["BAJAJ-AUTO", "M&M", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "MOTHERSON", "BOSCHLTD", "MRF", "APOLLOTYRE", "BALKRISIND", "EXIDEIND", "AMARAJABAT", "ENDURANCE"],
        "fast_moving_consumer_goods": ["NESTLEIND", "BRITANNIA", "TATACONSUM", "DABUR", "MARICO", "COLPAL", "GODREJCP", "VBL", "PGHH", "RADICO", "UBL", "EMAMILTD", "JYOTHYLAB", "BIKAJI"],
        "metals_mining": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL", "NMDC", "JINDALSTEL", "SAIL", "NATIONALUM", "APLAPOLLO", "RATNAMANI"],
        "oil_gas_consumable_fuels": ["ONGC", "IOC", "BPCL", "HPCL", "GAIL", "PETRONET", "IGL", "MGL", "GUJGASLTD", "OIL"],
        "chemicals": ["PIDILITIND", "SRF", "GUJFLUORO", "DEEPAKNTR", "ATUL", "AARTIIND", "TATACHEM", "CLEAN", "NAVINFLUOR", "FINEORG", "SUMICHEM"],
        "power": ["POWERGRID", "ADANIGREEN", "ADANIPOWER", "NHPC", "SJVN", "CESC", "JSWENERGY", "TORNTPOWER"],
        "consumer_durables": ["DIXON", "KALYANKJIL", "RAJESHEXPO", "CROMPTON", "WHIRLPOOL", "BLUESTARCO", "BATAINDIA", "RELAXO", "CENTURYPLY"],
        "construction_materials": ["ULTRACEMCO", "GRASIM", "AMBUJACEM", "ACC", "DALBHARAT", "SHREECEM", "RAMCOCEM", "JKCEMENT", "KAJARIACER"],
        "realty": ["DLF", "GODREJPROP", "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE", "BRIGADE", "SOBHA", "SIGNATURE"],
    }

    # Add well-known names first
    for sector, _, _, avg_mcap, avg_pe, avg_roe, avg_drift in SECTOR_DISTRIBUTION:
        if total_added >= target_total:
            break
        known_symbols = sector_prefixes.get(sector, [])
        for sym in known_symbols:
            if sym not in existing_symbols and total_added < target_total:
                archetype = SectorArchetype.FINANCIALS if sector == "financial_services" else (
                    SectorArchetype.TECH_SERVICES if sector == "information_technology" else (
                        SectorArchetype.HEALTHCARE_PHARMA if sector == "healthcare" else (
                            SectorArchetype.CONSUMER_MOATS if "consumer" in sector or "auto" in sector or sector == "fast_moving_consumer_goods" else SectorArchetype.INDUSTRIALS_CAPEX
                        )
                    )
                )
                mcap = round(avg_mcap * rng.uniform(0.5, 2.5), 1)
                pe = round(avg_pe * rng.uniform(0.7, 1.4), 1)
                pb = round(max(1.0, pe * avg_roe / 100.0 * 0.8), 2)
                roe = round(avg_roe * rng.uniform(0.8, 1.25), 1)
                roce = round(roe * rng.uniform(0.9, 1.15), 1)
                drift = round(avg_drift * rng.uniform(0.85, 1.25), 3)
                vol = round(rng.uniform(0.18, 0.32), 2)
                isin = f"INE{rng.randint(100, 999)}A01{rng.randint(10, 99)}"

                roster.append(StockDefinition(sym, sector, isin, archetype, mcap, pe, pb, roe, roce, drift, vol))
                existing_symbols.add(sym)
                total_added += 1

    # Fill remainder up to exactly 500
    sec_cycle = list(SECTOR_DISTRIBUTION)
    sec_idx = 0
    seq_counter = 101

    while total_added < target_total:
        sec_info = sec_cycle[sec_idx % len(sec_cycle)]
        sector, archetype, _, avg_mcap, avg_pe, avg_roe, avg_drift = sec_info

        sym = f"EQ_{sector[:4].upper()}_{seq_counter}"
        if sym not in existing_symbols:
            mcap = round(avg_mcap * rng.uniform(0.3, 1.5), 1)
            pe = round(avg_pe * rng.uniform(0.6, 1.5), 1)
            pb = round(max(0.8, pe * avg_roe / 100.0 * 0.7), 2)
            roe = round(avg_roe * rng.uniform(0.7, 1.3), 1)
            roce = round(roe * rng.uniform(0.85, 1.2), 1)
            drift = round(avg_drift * rng.uniform(0.8, 1.2), 3)
            vol = round(rng.uniform(0.20, 0.35), 2)
            isin = f"INE{rng.randint(100, 999)}B01{rng.randint(10, 99)}"

            roster.append(StockDefinition(sym, sector, isin, archetype, mcap, pe, pb, roe, roce, drift, vol))
            existing_symbols.add(sym)
            total_added += 1
            seq_counter += 1
        sec_idx += 1

    return roster


def get_universe_roster(mode: str = "sample20") -> list[StockDefinition]:
    """Retrieve the universe definition roster according to the requested mode."""
    if mode == "nifty500":
        return build_full_nifty500_roster()
    return list(CORE_20_STOCKS)
