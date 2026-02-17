"""Tests for the XGBoost HRV predictor model."""

import tempfile
from datetime import date, timedelta

import numpy as np
import pytest
from xgboost import XGBRegressor

from app.models.hrv_predictor import HRVPredictor


FEATURE_NAMES = [f"feat_{i}" for i in range(5)]


def _make_ready_predictor(model_dir: str) -> HRVPredictor:
    """Create a predictor with a dummy model (no Optuna / CV)."""
    predictor = HRVPredictor(model_dir)
    rng = np.random.RandomState(42)
    n, n_feat = 40, len(FEATURE_NAMES)
    X = rng.randn(n, n_feat)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + rng.randn(n) * 0.3

    predictor._feature_names = list(FEATURE_NAMES)
    predictor._feature_medians = np.nanmedian(X, axis=0)
    predictor._feature_stds = np.nanstd(X, axis=0)
    predictor._feature_stds[predictor._feature_stds == 0] = 1.0
    predictor._training_days = n
    predictor._cv_metrics = {
        "mae": 0.3, "rmse": 0.4, "r2": 0.6,
        "directional_accuracy": 0.8, "n_folds": 5,
    }
    predictor._best_params = {"max_depth": 3}
    predictor._stable_features = ["feat_0", "feat_1"]
    predictor._model_version = "hrv_v_test"

    X_norm = (X - predictor._feature_medians) / predictor._feature_stds
    model = XGBRegressor(n_estimators=10, max_depth=2, random_state=42)
    model.fit(X_norm, y, verbose=False)
    predictor._model = model

    return predictor


@pytest.fixture
def model_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# Fast tests (dummy model, no Optuna / CV)
# ---------------------------------------------------------------------------


def test_not_ready_initially(model_dir):
    predictor = HRVPredictor(model_dir)
    assert not predictor.is_ready
    assert predictor.model_version == ""


def test_predict(model_dir):
    predictor = _make_ready_predictor(model_dir)
    assert predictor.is_ready

    point = np.zeros(len(FEATURE_NAMES))
    z_score, confidence = predictor.predict(point)
    assert isinstance(z_score, float)
    assert np.isfinite(z_score)
    assert 0.0 <= confidence <= 1.0


def test_predict_before_train(model_dir):
    predictor = HRVPredictor(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        predictor.predict(np.zeros(5))


def test_explain(model_dir):
    predictor = _make_ready_predictor(model_dir)

    point = np.zeros(len(FEATURE_NAMES))
    shap_values = predictor.explain(point)

    assert isinstance(shap_values, dict)
    assert len(shap_values) == len(FEATURE_NAMES)
    for name in FEATURE_NAMES:
        assert name in shap_values
        assert isinstance(shap_values[name], float)


def test_explain_before_train(model_dir):
    predictor = HRVPredictor(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        predictor.explain(np.zeros(5))


def test_save_and_load(model_dir):
    predictor = _make_ready_predictor(model_dir)
    version = predictor.save()
    assert version == "hrv_v_test"

    # Load into new instance
    predictor2 = HRVPredictor(model_dir)
    assert not predictor2.is_ready
    loaded = predictor2.load()
    assert loaded
    assert predictor2.is_ready
    assert predictor2.model_version == version
    assert predictor2.feature_names == list(FEATURE_NAMES)
    assert predictor2.training_days == 40

    # Predictions should be consistent
    point = np.zeros(len(FEATURE_NAMES))
    z1, c1 = predictor.predict(point)
    z2, c2 = predictor2.predict(point)
    assert abs(z1 - z2) < 1e-6
    assert abs(c1 - c2) < 1e-6


def test_load_missing_model(model_dir):
    predictor = HRVPredictor(model_dir)
    assert not predictor.load()
    assert not predictor.is_ready


def test_predict_with_nan(model_dir):
    predictor = _make_ready_predictor(model_dir)

    features = np.array([0.0] * len(FEATURE_NAMES), dtype=np.float64)
    features[0] = float("nan")
    features[3] = float("nan")

    z_score, confidence = predictor.predict(features)
    assert isinstance(z_score, float)
    assert np.isfinite(z_score)
    # Confidence should be reduced due to missing values
    z_clean, c_clean = predictor.predict(np.zeros(len(FEATURE_NAMES)))
    assert confidence <= c_clean


def test_cv_metrics_accessible(model_dir):
    predictor = _make_ready_predictor(model_dir)

    metrics = predictor.cv_metrics
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert "directional_accuracy" in metrics
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0


# ---------------------------------------------------------------------------
# Slow tests — full Optuna + walk-forward CV
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_full_train_and_predict(model_dir):
    """End-to-end training with Optuna + walk-forward CV."""
    predictor = HRVPredictor(model_dir)
    rng = np.random.RandomState(42)
    n = 50
    n_features = len(FEATURE_NAMES)
    X = rng.randn(n, n_features)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + 0.2 * X[:, 2] + rng.randn(n) * 0.3
    dates = [date(2025, 6, 1) + timedelta(days=i) for i in range(n)]

    metadata = predictor.train(
        X, y, list(FEATURE_NAMES), dates, optuna_trials=3, min_train_days=30,
    )

    assert predictor.is_ready
    assert metadata["model_version"].startswith("hrv_v")
    assert metadata["training_days"] == 50
    assert "cv_mae" in metadata
    assert "best_params" in metadata

    point = np.zeros(n_features)
    z_score, confidence = predictor.predict(point)
    assert isinstance(z_score, float)
    assert np.isfinite(z_score)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.slow
def test_full_train_with_nan(model_dir):
    """Training data with NaN should be handled via median imputation."""
    predictor = HRVPredictor(model_dir)
    rng = np.random.RandomState(42)
    n = 50
    X = rng.randn(n, len(FEATURE_NAMES))
    y = rng.randn(n)
    X[0, 0] = float("nan")
    X[5, 2] = float("nan")
    X[10, 4] = float("nan")
    dates = [date(2025, 6, 1) + timedelta(days=i) for i in range(n)]

    metadata = predictor.train(
        X, y, list(FEATURE_NAMES), dates, optuna_trials=3, min_train_days=30,
    )
    assert predictor.is_ready
    assert metadata["training_days"] == n
