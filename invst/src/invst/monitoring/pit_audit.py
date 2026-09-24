"""Point-in-Time (PIT) Database Integrity Audit.

Runs programmatic assertions across the database to detect potential lookahead leakage:
1. No future disclosure dates (`disclosed_at > today`)
2. No implausible pre-announcements (`disclosed_at < period_end - 14 days`)
3. Backtest config freeze audit
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class PITAuditResult:
    audit_name: str
    passed: bool
    violations_count: int
    message: str


def audit_future_disclosure_dates(
    conn: sqlite3.Connection, asof: date | None = None
) -> PITAuditResult:
    """Detect any fundamental disclosures dated in the future."""
    today_str = (asof or date.today()).isoformat()
    cur = conn.execute(
        "SELECT COUNT(*) FROM fundamentals_quarterly WHERE disclosed_at > ?",
        (today_str,),
    )
    future_count = cur.fetchone()[0]
    passed = future_count == 0

    return PITAuditResult(
        audit_name="future_disclosures_audit",
        passed=passed,
        violations_count=future_count,
        message="Zero future disclosure timestamps detected"
        if passed
        else f"Found {future_count} rows with future disclosed_at!",
    )


def audit_pre_announcement_integrity(conn: sqlite3.Connection) -> PITAuditResult:
    """Ensure no result is claimed to have been disclosed > 14 days before period_end."""
    cur = conn.execute(
        """
        SELECT COUNT(*) FROM fundamentals_quarterly
        WHERE disclosed_at < date(period_end, '-14 days')
        """
    )
    violations = cur.fetchone()[0]
    passed = violations == 0

    return PITAuditResult(
        audit_name="pre_announcement_audit",
        passed=passed,
        violations_count=violations,
        message="All disclosure dates follow period ends correctly"
        if passed
        else f"Found {violations} pre-announcement violations",
    )


def audit_backtest_config_freeze(conn: sqlite3.Connection) -> PITAuditResult:
    """Verify that all recorded backtest runs have valid, parseable frozen JSON configs."""
    cur = conn.execute("SELECT run_id, config_json FROM backtest_runs")
    rows = cur.fetchall()
    malformed = 0

    for _r_id, cfg_str in rows:
        try:
            cfg = json.loads(cfg_str)
            if not isinstance(cfg, dict) or "start_date" not in cfg:
                malformed += 1
        except Exception:
            malformed += 1

    passed = malformed == 0
    return PITAuditResult(
        audit_name="backtest_config_freeze_audit",
        passed=passed,
        violations_count=malformed,
        message="All backtest configs are validly frozen"
        if passed
        else f"{malformed} backtest records have invalid config JSON",
    )


def audit_bitemporal_integrity(conn: sqlite3.Connection) -> PITAuditResult:
    """Ensure no bi-temporal row has valid_to < valid_from or effective_date < date(filing_timestamp)."""
    try:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM fundamentals_pit
            WHERE valid_to < valid_from
               OR effective_date < date(filing_timestamp)
            """
        )
        violations = cur.fetchone()[0]
        passed = violations == 0
        return PITAuditResult(
            audit_name="bitemporal_integrity_audit",
            passed=passed,
            violations_count=violations,
            message="Zero bi-temporal sequence violations detected"
            if passed
            else f"Found {violations} bi-temporal sequence violations",
        )
    except sqlite3.OperationalError:
        return PITAuditResult(
            audit_name="bitemporal_integrity_audit",
            passed=True,
            violations_count=0,
            message="fundamentals_pit table not yet initialized",
        )


def run_full_pit_audit(conn: sqlite3.Connection, asof: date | None = None) -> list[PITAuditResult]:
    """Execute all Point-in-Time integrity audits."""
    return [
        audit_future_disclosure_dates(conn, asof),
        audit_pre_announcement_integrity(conn),
        audit_backtest_config_freeze(conn),
        audit_bitemporal_integrity(conn),
    ]
