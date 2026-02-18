"""Divergence detector: Ridge regression + CuSum for subjective-objective gap detection."""

import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class DivergenceDetector:
    """Detects divergence between subjective condition and objective biometrics.

    Uses Ridge regression to predict expected condition score from biometrics,
    then CuSum to detect sustained deviations (divergence).
    """

    MIN_PAIRS_INITIAL = 14   # minimum for Ridge regression
    MIN_PAIRS_CUSUM = 28     # minimum for CuSum baseline
    MIN_PAIRS_FULL = 60      # fully calibrated
    CUSUM_THRESHOLD = 4.0    # h parameter (standard deviations)
    CUSUM_ALLOWANCE = 0.5    # k parameter (slack)
    LOGIT_EPS = 0.5          # boundary padding for logit transform

    def __init__(self, model_store_path: str):
        self._store = Path(model_store_path) / "divergence"
        self._scaler: StandardScaler | None = None
        self._model: Ridge | None = None
        self._feature_names: list[str] = []
        self._feature_medians: np.ndarray | None = None
        self._residual_mean: float = 0.0
        self._residual_std: float = 1.0
        self._r2_score: float | None = None
        self._mae: float | None = None
        self._rmse: float | None = None
        self._training_pairs: int = 0
        self._model_version: str = ""
        self._use_logit: bool = False

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    @property
    def training_pairs(self) -> int:
        return self._training_pairs

    @property
    def r2_score(self) -> float | None:
        return self._r2_score

    @property
    def mae(self) -> float | None:
        return self._mae

    @property
    def residual_mean(self) -> float:
        return self._residual_mean

    @property
    def residual_std(self) -> float:
        return self._residual_std

    def get_phase(self, n_pairs: int | None = None) -> str:
        """Return current phase based on number of paired observations."""
        n = n_pairs if n_pairs is not None else self._training_pairs
        if n < self.MIN_PAIRS_INITIAL:
            return "cold_start"
        if n < self.MIN_PAIRS_CUSUM:
            return "initial"
        if n < self.MIN_PAIRS_FULL:
            return "baseline"
        return "full"

    @staticmethod
    def _logit(y: np.ndarray, eps: float = 0.5) -> np.ndarray:
        """Transform VAS [0,100] to logit space (-inf, +inf)."""
        y_unit = np.clip(y, eps, 100.0 - eps) / 100.0
        return np.log(y_unit / (1.0 - y_unit))

    @staticmethod
    def _inverse_logit(y_logit: np.ndarray) -> np.ndarray:
        """Transform logit space back to VAS [0,100]."""
        y_unit = 1.0 / (1.0 + np.exp(-y_logit))
        return y_unit * 100.0

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        sample_weights: np.ndarray | None = None,
        use_logit: bool = True,
    ) -> dict:
        """Train StandardScaler + Ridge regression.

        Args:
            X: Feature matrix (n_samples, n_features). May contain NaN.
            y: Target condition scores (VAS 0-100).
            feature_names: Ordered feature names.
            sample_weights: Optional per-sample weights for Ridge.fit().
            use_logit: If True, apply logit transform to target before fitting.

        Returns:
            Training metadata dict.
        """
        self._feature_names = feature_names
        self._training_pairs = int(X.shape[0])
        self._use_logit = use_logit

        # Compute and store medians for NaN imputation
        self._feature_medians = np.nanmedian(X, axis=0)

        # Impute NaN
        X_imputed = X.copy()
        for col in range(X_imputed.shape[1]):
            mask = np.isnan(X_imputed[:, col])
            if mask.any():
                X_imputed[mask, col] = self._feature_medians[col]

        # Scale features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X_imputed)

        # Logit transform target for bounded [0,100] regression
        if self._use_logit:
            y_train = self._logit(y, self.LOGIT_EPS)
        else:
            y_train = y

        # Fit Ridge regression
        self._model = Ridge(alpha=1.0)
        self._model.fit(X_scaled, y_train, sample_weight=sample_weights)

        # Compute predictions in original VAS scale for metrics and CuSum
        y_pred_raw = self._model.predict(X_scaled)
        if self._use_logit:
            y_pred = np.clip(self._inverse_logit(y_pred_raw), 0.0, 100.0)
        else:
            y_pred = y_pred_raw

        # Residuals in original scale (VAS 0-100)
        residuals = y - y_pred

        self._residual_mean = float(np.mean(residuals))
        self._residual_std = float(np.std(residuals))
        if self._residual_std < 1e-8:
            self._residual_std = 1.0

        # Compute quality metrics in original scale
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        self._r2_score = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        self._mae = float(np.mean(np.abs(residuals)))
        self._rmse = float(np.sqrt(np.mean(residuals**2)))

        self._model_version = f"divergence_v{int(time.time())}"

        metadata = {
            "model_version": self._model_version,
            "training_pairs": self._training_pairs,
            "r2_score": self._r2_score,
            "mae": self._mae,
            "rmse": self._rmse,
            "residual_mean": self._residual_mean,
            "residual_std": self._residual_std,
            "feature_names": feature_names,
        }

        logger.info(
            "Trained divergence detector: %d pairs, R2=%.3f, MAE=%.3f, logit=%s",
            self._training_pairs,
            self._r2_score,
            self._mae,
            self._use_logit,
        )

        return metadata

    def predict(self, features: np.ndarray) -> tuple[float, float]:
        """Predict expected condition score from biometrics.

        Args:
            features: 1D array of feature values. May contain NaN.

        Returns:
            (predicted_score, confidence) — predicted_score in [0, 100].
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        features_imputed = features.copy()
        nan_count = 0
        for i in range(len(features_imputed)):
            if np.isnan(features_imputed[i]):
                features_imputed[i] = self._feature_medians[i]
                nan_count += 1

        X_scaled = self._scaler.transform(features_imputed.reshape(1, -1))
        predicted_raw = float(self._model.predict(X_scaled)[0])

        # Inverse-logit to map back to VAS [0, 100]
        if self._use_logit:
            predicted = float(self._inverse_logit(np.array([predicted_raw]))[0])
        else:
            predicted = predicted_raw

        # Safety clamp to [0, 100]
        predicted = float(np.clip(predicted, 0.0, 100.0))

        # Compute confidence
        feature_completeness = 1.0 - (nan_count / len(features)) if len(features) > 0 else 0.0
        maturity = min(1.0, self._training_pairs / self.MIN_PAIRS_FULL)
        model_quality = max(0.0, self._r2_score) if self._r2_score is not None else 0.0
        confidence = maturity * 0.4 + model_quality * 0.3 + feature_completeness * 0.3

        return predicted, confidence

    def compute_residual(self, actual: float, predicted: float) -> float:
        """Compute residual: actual - predicted.

        Positive = feeling better than expected.
        Negative = feeling worse than expected.
        """
        return actual - predicted

    def compute_cusum(
        self, residuals: list[float]
    ) -> tuple[float, float, bool, str]:
        """Compute CuSum on a series of residuals.

        Uses standardized CuSum per Mishra et al.

        Args:
            residuals: Ordered list of residuals (oldest first).

        Returns:
            (cusum_positive, cusum_negative, alert, divergence_type)
        """
        if not residuals or self._residual_std < 1e-8:
            return 0.0, 0.0, False, "aligned"

        cusum_pos = 0.0
        cusum_neg = 0.0

        for r in residuals:
            z = (r - self._residual_mean) / self._residual_std
            cusum_pos = max(0.0, cusum_pos + z - self.CUSUM_ALLOWANCE)
            cusum_neg = max(0.0, cusum_neg - z - self.CUSUM_ALLOWANCE)

        alert = cusum_pos > self.CUSUM_THRESHOLD or cusum_neg > self.CUSUM_THRESHOLD

        if cusum_pos > self.CUSUM_THRESHOLD:
            divergence_type = "feeling_better_than_expected"
        elif cusum_neg > self.CUSUM_THRESHOLD:
            divergence_type = "feeling_worse_than_expected"
        else:
            divergence_type = "aligned"

        return cusum_pos, cusum_neg, alert, divergence_type

    def explain(self, features: np.ndarray) -> dict[str, float]:
        """Compute feature contributions using Ridge coefficients.

        For each feature: contribution = coefficient * scaled_feature_value.

        Args:
            features: 1D array (may contain NaN, will be imputed).

        Returns:
            Dict of feature_name -> contribution.
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        features_imputed = features.copy()
        for i in range(len(features_imputed)):
            if np.isnan(features_imputed[i]):
                features_imputed[i] = self._feature_medians[i]

        X_scaled = self._scaler.transform(features_imputed.reshape(1, -1))[0]
        coefficients = self._model.coef_

        result = {}
        for i, name in enumerate(self._feature_names):
            result[name] = float(coefficients[i] * X_scaled[i])

        return result

    def save(self) -> str:
        """Persist model artifacts to disk."""
        self._store.mkdir(parents=True, exist_ok=True)

        joblib.dump(self._model, self._store / "ridge_model.joblib")
        joblib.dump(self._scaler, self._store / "scaler.joblib")
        joblib.dump(
            {
                "feature_medians": self._feature_medians,
                "residual_mean": self._residual_mean,
                "residual_std": self._residual_std,
                "training_pairs": self._training_pairs,
                "r2_score": self._r2_score,
                "mae": self._mae,
                "rmse": self._rmse,
                "use_logit": self._use_logit,
            },
            self._store / "params.joblib",
        )

        config = {
            "model_version": self._model_version,
            "feature_names": self._feature_names,
        }
        (self._store / "feature_config.json").write_text(json.dumps(config))

        logger.info("Saved divergence model: %s", self._model_version)
        return self._model_version

    def load(self) -> bool:
        """Load model artifacts from disk."""
        model_path = self._store / "ridge_model.joblib"
        scaler_path = self._store / "scaler.joblib"
        params_path = self._store / "params.joblib"
        config_path = self._store / "feature_config.json"

        if not all(p.exists() for p in [model_path, scaler_path, params_path, config_path]):
            logger.info("No divergence model found at %s", self._store)
            return False

        try:
            self._model = joblib.load(model_path)
            self._scaler = joblib.load(scaler_path)
            params = joblib.load(params_path)
            self._feature_medians = params["feature_medians"]
            self._residual_mean = params["residual_mean"]
            self._residual_std = params["residual_std"]
            self._training_pairs = params["training_pairs"]
            self._r2_score = params["r2_score"]
            self._mae = params["mae"]
            self._rmse = params.get("rmse")
            self._use_logit = params.get("use_logit", False)

            config = json.loads(config_path.read_text())
            self._model_version = config["model_version"]
            self._feature_names = config["feature_names"]

            logger.info("Loaded divergence model: %s", self._model_version)
            return True
        except Exception:
            logger.exception("Failed to load divergence model")
            return False
