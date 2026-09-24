# `invst` Database (`db/`)

This directory contains the database migration runner, migration scripts, and seed data for the `invst` investment decision-support system.

The application uses **SQLite** with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and foreign keys enabled (`PRAGMA foreign_keys = ON`), designed for fast point-in-time query performance and multi-process concurrency.

---

## 1. Database Location & Gitignore Status

- **Default Location**: `db/invst.db` (configurable via `config/settings.yaml` under `database.path`).
- **WAL & SHM Files**: SQLite produces `db/invst.db-wal` and `db/invst.db-shm` during operation.
- **Gitignore Status**: All `*.db`, `*.db-wal`, and `*.db-shm` files are **gitignored** (`.gitignore`). Database state is strictly local; schemas and migrations are tracked under version control in `db/migrations/`.

---

## 2. Core Tables Overview

The database schema (defined in `0001_init.sql`) contains 7 core tables designed for point-in-time integrity (preventing lookahead bias):

| Table | Description | Point-in-Time Key |
|---|---|---|
| `index_constituents_history` | Historical Nifty 500 membership snapshots | `effective_date` |
| `daily_prices` | Daily OHLCV price and volume series | `trade_date` |
| `fundamentals_quarterly` | Quarterly financial statements & ratios | `disclosed_at` |
| `news_sentiment` | News headlines and FinBERT sentiment scores | `published_at` |
| `model_predictions` | Walk-forward ML model scores and universe ranks | `asof_date` |
| `portfolio_history` | Quarterly target allocations and execution records | `asof_date`, `run_id` |
| `backtest_runs` | Backtest metadata, configs, and performance metrics | `run_id` |
| `schema_version` | Migration version tracking table | `version` |

---

## 3. How to Run Migrations

The migration runner script is [`db/migrate.py`](file:///Users/mandeepsmac/Documents/My%20Projects/invst_project_plan/invst/db/migrate.py).

### Apply Pending Migrations
Run from the `invst/` project root:

```bash
python db/migrate.py
```

### Check Migration Status
Check applied and pending migrations without executing changes:

```bash
python db/migrate.py --status
```

### Custom Database Path
To target a custom or test database:

```bash
python db/migrate.py --db-path /path/to/custom.db
# or relative path:
python db/migrate.py --db-path db/test.db
```

### Verbose Mode
To view details including skipped migrations:

```bash
python db/migrate.py -v
```

### Transaction & Rollback Guarantees
Each migration is executed within an atomic transaction. If any SQL statement fails:
1. The transaction is rolled back immediately.
2. The `schema_version` table is not updated for that version.
3. The runner halts and outputs the error.

---

## 4. How to Add New Migrations

1. Create a new `.sql` file in `db/migrations/` following the zero-padded 4-digit convention:
   ```
   db/migrations/0002_add_macro_features.sql
   db/migrations/0003_add_trade_execution_logs.sql
   ```
2. Write standard SQLite DDL/DML statements.
   - If setting SQLite PRAGMAs (e.g., `PRAGMA journal_mode = WAL;`), place them at the top of the file.
   - Use `IF NOT EXISTS` where applicable.
3. You do **not** need to manually add `INSERT INTO schema_version ...` in future migrations; `migrate.py` automatically registers the version and filename upon successful execution.
4. Run `python db/migrate.py` to apply and test the new migration.

---

## 5. Seed Data (`db/seed/`)

- [`db/seed/sectors_map.csv`](file:///Users/mandeepsmac/Documents/My%20Projects/invst_project_plan/invst/db/seed/sectors_map.csv): Maps 17 standardized NSE sector codes to human-readable display names (e.g. `financial_services` &rarr; `Financial Services`). Matches the sector definitions in [`config/sectors.yaml`](file:///Users/mandeepsmac/Documents/My%20Projects/invst_project_plan/invst/config/sectors.yaml).
- Used during ingestion and screener initialization to apply sector caps (max 40% sector allocation, max 35% in top-50 shortlist) and normalize within-sector valuation z-scores.
