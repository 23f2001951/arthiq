"""News RSS feed ingestor.

Fetches and parses financial news RSS feeds (Google News, Livemint, Moneycontrol, etc.),
extracts publication dates, headlines, and links, computes idempotent headline IDs,
and upserts records into the news_sentiment table.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_headline_id(
    headline: str, link: str | None = None, pub_date: str | None = None
) -> str:
    """Generate an idempotent sha256 hash ID for a news headline."""
    key = f"{headline.strip()}|{link or ''}|{pub_date or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def parse_rss_xml(
    xml_content: str, default_symbol: str | None = None, default_source: str = "rss"
) -> list[dict[str, Any]]:
    """Parse RSS 2.0 XML string into headline item records."""
    records: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"Failed to parse RSS XML: {e}")
        return records

    channel = root.find("channel")
    if channel is None:
        items = root.findall(".//item")
    else:
        items = channel.findall("item")

    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el = item.find("source")

        headline = title_el.text.strip() if title_el is not None and title_el.text else ""
        if not headline:
            continue

        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        source_name = (
            source_el.text.strip() if source_el is not None and source_el.text else default_source
        )

        pub_date_str = None
        if pubdate_el is not None and pubdate_el.text:
            raw_date = pubdate_el.text.strip()
            # Try standard RFC 822 format (e.g. 'Tue, 15 Oct 2024 12:30:00 GMT')
            try:
                # Simple parsing fallback
                parsed_dt = datetime.strptime(raw_date[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                pub_date_str = parsed_dt.strftime("%Y-%m-%d")
            except Exception:
                # Try isoformat or date string
                pub_date_str = raw_date[:10]
        if not pub_date_str:
            pub_date_str = datetime.now().strftime("%Y-%m-%d")

        headline_id = generate_headline_id(headline, link, pub_date_str)

        records.append(
            {
                "headline_id": headline_id,
                "symbol": default_symbol.upper() if default_symbol else None,
                "published_at": pub_date_str,
                "headline": headline,
                "source": source_name,
                "sentiment_score": None,
                "model_version": None,
            }
        )

    return records


def ingest_news_records(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> int:
    """Insert news items into news_sentiment table."""
    if not records:
        return 0

    query = """
    INSERT OR REPLACE INTO news_sentiment (
        headline_id, symbol, published_at, headline, source, sentiment_score, model_version
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    params = [
        (
            r["headline_id"],
            r.get("symbol"),
            r["published_at"],
            r["headline"],
            r.get("source", "rss"),
            r.get("sentiment_score"),
            r.get("model_version"),
        )
        for r in records
    ]

    conn.executemany(query, params)
    conn.commit()
    logger.info(f"Ingested {len(params)} news headlines into news_sentiment")
    return len(params)


def fetch_google_news_rss(
    symbol: str,
    query: str | None = None,
    timeout: float = 5.0,
) -> list[dict[str, Any]]:
    """Fetch live news headlines from Google News RSS for a stock symbol or query.

    Gracefully falls back to empty list on network error or timeout.
    """
    import urllib.parse
    import urllib.request

    from invst.ml.sentiment import rule_based_financial_sentiment

    clean_symbol = symbol.strip().upper()
    search_query = query or f"{clean_symbol} stock NSE India"
    encoded_query = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    import ssl
    try:
        import certifi
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(rss_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as response:
                xml_data = response.read().decode("utf-8", errors="ignore")
        except ssl.SSLError:
            unverified_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=unverified_ctx) as response:
                xml_data = response.read().decode("utf-8", errors="ignore")

        records = parse_rss_xml(xml_data, default_symbol=clean_symbol, default_source="Google News")
        for r in records:
            r["sentiment_score"] = rule_based_financial_sentiment(r["headline"])
            r["model_version"] = "rule_based_v1"
        return records
    except Exception as e:
        logger.debug(f"Live Google News RSS fetch failed for {clean_symbol} ({e}). Falling back gracefully.")
        return []

