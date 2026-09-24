"""Sector and Archetype-Relative Feature Normalization.

Eliminates cross-industry metric incomparability (e.g., bank leverage vs IT cash,
capital-goods capital intensity vs software margins) by standardizing quantitative
signals within their corresponding Economic Sector Archetype cohorts.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

from invst.scoring.sectors.archetypes import SectorArchetype, get_sector_archetype

logger = logging.getLogger(__name__)


def normalize_cross_sectional_features_by_sector(
    feature_matrix: np.ndarray,
    symbols: Sequence[str],
    sector_map: dict[str, str],
    clip_zscore: float = 3.0,
    min_cluster_size: int = 2,
) -> np.ndarray:
    """Standardize feature matrix cross-sectionally within sector archetype clusters.

    Parameters
    ----------
    feature_matrix : np.ndarray
        2D array of shape (n_samples, n_features).
    symbols : Sequence[str]
        List of ticker symbols corresponding to rows of feature_matrix.
    sector_map : dict[str, str]
        Mapping of symbol to sector code.
    clip_zscore : float, default 3.0
        Winsorization threshold for standard deviations.
    min_cluster_size : int, default 2
        Minimum symbols required in a sector cohort to compute cohort z-score;
        falls back to overall cross-sectional z-score if smaller.

    Returns
    -------
    np.ndarray
        Standardized feature matrix of identical shape.
    """
    n_samples, n_features = feature_matrix.shape
    if n_samples == 0 or n_features == 0:
        return feature_matrix.copy()

    norm_matrix = np.empty_like(feature_matrix, dtype=float)

    # Map each symbol to its Economic Archetype
    archetypes = [
        get_sector_archetype(sector_map.get(sym, "financial_services"))
        for sym in symbols
    ]

    # Pre-calculate global cross-sectional mean and std as robust fallback
    global_means = np.nanmean(feature_matrix, axis=0)
    global_stds = np.nanstd(feature_matrix, axis=0)
    global_stds = np.where(global_stds > 1e-6, global_stds, 1.0)

    # Group sample row indices by SectorArchetype
    archetype_to_indices: dict[SectorArchetype, list[int]] = {}
    for idx, arch in enumerate(archetypes):
        archetype_to_indices.setdefault(arch, []).append(idx)

    for col in range(n_features):
        feat_col = feature_matrix[:, col]

        for _arch, row_indices in archetype_to_indices.items():
            if len(row_indices) >= min_cluster_size:
                cluster_vals = feat_col[row_indices]
                c_mean = float(np.nanmean(cluster_vals))
                c_std = float(np.nanstd(cluster_vals))
                if c_std < 1e-6 or np.isnan(c_std):
                    c_std = global_stds[col]
                    c_mean = global_means[col]
            else:
                c_mean = global_means[col]
                c_std = global_stds[col]

            # Compute standardized z-score for this cluster
            z = (feat_col[row_indices] - c_mean) / c_std
            # Winsorize extreme tails
            z_clipped = np.clip(z, -clip_zscore, clip_zscore)
            norm_matrix[row_indices, col] = z_clipped

    # Fill any remaining NaNs with 0.0 (neutral score)
    np.nan_to_num(norm_matrix, copy=False, nan=0.0)
    return norm_matrix
