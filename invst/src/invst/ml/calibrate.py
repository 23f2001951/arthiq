"""Model calibration checking and Population Stability Index (PSI) drift monitoring."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def compute_brier_score(y_true: Sequence[int | float], y_prob: Sequence[float]) -> float:
    """Compute the Brier calibration loss: mean((p - y)^2). Lower is better."""
    y_t = np.array(y_true)
    y_p = np.array(y_prob)
    if len(y_t) == 0:
        return 0.0
    loss = float(np.mean((y_p - y_t) ** 2))
    return round(loss, 4)


def compute_reliability_curve(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> list[dict[str, float]]:
    """Compute calibration curve data comparing predicted bin probability to observed frequency."""
    y_t = np.array(y_true)
    y_p = np.array(y_prob)
    if len(y_t) == 0:
        return []

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    curve = []

    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        mask = (y_p >= low) & (y_p <= high if i == n_bins - 1 else y_p < high)
        if np.sum(mask) > 0:
            mean_pred = float(np.mean(y_p[mask]))
            emp_freq = float(np.mean(y_t[mask]))
            curve.append(
                {
                    "bin_low": round(low, 2),
                    "bin_high": round(high, 2),
                    "count": int(np.sum(mask)),
                    "predicted_prob": round(mean_pred, 3),
                    "empirical_freq": round(emp_freq, 3),
                    "calibration_gap": round(abs(mean_pred - emp_freq), 3),
                }
            )

    return curve


def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """Compute Population Stability Index (PSI) between two feature distributions.

    Rule of thumb:
    - PSI < 0.10: No significant drift
    - 0.10 <= PSI <= 0.20: Moderate drift
    - PSI > 0.20: Significant feature drift (triggers retrain alert)
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    exp_clean = np.asarray(expected, dtype=float)
    act_clean = np.asarray(actual, dtype=float)

    # Determine safe number of bins based on sample size
    effective_bins = max(2, min(n_bins, len(exp_clean) // 2))
    percentiles = np.linspace(0, 100, effective_bins + 1)
    bin_edges = np.unique(np.percentile(exp_clean, percentiles))

    if len(bin_edges) < 2:
        min_val = min(np.min(exp_clean), np.min(act_clean))
        max_val = max(np.max(exp_clean), np.max(act_clean))
        bin_edges = np.linspace(min_val - 1e-4, max_val + 1e-4, 5)

    bin_edges[0] = min(bin_edges[0], np.min(act_clean) - 1e-4, np.min(exp_clean) - 1e-4)
    bin_edges[-1] = max(bin_edges[-1], np.max(act_clean) + 1e-4, np.max(exp_clean) + 1e-4)

    e_counts = np.histogram(exp_clean, bins=bin_edges)[0]
    a_counts = np.histogram(act_clean, bins=bin_edges)[0]
    actual_bins = len(e_counts)

    e_total = float(np.sum(e_counts)) or 1.0
    a_total = float(np.sum(a_counts)) or 1.0

    # Convert to proportions with smoothing epsilon to prevent log(0)
    e_pct = (e_counts + 1e-4) / (e_total + 1e-4 * actual_bins)
    a_pct = (a_counts + 1e-4) / (a_total + 1e-4 * actual_bins)

    psi_val = np.sum((a_pct - e_pct) * np.log(a_pct / e_pct))
    return round(float(psi_val), 4)


def compute_ece(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE).

    ECE = sum(|B_m| / N * |acc(B_m) - conf(B_m)|)
    """
    curve = compute_reliability_curve(y_true, y_prob, n_bins=n_bins)
    total_samples = sum(bin_info["count"] for bin_info in curve)
    if total_samples == 0:
        return 0.0

    ece = sum(
        (bin_info["count"] / total_samples) * bin_info["calibration_gap"]
        for bin_info in curve
    )
    return round(float(ece), 4)


def compute_log_loss(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    eps: float = 1e-15,
) -> float:
    """Compute cross-entropy log loss."""
    y_t = np.array(y_true, dtype=float)
    y_p = np.clip(np.array(y_prob, dtype=float), eps, 1.0 - eps)
    if len(y_t) == 0:
        return 0.0
    loss = -np.mean(y_t * np.log(y_p) + (1.0 - y_t) * np.log(1.0 - y_p))
    return round(float(loss), 4)


def evaluate_calibration_suite(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> dict[str, object]:
    """Calculate complete institutional calibration diagnostic suite."""
    y_t = np.array(y_true, dtype=int)
    y_p = np.array(y_prob, dtype=float)
    n = len(y_t)
    if n == 0:
        return {
            "samples": 0,
            "brier_score": 0.0,
            "ece": 0.0,
            "log_loss": 0.0,
            "pos_class_pct": 0.0,
            "roc_auc": 0.5,
            "reliability_curve": [],
        }

    brier = compute_brier_score(y_t, y_p)
    ece = compute_ece(y_t, y_p, n_bins=n_bins)
    ll = compute_log_loss(y_t, y_p)
    pos_pct = round(float(np.mean(y_t)) * 100.0, 2)
    curve = compute_reliability_curve(y_t, y_p, n_bins=n_bins)

    # Scikit-learn ROC-AUC if both classes present
    roc_auc = 0.5
    if len(np.unique(y_t)) > 1:
        try:
            from sklearn.metrics import roc_auc_score
            roc_auc = round(float(roc_auc_score(y_t, y_p)), 4)
        except Exception:
            roc_auc = 0.5

    return {
        "samples": n,
        "pos_count": int(np.sum(y_t)),
        "pos_class_pct": pos_pct,
        "brier_score": brier,
        "ece": ece,
        "log_loss": ll,
        "roc_auc": roc_auc,
        "reliability_curve": curve,
    }

