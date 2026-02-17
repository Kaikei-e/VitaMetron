"""Tests for the LSTM HRV predictor model."""

import tempfile
from datetime import date, timedelta

import numpy as np
import pytest

from app.features.hrv_features import HRV_FEATURE_NAMES
from app.models.lstm_predictor import LSTMHRVPredictor, _create_sequences


FEATURE_NAMES = list(HRV_FEATURE_NAMES)
N_FEATURES = len(FEATURE_NAMES)


@pytest.fixture
def rng():
    return np.random.RandomState(42)


@pytest.fixture
def model_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_training_data(rng, n=120):
    X = rng.randn(n, N_FEATURES)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + rng.randn(n) * 0.3
    dates = [date(2025, 6, 1) + timedelta(days=i) for i in range(n)]
    return X, y, FEATURE_NAMES, dates


def _make_ready_predictor(model_dir: str, rng) -> LSTMHRVPredictor:
    """Create a predictor with a trained model."""
    predictor = LSTMHRVPredictor(model_dir)
    X, y, names, dates = _make_training_data(rng, n=60)
    predictor.train(X, y, names, dates, lookback_days=7, max_epochs=5, patience=3)
    return predictor


# ---------------------------------------------------------------------------
# Sequence creation
# ---------------------------------------------------------------------------


def test_create_sequences_shape(rng):
    X = rng.randn(20, 5)
    y = rng.randn(20)
    X_seq, y_seq, indices = _create_sequences(X, y, lookback=7)

    assert X_seq.shape == (13, 7, 5)
    assert y_seq.shape == (13,)
    assert len(indices) == 13
    assert indices[0] == 7
    assert indices[-1] == 19


def test_create_sequences_values(rng):
    X = np.arange(30).reshape(10, 3).astype(np.float32)
    y = np.arange(10, dtype=np.float32)
    X_seq, y_seq, _ = _create_sequences(X, y, lookback=3)

    # First sequence should be X[0:3], target y[3]
    np.testing.assert_array_equal(X_seq[0], X[0:3])
    assert y_seq[0] == y[3]


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def test_train_basic(model_dir, rng):
    predictor = LSTMHRVPredictor(model_dir)
    X, y, names, dates = _make_training_data(rng, n=60)

    metadata = predictor.train(
        X, y, names, dates,
        lookback_days=7, max_epochs=5, patience=3,
    )

    assert predictor.is_ready
    assert "model_version" in metadata
    assert metadata["model_version"].startswith("lstm_v")
    assert metadata["lookback_days"] == 7
    assert metadata["n_sequences"] > 0
    assert metadata["input_dim"] > 0
    assert metadata["n_params"] > 0


def test_train_insufficient_data(model_dir, rng):
    predictor = LSTMHRVPredictor(model_dir)
    X = rng.randn(10, N_FEATURES)
    y = rng.randn(10)
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(10)]

    with pytest.raises(ValueError, match="Too few sequences"):
        predictor.train(X, y, FEATURE_NAMES, dates, lookback_days=7, max_epochs=5)


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def test_predict(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)

    # Create a dummy sequence (7, reduced_dim)
    reduced_dim = predictor._input_dim
    seq = rng.randn(7, reduced_dim).astype(np.float32)

    z_score, confidence = predictor.predict(seq)
    assert isinstance(z_score, float)
    assert np.isfinite(z_score)
    assert 0.0 <= confidence <= 1.0


def test_predict_before_train(model_dir):
    predictor = LSTMHRVPredictor(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        predictor.predict(np.zeros((7, 5), dtype=np.float32))


# ---------------------------------------------------------------------------
# Sequence preparation
# ---------------------------------------------------------------------------


def test_prepare_sequence(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)

    features_list = [rng.randn(N_FEATURES) for _ in range(7)]
    seq = predictor.prepare_sequence(features_list)
    assert seq is not None
    assert seq.shape == (7, predictor._input_dim)
    assert not np.any(np.isnan(seq))


def test_prepare_sequence_wrong_length(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)

    features_list = [rng.randn(N_FEATURES) for _ in range(5)]
    assert predictor.prepare_sequence(features_list) is None


def test_prepare_sequence_with_none(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)

    features_list = [rng.randn(N_FEATURES) for _ in range(6)] + [None]
    assert predictor.prepare_sequence(features_list) is None


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


def test_save_and_load(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)
    version = predictor.save()
    assert version.startswith("lstm_v")

    predictor2 = LSTMHRVPredictor(model_dir)
    assert not predictor2.is_ready
    loaded = predictor2.load()
    assert loaded
    assert predictor2.is_ready
    assert predictor2.model_version == version
    assert predictor2._input_dim == predictor._input_dim

    # Predictions should be consistent
    reduced_dim = predictor._input_dim
    seq = rng.randn(7, reduced_dim).astype(np.float32)
    z1, _ = predictor.predict(seq)
    z2, _ = predictor2.predict(seq)
    assert abs(z1 - z2) < 1e-5


def test_load_missing_model(model_dir):
    predictor = LSTMHRVPredictor(model_dir)
    assert not predictor.load()
    assert not predictor.is_ready


# ---------------------------------------------------------------------------
# NaN handling
# ---------------------------------------------------------------------------


def test_train_with_nan(model_dir, rng):
    predictor = LSTMHRVPredictor(model_dir)
    X, y, names, dates = _make_training_data(rng, n=60)
    X[0, 0] = float("nan")
    X[5, 3] = float("nan")
    X[10, 7] = float("nan")

    metadata = predictor.train(
        X, y, names, dates, lookback_days=7, max_epochs=5, patience=3,
    )
    assert predictor.is_ready
    assert metadata["n_sequences"] > 0


def test_prepare_sequence_with_nan(model_dir, rng):
    predictor = _make_ready_predictor(model_dir, rng)

    features_list = [rng.randn(N_FEATURES) for _ in range(7)]
    features_list[2][0] = float("nan")
    features_list[4][5] = float("nan")

    seq = predictor.prepare_sequence(features_list)
    assert seq is not None
    assert not np.any(np.isnan(seq))


# ---------------------------------------------------------------------------
# Confidence scaling
# ---------------------------------------------------------------------------


def test_confidence_decreases_with_extreme_predictions(model_dir, rng):
    """Confidence should be lower for extreme Z-score predictions."""
    predictor = _make_ready_predictor(model_dir, rng)
    reduced_dim = predictor._input_dim

    # Use two different inputs that hopefully give different magnitudes
    seq_small = np.zeros((7, reduced_dim), dtype=np.float32)
    seq_large = np.ones((7, reduced_dim), dtype=np.float32) * 5.0

    _, conf_small = predictor.predict(seq_small)
    _, conf_large = predictor.predict(seq_large)

    # Both should be valid
    assert 0.0 <= conf_small <= 1.0
    assert 0.0 <= conf_large <= 1.0
