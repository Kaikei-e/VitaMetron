"""Tests for walk-forward cross-validation engine."""

from datetime import date, timedelta

import numpy as np
import pytest

from app.models.validation import CVResult, walk_forward_cv


MIN_TRAIN = 30
FAST_PARAMS = {
    "objective": "reg:squarederror",
    "max_depth": 2,
    "min_child_weight": 5,
    "learning_rate": 0.1,
    "n_estimators": 10,
    "random_state": 42,
}


def _make_data(n=50, n_features=3):
    rng = np.random.RandomState(42)
    X = rng.randn(n, n_features)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + rng.randn(n) * 0.3
    names = [f"feat_{i}" for i in range(n_features)]
    dates = [date(2025, 6, 1) + timedelta(days=i) for i in range(n)]
    return X, y, names, dates


# Compute once, test multiple properties
_X, _y, _names, _dates = _make_data()
_result = walk_forward_cv(
    _X, _y, _dates, _names,
    min_train_days=MIN_TRAIN, gap_days=1, params=FAST_PARAMS, compute_shap=False,
)


def test_returns_cv_result():
    assert isinstance(_result, CVResult)
    assert len(_result.fold_results) > 0


def test_fold_count():
    expected = _X.shape[0] - MIN_TRAIN - 1  # n - min_train - gap
    assert len(_result.fold_results) == expected


def test_no_temporal_leakage():
    for fold in _result.fold_results:
        assert fold.train_end < fold.test_date
        gap = (fold.test_date - fold.train_end).days
        assert gap >= 2


def test_folds_ordered_temporally():
    for i in range(1, len(_result.fold_results)):
        prev = _result.fold_results[i - 1]
        curr = _result.fold_results[i]
        assert curr.test_date > prev.test_date
        assert curr.train_end >= prev.train_end


def test_expanding_window():
    for i in range(1, len(_result.fold_results)):
        prev = _result.fold_results[i - 1]
        curr = _result.fold_results[i]
        assert (curr.train_end - curr.train_start).days >= (prev.train_end - prev.train_start).days


def test_metrics_reasonable():
    assert _result.mae >= 0
    assert _result.rmse >= 0
    assert _result.rmse >= _result.mae
    assert 0 <= _result.directional_accuracy <= 1


def test_feature_importances_present():
    for fold in _result.fold_results:
        assert len(fold.feature_importances) == len(_names)
        for name in _names:
            assert name in fold.feature_importances


def test_gap_respected_large_gap():
    X, y, names, dates = _make_data(n=45)
    result = walk_forward_cv(
        X, y, dates, names,
        min_train_days=MIN_TRAIN, gap_days=3, params=FAST_PARAMS, compute_shap=False,
    )
    for fold in result.fold_results:
        gap = (fold.test_date - fold.train_end).days
        assert gap >= 4  # gap_days + 1


def test_insufficient_data_raises():
    rng = np.random.RandomState(42)
    X = rng.randn(MIN_TRAIN, 3)
    y = rng.randn(MIN_TRAIN)
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(MIN_TRAIN)]

    with pytest.raises(ValueError, match="Need at least"):
        walk_forward_cv(X, y, dates, ["a", "b", "c"], min_train_days=MIN_TRAIN)


def test_handles_nan():
    rng = np.random.RandomState(42)
    n = 40
    X = rng.randn(n, 3)
    y = rng.randn(n)
    X[5, 0] = float("nan")
    X[10, 1] = float("nan")
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(n)]

    result = walk_forward_cv(
        X, y, dates, ["a", "b", "c"],
        min_train_days=MIN_TRAIN, gap_days=1, params=FAST_PARAMS, compute_shap=False,
    )
    assert len(result.fold_results) > 0
    for fold in result.fold_results:
        assert np.isfinite(fold.y_pred)


def test_shap_computation():
    """SHAP values should be returned when compute_shap=True."""
    X, y, names, dates = _make_data(n=40, n_features=3)
    result = walk_forward_cv(
        X, y, dates, names,
        min_train_days=MIN_TRAIN, gap_days=1, params=FAST_PARAMS, compute_shap=True,
    )
    assert len(result.fold_results) > 0
    for fold in result.fold_results:
        assert len(fold.feature_importances) == len(names)
        # SHAP values should be non-negative (absolute values used)
        for name in names:
            assert name in fold.feature_importances
            assert fold.feature_importances[name] >= 0


def test_stability_selection():
    """Features consistently in top-10 across folds should appear in stable_features."""
    # Use many features so stability selection is meaningful
    n, n_features = 80, 15
    rng = np.random.RandomState(42)
    X = rng.randn(n, n_features)
    # Make first feature strongly predictive so it's always top-ranked
    y = 2.0 * X[:, 0] + rng.randn(n) * 0.1
    names = [f"feat_{i}" for i in range(n_features)]
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(n)]

    result = walk_forward_cv(
        X, y, dates, names,
        min_train_days=MIN_TRAIN, gap_days=1, params=FAST_PARAMS, compute_shap=False,
    )
    # feat_0 should be stable since it dominates the signal
    assert "feat_0" in result.stable_features


def test_single_fold():
    """With exactly min_train + gap + 1 samples, should produce exactly 1 fold."""
    n = MIN_TRAIN + 1 + 1  # min_train_days + gap_days + 1
    rng = np.random.RandomState(42)
    X = rng.randn(n, 3)
    y = rng.randn(n)
    names = ["a", "b", "c"]
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(n)]

    result = walk_forward_cv(
        X, y, dates, names,
        min_train_days=MIN_TRAIN, gap_days=1, params=FAST_PARAMS, compute_shap=False,
    )
    assert len(result.fold_results) == 1
    assert result.fold_results[0].test_date == dates[-1]
