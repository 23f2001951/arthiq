"""Script to execute full quarterly recommendation cycle."""

import sqlite3
from datetime import date

from invst.config import get_config
from invst.data_access import PointInTimeDataAccess
from invst.optimization.mean_variance import estimate_returns_and_covariance, optimize_portfolio
from invst.reporting.report import generate_report_files
from invst.scoring.composite import compute_composite_scores, select_shortlist_with_sector_caps


def main():
    cfg = get_config()
    conn = sqlite3.connect(str(cfg.database.path))
    asof = date.today()

    print(f"Executing Quarterly Cycle for {asof.isoformat()}...")
    pit = PointInTimeDataAccess(conn, asof=asof)
    scorecards = compute_composite_scores(pit, filter_universe_first=True)

    if not scorecards:
        print("No candidates available.")
        conn.close()
        return

    shortlist = select_shortlist_with_sector_caps(scorecards, shortlist_size=15)
    shortlist_syms = [s.symbol for s in shortlist]
    sector_map = {s.symbol: s.sector for s in shortlist}

    mu, sigma, opt_syms = estimate_returns_and_covariance(pit, shortlist_syms)
    res = optimize_portfolio(opt_syms, sector_map, mu, sigma, target_holdings=8)

    holdings_data = [
        {
            "symbol": s,
            "sector": sector_map.get(s, "general"),
            "action": "BUY",
            "target_weight": res.weights.get(s, 0.0),
            "current_weight": 0.0,
            "scorecard": {
                "composite_score": next((sc.composite_score for sc in shortlist if sc.symbol == s), 50.0),
                "quality_score": next((sc.quality_score for sc in shortlist if sc.symbol == s), 50.0),
                "valuation_score": next((sc.valuation_score for sc in shortlist if sc.symbol == s), 50.0),
                "risk_score": next((sc.risk_score for sc in shortlist if sc.symbol == s), 50.0),
                "sentiment_overlay_points": next((sc.sentiment_overlay_points for sc in shortlist if sc.symbol == s), 0.0),
            },
        }
        for s in res.weights if res.weights[s] > 0
    ]

    out_files = generate_report_files(asof_date=asof, holdings_data=holdings_data)
    print(f"Quarterly recommendations report generated: {out_files.get('html')}")
    conn.close()

if __name__ == "__main__":
    main()
