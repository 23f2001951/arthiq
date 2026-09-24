# Point-in-Time (PIT) Data Integrity

## The Problem: Look-Ahead Bias
Backtests that use today's restated fundamentals to make trading decisions in 2017 are fundamentally invalid. In reality, investors only had access to filings that were disclosed on or before the rebalance date.

## How `invst` Enforces PIT Integrity
1. **Timestamp Keying:** Every row in `fundamentals_quarterly` carries `disclosed_at` (the date the filing became publicly available).
2. **PointInTimeDataAccess Class:** The only blessed gateway to query fundamentals and prices for scoring and backtesting:
   ```sql
   SELECT value FROM fundamentals_quarterly
   WHERE symbol = ? AND metric = ? AND disclosed_at <= ?
   ORDER BY disclosed_at DESC, period_end DESC LIMIT 1;
   ```
3. **Historical Constituents:** Nifty 500 membership is resolved using point-in-time snapshots in `index_constituents_history`.
4. **Automated Audits:** Weekly audits verify that no `disclosed_at` timestamp is in the future or precedes the period end by > 14 days.
