"""Outperformance Probability Classifier & Model Calibration.

Predicts P(outperform Nifty 500 over next 90 days).
Employs CalibratedClassifierCV with LightGBM, XGBoost, and regularized LogisticRegression.
Provides feature attribution, Brier score verification, and probability-based portfolio filtering.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class OutperformanceClassifier:
    """Calibrated outperformance probability model."""

    _LIGHTGBM_AVAILABLE: bool = True
    _WARNED_LIGHTGBM: bool = False

    def __init__(
        self,
        model_type: str = "lightgbm",
        threshold: float = 0.50,
        calibration_method: str = "isotonic",
    ) -> None:
        self.model_type = model_type.lower()
        if self.model_type == "lightgbm" and not self._LIGHTGBM_AVAILABLE:
            self.model_type = "logistic"
        self.threshold = threshold
        # Normalize Platt scaling alias to scikit-learn 'sigmoid'
        self.calibration_method = "sigmoid" if calibration_method in ["platt", "sigmoid"] else calibration_method
        self.scaler = StandardScaler()
        self.model: Any = None
        self.calibrated_model: Any = None
        self.feature_names: list[str] = []
        self.feature_importances: dict[str, float] = {}
        self.last_brier_score: float = 0.0
        self.is_trained = False

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> None:
        """Fit classifier and calibrate probabilities on training features."""
        if len(X) == 0 or len(y) == 0:
            logger.warning("Empty training dataset provided to OutperformanceClassifier")
            return

        # Check binary class balance
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            logger.warning(f"Training dataset contains single class {unique_classes}; defaulting to prior")
            self.is_trained = False
            return

        if feature_names:
            self.feature_names = list(feature_names)

        X_scaled = self.scaler.fit_transform(X)

        # 1. Instantiate base model
        base_estimator: Any = None
        if self.model_type == "lightgbm" and self._LIGHTGBM_AVAILABLE:
            try:
                import lightgbm as lgb  # type: ignore[import-untyped]

                base_estimator = lgb.LGBMClassifier(
                    n_estimators=100,
                    learning_rate=0.03,
                    max_depth=4,
                    num_leaves=15,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbose=-1,
                )
            except Exception as e:
                OutperformanceClassifier._LIGHTGBM_AVAILABLE = False
                if not OutperformanceClassifier._WARNED_LIGHTGBM:
                    logger.info(f"LightGBM native library unavailable ({e}); using native HistGradientBoostingClassifier")
                    OutperformanceClassifier._WARNED_LIGHTGBM = True
                from sklearn.ensemble import HistGradientBoostingClassifier
                base_estimator = HistGradientBoostingClassifier(
                    max_iter=60, max_depth=3, min_samples_leaf=8, l2_regularization=2.0, random_state=42
                )
                self.model_type = "histgbm"
        elif self.model_type in ["histgbm", "gradient_boosting"]:
            from sklearn.ensemble import HistGradientBoostingClassifier
            base_estimator = HistGradientBoostingClassifier(
                max_iter=60, max_depth=3, min_samples_leaf=8, l2_regularization=2.0, random_state=42
            )
        elif self.model_type == "xgboost":
            try:
                import xgboost as xgb  # type: ignore[import-untyped]

                base_estimator = xgb.XGBClassifier(
                    n_estimators=100,
                    learning_rate=0.03,
                    max_depth=4,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbosity=0,
                )
            except Exception as e:
                logger.warning(f"XGBoost unavailable ({e}); using regularized LogisticRegression")
                base_estimator = LogisticRegression(C=0.2, max_iter=500, random_state=42)
                self.model_type = "logistic"
        else:
            base_estimator = LogisticRegression(C=0.2, max_iter=500, random_state=42)

        # Fit base model to extract feature importances
        base_estimator.fit(X_scaled, y)
        self.model = base_estimator

        if hasattr(base_estimator, "feature_importances_") and self.feature_names:
            raw_imp = base_estimator.feature_importances_
            total_imp = np.sum(raw_imp) or 1.0
            self.feature_importances = {
                name: round(float(imp / total_imp), 4)
                for name, imp in zip(self.feature_names, raw_imp, strict=False)
            }
        elif hasattr(base_estimator, "coef_") and self.feature_names:
            abs_coef = np.abs(base_estimator.coef_[0])
            total_c = np.sum(abs_coef) or 1.0
            self.feature_importances = {
                name: round(float(c / total_c), 4)
                for name, c in zip(self.feature_names, abs_coef, strict=False)
            }
        elif self.feature_names:
            # Fallback for tree models without explicit feature_importances_: use univariate correlation with y
            corrs = [abs(float(np.corrcoef(X_scaled[:, i], y)[0, 1])) if np.std(X_scaled[:, i]) > 1e-6 else 0.0 for i in range(X_scaled.shape[1])]
            total_corr = sum(corrs) or 1.0
            self.feature_importances = {
                name: round(float(c / total_corr), 4)
                for name, c in zip(self.feature_names, corrs, strict=False)
            }

        # 2. Probability Calibration
        # Skip calibration if method is 'none' (for raw baseline)
        if self.calibration_method in ["none", None]:
            self.calibrated_model = base_estimator
        else:
            # Use cross-validation calibration if sufficient samples, else fit directly
            cv_splits = 3 if len(y) >= 30 else 2
            try:
                calibrated = CalibratedClassifierCV(
                    estimator=base_estimator,
                    method=self.calibration_method if len(y) >= 50 else "sigmoid",
                    cv=cv_splits,
                )
                calibrated.fit(X_scaled, y)
                self.calibrated_model = calibrated
            except Exception as e:
                logger.warning(f"Probability calibration failed ({e}); using uncalibrated base estimator")
                self.calibrated_model = base_estimator

        # 3. Compute Brier calibration loss on training set
        pred_probs = self.predict_proba(X)
        self.last_brier_score = round(float(np.mean((pred_probs - y) ** 2)), 4)
        self.is_trained = True

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] | None = None) -> None:
        """Alias for train() following scikit-learn standard interface."""
        self.train(X, y, feature_names=feature_names)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return calibrated probability of outperforming benchmark P(y=1) with spread preservation."""
        if not self.is_trained or self.model is None or len(X) == 0:
            return np.ones(len(X)) * 0.50

        X_scaled = self.scaler.transform(X)
        active_model = self.calibrated_model if self.calibrated_model is not None else self.model
        try:
            probs = active_model.predict_proba(X_scaled)[:, 1]
            # Cross-sectional contrast stretch when sigmoid over-compresses probability distribution
            if len(probs) > 3:
                p_std = float(np.std(probs))
                if 0.0 < p_std < 0.05:
                    med = float(np.median(probs))
                    scale = min(3.0, 0.12 / (p_std + 1e-6))
                    probs = np.clip(med + (probs - med) * scale, 0.10, 0.90)
            return np.clip(probs, 0.05, 0.95)
        except Exception as e:
            logger.warning(f"predict_proba error ({e}); returning neutral 0.50")
            return np.ones(len(X)) * 0.50

    def filter_by_probability(self, symbols: list[str], probs: np.ndarray) -> list[str]:
        """Filter symbols that satisfy P(outperform) >= threshold."""
        passed = []
        for sym, p in zip(symbols, probs, strict=False):
            if p >= self.threshold:
                passed.append(sym)
        return passed
