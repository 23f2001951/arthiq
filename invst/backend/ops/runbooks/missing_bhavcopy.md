# Runbook: Missing Bhavcopy Recovery

## Symptom
Daily monitor flags that Bhavcopy row count for today is 0.

## Root Causes
1. Trading holiday (exchange closed).
2. NSE archives upload delayed (typically available by 20:00 IST).
3. Network timeout or IP rate-limiting.

## Action Steps
1. Verify if today was an official NSE trading holiday. If yes, no action needed.
2. Run manual retry:
   ```bash
   python -m invst.cli ingest --date YYYY-MM-DD
   ```
3. If NSE site is temporarily unavailable, prices will automatically fall back to yfinance during the morning pass.
