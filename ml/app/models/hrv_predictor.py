"""XGBoost HRV prediction model.

Predicts next-morning HRV Z-score from today's biometric features.
Follows the AnomalyDetector pattern (train/predict/explain/save/load).
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import optuna
import shap
from xgboost import XGBRegressor

from app.models.validation import walk_forward_cv

logger = logging.getLogger(__name__)

# Suppress Optuna info logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

BASE_PARAMS = {
    "objective": "reg:squarederror",
    "max_depth": 3,
    "min_child_weight": 10,
    "learning_rate": 0.05,
    "subsample": 0.7,
    "colsample_bytree": 0.7,
    "reg_lambda": 5,
    "n_estimators": 500,
    "random_state": 42,
    "device": "cuda",
}


class HRVPredictor:
    """XGBoost predictor for next-morning HRV Z-score."""

    def __init__(self, model_store_path: str):
        self._store = Path(model_store_path)
        self._model: XGBRegressor | None = None
        self._feature_names: list[str] = []
        self._feature_medians: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None
        self._winsor_low: np.ndarray | None = None
        self._winsor_high: np.ndarray | None = None
        self._model_version: str = ""
        self._cv_metrics: dict = {}
        self._best_params: dict = {}
        self._stable_features: list[str] = []
        self._training_days: int = 0

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
    def cv_metrics(self) -> dict:
        return self._cv_metrics

    @property
    def stable_features(self) -> list[str]:
        return self._stable_features

    @property
    def training_days(self) -> int:
        return self._training_days

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        dates: list[date],
        optuna_trials: int = 50,
        min_train_days: int = 90,
    ) -> dict:
        """Train XGBoost with Optuna hyperparameter tuning + walk-forward CV.

        Args:
            X: Feature matrix (n_samples, n_features). May contain NaN.
            y: Target vector (next-day ln(RMSSD) Z-scores).
            feature_names: Ordered feature names.
            dates: Corresponding dates.
            optuna_trials: Number of Optuna trials for hyperparameter search.

        Returns:
            Training metadata dict.
        """
        self._feature_names = feature_names

        # IQR-based outlier filtering on target variable (y)
        # Conservative multiplier=3.0 removes only sensor errors
        q1 = np.nanpercentile(y, 25)
        q3 = np.nanpercentile(y, 75)
        iqr = q3 - q1
        lower_bound = q1 - 3.0 * iqr
        upper_bound = q3 + 3.0 * iqr
        inlier_mask = (y >= lower_bound) & (y <= upper_bound)
        n_removed = int(np.sum(~inlier_mask))
        if n_removed > 0:
            logger.info(
                "IQR outlier filter: removed %d/%d samples (bounds=[%.3f, %.3f])",
                n_removed, len(y), lower_bound, upper_bound,
            )
            X = X[inlier_mask]
            y = y[inlier_mask]
            dates = [d for d, keep in zip(dates, inlier_mask) if keep]

        self._training_days = X.shape[0]

        # Compute training statistics for normalization
        self._feature_medians = np.nanmedian(X, axis=0)
        self._feature_stds = np.nanstd(X, axis=0)
        self._feature_stds[self._feature_stds == 0] = 1.0

        # Compute winsorization bounds (1st/99th percentile) for features
        self._winsor_low = np.nanpercentile(X, 1, axis=0)
        self._winsor_high = np.nanpercentile(X, 99, axis=0)

        # Optuna hyperparameter search
        best_params = self._optuna_search(
            X, y, dates, feature_names, optuna_trials, min_train_days
        )
        self._best_params = best_params

        # Final walk-forward CV with best params for reporting
        cv_result = walk_forward_cv(
            X, y, dates, feature_names,
            min_train_days=min_train_days,
            gap_days=1,
            params=best_params,
        )
        self._cv_metrics = {
            "mae": cv_result.mae,
            "rmse": cv_result.rmse,
            "r2": cv_result.r2,
            "directional_accuracy": cv_result.directional_accuracy,
            "n_folds": len(cv_result.fold_results),
        }
        self._stable_features = cv_result.stable_features

        # Train final model on all data with best params + early stopping
        X_imputed = self._impute_and_normalize(X)
        n_eval = max(1, int(X_imputed.shape[0] * 0.1))
        X_train_final = X_imputed[:-n_eval]
        y_train_final = y[:-n_eval]
        X_eval_final = X_imputed[-n_eval:]
        y_eval_final = y[-n_eval:]

        self._model = XGBRegressor(**best_params, early_stopping_rounds=20)
        self._model.fit(
            X_train_final,
            y_train_final,
            eval_set=[(X_eval_final, y_eval_final)],
            verbose=False,
        )

        self._model_version = f"hrv_v{int(time.time())}"

        metadata = {
            "model_version": self._model_version,
            "training_days": self._training_days,
            "cv_mae": cv_result.mae,
            "cv_rmse": cv_result.rmse,
            "cv_r2": cv_result.r2,
            "cv_directional_accuracy": cv_result.directional_accuracy,
            "best_params": best_params,
            "stable_features": self._stable_features,
            "feature_names": feature_names,
        }

        logger.info(
            "Trained HRV predictor: %d days, MAE=%.3f, R2=%.3f, dir_acc=%.1f%%",
            self._training_days,
            cv_result.mae,
            cv_result.r2,
            cv_result.directional_accuracy * 100,
        )

        return metadata

    def _optuna_search(
        self,
        X: np.ndarray,
        y: np.ndarray,
        dates: list[date],
        feature_names: list[str],
        n_trials: int,
        min_train_days: int = 90,
    ) -> dict:
        """Optuna hyperparameter search using walk-forward CV MAE."""

        def objective(trial):
            params = {
                "objective": "reg:squarederror",
                "max_depth": trial.suggest_int("max_depth", 2, 4),
                "min_child_weight": trial.suggest_int("min_child_weight", 5, 20),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                "subsample": trial.suggest_float("subsample", 0.5, 0.8),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 0.8),
                "reg_lambda": trial.suggest_float("reg_lambda", 1.0, 10.0),
                "n_estimators": 500,
                "random_state": 42,
                "device": "cuda",
            }

            try:
                cv_result = walk_forward_cv(
                    X, y, dates, feature_names,
                    min_train_days=min_train_days,
                    gap_days=1,
                    params=params,
                    compute_shap=False,  # skip SHAP in inner loop for speed
                )
                return cv_result.mae
            except Exception:
                return float("inf")

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        best = {**BASE_PARAMS, **study.best_params}
        logger.info("Optuna best MAE=%.4f, params=%s", study.best_value, study.best_params)
        return best

    def _impute_and_normalize(self, X: np.ndarray) -> np.ndarray:
        """Impute NaN with training medians, winsorize, and normalize."""
        X_out = X.copy()
        for col in range(X_out.shape[1]):
            mask = np.isnan(X_out[:, col])
            if mask.any():
                X_out[mask, col] = self._feature_medians[col]
        # Winsorize: clip features to 1st/99th percentile bounds
        if self._winsor_low is not None and self._winsor_high is not None:
            X_out = np.clip(X_out, self._winsor_low, self._winsor_high)
        X_out = (X_out - self._feature_medians) / self._feature_stds
        return X_out

    def predict(self, features: np.ndarray) -> tuple[float, float]:
        """Predict next-morning HRV Z-score.

        Args:
            features: 1D array of feature values (may contain NaN).

        Returns:
            (predicted_z_score, confidence).
            Confidence is based on data completeness (1 - missing_ratio).
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        features_prepared = features.copy()
        nan_count = 0
        for i in range(len(features_prepared)):
            if np.isnan(features_prepared[i]):
                features_prepared[i] = self._feature_medians[i]
                nan_count += 1

        # Winsorize
        if self._winsor_low is not None and self._winsor_high is not None:
            features_prepared = np.clip(features_prepared, self._winsor_low, self._winsor_high)

        # Normalize
        features_prepared = (features_prepared - self._feature_medians) / self._feature_stds

        z_score = float(self._model.predict(features_prepared.reshape(1, -1))[0])

        # Confidence based on data completeness and model CV performance
        missing_ratio = nan_count / len(features) if len(features) > 0 else 0
        base_confidence = min(1.0, max(0.0, 1.0 - self._cv_metrics.get("mae", 1.0)))
        confidence = base_confidence * (1.0 - missing_ratio * 0.5)
        confidence = max(0.0, min(1.0, confidence))

        return z_score, confidence

    def explain(self, features: np.ndarray) -> dict[str, float]:
        """Compute SHAP values for a single prediction.

        Args:
            features: 1D array (may contain NaN, will be imputed).

        Returns:
            Dict of feature_name -> SHAP value.
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")

        features_prepared = features.copy()
        for i in range(len(features_prepared)):
            if np.isnan(features_prepared[i]):
                features_prepared[i] = self._feature_medians[i]

        if self._winsor_low is not None and self._winsor_high is not None:
            features_prepared = np.clip(features_prepared, self._winsor_low, self._winsor_high)

        features_prepared = (features_prepared - self._feature_medians) / self._feature_stds

        explainer = shap.TreeExplainer(self._model)
        shap_values = explainer.shap_values(features_prepared.reshape(1, -1))

        result = {}
        for i, name in enumerate(self._feature_names):
            result[name] = float(shap_values[0][i])

        return result

    def save(self) -> str:
        """Persist model artifacts to disk.

        Returns model_version string.
        """
        self._store.mkdir(parents=True, exist_ok=True)

        joblib.dump(self._model, self._store / "hrv_xgboost.joblib")
        joblib.dump(
            {
                "feature_medians": self._feature_medians,
                "feature_stds": self._feature_stds,
                "winsor_low": self._winsor_low,
                "winsor_high": self._winsor_high,
            },
            self._store / "hrv_scaler.joblib",
        )

        config = {
            "model_version": self._model_version,
            "feature_names": self._feature_names,
            "cv_metrics": self._cv_metrics,
            "best_params": self._best_params,
            "stable_features": self._stable_features,
            "training_days": self._training_days,
        }
        (self._store / "hrv_config.json").write_text(json.dumps(config))

        logger.info("Saved HRV model: %s", self._model_version)
        return self._model_version

    def load(self) -> bool:
        """Load model artifacts from disk.

        Returns True if successfully loaded, False otherwise.
        """
        model_path = self._store / "hrv_xgboost.joblib"
        scaler_path = self._store / "hrv_scaler.joblib"
        config_path = self._store / "hrv_config.json"

        if not all(p.exists() for p in [model_path, scaler_path, config_path]):
            logger.info("No HRV model found at %s", self._store)
            return False

        try:
            self._model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            self._feature_medians = scaler["feature_medians"]
            self._feature_stds = scaler["feature_stds"]
            self._winsor_low = scaler.get("winsor_low")
            self._winsor_high = scaler.get("winsor_high")

            config = json.loads(config_path.read_text())
            self._model_version = config["model_version"]
            self._feature_names = config["feature_names"]
            self._cv_metrics = config.get("cv_metrics", {})
            self._best_params = config.get("best_params", {})
            self._stable_features = config.get("stable_features", [])
            self._training_days = config.get("training_days", 0)

            logger.info("Loaded HRV model: %s", self._model_version)
            return True
        except Exception:
            logger.exception("Failed to load HRV model")
            return False
