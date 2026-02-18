"""Core anomaly detection model using Isolation Forest + POT + SHAP."""

import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import shap
from scipy.stats import genpareto
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Isolation Forest anomaly detector with POT threshold and SHAP explanations."""

    def __init__(self, model_store_path: str):
        self._store = Path(model_store_path)
        self._model: IsolationForest | None = None
        self._pot_threshold: float = 0.0
        self._train_score_min: float = 0.0
        self._train_score_max: float = 1.0
        self._feature_names: list[str] = []
        self._feature_medians: np.ndarray | None = None
        self._winsor_low: np.ndarray | None = None
        self._winsor_high: np.ndarray | None = None
        self._model_version: str = ""

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    def train(
        self,
        X: np.ndarray,
        feature_names: list[str],
        contamination: float = 0.02,
        n_estimators: int = 200,
    ) -> dict:
        """Train Isolation Forest on quality-gated feature matrix.

        Args:
            X: Feature matrix (n_samples, n_features). May contain NaN.
            feature_names: Ordered feature names.
            contamination: Expected proportion of outliers.
            n_estimators: Number of trees.

        Returns:
            Training metadata dict.
        """
        self._feature_names = feature_names

        # Compute and store training medians for NaN imputation (Layer 3)
        self._feature_medians = np.nanmedian(X, axis=0)

        # Impute NaN with medians for training
        X_imputed = X.copy()
        for col in range(X_imputed.shape[1]):
            mask = np.isnan(X_imputed[:, col])
            if mask.any():
                X_imputed[mask, col] = self._feature_medians[col]

        # Winsorize: clip features to 1st/99th percentile to suppress extreme values
        self._winsor_low = np.percentile(X_imputed, 1, axis=0)
        self._winsor_high = np.percentile(X_imputed, 99, axis=0)
        X_imputed = np.clip(X_imputed, self._winsor_low, self._winsor_high)

        # Fit Isolation Forest
        self._model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X_imputed)

        # Compute training scores for normalization + POT
        train_scores = self._model.decision_function(X_imputed)

        # Normalize score range
        self._train_score_min = float(np.min(train_scores))
        self._train_score_max = float(np.max(train_scores))

        # Fit POT threshold
        self._pot_threshold = self._fit_pot_threshold(train_scores, contamination)

        # Generate model version
        self._model_version = f"anomaly_v{int(time.time())}"

        metadata = {
            "model_version": self._model_version,
            "training_days": int(X.shape[0]),
            "contamination": contamination,
            "n_estimators": n_estimators,
            "pot_threshold": self._pot_threshold,
            "feature_names": feature_names,
            "train_score_min": self._train_score_min,
            "train_score_max": self._train_score_max,
        }

        logger.info(
            "Trained anomaly detector: %d days, contamination=%.3f, pot_threshold=%.4f",
            X.shape[0],
            contamination,
            self._pot_threshold,
        )

        return metadata

    def _fit_pot_threshold(self, scores: np.ndarray, contamination: float) -> float:
        """Fit Generalized Pareto Distribution for adaptive threshold.

        Uses the most anomalous scores (below 5th percentile of decision_function)
        to fit GPD. Falls back to percentile-based threshold if GPD fit fails.
        """
        # Lower decision_function scores = more anomalous
        threshold_percentile = 5
        tail_threshold = np.percentile(scores, threshold_percentile)
        tail_excesses = tail_threshold - scores[scores <= tail_threshold]

        if len(tail_excesses) < 5:
            # Not enough tail data, fallback
            return float(np.percentile(scores, contamination * 100))

        try:
            shape, _, scale = genpareto.fit(tail_excesses, floc=0)
            # Derive threshold at the contamination quantile
            gpd_quantile = genpareto.ppf(1 - contamination, shape, loc=0, scale=scale)
            pot_threshold = tail_threshold - gpd_quantile
            logger.info(
                "POT fit: shape=%.3f, scale=%.3f, threshold=%.4f",
                shape,
                scale,
                pot_threshold,
            )
            return float(pot_threshold)
        except Exception:
            logger.warning("GPD fit failed, falling back to percentile threshold")
            return float(np.percentile(scores, contamination * 100))

    def score(self, features: np.ndarray) -> tuple[float, float, bool]:
        """Score a single observation.

        Args:
            features: 1D array of feature values. May contain NaN.

        Returns:
            (raw_anomaly_score, normalized_score_0_1, is_anomaly)
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        # Layer 3: NaN imputation with training medians + penalty
        features_imputed = features.copy()
        nan_count = 0
        for i in range(len(features_imputed)):
            if np.isnan(features_imputed[i]):
                features_imputed[i] = self._feature_medians[i]
                nan_count += 1

        # Winsorize
        if self._winsor_low is not None and self._winsor_high is not None:
            features_imputed = np.clip(features_imputed, self._winsor_low, self._winsor_high)

        # Get raw score from isolation forest
        raw_score = float(self._model.decision_function(features_imputed.reshape(1, -1))[0])

        # Normalize to [0, 1] (inverted: lower decision_function = more anomalous = higher normalized)
        score_range = self._train_score_max - self._train_score_min
        if score_range > 0:
            normalized = 1.0 - (raw_score - self._train_score_min) / score_range
        else:
            normalized = 0.5

        normalized = max(0.0, min(1.0, normalized))

        # Apply missing-feature penalty
        if nan_count > 0 and len(features) > 0:
            missing_ratio = nan_count / len(features)
            # Dampen the anomaly score proportional to missing data
            normalized *= 1.0 - (missing_ratio * 0.5)

        # Compare against POT threshold for anomaly flag
        is_anomaly = raw_score < self._pot_threshold

        return raw_score, normalized, is_anomaly

    def explain(self, features: np.ndarray) -> dict[str, float]:
        """Compute SHAP values for a single observation.

        Args:
            features: 1D array (may contain NaN, will be imputed).

        Returns:
            Dict of feature_name -> SHAP value.
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        features_imputed = features.copy()
        for i in range(len(features_imputed)):
            if np.isnan(features_imputed[i]):
                features_imputed[i] = self._feature_medians[i]

        if self._winsor_low is not None and self._winsor_high is not None:
            features_imputed = np.clip(features_imputed, self._winsor_low, self._winsor_high)

        explainer = shap.TreeExplainer(self._model)
        shap_values = explainer.shap_values(features_imputed.reshape(1, -1))

        result = {}
        for i, name in enumerate(self._feature_names):
            result[name] = float(shap_values[0][i])

        return result

    def save(self) -> str:
        """Persist model artifacts to disk.

        Returns model_version string.
        """
        self._store.mkdir(parents=True, exist_ok=True)

        joblib.dump(self._model, self._store / "isolation_forest.joblib")
        joblib.dump(
            {
                "pot_threshold": self._pot_threshold,
                "train_score_min": self._train_score_min,
                "train_score_max": self._train_score_max,
                "feature_medians": self._feature_medians,
                "winsor_low": self._winsor_low,
                "winsor_high": self._winsor_high,
            },
            self._store / "pot_params.joblib",
        )

        config = {
            "model_version": self._model_version,
            "feature_names": self._feature_names,
        }
        (self._store / "feature_config.json").write_text(json.dumps(config))

        logger.info("Saved anomaly model: %s", self._model_version)
        return self._model_version

    def load(self) -> bool:
        """Load model artifacts from disk.

        Returns True if successfully loaded, False otherwise.
        """
        model_path = self._store / "isolation_forest.joblib"
        params_path = self._store / "pot_params.joblib"
        config_path = self._store / "feature_config.json"

        if not all(p.exists() for p in [model_path, params_path, config_path]):
            logger.info("No anomaly model found at %s", self._store)
            return False

        try:
            self._model = joblib.load(model_path)
            params = joblib.load(params_path)
            self._pot_threshold = params["pot_threshold"]
            self._train_score_min = params["train_score_min"]
            self._train_score_max = params["train_score_max"]
            self._feature_medians = params["feature_medians"]
            self._winsor_low = params.get("winsor_low")
            self._winsor_high = params.get("winsor_high")

            config = json.loads(config_path.read_text())
            self._model_version = config["model_version"]
            self._feature_names = config["feature_names"]

            logger.info("Loaded anomaly model: %s", self._model_version)
            return True
        except Exception:
            logger.exception("Failed to load anomaly model")
            return False
