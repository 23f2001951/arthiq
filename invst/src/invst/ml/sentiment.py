"""News sentiment scoring with FinBERT and rule-based fallback.

Analyzes financial headlines and generates continuous sentiment scores in [-1.0, +1.0].
Employs FinBERT (`ProsusAI/finbert` or `yiyanghkust/finbert-tone`) when torch/transformers
are available, and a fast, deterministic financial-lexicon baseline as fallback.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

# Lightweight financial sentiment lexicon for deterministic fallback
POSITIVE_FINANCIAL_WORDS = {
    "surge",
    "jump",
    "rally",
    "gain",
    "profit",
    "growth",
    "beat",
    "strong",
    "bull",
    "upgrade",
    "dividend",
    "record",
    "high",
    "outperform",
    "expand",
    "robust",
    "soar",
    "deal",
    "win",
    "contract",
    "recovery",
    "boost",
    "positive",
    "uptick",
    "leverage",
    "buy",
    "opportunity",
}

NEGATIVE_FINANCIAL_WORDS = {
    "fall",
    "drop",
    "plunge",
    "slump",
    "loss",
    "decline",
    "miss",
    "weak",
    "bear",
    "downgrade",
    "debt",
    "default",
    "crisis",
    "underperform",
    "cut",
    "probe",
    "fraud",
    "penalty",
    "crash",
    "risk",
    "slowdown",
    "headwind",
    "negative",
    "downturn",
    "sell",
    "lawsuit",
    "inflation",
}


def rule_based_financial_sentiment(text: str) -> float:
    """Fast, deterministic rule-based financial sentiment score in [-1.0, +1.0]."""
    tokens = text.lower().split()
    if not tokens:
        return 0.0

    pos_count = sum(1 for t in tokens if t.strip(".,;:!?()[]\"'") in POSITIVE_FINANCIAL_WORDS)
    neg_count = sum(1 for t in tokens if t.strip(".,;:!?()[]\"'") in NEGATIVE_FINANCIAL_WORDS)

    total = pos_count + neg_count
    if total == 0:
        return 0.0

    # Normalized polarity
    score = (pos_count - neg_count) / total
    return round(float(score), 3)


class SentimentScorer:
    """Unified news sentiment model wrapper."""

    def __init__(self, model_name: str = "ProsusAI/finbert", use_transformer: bool = False):
        self.model_name = model_name
        self.use_transformer = use_transformer
        self._pipeline = None

        if use_transformer:
            try:
                from transformers import pipeline  # type: ignore[import-untyped]

                self._pipeline = pipeline("sentiment-analysis", model=model_name)
                logger.info(f"Loaded FinBERT transformer pipeline ({model_name})")
            except Exception as e:
                logger.warning(
                    f"Could not initialize transformer pipeline ({e}); using rule-based fallback"
                )
                self._pipeline = None

    def score_text(self, headline: str) -> float:
        """Score a single headline into [-1.0, +1.0]."""
        if not headline or not headline.strip():
            return 0.0

        if self._pipeline is not None:
            try:
                res = self._pipeline(headline[:512])[0]
                label = res["label"].lower()
                score = float(res["score"])
                if label == "positive":
                    return round(score, 3)
                elif label == "negative":
                    return round(-score, 3)
                else:
                    return 0.0
            except Exception as e:
                logger.debug(f"Transformer inference error: {e}; falling back to lexicon")

        return rule_based_financial_sentiment(headline)

    def score_batch(self, headlines: list[str]) -> list[float]:
        """Score a list of headlines."""
        return [self.score_text(h) for h in headlines]


def score_unprocessed_news_in_db(
    conn: sqlite3.Connection,
    scorer: SentimentScorer | None = None,
    batch_size: int = 200,
) -> int:
    """Find news headlines with NULL sentiment_score and update them."""
    s = scorer or SentimentScorer()
    cur = conn.execute(
        "SELECT headline_id, headline FROM news_sentiment WHERE sentiment_score IS NULL LIMIT ?",
        (batch_size,),
    )
    rows = cur.fetchall()
    if not rows:
        return 0

    updates = []
    for hid, headline in rows:
        score = s.score_text(headline)
        model_ver = "finbert" if s._pipeline is not None else "lexicon-v1"
        updates.append((score, model_ver, hid))

    conn.executemany(
        "UPDATE news_sentiment SET sentiment_score = ?, model_version = ? WHERE headline_id = ?",
        updates,
    )
    conn.commit()
    logger.info(f"Updated sentiment scores for {len(updates)} news records")
    return len(updates)
