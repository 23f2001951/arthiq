# invst — Configuration Directory

This directory houses the declarative YAML configuration files governing all aspects of the **invst** investment decision-support platform. The design guarantees determinism, point-in-time reproducibility, and auditability across backtesting and live execution runs.

---

## Configuration Files

### 1. `settings.yaml`
Central operational configuration file. Contains global parameters across the investment pipeline:

- **`project`**: Project metadata (`name`, semantic `version`).
- **`database`**: SQLite database path (`db/invst.db`) and WAL mode flag (`wal_mode: true`) for concurrent reads and safe writes.
- **`data`**: Directory structure for data pipelines (`data/raw`, `data/interim`, `data/processed`).
- **`universe`**: Target index (`nifty_500`) and benchmark index (`nifty_500_tri`).
- **`rebalance`**: Rebalance cadence (`quarterly`) and scheduled calendar months (`[3, 6, 9, 12]`).
- **`constraints`**: Portfolio construction limits:
  - `max_single_stock_weight`: 0.25 (25% maximum allocation per asset)
  - `max_sector_weight`: 0.40 (40% maximum allocation per sector)
  - `max_holdings`: 8 (target concentrated portfolio size)
  - `top_n_composite`: 50 (first-stage composite score funnel)
  - `sector_cap_in_top50`: 0.35 (sector concentration cap in top 50)
  - `top_n_shortlist`: 15 (candidate universe passed to optimizer)
- **`screening`**: Stage 0 universe qualification criteria:
  - `min_liquidity_cr`: ₹5.0 crore 30-day median traded value
  - `min_market_cap_cr`: ₹1,000.0 crore point-in-time market capitalization
  - `min_listing_years`: 3 years of trading history
  - `max_promoter_holding_pct`: 75.0% promoter holding cap
  - `min_quarters_available`: 10 of last 12 quarterly fundamental statements
  - `min_price`: ₹10.0 (penny stock filter)
- **`backtest`**: Historical simulation settings:
  - Date window: `2016-01-01` to `2026-09-30`
  - Execution model: `next_day_open`
  - Transaction costs: `buy_cost_bps: 30`, `sell_cost_bps: 20`, `slippage_bps: 5`
- **`ml`**: Machine learning and sentiment thresholds:
  - `classifier_threshold`: 0.55
  - `walk_forward_train_years`: 5
  - `sentiment_cap_points`: 10
- **`risk_free_rate`**: Sovereign risk-free rate configuration (`rbi_364d_tbill` with `0.065` / 6.5% fallback).
- **`logging`**: Application logging level, format, and destination log file (`logs/invst.log`).

---

### 2. `scoring_weights.yaml`
Specifies quantitative scoring weights across the four-stage framework defined in `PROJECT_PLAN.md` §2:

- **Stage 1: Quality (`quality`)** — Weights sum to `1.0`:
  - `roe_5yr_avg` (0.25): 5-year average Return on Equity
  - `roce_5yr_avg` (0.25): 5-year average Return on Capital Employed
  - `debt_equity` (0.15): Debt-to-Equity ratio (lower is better)
  - `interest_coverage` (0.10): EBIT / Interest expense
  - `earnings_cagr_5yr` (0.15): 5-year earnings compound annual growth rate
  - `ocf_to_net_profit` (0.10): Operating Cash Flow / Net Profit ratio (accruals check)
- **Stage 2: Valuation (`valuation`)** — Weights sum to `1.0`:
  - `pe_ttm` (0.30): Trailing 12-month Price-to-Earnings vs. sector history
  - `pb` (0.20): Price-to-Book vs. sector history
  - `ev_ebitda` (0.30): Enterprise Value to EBITDA
  - `dividend_yield` (0.10): Dividend yield
  - `peg` (0.10): Price/Earnings to Growth ratio
- **Stage 3: Risk (`risk`)** — Weights sum to `1.0` (subtractive penalty score):
  - `annualised_vol_252d` (0.25): 252-day annualised price volatility
  - `beta_nifty500_2yr` (0.20): 2-year beta against Nifty 500
  - `max_drawdown_3yr` (0.25): 3-year rolling maximum drawdown
  - `downside_deviation_1yr` (0.15): 1-year downside risk
  - `altman_z_score` (0.15): Financial distress probability
- **Stage 4: Sentiment Overlay (`sentiment_overlay`)** — Additive point caps (max ±10 points):
  - `price_momentum_6_12_1`: max 5 points
  - `news_sentiment_90d`: max 5 points
  - `insider_promoter_trend`: max 3 points
  - `total_cap`: 10 points
- **Composite Weights (`composite`)** — Contribution of each stage to final composite score (sums to `1.0`):
  - `quality`: 0.35
  - `valuation`: 0.30
  - `risk`: 0.20
  - `sentiment_overlay`: 0.15

---

### 3. `sectors.yaml`
Standard National Stock Exchange (NSE) sector and industry classification for Nifty 500 constituents.

Maps canonical sector keys (e.g., `financial_services`, `information_technology`, `capital_goods`, `healthcare`, `fast_moving_consumer_goods`) to their human-readable `display_name` and detailed `sub_sectors` list. This taxonomy is used for:
- Intra-sector z-scoring of fundamentals and valuation multiples.
- Enforcing sector allocation caps during ranking (35% in Top 50) and optimization (40% in portfolio).

---

## Loading and Usage

Configurations are loaded programmatically by the configuration module (`src/invst/config.py`).

### Example Python Loading Pattern

```python
import yaml
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

def load_yaml(filename: str) -> Dict[str, Any]:
    file_path = CONFIG_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Load individual configs
settings = load_yaml("settings.yaml")
scoring_weights = load_yaml("scoring_weights.yaml")
sectors = load_yaml("sectors.yaml")
```

### Weight Validation Rule
When parsing `scoring_weights.yaml`, loader implementations should assert that weights in each normalized group sum to `1.0` within floating point tolerance:

$$\sum w_{\text{quality}} = 1.0, \quad \sum w_{\text{valuation}} = 1.0, \quad \sum w_{\text{risk}} = 1.0, \quad \sum w_{\text{composite}} = 1.0$$

### Config Freezing for Reproducibility
For backtest and production rebalance execution:
- Every backtest execution serializes the active configuration into `backtest_runs.config_json` in the SQLite database.
- Any rerun using that frozen JSON reproduces identical scores, ranks, and portfolio weights.
