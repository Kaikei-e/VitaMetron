"""Tests for HRV ensemble combiner."""

import tempfile
from unittest.mock import MagicMock

import numpy as np

from app.models.ensemble_hrv import HRVEnsemble, optimize_ensemble_weight


def _mock_xgb(z=0.5, conf=0.8):
    """Create a mock XGBoost predictor."""
    m = MagicMock()
    m.is_ready = True
    m.predict.return_value = (z, conf)
    m.explain.return_value = {"feat_0": 0.3, "feat_1": -0.2}
    return m


def _mock_lstm(z=0.4, conf=0.7, ready=True):
    """Create a mock LSTM predictor."""
    m = MagicMock()
    m.is_ready = ready
    m.predict.return_value = (z, conf)
    return m


# ---------------------------------------------------------------------------
# Ensemble prediction
# ---------------------------------------------------------------------------


def test_ensemble_weighted_prediction():
    xgb = _mock_xgb(z=1.0, conf=0.8)
    lstm = _mock_lstm(z=0.0, conf=0.6)
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.5)

    features = np.zeros(5)
    seq = np.zeros((7, 10), dtype=np.float32)
    z, conf = ensemble.predict(features, seq)

    # z = 0.5 * 1.0 + 0.5 * 0.0 = 0.5
    assert abs(z - 0.5) < 1e-6
    # conf = 0.5 * 0.8 + 0.5 * 0.6 = 0.7
    assert abs(conf - 0.7) < 1e-6


def test_ensemble_with_alpha():
    xgb = _mock_xgb(z=1.0, conf=0.8)
    lstm = _mock_lstm(z=0.0, conf=0.6)
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.7)

    features = np.zeros(5)
    seq = np.zeros((7, 10), dtype=np.float32)
    z, conf = ensemble.predict(features, seq)

    # z = 0.7 * 1.0 + 0.3 * 0.0 = 0.7
    assert abs(z - 0.7) < 1e-6
    # conf = 0.7 * 0.8 + 0.3 * 0.6 = 0.74
    assert abs(conf - 0.74) < 1e-6


# ---------------------------------------------------------------------------
# XGBoost-only fallback
# ---------------------------------------------------------------------------


def test_xgb_only_when_no_lstm():
    xgb = _mock_xgb(z=0.5, conf=0.8)
    ensemble = HRVEnsemble(xgb, lstm_predictor=None, alpha=0.5)

    assert not ensemble.has_lstm
    features = np.zeros(5)
    z, conf = ensemble.predict(features, None)
    assert abs(z - 0.5) < 1e-6
    assert abs(conf - 0.8) < 1e-6


def test_xgb_only_when_lstm_not_ready():
    xgb = _mock_xgb(z=0.5, conf=0.8)
    lstm = _mock_lstm(ready=False)
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.5)

    assert not ensemble.has_lstm
    features = np.zeros(5)
    z, conf = ensemble.predict(features, None)
    assert abs(z - 0.5) < 1e-6


def test_xgb_only_when_sequence_is_none():
    xgb = _mock_xgb(z=0.5, conf=0.8)
    lstm = _mock_lstm(z=0.4, conf=0.7)
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.5)

    features = np.zeros(5)
    z, conf = ensemble.predict(features, feature_sequence_2d=None)
    # Should fall back to XGBoost only
    assert abs(z - 0.5) < 1e-6
    assert abs(conf - 0.8) < 1e-6


def test_xgb_only_when_lstm_raises():
    xgb = _mock_xgb(z=0.5, conf=0.8)
    lstm = _mock_lstm()
    lstm.predict.side_effect = RuntimeError("LSTM error")
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.5)

    features = np.zeros(5)
    seq = np.zeros((7, 10), dtype=np.float32)
    z, conf = ensemble.predict(features, seq)
    assert abs(z - 0.5) < 1e-6


# ---------------------------------------------------------------------------
# Explain
# ---------------------------------------------------------------------------


def test_explain_delegates_to_xgb():
    xgb = _mock_xgb()
    lstm = _mock_lstm()
    ensemble = HRVEnsemble(xgb, lstm)

    result = ensemble.explain(np.zeros(5))
    xgb.explain.assert_called_once()
    assert "feat_0" in result


# ---------------------------------------------------------------------------
# Weight optimization
# ---------------------------------------------------------------------------


def test_optimize_ensemble_weight_basic():
    rng = np.random.RandomState(42)
    y_true = rng.randn(50)
    xgb_preds = y_true + rng.randn(50) * 0.3
    lstm_preds = y_true + rng.randn(50) * 0.5

    alpha = optimize_ensemble_weight(xgb_preds, lstm_preds, y_true)
    assert alpha in [0.3, 0.4, 0.5, 0.6, 0.7]


def test_optimize_weight_prefers_better_model():
    """When XGBoost is much better, alpha should be high."""
    rng = np.random.RandomState(42)
    y_true = rng.randn(50)
    xgb_preds = y_true + rng.randn(50) * 0.01  # very good
    lstm_preds = y_true + rng.randn(50) * 2.0  # very bad

    alpha = optimize_ensemble_weight(xgb_preds, lstm_preds, y_true)
    assert alpha >= 0.6  # Should favor XGBoost


def test_optimize_weight_equal_models():
    """When both models are identical, any alpha gives same result."""
    y_true = np.arange(10, dtype=np.float64)
    same_preds = y_true + 0.1

    alpha = optimize_ensemble_weight(same_preds, same_preds, y_true)
    # Any alpha is valid since both predict the same
    assert alpha in [0.3, 0.4, 0.5, 0.6, 0.7]


# ---------------------------------------------------------------------------
# Confidence bounds
# ---------------------------------------------------------------------------


def test_confidence_clamped():
    xgb = _mock_xgb(z=0.5, conf=1.5)  # artificially high
    lstm = _mock_lstm(z=0.4, conf=1.5)
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.5)

    _, conf = ensemble.predict(np.zeros(5), np.zeros((7, 10), dtype=np.float32))
    assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Save / Load config
# ---------------------------------------------------------------------------


def test_save_and_load_config():
    xgb = _mock_xgb()
    lstm = _mock_lstm()
    ensemble = HRVEnsemble(xgb, lstm, alpha=0.6)

    with tempfile.TemporaryDirectory() as tmpdir:
        ensemble.save_config(tmpdir)
        config = HRVEnsemble.load_config(tmpdir)

    assert config is not None
    assert abs(config["alpha"] - 0.6) < 1e-6
    assert config["has_lstm"] is True


def test_load_config_missing():
    config = HRVEnsemble.load_config("/nonexistent/path")
    assert config is None
