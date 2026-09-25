"""Seed Nifty 500 constituents history into the database."""

import sqlite3

from invst.config import get_config


def seed():
    cfg = get_config()
    conn = sqlite3.connect(str(cfg.database.path))

    # Basic baseline constituents
    baseline = [
        ("2020-03-31", "RELIANCE", "INE002A01018", "oil_gas_consumable_fuels", "seed"),
        ("2020-03-31", "TCS", "INE467B01029", "information_technology", "seed"),
        ("2020-03-31", "INFY", "INE009A01021", "information_technology", "seed"),
        ("2020-03-31", "HDFCBANK", "INE040A01034", "financial_services", "seed"),
        ("2020-03-31", "ICICIBANK", "INE090A01021", "financial_services", "seed"),
        ("2020-03-31", "HINDUNILVR", "INE030A01027", "fast_moving_consumer_goods", "seed"),
        ("2020-03-31", "ITC", "INE154A01025", "fast_moving_consumer_goods", "seed"),
        ("2020-03-31", "LT", "INE018A01030", "capital_goods", "seed"),
    ]

    conn.executemany(
        "INSERT OR REPLACE INTO index_constituents_history (effective_date, symbol, isin, sector, source) VALUES (?, ?, ?, ?, ?)",
        baseline,
    )
    conn.commit()
    print(f"Seeded {len(baseline)} baseline constituents into index_constituents_history")
    conn.close()

if __name__ == "__main__":
    seed()
