"""Tests for LSTM walk-forward cross-validation."""

from datetime import date, timedelta

import numpy as np
import pytest

from app.features.hrv_features import HRV_FEATURE_NAMES
from app.models.validation import CVResult, walk_forward_cv_lstm


FEATURE_NAMES = list(HRV_FEATURE_NAMES)
N_FEATURES = len(FEATURE_NAMES)
MIN_TRAIN = 30
FAST_PARAMS = {
    "max_epochs": 3,
    "patience": 2,
    "batch_size": 8,
    "hidden_dim": 4,
}


def _make_data(n=50):
    rng = np.random.RandomState(42)
    X = rng.randn(n, N_FEATURES)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + rng.randn(n) * 0.3
    dates = [date(2025, 6, 1) + timedelta(days=i) for i in range(n)]
    return X, y, FEATURE_NAMES, dates


def test_returns_cv_result():
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    assert isinstance(result, CVResult)
    assert len(result.fold_results) > 0


def test_no_temporal_leakage():
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    for fold in result.fold_results:
        # Train end must be before test date with at least gap_days+1 difference
        assert fold.train_end < fold.test_date
        gap = (fold.test_date - fold.train_end).days
        assert gap >= 2  # gap_days=1 means at least 2 days apart


def test_fold_boundaries_respect_lookback():
    """Test indices must be >= min_train_days + gap + lookback window start."""
    X, y, names, dates = _make_data(n=50)
    lookback = 7
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=lookback, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    for fold in result.fold_results:
        test_idx = dates.index(fold.test_date)
        # Sequence needs `lookback` days before test_idx
        assert test_idx >= lookback


def test_folds_ordered_temporally():
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    for i in range(1, len(result.fold_results)):
        prev = result.fold_results[i - 1]
        curr = result.fold_results[i]
        assert curr.test_date > prev.test_date


def test_metrics_reasonable():
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    assert result.mae >= 0
    assert result.rmse >= 0
    assert result.rmse >= result.mae
    assert 0 <= result.directional_accuracy <= 1


def test_predictions_are_finite():
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    for fold in result.fold_results:
        assert np.isfinite(fold.y_pred)
        assert np.isfinite(fold.y_true)


def test_handles_nan():
    rng = np.random.RandomState(42)
    n = 50
    X = rng.randn(n, N_FEATURES)
    y = rng.randn(n)
    X[5, 0] = float("nan")
    X[10, 3] = float("nan")
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(n)]

    result = walk_forward_cv_lstm(
        X, y, dates, FEATURE_NAMES,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    assert len(result.fold_results) > 0
    for fold in result.fold_results:
        assert np.isfinite(fold.y_pred)


def test_insufficient_data_raises():
    rng = np.random.RandomState(42)
    n = MIN_TRAIN  # exactly min_train, no room for gap + test
    X = rng.randn(n, N_FEATURES)
    y = rng.randn(n)
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(n)]

    with pytest.raises(ValueError, match="Need at least"):
        walk_forward_cv_lstm(
            X, y, dates, FEATURE_NAMES,
            lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
            **FAST_PARAMS,
        )


def test_larger_gap():
    X, y, names, dates = _make_data(n=60)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=3,
        **FAST_PARAMS,
    )
    for fold in result.fold_results:
        gap = (fold.test_date - fold.train_end).days
        assert gap >= 4  # gap_days=3 means at least 4 days apart


def test_stable_features_empty():
    """LSTM CV should not produce stable_features (no SHAP)."""
    X, y, names, dates = _make_data(n=50)
    result = walk_forward_cv_lstm(
        X, y, dates, names,
        lookback=7, min_train_days=MIN_TRAIN, gap_days=1,
        **FAST_PARAMS,
    )
    assert result.stable_features == []
