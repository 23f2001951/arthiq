"""Tests for Reporting engine and CLI commands."""

import sqlite3
from pathlib import Path

from invst.cli import build_parser, cmd_monitor
from invst.reporting.rationale import generate_plain_english_rationale
from invst.reporting.report import generate_report_files, render_report_html


def test_generate_plain_english_rationale():
    scorecard = {
        "quality_details": {
            "metrics": {
                "roe_5yr_avg": 22.5,
                "roce_5yr_avg": 26.0,
                "debt_equity": 0.25,
                "interest_coverage": 12.0,
                "earnings_cagr_5yr": 16.5,
            }
        },
        "valuation_details": {
            "metrics": {
                "pe_ttm": 24.5,
                "pb": 4.2,
                "ev_ebitda": 15.0,
            }
        },
        "risk_details": {
            "metrics": {
                "annualised_vol_252d": 0.22,
                "beta_nifty500_2yr": 0.95,
                "max_drawdown_3yr": -0.18,
            }
        },
        "sentiment_details": {
            "momentum_return": 0.18,
            "sentiment_score": 0.45,
        },
    }

    rationale = generate_plain_english_rationale(
        symbol="TCS",
        company_name="Tata Consultancy Services",
        sector="information_technology",
        action="BUY",
        target_weight=0.15,
        current_weight=0.0,
        scorecard=scorecard,
    )

    assert "TCS" in rationale
    assert "Tata Consultancy Services" in rationale
    assert "ROE of 22.5%" in rationale
    assert "P/E is trading at 24.5x" in rationale
    assert "momentum" in rationale.lower()


def test_render_report_html():
    holdings = [
        {
            "symbol": "RELIANCE",
            "sector": "oil_gas",
            "action": "BUY",
            "target_weight": 0.20,
            "scorecard": {
                "composite_score": 85.0,
                "quality_score": 82.0,
                "valuation_score": 80.0,
                "risk_score": 75.0,
                "sentiment_overlay_points": 4.5,
            },
        }
    ]

    html = render_report_html(asof_date="2024-03-31", holdings_data=holdings)
    assert "<!DOCTYPE html>" in html
    assert "RELIANCE" in html
    assert "85.0 / 100" in html
    assert "Why we like it:" in html


def test_generate_report_files(tmp_path: Path):
    holdings = [
        {
            "symbol": "INFY",
            "sector": "tech",
            "action": "BUY",
            "target_weight": 0.125,
            "scorecard": {
                "composite_score": 78.0,
                "quality_score": 80.0,
                "valuation_score": 75.0,
                "risk_score": 82.0,
                "sentiment_overlay_points": 2.0,
            },
        }
    ]
    files = generate_report_files(
        asof_date="2024-03-31",
        holdings_data=holdings,
        output_dir=tmp_path,
        generate_pdf=False,  # Skip PDF dependency in test
    )
    assert "html" in files
    assert files["html"].is_file()
    assert files["html"].read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_cli_parser():
    parser = build_parser()
    args = parser.parse_args(["score", "--asof", "2024-03-31"])
    assert args.command == "score"
    assert args.asof == "2024-03-31"

    bt_args = parser.parse_args(["backtest", "--start", "2020-01-01", "--end", "2024-03-31"])
    assert bt_args.command == "backtest"
    assert bt_args.start == "2020-01-01"


def test_cli_monitor_cmd(scoring_db: sqlite3.Connection, tmp_path: Path):
    parser = build_parser()
    db_file = tmp_path / "test.db"
    # Dump test DB to file for CLI
    disk_conn = sqlite3.connect(str(db_file))
    scoring_db.backup(disk_conn)
    disk_conn.close()

    args = parser.parse_args(["monitor", "--db", str(db_file)])
    ret = cmd_monitor(args)
    assert ret == 0
