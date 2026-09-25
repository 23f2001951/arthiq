"""Report builder for HTML and PDF investment recommendation reports."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import jinja2

from invst.reporting.rationale import generate_plain_english_rationale

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_report_html(
    asof_date: str | date,
    holdings_data: list[dict[str, Any]],
    run_id: str | None = None,
) -> str:
    """Render the quarterly investment recommendation report to HTML."""
    asof_str = asof_date.isoformat() if isinstance(asof_date, date) else str(asof_date)
    r_id = run_id or str(uuid.uuid4())

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")

    css_path = TEMPLATES_DIR / "styles.css"
    css_content = css_path.read_text(encoding="utf-8") if css_path.is_file() else ""

    # Enrich holdings with rationales if not already present
    enriched_holdings = []
    for h in holdings_data:
        h_copy = dict(h)
        if "rationale" not in h_copy or not h_copy["rationale"]:
            h_copy["rationale"] = generate_plain_english_rationale(
                symbol=h_copy["symbol"],
                company_name=h_copy.get("company_name", h_copy["symbol"]),
                sector=h_copy.get("sector", "general"),
                action=h_copy.get("action", "BUY"),
                target_weight=h_copy.get("target_weight", 0.125),
                current_weight=h_copy.get("current_weight", 0.0),
                scorecard=h_copy.get("scorecard", {}),
            )
        enriched_holdings.append(h_copy)

    html_out = template.render(
        asof_date=asof_str,
        run_id=r_id,
        holdings=enriched_holdings,
        css_styles=css_content,
    )
    return html_out


def generate_report_files(
    asof_date: str | date,
    holdings_data: list[dict[str, Any]],
    output_dir: str | Path = "reports",
    run_id: str | None = None,
    generate_pdf: bool = True,
) -> dict[str, Path]:
    """Generate HTML and PDF report artifacts."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    asof_str = asof_date.isoformat() if isinstance(asof_date, date) else str(asof_date)
    html_content = render_report_html(asof_str, holdings_data, run_id=run_id)

    html_file = out_dir / f"invst_report_{asof_str}.html"
    html_file.write_text(html_content, encoding="utf-8")
    result_files = {"html": html_file}

    if generate_pdf:
        try:
            import weasyprint  # type: ignore[import-untyped]

            pdf_file = out_dir / f"invst_report_{asof_str}.pdf"
            weasyprint.HTML(string=html_content).write_pdf(str(pdf_file))
            result_files["pdf"] = pdf_file
            logger.info(f"Generated PDF report: {pdf_file}")
        except Exception as e:
            logger.warning(
                f"Could not generate PDF report (WeasyPrint error or not installed): {e}"
            )

    logger.info(f"Generated HTML report: {html_file}")
    return result_files
