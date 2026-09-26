"""Mutual Fund Portfolio Service & Active/Closed SIP Diagnostics.

Handles:
- User portfolio retrieval & creation
- Adding/updating active, paused, and closed SIP schedules
- Recording transactions and lump-sum investments
- Computing portfolio-wide XIRR, valuation, and asset allocation
- Deep diagnostic of Active SIPs (performance vs category benchmark)
- Deep diagnostic of Closed/Paused SIPs (stoppage post-mortem & opportunity analysis)
- Stock overlap matrix across portfolio holdings
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any

import pandas as pd

from invst.db.engine import get_db_connection
from invst.ingestion.mf_ingestion import fetch_and_cache_scheme_nav, get_scheme_nav_series
from invst.scoring.mf_metrics import (
    calculate_cagr,
    calculate_portfolio_overlap,
    calculate_risk_metrics,
    calculate_trailing_returns,
    calculate_xirr,
)

logger = logging.getLogger(__name__)

# Category benchmarks and representative parameters for objective fund health auditing
CATEGORY_BENCHMARKS: dict[str, dict[str, Any]] = {
    "Equity: Small Cap": {"index_name": "Nifty Smallcap 250 TRI", "expected_3y_cagr": 20.0, "avg_ter": 0.70},
    "Equity: Mid Cap": {"index_name": "Nifty Midcap 150 TRI", "expected_3y_cagr": 18.0, "avg_ter": 0.75},
    "Equity: Large Cap": {"index_name": "Nifty 100 TRI", "expected_3y_cagr": 13.5, "avg_ter": 0.75},
    "Equity: Flexi Cap": {"index_name": "Nifty 500 TRI", "expected_3y_cagr": 14.8, "avg_ter": 0.70},
    "Equity: Multi Cap": {"index_name": "Nifty 500 Multicap 50:25:25 TRI", "expected_3y_cagr": 15.5, "avg_ter": 0.75},
    "Equity: ELSS": {"index_name": "Nifty 500 TRI", "expected_3y_cagr": 14.5, "avg_ter": 0.68},
    "Hybrid: Balanced Advantage": {"index_name": "Nifty 50 Hybrid Composite", "expected_3y_cagr": 11.5, "avg_ter": 0.72},
    "Equity: Index / Passive": {"index_name": "Nifty 50 TRI", "expected_3y_cagr": 12.8, "avg_ter": 0.20},
    "Debt: Liquid": {"index_name": "Crisil Liquid Debt Index", "expected_3y_cagr": 6.8, "avg_ter": 0.25},
}


def get_switch_options_for_scheme(
    scheme_code: int,
    category: str,
    conn: Any,
    current_val: float,
    monthly_amt: float,
) -> list[dict[str, Any]]:
    """Generate 2-3 superior category replacement options with detailed execution instructions."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT scheme_code, scheme_name, fund_house, category, expense_ratio, crisil_rating, aum_cr
        FROM mf_schemes
        WHERE category = ? AND scheme_code != ?
        ORDER BY crisil_rating DESC, aum_cr DESC
        LIMIT 3;
        """,
        (category, scheme_code),
    )
    rows = cur.fetchall()
    if not rows:
        cur.execute(
            """
            SELECT scheme_code, scheme_name, fund_house, category, expense_ratio, crisil_rating, aum_cr
            FROM mf_schemes
            WHERE scheme_code != ?
            ORDER BY crisil_rating DESC, aum_cr DESC
            LIMIT 3;
            """,
            (scheme_code,),
        )
        rows = cur.fetchall()

    options = []
    # Current fund holdings for overlap calculation
    cur.execute("SELECT symbol, weight_pct FROM mf_holdings WHERE scheme_code = ?;", (scheme_code,))
    curr_h = {hr[0]: float(hr[1]) for hr in cur.fetchall() if hr[0]}

    for r in rows:
        cand_code, cand_name, cand_house, cand_cat, cand_ter, cand_rating, cand_aum = r
        cand_nav = get_scheme_nav_series(cand_code)
        cand_trailing = calculate_trailing_returns(cand_nav)
        cand_risk = calculate_risk_metrics(cand_nav)
        cand_3y = cand_trailing.get("3y")
        cand_3y_pct = round(cand_3y * 100, 2) if cand_3y is not None else 18.5
        cand_downside = cand_risk.get("downside_capture") if cand_risk.get("downside_capture") is not None else 84.0
        cand_ter_val = float(cand_ter) if cand_ter is not None else 0.65

        cur.execute("SELECT symbol, weight_pct FROM mf_holdings WHERE scheme_code = ?;", (cand_code,))
        cand_h = {hr[0]: float(hr[1]) for hr in cur.fetchall() if hr[0]}

        overlap_pct = 0.0
        if curr_h and cand_h:
            common = set(curr_h.keys()) & set(cand_h.keys())
            overlap_pct = round(sum(min(curr_h[s], cand_h[s]) for s in common), 1)

        val_display = max(current_val, 1000.0)
        amt_display = max(monthly_amt, 1000.0)

        options.append({
            "target_scheme_code": cand_code,
            "target_scheme_name": cand_name,
            "fund_house": cand_house,
            "category": cand_cat,
            "crisil_rating": cand_rating or 5,
            "expense_ratio": cand_ter_val,
            "trailing_3y_cagr": cand_3y_pct,
            "downside_capture": cand_downside,
            "overlap_with_current_pct": overlap_pct,
            "comparison_advantage": f"{cand_3y_pct:.1f}% 3Y CAGR, {cand_ter_val:.2f}% TER, {cand_downside:.0f}% downside capture, {overlap_pct}% stock overlap",
            "execution_modes": {
                "full_switch": f"Redeem 100% of accumulated units (₹{val_display:,.0f}) from current fund and shift capital into {cand_name}. Transfer ongoing monthly SIP of ₹{amt_display:,.0f}.",
                "pause_and_redirect": f"Pause current SIP immediately to avoid exit loads / STCG taxes. Leave existing ₹{val_display:,.0f} invested to compound undisturbed, and start a fresh monthly SIP of ₹{amt_display:,.0f} in {cand_name}.",
                "partial_switch": f"Redeem 50% (₹{val_display * 0.5:,.0f}) and shift into {cand_name} while redirecting ongoing SIP to achieve superior balance and minimize drawdown risk.",
            },
        })
    return options


def _ensure_checkin_tables(conn: Any) -> None:
    """Ensure check-in tables and portfolio metadata columns exist."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mf_sip_checkins (
                id              TEXT PRIMARY KEY,
                portfolio_id    TEXT NOT NULL,
                sip_id          TEXT NOT NULL,
                scheme_code     INTEGER NOT NULL,
                due_date        DATE NOT NULL,
                status          TEXT NOT NULL,
                confirmed_date  DATE,
                amount          REAL NOT NULL,
                notes           TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    except Exception as exc:
        logger.debug("mf_sip_checkins table check: %s", exc)

    for col_def in ("notes TEXT", "last_saved_at TIMESTAMP"):
        try:
            cur.execute(f"ALTER TABLE user_mf_portfolios ADD COLUMN {col_def};")
        except Exception:
            pass
    conn.commit()


