"""Group-wise PCA dimensionality reduction for HRV features.

Reduces 29 features to ~21 principal components via domain-grouped PCA,
with 3-5 PCs per group targeting 90% explained variance.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

# Feature groups by physiological domain
FEATURE_GROUPS: dict[str, list[str]] = {
    "sleep": [
        "sleep_duration_min",
        "sleep_deep_min",
        "sleep_rem_min",
        "br_full_sleep",
        "sleep_delta",
        "sleep_3d_std",
        "z_sleep_dur",
    ],
    "hrv": [
        "hrv_ln_rmssd",
        "hrv_deep_ln_rmssd",
        "hrv_deep_daily_ratio",
        "hrv_deep_delta",
        "hrv_delta",
        "hrv_3d_std",
        "hrv_change_rate",
        "z_hrv",
    ],
    "heart_rate": [
        "resting_hr",
        "resting_hr_delta",
        "rhr_3d_std",
        "rhr_change_rate",
        "z_rhr",
    ],
    "activity": [
        "steps",
        "calories_active",
        "active_zone_min",
        "steps_delta",
    ],
    "other": [
        "spo2_avg",
        "skin_temp_variation",
        "spo2_delta",
        "dow_sin",
        "dow_cos",
    ],
}

# Maximum PCs per group (caps to ensure we don't overfit small groups)
MAX_PCS_PER_GROUP: dict[str, int] = {
    "sleep": 4,
    "hrv": 4,
    "heart_rate": 3,
    "activity": 3,
    "other": 3,
}

EXPLAINED_VARIANCE_TARGET = 0.90


class PCAReducer:
    """Group-wise PCA that reduces features by physiological domain."""

    def __init__(self):
        self._group_pcas: dict[str, PCA] = {}
        self._group_indices: dict[str, list[int]] = {}
        self._medians: np.ndarray | None = None
        self._n_features_in: int = 0
        self._n_features_out: int = 0
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def n_features_out(self) -> int:
        return self._n_features_out

    def fit(self, X: np.ndarray, feature_names: list[str]) -> "PCAReducer":
        """Fit PCA per feature group.

        Args:
            X: Feature matrix (n_samples, n_features). May contain NaN.
            feature_names: Ordered feature names matching X columns.

        Returns:
            self
        """
        self._n_features_in = X.shape[1]

        # Compute medians for NaN imputation
        self._medians = np.nanmedian(X, axis=0)

        # Fallback for all-NaN columns (nanmedian returns NaN)
        nan_median_mask = np.isnan(self._medians)
        if nan_median_mask.any():
            self._medians[nan_median_mask] = 0.0

        # Impute NaN with medians
        X_imputed = X.copy()
        for col in range(X_imputed.shape[1]):
            mask = np.isnan(X_imputed[:, col])
            if mask.any():
                X_imputed[mask, col] = self._medians[col]

        # Map feature names to column indices
        name_to_idx = {name: i for i, name in enumerate(feature_names)}

        self._group_indices = {}
        self._group_pcas = {}
        total_pcs = 0

        for group_name, group_features in FEATURE_GROUPS.items():
            indices = [name_to_idx[f] for f in group_features if f in name_to_idx]
            if not indices:
                continue

            self._group_indices[group_name] = indices
            X_group = X_imputed[:, indices]

            max_pcs = min(MAX_PCS_PER_GROUP.get(group_name, 3), len(indices), X.shape[0])

            # Fit PCA with max components, then select enough for 90% variance
            pca = PCA(n_components=max_pcs)
            pca.fit(X_group)

            # Find minimum components for target explained variance
            cumvar = np.cumsum(pca.explained_variance_ratio_)
            n_keep = int(np.searchsorted(cumvar, EXPLAINED_VARIANCE_TARGET) + 1)
            n_keep = min(n_keep, max_pcs)
            n_keep = max(n_keep, 1)  # at least 1 PC per group

            # Re-fit with exact number of components
            pca_final = PCA(n_components=n_keep)
            pca_final.fit(X_group)
            self._group_pcas[group_name] = pca_final
            total_pcs += n_keep

            logger.debug(
                "PCA group '%s': %d features -> %d PCs (%.1f%% variance)",
                group_name,
                len(indices),
                n_keep,
                cumvar[n_keep - 1] * 100,
            )

        self._n_features_out = total_pcs
        self._is_fitted = True

        logger.info(
            "PCA reducer fitted: %d features -> %d PCs across %d groups",
            self._n_features_in,
            self._n_features_out,
            len(self._group_pcas),
        )
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform feature matrix to PCA-reduced space.

        Args:
            X: Feature matrix (n_samples, n_features) or (n_features,).

        Returns:
            Reduced array (n_samples, n_pcs) or (n_pcs,).
        """
        if not self._is_fitted:
            raise RuntimeError("PCAReducer not fitted")

        single = X.ndim == 1
        if single:
            X = X.reshape(1, -1)

        # Impute NaN with training medians
        X_imputed = X.copy()
        for col in range(X_imputed.shape[1]):
            mask = np.isnan(X_imputed[:, col])
            if mask.any():
                X_imputed[mask, col] = self._medians[col]

        parts = []
        for group_name in FEATURE_GROUPS:
            if group_name not in self._group_pcas:
                continue
            indices = self._group_indices[group_name]
            X_group = X_imputed[:, indices]
            parts.append(self._group_pcas[group_name].transform(X_group))

        result = np.hstack(parts)
        return result[0] if single else result

    def save(self, path: str | Path) -> None:
        """Save PCA reducer to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "group_pcas": self._group_pcas,
                "group_indices": self._group_indices,
                "medians": self._medians,
                "n_features_in": self._n_features_in,
                "n_features_out": self._n_features_out,
            },
            path / "pca_reducer.joblib",
        )

    def load(self, path: str | Path) -> bool:
        """Load PCA reducer from disk. Returns True if successful."""
        fpath = Path(path) / "pca_reducer.joblib"
        if not fpath.exists():
            return False
        try:
            data = joblib.load(fpath)
            self._group_pcas = data["group_pcas"]
            self._group_indices = data["group_indices"]
            self._medians = data["medians"]
            self._n_features_in = data["n_features_in"]
            self._n_features_out = data["n_features_out"]
            self._is_fitted = True
            return True
        except Exception:
            logger.exception("Failed to load PCA reducer")
            return False
