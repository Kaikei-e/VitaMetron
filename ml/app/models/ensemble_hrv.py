"""HRV Ensemble: conditional weighted combination of XGBoost and LSTM.

XGBoost provides the primary prediction and SHAP explanations.
LSTM is only included if its standalone MAE is within 15% of XGBoost's.
"""

import json
import logging
from pathlib import Path

import numpy as np

from app.models.hrv_predictor import HRVPredictor
from app.models.lstm_predictor import LSTMHRVPredictor

logger = logging.getLogger(__name__)

ALPHA_GRID = [0.3, 0.4, 0.5, 0.6, 0.7]


def optimize_ensemble_weight(
    xgb_preds: np.ndarray,
    lstm_preds: np.ndarray,
    y_true: np.ndarray,
) -> float:
    """Find optimal blending weight via grid search.

    Args:
        xgb_preds: XGBoost predictions (n_samples,).
        lstm_preds: LSTM predictions (n_samples,).
        y_true: True values (n_samples,).

    Returns:
        Optimal alpha where ensemble = alpha * xgb + (1-alpha) * lstm.
    """
    best_alpha = 0.5
    best_mae = float("inf")

    for alpha in ALPHA_GRID:
        blended = alpha * xgb_preds + (1 - alpha) * lstm_preds
        mae = float(np.mean(np.abs(blended - y_true)))
        if mae < best_mae:
            best_mae = mae
            best_alpha = alpha

    logger.info("Optimal ensemble alpha=%.1f (MAE=%.4f)", best_alpha, best_mae)
    return best_alpha


class HRVEnsemble:
    """Weighted ensemble of XGBoost and LSTM predictors."""

    def __init__(
        self,
        xgb_predictor: HRVPredictor,
        lstm_predictor: LSTMHRVPredictor | None = None,
        alpha: float = 0.5,
    ):
        self._xgb = xgb_predictor
        self._lstm = lstm_predictor
        self._alpha = alpha

    @property
    def has_lstm(self) -> bool:
        return self._lstm is not None and self._lstm.is_ready

    @property
    def alpha(self) -> float:
        return self._alpha

    def predict(
        self,
        features_1d: np.ndarray,
        feature_sequence_2d: np.ndarray | None = None,
    ) -> tuple[float, float]:
        """Ensemble prediction.

        Args:
            features_1d: Raw feature vector for XGBoost (may contain NaN).
            feature_sequence_2d: PCA-reduced, normalized sequence for LSTM
                (lookback, reduced_dim), or None to use XGBoost only.

        Returns:
            (z_score, confidence).
        """
        xgb_z, xgb_conf = self._xgb.predict(features_1d)

        if not self.has_lstm or feature_sequence_2d is None:
            return xgb_z, xgb_conf

        try:
            lstm_z, lstm_conf = self._lstm.predict(feature_sequence_2d)
        except Exception:
            logger.debug("LSTM prediction failed, falling back to XGBoost only")
            return xgb_z, xgb_conf

        # Weighted blend
        z_score = self._alpha * xgb_z + (1 - self._alpha) * lstm_z
        confidence = self._alpha * xgb_conf + (1 - self._alpha) * lstm_conf
        confidence = max(0.0, min(1.0, confidence))

        return z_score, confidence

    def explain(self, features: np.ndarray) -> dict[str, float]:
        """SHAP explanation — always from XGBoost."""
        return self._xgb.explain(features)

    def save_config(self, path: str | Path) -> None:
        """Save ensemble configuration."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        config = {
            "alpha": self._alpha,
            "has_lstm": self.has_lstm,
        }
        (path / "ensemble_config.json").write_text(json.dumps(config))

    @staticmethod
    def load_config(path: str | Path) -> dict | None:
        """Load ensemble config from disk. Returns dict or None."""
        fpath = Path(path) / "ensemble_config.json"
        if not fpath.exists():
            return None
        try:
            return json.loads(fpath.read_text())
        except Exception:
            logger.exception("Failed to load ensemble config")
            return None