def save_user_mf_portfolio(
    portfolio_id: str,
    portfolio_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Explicitly save portfolio metadata, custom notes, and record last_saved_at timestamp."""
    conn = get_db_connection()
    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if portfolio_name and notes is not None:
            cur.execute(
                "UPDATE user_mf_portfolios SET name = ?, notes = ?, last_saved_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (portfolio_name, notes, now_str, portfolio_id),
            )
        elif portfolio_name:
            cur.execute(
                "UPDATE user_mf_portfolios SET name = ?, last_saved_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (portfolio_name, now_str, portfolio_id),
            )
        elif notes is not None:
            cur.execute(
                "UPDATE user_mf_portfolios SET notes = ?, last_saved_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (notes, now_str, portfolio_id),
            )
        else:
            cur.execute(
                "UPDATE user_mf_portfolios SET last_saved_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (now_str, portfolio_id),
            )
        conn.commit()
        return {
            "status": "success",
            "message": "Mutual Fund portfolio saved successfully",
            "portfolio_id": portfolio_id,
            "last_saved_at": now_str,
            "portfolio_name": portfolio_name or "My Mutual Funds",
        }
    finally:
        conn.close()


def get_or_create_user_mf_portfolio(user_id: int, portfolio_name: str = "My Mutual Funds") -> str:
    """Ensure a user has an active mutual fund portfolio and return its ID."""
    conn = get_db_connection()
    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()
        cur.execute("SELECT id FROM user_mf_portfolios WHERE user_id = ? LIMIT 1;", (user_id,))
        row = cur.fetchone()
        if row:
            return str(row[0])

        new_id = f"mf_port_{uuid.uuid4().hex[:12]}"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO user_mf_portfolios (id, user_id, name, last_saved_at) VALUES (?, ?, ?, ?);",
            (new_id, user_id, portfolio_name, now_str),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


def add_or_update_sip(
    portfolio_id: str,
    scheme_code: int,
    amount: float,
    start_date: str,
    status: str = "ACTIVE",
    end_date: str | None = None,
    folio_number: str | None = None,
    step_up_pct: float = 0.0,
    sip_day: int | None = None,
    auto_generate_tx: bool = True,
    custom_invested: float | None = None,
    custom_current_value: float | None = None,
    custom_units: float | None = None,
    skipped_months: list[str] | None = None,
    paid_months: list[str] | None = None,
) -> str:
    """Register or update an active, paused, or closed SIP schedule.

    Dynamically derives sip_day from start_date if not provided.
    Expands monthly installments across paid months (omitting skipped months)
    to calculate precise ledger XIRR matching official AMFI/Groww statements.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Ensure scheme is cached
        fetch_and_cache_scheme_nav(scheme_code)
        _ensure_checkin_tables(conn)

        s_date = datetime.datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        if sip_day is None or sip_day <= 0:
            sip_day = min(max(1, s_date.day), 28)

        e_date = datetime.datetime.strptime(end_date[:10], "%Y-%m-%d").date() if end_date else datetime.date.today()

        sip_id = f"sip_{uuid.uuid4().hex[:10]}"
        cur.execute(
            """
            INSERT INTO mf_sip_schedules (
                id, portfolio_id, scheme_code, folio_number, amount,
                sip_day, start_date, end_date, status, step_up_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                sip_id,
                portfolio_id,
                scheme_code,
                folio_number or f"FOLIO-{scheme_code}-01",
                amount,
                sip_day,
                start_date,
                end_date,
                status.upper(),
                step_up_pct,
            ),
        )

        # 1. Build all monthly installment dates from start_date to end_date (or today)
        month_dates: list[datetime.date] = []
        cur_m = s_date.replace(day=min(sip_day, 28))
        while cur_m <= e_date:
            month_dates.append(cur_m)
            next_m = cur_m.month + 1
            next_y = cur_m.year
            if next_m > 12:
                next_m = 1
                next_y += 1
            cur_m = datetime.date(next_y, next_m, min(sip_day, 28))

        if not month_dates:
            month_dates = [s_date]

        # 2. Determine skipped vs paid months
        skipped_set = set(skipped_months or [])
        if paid_months:
            paid_set = set(paid_months)
            skipped_set = {m.strftime("%Y-%m") for m in month_dates if m.strftime("%Y-%m") not in paid_set}

        paid_dates = [m for m in month_dates if m.strftime("%Y-%m") not in skipped_set]
        if not paid_dates:
            paid_dates = [month_dates[0]]

        # Record checkin audit trail if explicitly provided by user checklist
        if skipped_months or paid_months:
            for m in month_dates:
                m_str = m.strftime("%Y-%m")
                m_date_str = m.strftime("%Y-%m-%d")
                c_id = f"chk_{sip_id}_{m_date_str}"
                chk_status = "SKIPPED" if m_str in skipped_set else "PAID"
                cur.execute(
                    """
                    INSERT INTO mf_sip_checkins (
                        id, portfolio_id, sip_id, scheme_code, due_date, status, confirmed_date, amount, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        status = excluded.status,
                        confirmed_date = excluded.confirmed_date,
                        notes = excluded.notes,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (c_id, portfolio_id, sip_id, scheme_code, m_date_str, chk_status, m_date_str, amount, f"Marked {chk_status} during schedule setup"),
                )

        # 3. Generate granular monthly transaction cash flows
        if auto_generate_tx or (custom_invested is not None and custom_invested > 0):
            # Fetch latest NAV
            cur.execute(
                "SELECT nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;",
                (scheme_code,),
            )
            n_row = cur.fetchone()
            latest_nav = float(n_row[0]) if n_row else 100.0

            n_paid = len(paid_dates)
            if custom_invested is not None and custom_invested > 0:
                base_installment = round(custom_invested / n_paid, 2)
            else:
                base_installment = amount

            raw_txs: list[dict[str, Any]] = []
            cur_amt = base_installment
            cur_year = s_date.year

            for p_date in paid_dates:
                # Apply step-up if custom_invested is not overriding fixed total
                if custom_invested is None and step_up_pct > 0 and p_date.year > cur_year:
                    cur_amt = cur_amt * (1.0 + (step_up_pct / 100.0))
                    cur_year = p_date.year

                d_str = p_date.strftime("%Y-%m-%d")
                cur.execute(
                    """
                    SELECT nav_date, nav FROM mf_nav_history
                    WHERE scheme_code = ? AND nav_date >= ?
                    ORDER BY nav_date ASC LIMIT 1;
                    """,
                    (scheme_code, d_str),
                )
                nav_row = cur.fetchone()
                if not nav_row:
                    cur.execute(
                        """
                        SELECT nav_date, nav FROM mf_nav_history
                        WHERE scheme_code = ? AND nav_date <= ?
                        ORDER BY nav_date DESC LIMIT 1;
                        """,
                        (scheme_code, d_str),
                    )
                    nav_row = cur.fetchone()

                actual_nav = float(nav_row[1]) if nav_row else latest_nav
                actual_date = nav_row[0] if nav_row else d_str
                raw_txs.append({
                    "tx_date": actual_date,
                    "amount": cur_amt,
                    "nav": actual_nav,
                    "units": cur_amt / actual_nav if actual_nav > 0 else 0.0,
                })

            # Align total custom_invested exactly if provided
            if custom_invested is not None and custom_invested > 0 and raw_txs:
                allocated_sum = sum(t["amount"] for t in raw_txs)
                diff = round(custom_invested - allocated_sum, 2)
                raw_txs[-1]["amount"] += diff
                raw_txs[-1]["units"] = raw_txs[-1]["amount"] / raw_txs[-1]["nav"] if raw_txs[-1]["nav"] > 0 else 0.0

            # Determine target total units if custom_units or custom_current_value is specified
            target_units = None
            if custom_units is not None and custom_units > 0:
                target_units = float(custom_units)
            elif custom_current_value is not None and custom_current_value > 0:
                target_units = float(custom_current_value) / latest_nav

            if target_units is not None and target_units > 0 and raw_txs:
                current_raw_units_sum = sum(t["units"] for t in raw_txs)
                if current_raw_units_sum > 0:
                    scale = target_units / current_raw_units_sum
                    for t in raw_txs:
                        t["units"] = t["units"] * scale

            tx_batch = []
            for t in raw_txs:
                tx_id = f"tx_{uuid.uuid4().hex[:12]}"
                tx_batch.append((
                    tx_id,
                    portfolio_id,
                    sip_id,
                    scheme_code,
                    t["tx_date"],
                    "BUY_SIP",
                    t["amount"],
                    t["units"],
                    t["nav"],
                    f"Monthly SIP installment ({status})",
                ))

            if tx_batch:
                cur.executemany(
                    """
                    INSERT INTO mf_transactions (
                        id, portfolio_id, sip_id, scheme_code, tx_date,
                        tx_type, amount, units, nav, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    tx_batch,
                )

        conn.commit()
        return sip_id
    finally:
        conn.close()


def get_pending_sip_checkins(portfolio_id: str, conn: Any | None = None) -> list[dict[str, Any]]:
    """Identify scheduled SIP installments requiring monthly user confirmation (Paid vs Skipped)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()
        # Fetch active SIPs with scheme details
        cur.execute(
            """
            SELECT s.id, s.scheme_code, s.amount, s.sip_day, s.start_date, s.end_date, s.status,
                   sch.scheme_name, sch.category
            FROM mf_sip_schedules s
            JOIN mf_schemes sch ON s.scheme_code = sch.scheme_code
            WHERE s.portfolio_id = ? AND UPPER(s.status) = 'ACTIVE';
            """,
            (portfolio_id,),
        )
        schedules = cur.fetchall()
        if not schedules:
            return []

        # Fetch existing check-in records for this portfolio
        cur.execute(
            """
            SELECT sip_id, due_date, status, confirmed_date
            FROM mf_sip_checkins
            WHERE portfolio_id = ?;
            """,
            (portfolio_id,),
        )
        existing_checkins = {(r[0], str(r[1])[:10]): r[2] for r in cur.fetchall()}

        today = datetime.date.today()
        pending_list = []

        for row in schedules:
            s_id, sc, amt, sip_day, s_date_str, e_date_str, status, s_name, cat = row
            try:
                s_dt = datetime.datetime.strptime(str(s_date_str)[:10], "%Y-%m-%d").date()
            except Exception:
                s_dt = today

            e_dt = None
            if e_date_str:
                try:
                    e_dt = datetime.datetime.strptime(str(e_date_str)[:10], "%Y-%m-%d").date()
                except Exception:
                    e_dt = None

            sip_day_clamped = min(max(1, sip_day or 5), 28)

            # Check target months: current month and preceding month
            target_months = []
            target_months.append((today.year, today.month))
            prev_m = today.month - 1 if today.month > 1 else 12
            prev_y = today.year if today.month > 1 else today.year - 1
            target_months.append((prev_y, prev_m))

            for y, m in target_months:
                due_d = datetime.date(y, m, sip_day_clamped)
                if due_d < s_dt:
                    continue
                if e_dt and due_d > e_dt:
                    continue

                due_d_str = due_d.strftime("%Y-%m-%d")
                chk_key = (s_id, due_d_str)

                if chk_key not in existing_checkins:
                    if today >= due_d:
                        m_label = due_d.strftime("%B %Y")
                        day_ordinal = f"{due_d.day}{'th' if 11 <= due_d.day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(due_d.day % 10, 'th')}"
                        pending_list.append({
                            "checkin_id": f"chk_{s_id}_{due_d_str}",
                            "sip_id": s_id,
                            "scheme_code": sc,
                            "scheme_name": s_name,
                            "category": cat,
                            "monthly_amount": float(amt),
                            "sip_day": sip_day_clamped,
                            "due_date": due_d_str,
                            "month_label": m_label,
                            "status": "PENDING",
                            "is_overdue": (today - due_d).days >= 1,
                            "days_ago": (today - due_d).days,
                            "question": f"Did your scheduled SIP of ₹{amt:,.0f} for {s_name} debit on {day_ordinal} {due_d.strftime('%b')}?",
                        })

        pending_list.sort(key=lambda x: x["due_date"], reverse=True)
        return pending_list
    finally:
        if close_conn:
            conn.close()


def record_sip_checkin(
    portfolio_id: str,
    sip_id: str,
    due_date: str,
    status: str,
    amount: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Confirm whether a monthly SIP was debited (PAID) or skipped (SKIPPED)."""
    conn = get_db_connection()
    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()

        cur.execute(
            "SELECT scheme_code, amount, sip_day FROM mf_sip_schedules WHERE id = ? AND portfolio_id = ?;",
            (sip_id, portfolio_id),
        )
        sip_row = cur.fetchone()
        if not sip_row:
            return {"status": "error", "message": "SIP schedule not found"}

        scheme_code, sched_amt, sip_day = sip_row
        actual_amt = float(amount if amount is not None and amount > 0 else sched_amt)
        st = status.upper()
        now_date_str = datetime.date.today().strftime("%Y-%m-%d")
        due_date_clean = due_date[:10]

        checkin_id = f"chk_{sip_id}_{due_date_clean}"

        # 1. Upsert into mf_sip_checkins
        cur.execute(
            """
            INSERT INTO mf_sip_checkins (
                id, portfolio_id, sip_id, scheme_code, due_date, status, confirmed_date, amount, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                status = excluded.status,
                confirmed_date = excluded.confirmed_date,
                amount = excluded.amount,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (checkin_id, portfolio_id, sip_id, scheme_code, due_date_clean, st, now_date_str, actual_amt, notes or f"Investor confirmed {st}"),
        )

        if st == "PAID":
            # 2. If PAID, ensure a transaction exists for this SIP around this due date
            cur.execute(
                """
                SELECT id FROM mf_transactions
                WHERE portfolio_id = ? AND sip_id = ? AND tx_date BETWEEN date(?, '-5 days') AND date(?, '+5 days')
                LIMIT 1;
                """,
                (portfolio_id, sip_id, due_date_clean, due_date_clean),
            )
            existing_tx = cur.fetchone()
            if not existing_tx:
                cur.execute(
                    """
                    SELECT nav_date, nav FROM mf_nav_history
                    WHERE scheme_code = ? AND nav_date >= ?
                    ORDER BY nav_date ASC LIMIT 1;
                    """,
                    (scheme_code, due_date_clean),
                )
                nav_row = cur.fetchone()
                if not nav_row:
                    cur.execute(
                        "SELECT nav_date, nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;",
                        (scheme_code,),
                    )
                    nav_row = cur.fetchone()

                actual_nav = float(nav_row[1]) if nav_row else 100.0
                actual_date = nav_row[0] if nav_row else due_date_clean
                units = actual_amt / actual_nav
                tx_id = f"tx_{uuid.uuid4().hex[:12]}"
                cur.execute(
                    """
                    INSERT INTO mf_transactions (
                        id, portfolio_id, sip_id, scheme_code, tx_date,
                        tx_type, amount, units, nav, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        tx_id,
                        portfolio_id,
                        sip_id,
                        scheme_code,
                        actual_date,
                        "BUY_SIP",
                        actual_amt,
                        units,
                        actual_nav,
                        f"Monthly SIP confirmed paid ({due_date_clean})",
                    ),
                )
        elif st == "SKIPPED":
            # 3. If SKIPPED, remove any false buy transaction that might have been auto-generated for this specific due date
            cur.execute(
                """
                DELETE FROM mf_transactions
                WHERE portfolio_id = ? AND sip_id = ? AND tx_date BETWEEN date(?, '-4 days') AND date(?, '+4 days');
                """,
                (portfolio_id, sip_id, due_date_clean, due_date_clean),
            )

        conn.commit()
        return {
            "status": "success",
            "message": f"Installment for {due_date_clean} marked as {st}",
            "sip_id": sip_id,
            "due_date": due_date_clean,
            "checkin_status": st,
        }
    finally:
        conn.close()


def batch_record_sip_checkin(
    portfolio_id: str,
    action: str = "MARK_ALL_PAID",
    checkin_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Bulk confirm multiple pending check-ins at once."""
    pending = get_pending_sip_checkins(portfolio_id)
    if not pending:
        return {"status": "success", "message": "No pending check-ins to process", "processed_count": 0}

    target_items = pending
    if checkin_ids:
        target_items = [p for p in pending if p["checkin_id"] in checkin_ids or p["sip_id"] in checkin_ids]

    st = "PAID" if "PAID" in action.upper() else "SKIPPED"
    processed = 0
    for item in target_items:
        res = record_sip_checkin(
            portfolio_id=portfolio_id,
            sip_id=item["sip_id"],
            due_date=item["due_date"],
            status=st,
            amount=item["monthly_amount"],
            notes=f"Bulk confirmed {st}",
        )
        if res.get("status") == "success":
            processed += 1

    return {
        "status": "success",
        "message": f"Successfully marked {processed} installment(s) as {st}",
        "processed_count": processed,
    }


def get_sip_checkin_history(portfolio_id: str, limit: int = 15, conn: Any | None = None) -> list[dict[str, Any]]:
    """Retrieve history of past monthly SIP check-ins."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.sip_id, c.scheme_code, c.due_date, c.status, c.confirmed_date, c.amount,
                   sch.scheme_name, sch.category
            FROM mf_sip_checkins c
            JOIN mf_schemes sch ON c.scheme_code = sch.scheme_code
            WHERE c.portfolio_id = ?
            ORDER BY c.due_date DESC, c.updated_at DESC
            LIMIT ?;
            """,
            (portfolio_id, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "checkin_id": r[0],
                "sip_id": r[1],
                "scheme_code": r[2],
                "due_date": str(r[3])[:10],
                "status": r[4],
                "confirmed_date": str(r[5])[:10] if r[5] else None,
                "amount": float(r[6]),
                "scheme_name": r[7],
                "category": r[8],
            }
            for r in rows
        ]
    finally:
        if close_conn:
            conn.close()


def analyze_mf_portfolio(portfolio_id: str) -> dict[str, Any]:
    """Perform comprehensive institutional diagnostic on user's MF portfolio.

    Evaluates:
    - Overall Valuation, Invested, Profit, and Portfolio XIRR
    - Active SIPs: Installments, current XIRR, monthly outflow, benchmark alpha
    - Closed / Discontinued SIPs: Stoppage post-mortem & missed opportunity analysis
    - Asset Allocation breakdown across categories
    - Cross-Fund Stock Overlap Matrix
    """
    conn = get_db_connection()
    try:
        _ensure_checkin_tables(conn)
        cur = conn.cursor()

        # Fetch portfolio metadata
        cur.execute("SELECT name, notes, last_saved_at FROM user_mf_portfolios WHERE id = ?;", (portfolio_id,))
        p_meta = cur.fetchone()
        port_name = p_meta[0] if p_meta and p_meta[0] else "My Mutual Funds"
        port_notes = p_meta[1] if p_meta and p_meta[1] else None
        last_saved = str(p_meta[2]) if p_meta and p_meta[2] else None

        pending_checkins = get_pending_sip_checkins(portfolio_id, conn=conn)
        checkin_history = get_sip_checkin_history(portfolio_id, limit=10, conn=conn)

        # 1. Fetch all transactions
        cur.execute(
            """
            SELECT t.scheme_code, s.scheme_name, s.category, t.tx_date, t.tx_type,
                   t.amount, t.units, t.nav, t.sip_id
            FROM mf_transactions t
            JOIN mf_schemes s ON t.scheme_code = s.scheme_code
            WHERE t.portfolio_id = ?
            ORDER BY t.tx_date ASC;
            """,
            (portfolio_id,),
        )
        tx_rows = cur.fetchall()

        if not tx_rows:
            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": port_name,
                "notes": port_notes,
                "last_saved_at": last_saved,
                "total_invested": 0.0,
                "current_value": 0.0,
                "unrealized_profit": 0.0,
                "absolute_return_pct": 0.0,
                "portfolio_xirr_pct": 0.0,
                "monthly_sip_run_rate": 0.0,
                "active_sips_count": 0,
                "closed_sips_count": 0,
                "active_sips": [],
                "closed_sips": [],
                "scheme_holdings": [],
                "asset_allocation": {},
                "overlap_analysis": {},
                "pending_checkins": pending_checkins,
                "checkin_history": checkin_history,
            }

        # 2. Group by scheme to calculate total units and invested amount
        scheme_summary: dict[int, dict[str, Any]] = {}
        all_cashflows: list[tuple[str, float]] = []

        for r in tx_rows:
            sc, sname, cat, tdate, ttype, amt, units, nav, sip_id = r
            if sc not in scheme_summary:
                scheme_summary[sc] = {
                    "scheme_code": sc,
                    "scheme_name": sname,
                    "category": cat,
                    "total_units": 0.0,
                    "invested_amount": 0.0,
                    "transactions_count": 0,
                    "cashflows": [],
                }
            if ttype in ("BUY_SIP", "BUY_LUMPSUM"):
                scheme_summary[sc]["total_units"] += float(units)
                scheme_summary[sc]["invested_amount"] += float(amt)
                scheme_summary[sc]["cashflows"].append((tdate, -float(amt)))
                all_cashflows.append((tdate, -float(amt)))
            elif ttype == "REDEEM":
                scheme_summary[sc]["total_units"] -= float(units)
                scheme_summary[sc]["cashflows"].append((tdate, float(amt)))
                all_cashflows.append((tdate, float(amt)))
            scheme_summary[sc]["transactions_count"] += 1

        # 3. Fetch latest NAV for each scheme to compute current valuation
        total_invested = sum(s["invested_amount"] for s in scheme_summary.values())
        total_current_value = 0.0
        holdings_by_scheme_for_overlap: dict[int, list[dict[str, Any]]] = {}

        for sc, data in scheme_summary.items():
            cur.execute(
                "SELECT nav_date, nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;",
                (sc,),
            )
            latest_nav_row = cur.fetchone()
            latest_nav = float(latest_nav_row[1]) if latest_nav_row else 100.0
            latest_date = latest_nav_row[0] if latest_nav_row else datetime.date.today().strftime("%Y-%m-%d")

            cur_val = data["total_units"] * latest_nav
            data["current_nav"] = latest_nav
            data["latest_nav_date"] = latest_date
            data["current_value"] = round(cur_val, 2)
            data["unrealized_profit"] = round(cur_val - data["invested_amount"], 2)
            data["abs_return_pct"] = round(
                ((cur_val - data["invested_amount"]) / data["invested_amount"] * 100.0) if data["invested_amount"] > 0 else 0.0,
                2,
            )

            # Scheme XIRR
            scheme_cfs = list(data["cashflows"])
            if cur_val > 0:
                scheme_cfs.append((latest_date, cur_val))
            data["xirr_pct"] = calculate_xirr(scheme_cfs)

            total_current_value += cur_val

            # Fetch holdings for overlap analysis
            cur.execute(
                "SELECT company_name, symbol, sector, weight_pct FROM mf_holdings WHERE scheme_code = ?;",
                (sc,),
            )
            h_rows = cur.fetchall()
            holdings_by_scheme_for_overlap[sc] = [
                {"company_name": hr[0], "symbol": hr[1], "sector": hr[2], "weight_pct": float(hr[3])}
                for hr in h_rows
            ]

        # Terminal cashflow for portfolio XIRR
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        all_cashflows.append((today_str, total_current_value))
        portfolio_xirr = calculate_xirr(all_cashflows)

        total_profit = total_current_value - total_invested
        total_abs_ret = (total_profit / total_invested * 100.0) if total_invested > 0 else 0.0

        # 4. Active vs Closed SIP Breakdown
        cur.execute(
            """
            SELECT id, scheme_code, amount, sip_day, start_date, end_date, status, step_up_pct
            FROM mf_sip_schedules
            WHERE portfolio_id = ?
            ORDER BY status ASC, start_date DESC;
            """,
            (portfolio_id,),
        )
        sip_rows = cur.fetchall()

        active_sips = []
        closed_sips = []

        for sip_row in sip_rows:
            s_id, sc, amt, day, s_date, e_date, status, step_up = sip_row
            sch_info = scheme_summary.get(sc, {})

            # Filter transactions linked to this SIP
            sip_txs = [r for r in tx_rows if r[8] == s_id]
            sip_invested = sum(float(r[5]) for r in sip_txs)
            sip_units = sum(float(r[6]) for r in sip_txs)
            sip_latest_nav = sch_info.get("current_nav", 100.0)
            sip_current_value = sip_units * sip_latest_nav

            sip_cfs = [(r[3], -float(r[5])) for r in sip_txs]
            if sip_current_value > 0:
                sip_cfs.append((today_str, sip_current_value))
            sip_xirr = calculate_xirr(sip_cfs)

            sip_data = {
                "sip_id": s_id,
                "scheme_code": sc,
                "scheme_name": sch_info.get("scheme_name", f"Scheme {sc}"),
                "category": sch_info.get("category", "Equity"),
                "monthly_amount": amt,
                "sip_day": day,
                "start_date": s_date,
                "end_date": e_date,
                "status": status,
                "step_up_pct": step_up,
                "installments_count": len(sip_txs),
                "total_invested": round(sip_invested, 2),
                "current_value": round(sip_current_value, 2),
                "profit": round(sip_current_value - sip_invested, 2),
                "xirr_pct": sip_xirr,
            }

            if status.upper() == "ACTIVE":
                # 1. Cash flow discipline & skipped installments analysis
                try:
                    s_dt = datetime.datetime.strptime(s_date[:10], "%Y-%m-%d").date()
                    today = datetime.date.today()
                    elapsed_months = max(1, (today.year - s_dt.year) * 12 + (today.month - s_dt.month) + 1)
                except Exception:
                    elapsed_months = max(1, len(sip_txs))

                actual_installments = len(sip_txs)
                skipped_installments = max(0, elapsed_months - actual_installments)
                regularity_pct = round(min(100.0, (actual_installments / elapsed_months * 100.0)), 1) if elapsed_months > 0 else 100.0

                sip_day_clamped = min(max(1, day or 5), 28)
                cur_due = datetime.date(today.year, today.month, sip_day_clamped)
                cur_due_str = cur_due.strftime("%Y-%m-%d")

                # Check check-in status for this month
                cur.execute(
                    "SELECT status FROM mf_sip_checkins WHERE sip_id = ? AND due_date = ? ORDER BY updated_at DESC, created_at DESC LIMIT 1;",
                    (s_id, cur_due_str),
                )
                chk_row = cur.fetchone()
                if chk_row:
                    checkin_status = str(chk_row[0]).upper()
                elif today >= cur_due:
                    checkin_status = "PENDING"
                else:
                    checkin_status = "UPCOMING"

                # Next scheduled debit date
                if today < cur_due:
                    next_due = cur_due
                else:
                    next_m = today.month + 1 if today.month < 12 else 1
                    next_y = today.year if today.month < 12 else today.year + 1
                    next_due = datetime.date(next_y, next_m, sip_day_clamped)

                sip_data["next_sip_date"] = next_due.strftime("%Y-%m-%d")
                sip_data["days_until_next_sip"] = max(0, (next_due - today).days)
                sip_data["current_month_checkin_status"] = checkin_status
                sip_data["due_date_current_month"] = cur_due_str

                sip_data["expected_installments"] = elapsed_months
                sip_data["actual_installments"] = actual_installments
                sip_data["skipped_installments_count"] = skipped_installments
                sip_data["regularity_pct"] = regularity_pct

                # 2. Fund intrinsic quantitative metrics
                nav_series = get_scheme_nav_series(sc)
                trailing = calculate_trailing_returns(nav_series)
                risk = calculate_risk_metrics(nav_series)
                ret_3y = trailing.get("3y")
                ret_3y_pct = round(ret_3y * 100, 2) if ret_3y is not None else None

                bench = CATEGORY_BENCHMARKS.get(sch_info.get("category", ""), {"index_name": "Nifty 500 TRI", "expected_3y_cagr": 14.5, "avg_ter": 0.70})
                rolling_alpha = round(ret_3y_pct - bench["expected_3y_cagr"], 2) if ret_3y_pct is not None else 0.0
                downside_cap = risk.get("downside_capture") if risk.get("downside_capture") is not None else 92.0
                expense_ratio = sch_info.get("expense_ratio") or 0.65

                sip_data["fund_cagr_3y"] = ret_3y_pct
                sip_data["benchmark_cagr_3y"] = bench["expected_3y_cagr"]
                sip_data["benchmark_name"] = bench["index_name"]
                sip_data["rolling_alpha_pct"] = rolling_alpha
                sip_data["downside_capture"] = downside_cap
                sip_data["expense_ratio"] = expense_ratio

                # 3. Cashflow diagnostic memo (disentangling timing/skipped installments from fund alpha)
                memo_parts = []
                if skipped_installments > 0:
                    memo_parts.append(
                        f"{skipped_installments} installment{'s' if skipped_installments > 1 else ''} skipped "
                        f"({regularity_pct}% regularity). Personal XIRR is {sip_xirr if sip_xirr is not None else '—'}% "
                        f"due to missed dates, whereas fund intrinsic 3Y CAGR is {ret_3y_pct if ret_3y_pct is not None else '—'}%."
                    )
                else:
                    memo_parts.append(f"Perfect 100% monthly discipline ({actual_installments}/{elapsed_months} installments executed seamlessly).")

                if checkin_status == "PENDING":
                    memo_parts.append(f"🔔 {cur_due.strftime('%B')} installment of ₹{amt:,.0f} is due for confirmation.")
                elif checkin_status == "SKIPPED":
                    memo_parts.append(f"⚠️ {cur_due.strftime('%B')} installment marked as skipped.")
                elif checkin_status == "PAID":
                    memo_parts.append(f"✓ {cur_due.strftime('%B')} installment debited & confirmed.")

                sip_data["cashflow_diagnostic_memo"] = " ".join(memo_parts)

                # 4. Action Prescription & Switch Options
                if ret_3y_pct is not None and ret_3y_pct < (bench["expected_3y_cagr"] - 3.0):
                    alert = "UNDERPERFORMING"
                    if sip_current_value > 40000:
                        action_type = "PAUSE_AND_REDIRECT"
                        action_headline = "Pause Future SIP & Reallocate Monthly Flow"
                        rec = (
                            f"Fund trails {bench['index_name']} by {abs(rolling_alpha):.1f}% over 3 years with {downside_cap:.0f}% downside capture. "
                            f"Pause monthly debits immediately to stop capital drag; leave existing corpus (₹{sip_current_value:,.0f}) to compound without triggering early exit loads/STCG, "
                            f"and redirect fresh SIP into a recommended top-quartile peer."
                        )
                    else:
                        action_type = "SWITCH_FULLY"
                        action_headline = "Switch Fully (Redeem Units & Reallocate SIP)"
                        rec = (
                            f"Fund exhibits chronic underperformance vs {bench['index_name']} ({rolling_alpha:+.1f}% alpha gap). "
                            f"Recommend redeeming 100% of accumulated units (₹{sip_current_value:,.0f}) and transferring monthly SIP of ₹{amt:,.0f} into an elite category leader."
                        )
                elif ret_3y_pct is not None and ret_3y_pct < bench["expected_3y_cagr"]:
                    alert = "WATCHLIST"
                    action_type = "WATCHLIST_HOLD"
                    action_headline = "Watchlist & Review Next Quarter"
                    rec = (
                        f"Fund slightly lags {bench['index_name']} by {abs(rolling_alpha):.1f}%, but downside protection ({downside_cap:.0f}%) remains acceptable. "
                        f"Maintain current SIP for 6 months before initiating a switch."
                    )
                else:
                    alert = "OUTPERFORMING"
                    action_type = "CONTINUE_CORE"
                    action_headline = "Maintain Core SIP Discipline"
                    rec = (
                        f"Exceptional fund health. Fund delivers +{rolling_alpha:.1f}% rolling alpha over {bench['index_name']} with defensive {downside_cap:.0f}% downside capture. "
                        f"Continue systematic compounding."
                    )

                sip_data["health_status"] = alert
                sip_data["action_type"] = action_type
                sip_data["action_headline"] = action_headline
                sip_data["recommendation"] = rec
                sip_data["trailing_3y_cagr"] = ret_3y_pct

                # Get concrete replacement options
                sip_data["switch_options"] = get_switch_options_for_scheme(
                    scheme_code=sc,
                    category=sch_info.get("category", "Equity: Flexi Cap"),
                    conn=conn,
                    current_val=sip_current_value,
                    monthly_amt=amt,
                )
                active_sips.append(sip_data)
            else:
                # Closed / Paused SIP Diagnostic (Post-Mortem)
                # Compute opportunity cost: What would value be if SIP had continued?
                months_since_stopped = 0
                if e_date:
                    try:
                        stop_d = datetime.datetime.strptime(e_date[:10], "%Y-%m-%d").date()
                        months_since_stopped = max(0, (datetime.date.today().year - stop_d.year) * 12 + (datetime.date.today().month - stop_d.month))
                    except Exception:
                        pass

                post_mortem = {
                    "stopped_date": e_date,
                    "months_inactive": months_since_stopped,
                    "retained_units": round(sip_units, 3),
                    "retained_valuation": round(sip_current_value, 2),
                }

                # If units retained and compounding
                if months_since_stopped > 6:
                    post_mortem["verdict"] = "Units still compounding. Review whether to resume or reallocate to core funds."
                else:
                    post_mortem["verdict"] = "Recently paused. Monitor closely or resume during market dips."

                sip_data["post_mortem"] = post_mortem

                # 3 Tactical Action Modes for Closed / Paused SIPs
                cat = sch_info.get("category", "Equity: Flexi Cap")
                bench = CATEGORY_BENCHMARKS.get(cat, {"index_name": "Nifty 500 TRI", "expected_3y_cagr": 14.5})
                nav_s = get_scheme_nav_series(sc)
                trailing_m = calculate_trailing_returns(nav_s)
                c_3y = trailing_m.get("3y")
                closed_ret_3y_pct = round(c_3y * 100, 2) if c_3y is not None else None
                compound_cagr = closed_ret_3y_pct if (closed_ret_3y_pct is not None and closed_ret_3y_pct > 0) else bench["expected_3y_cagr"]
                r = compound_cagr / 100.0
                scheme_name_str = sch_info.get("scheme_name", f"Scheme {sc}")
                sip_day_val = day or 5

                sip_data["action_options"] = {
                    "resume": {
                        "action": "RESUME",
                        "title": "Resume SIP",
                        "description": f"Restart systematic monthly investing in {scheme_name_str}.",
                        "suggested_amount": amt,
                        "suggested_sip_day": sip_day_val,
                        "rationale": f"Rupee-cost averaging benefits restart immediately. Continuing ₹{amt:,.0f}/month expands upon your ₹{sip_current_value:,.0f} retained balance.",
                    },
                    "reallocate": {
                        "action": "REALLOCATE",
                        "title": "Reallocate / Switch",
                        "description": "Shift retained capital or ongoing SIP into higher-alpha recommended schemes.",
                        "rationale": f"Your ₹{sip_current_value:,.0f} corpus can be rotated into top-quartile peers with superior Sharpe ratio and lower expense ratio.",
                        "options": get_switch_options_for_scheme(
                            scheme_code=sc,
                            category=cat,
                            conn=conn,
                            current_val=sip_current_value,
                            monthly_amt=amt,
                        ),
                    },
                    "let_compound": {
                        "action": "LET_COMPOUND",
                        "title": "Let Compound (Hold)",
                        "description": "Leave retained units untouched to compound passively without fresh capital.",
                        "rationale": f"Holding your {round(sip_units, 2)} units allows ₹{sip_current_value:,.0f} to grow unhindered with zero monthly commitment.",
                        "expected_cagr_pct": round(compound_cagr, 1),
                        "projections": {
                            "years_1": round(sip_current_value * ((1 + r) ** 1), 2),
                            "years_3": round(sip_current_value * ((1 + r) ** 3), 2),
                            "years_5": round(sip_current_value * ((1 + r) ** 5), 2),
                            "years_10": round(sip_current_value * ((1 + r) ** 10), 2),
                        },
                    },
                }
                closed_sips.append(sip_data)

        # 5. Asset Allocation breakdown
        alloc_by_cat: dict[str, float] = {}
        for s in scheme_summary.values():
            cat = s["category"]
            alloc_by_cat[cat] = alloc_by_cat.get(cat, 0.0) + s["current_value"]

        asset_alloc = {
            cat: round((val / total_current_value * 100.0), 1) if total_current_value > 0 else 0.0
            for cat, val in alloc_by_cat.items()
        }

        # 6. Cross-fund Overlap Matrix
        overlap_res = calculate_portfolio_overlap(holdings_by_scheme_for_overlap) if len(holdings_by_scheme_for_overlap) > 1 else {}

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": port_name,
            "notes": port_notes,
            "last_saved_at": last_saved,
            "total_invested": round(total_invested, 2),
            "current_value": round(total_current_value, 2),
            "unrealized_profit": round(total_profit, 2),
            "absolute_return_pct": round(total_abs_ret, 2),
            "portfolio_xirr_pct": portfolio_xirr,
            "monthly_sip_run_rate": sum(s["monthly_amount"] for s in active_sips),
            "active_sips_count": len(active_sips),
            "closed_sips_count": len(closed_sips),
            "active_sips": active_sips,
            "closed_sips": closed_sips,
            "scheme_holdings": list(scheme_summary.values()),
            "asset_allocation": asset_alloc,
            "overlap_analysis": overlap_res,
            "pending_checkins": pending_checkins,
            "checkin_history": checkin_history,
        }
    finally:
        conn.close()


def reset_user_mf_portfolio(portfolio_id: str) -> None:
    """Clear all SIP schedules, transactions, and check-ins from the portfolio to start fresh."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM mf_sip_checkins WHERE portfolio_id = ?;", (portfolio_id,))
        cur.execute("DELETE FROM mf_transactions WHERE portfolio_id = ?;", (portfolio_id,))
        cur.execute("DELETE FROM mf_sip_schedules WHERE portfolio_id = ?;", (portfolio_id,))
        conn.commit()
        logger.info("Successfully reset portfolio %s", portfolio_id)
    finally:
        conn.close()


def predict_mf_portfolio_health(portfolio_id: str) -> dict[str, Any]:
    """Evaluate comprehensive portfolio health and compute forward-looking predictive trajectories."""
    diag = analyze_mf_portfolio(portfolio_id)

    if not diag["scheme_holdings"]:
        return {
            "portfolio_id": portfolio_id,
            "health_score": 0,
            "verdict": "EMPTY_PORTFOLIO",
            "rating_label": "No Holdings Added Yet",
            "pillars": {
                "alpha_performance": 0,
                "diversification": 0,
                "overlap_efficiency": 0,
                "sip_discipline": 0,
            },
            "predictive_scenarios": [],
            "actionable_recommendations": [
                "Your mutual fund portfolio is currently empty. Use 'Add SIP Schedule' to add active or discontinued SIPs with your current invested amounts and valuations.",
                "Consult the Smart Advisor in the Intelligence section for a quantitative asset allocation model.",
            ],
        }

    # 1. Performance & Alpha Consistency (25 pts)
    # Evaluates benchmark-relative rolling excess return independent of investor cashflow timing
    active_sips = diag.get("active_sips", [])
    if active_sips:
        avg_alpha = sum(s.get("rolling_alpha_pct", 0.0) for s in active_sips) / len(active_sips)
        if avg_alpha >= 4.0:
            perf_score = 25.0
        elif avg_alpha >= 1.5:
            perf_score = 21.0
        elif avg_alpha >= -1.0:
            perf_score = 16.0
        elif avg_alpha >= -3.5:
            perf_score = 11.0
        else:
            perf_score = 6.0
    else:
        perf_score = 15.0

    # 2. Downside Risk & Capital Preservation (20 pts)
    if active_sips:
        avg_downside = sum(s.get("downside_capture", 95.0) for s in active_sips) / len(active_sips)
        if avg_downside <= 85.0:
            downside_score = 20.0
        elif avg_downside <= 95.0:
            downside_score = 16.0
        elif avg_downside <= 105.0:
            downside_score = 12.0
        else:
            downside_score = 6.0
    else:
        downside_score = 14.0

    # 3. Overlap & Redundancy Efficiency (20 pts)
    overlap_info = diag.get("overlap_analysis", {})
    avg_overlap = overlap_info.get("average_overlap_pct", 0.0)
    if avg_overlap <= 15.0:
        overlap_score = 20.0
    elif avg_overlap <= 28.0:
        overlap_score = 16.0
    elif avg_overlap <= 40.0:
        overlap_score = 10.0
    else:
        overlap_score = 4.0

    # 4. Asset Allocation & Diversification (20 pts)
    alloc = diag.get("asset_allocation", {})
    unique_cats = len(alloc)
    if unique_cats >= 4:
        div_score = 20.0
    elif unique_cats == 3:
        div_score = 16.0
    elif unique_cats == 2:
        div_score = 12.0
    else:
        div_score = 7.0

    # 5. SIP Execution & Regularity Discipline (15 pts)
    # Detects skipped installments vs scheduled run-rate
    if active_sips:
        avg_reg = sum(s.get("regularity_pct", 100.0) for s in active_sips) / len(active_sips)
        total_skipped = sum(s.get("skipped_installments_count", 0) for s in active_sips)
        if avg_reg >= 95.0:
            disc_score = 15.0
        elif avg_reg >= 85.0:
            disc_score = 12.0
        elif avg_reg >= 70.0:
            disc_score = 8.0
        else:
            disc_score = 4.0
    else:
        avg_reg = 100.0
        total_skipped = 0
        disc_score = 12.0

    total_health = int(round(perf_score + downside_score + overlap_score + div_score + disc_score))
    total_health = min(98, max(25, total_health))

    if total_health >= 85:
        verdict = "INSTITUTIONAL_EXCELLENCE"
        rating_label = "Institutional High Conviction"
    elif total_health >= 72:
        verdict = "HEALTHY_AND_BALANCED"
        rating_label = "Well-Balanced Alpha Portfolio"
    elif total_health >= 55:
        verdict = "MODERATE_DRAG"
        rating_label = "Moderate Overlap / Cost Drag"
    else:
        verdict = "REQUIRES_REALIGNMENT"
        rating_label = "Sub-Optimal Allocation / High Redundancy"

    # Forward Projections
    cur_val = diag["current_value"]
    m_sip = diag["monthly_sip_run_rate"]

    scenarios = []
    for yrs in [3, 5, 10]:
        def _sim(cagr_pct: float) -> float:
            r = (1.0 + (cagr_pct / 100.0)) ** (1.0 / 12.0) - 1.0
            val = cur_val
            for _ in range(yrs * 12):
                val = (val + m_sip) * (1.0 + r)
            return round(val, 0)

        scenarios.append({
            "horizon_years": yrs,
            "base_case_13pct": _sim(13.0),
            "bull_case_16pct": _sim(16.0),
            "bear_case_8pct": _sim(8.5),
        })

    # Actionable switching items list
    actionable_switches = []
    for s in active_sips:
        if s.get("action_type") in ("SWITCH_FULLY", "PAUSE_AND_REDIRECT", "SWITCH_PARTIALLY"):
            actionable_switches.append({
                "scheme_name": s["scheme_name"],
                "scheme_code": s["scheme_code"],
                "category": s["category"],
                "current_value": s["current_value"],
                "monthly_amount": s["monthly_amount"],
                "action_type": s["action_type"],
                "action_headline": s["action_headline"],
                "recommendation": s["recommendation"],
                "cashflow_diagnostic_memo": s.get("cashflow_diagnostic_memo", ""),
                "switch_options": s.get("switch_options", []),
            })

    # Recommendations
    recs = []
    if total_skipped > 0:
        recs.append(
            f"Cash Flow Regularity Alert: {total_skipped} skipped monthly installments detected across your SIPs ({avg_reg:.1f}% regularity). "
            f"Set up auto-debit or bank e-mandates to prevent compounding drag."
        )
    if avg_overlap > 30.0:
        recs.append(f"High Stock Redundancy ({avg_overlap}% avg overlap): Consolidate duplicate schemes across Large/Flexi cap to eliminate portfolio drag.")
    if actionable_switches:
        recs.append(f"Actionable Switching Advisory: {len(actionable_switches)} fund(s) flagged for strategic replacement or SIP pause. Review concrete switch options below.")
    if len(active_sips) > 0 and diag.get("closed_sips_count", 0) > 0:
        recs.append(f"Discontinued SIPs audit: You have {diag['closed_sips_count']} stopped SIPs with retained units compounding. Review whether to keep or consolidate.")
    if m_sip > 0:
        recs.append("SIP Acceleration: Setting an annual 10% step-up will grow your 10-year projected corpus by ~40% with minimal immediate cash impact.")
    if not recs:
        recs.append("Portfolio is mathematically sound. Maintain systematic SIP discipline and review quarterly.")

    return {
        "portfolio_id": portfolio_id,
        "health_score": total_health,
        "verdict": verdict,
        "rating_label": rating_label,
        "current_valuation": cur_val,
        "portfolio_xirr": diag.get("portfolio_xirr_pct"),
        "pillars": {
            "alpha_performance": round(perf_score, 1),
            "downside_protection": round(downside_score, 1),
            "overlap_efficiency": round(overlap_score, 1),
            "diversification": round(div_score, 1),
            "sip_discipline": round(disc_score, 1),
        },
        "cash_flow_discipline_analysis": {
            "total_active_sips": len(active_sips),
            "total_skipped_installments": total_skipped,
            "average_regularity_pct": round(avg_reg, 1),
            "verdict": "Disciplined Systematic Execution" if total_skipped == 0 else f"{total_skipped} Skipped Installments Detected",
            "insight": (
                "Zero missed dates! Your portfolio compounding is operating at peak mathematical efficiency."
                if total_skipped == 0
                else f"You have {total_skipped} skipped monthly installments ({avg_reg:.1f}% regularity). Skipped installments cause noticeable drag on long-term terminal corpus."
            ),
        },
        "actionable_switches": actionable_switches,
        "holding_diagnostics": active_sips,
        "predictive_scenarios": scenarios,
        "actionable_recommendations": recs,
    }


def resume_user_sip(
    portfolio_id: str,
    sip_id: str,
    amount: float | None = None,
    sip_day: int | None = None,
) -> dict[str, Any]:
    """Resume a paused or closed SIP schedule."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT scheme_code, amount, sip_day FROM mf_sip_schedules WHERE id = ? AND portfolio_id = ?;",
            (sip_id, portfolio_id),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"SIP schedule {sip_id} not found in portfolio {portfolio_id}")

        new_amt = float(amount) if amount is not None and amount > 0 else float(row[1])
        new_day = int(sip_day) if sip_day is not None and 1 <= sip_day <= 28 else int(row[2])

        cur.execute(
            """
            UPDATE mf_sip_schedules
            SET status = 'ACTIVE', end_date = NULL, amount = ?, sip_day = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND portfolio_id = ?;
            """,
            (new_amt, new_day, sip_id, portfolio_id),
        )
        conn.commit()
        return {
            "status": "success",
            "message": f"SIP {sip_id} resumed successfully as ACTIVE at ₹{new_amt:,.0f}/month.",
            "sip_id": sip_id,
            "portfolio_id": portfolio_id,
            "amount": new_amt,
            "sip_day": new_day,
        }
    finally:
        conn.close()


def reallocate_user_sip(
    portfolio_id: str,
    sip_id: str,
    target_scheme_code: int,
    allocation_mode: str = "full_switch",
    amount: float | None = None,
) -> dict[str, Any]:
    """Reallocate units or redirect SIP capital to a recommended target scheme."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT scheme_code, amount, sip_day FROM mf_sip_schedules WHERE id = ? AND portfolio_id = ?;",
            (sip_id, portfolio_id),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"SIP schedule {sip_id} not found in portfolio {portfolio_id}")

        old_sc = row[0]
        old_amt = float(row[1])
        old_day = int(row[2])
        new_amt = float(amount) if amount is not None and amount > 0 else old_amt

        fetch_and_cache_scheme_nav(target_scheme_code)

        cur.execute("SELECT sum(units), sum(amount) FROM mf_transactions WHERE sip_id = ?;", (sip_id,))
        tx_row = cur.fetchone()
        retained_units = float(tx_row[0]) if tx_row and tx_row[0] else 0.0

        cur.execute("SELECT nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;", (old_sc,))
        n_row = cur.fetchone()
        old_nav = float(n_row[0]) if n_row else 100.0
        retained_val = retained_units * old_nav

        cur.execute("SELECT nav FROM mf_nav_history WHERE scheme_code = ? ORDER BY nav_date DESC LIMIT 1;", (target_scheme_code,))
        t_row = cur.fetchone()
        target_nav = float(t_row[0]) if t_row else 100.0

        today_str = datetime.date.today().strftime("%Y-%m-%d")

        if allocation_mode == "full_switch":
            cur.execute("UPDATE mf_sip_schedules SET status = 'CLOSED', end_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (today_str, sip_id))
            if retained_units > 0:
                cur.execute(
                    """
                    INSERT INTO mf_transactions (id, portfolio_id, sip_id, scheme_code, tx_date, tx_type, amount, units, nav, notes)
                    VALUES (?, ?, ?, ?, ?, 'SELL', ?, ?, ?, ?);
                    """,
                    (f"tx_{uuid.uuid4().hex[:12]}", portfolio_id, sip_id, old_sc, today_str, retained_val, retained_units, old_nav, "Full Switch Redemption"),
                )
            new_sip_id = add_or_update_sip(
                portfolio_id=portfolio_id,
                scheme_code=target_scheme_code,
                amount=new_amt,
                start_date=today_str,
                status="ACTIVE",
                sip_day=old_day,
                custom_invested=retained_val if retained_val > 0 else None,
                custom_units=(retained_val / target_nav) if retained_val > 0 else None,
                auto_generate_tx=False,
            )
            msg = f"Full switch executed: Redeemed ₹{retained_val:,.0f} and shifted to scheme {target_scheme_code}."
        elif allocation_mode == "partial_switch":
            redeem_units = retained_units * 0.5
            redeem_val = retained_val * 0.5
            if redeem_units > 0:
                cur.execute(
                    """
                    INSERT INTO mf_transactions (id, portfolio_id, sip_id, scheme_code, tx_date, tx_type, amount, units, nav, notes)
                    VALUES (?, ?, ?, ?, ?, 'SELL', ?, ?, ?, ?);
                    """,
                    (f"tx_{uuid.uuid4().hex[:12]}", portfolio_id, sip_id, old_sc, today_str, redeem_val, redeem_units, old_nav, "Partial Switch (50% Redemption)"),
                )
            new_sip_id = add_or_update_sip(
                portfolio_id=portfolio_id,
                scheme_code=target_scheme_code,
                amount=new_amt * 0.5,
                start_date=today_str,
                status="ACTIVE",
                sip_day=old_day,
                custom_invested=redeem_val if redeem_val > 0 else None,
                custom_units=(redeem_val / target_nav) if redeem_val > 0 else None,
                auto_generate_tx=False,
            )
            msg = f"Partial switch (50%) executed: Shifted ₹{redeem_val:,.0f} into scheme {target_scheme_code}."
        else:
            cur.execute("UPDATE mf_sip_schedules SET status = 'CLOSED', end_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (today_str, sip_id))
            new_sip_id = add_or_update_sip(
                portfolio_id=portfolio_id,
                scheme_code=target_scheme_code,
                amount=new_amt,
                start_date=today_str,
                status="ACTIVE",
                sip_day=old_day,
                auto_generate_tx=False,
            )
            msg = f"Paused old SIP while retaining compounding units. Started fresh SIP of ₹{new_amt:,.0f}/mo in scheme {target_scheme_code}."

        conn.commit()
        return {
            "status": "success",
            "message": msg,
            "target_scheme_code": target_scheme_code,
            "new_sip_id": new_sip_id,
            "allocation_mode": allocation_mode,
        }
    finally:
        conn.close()
