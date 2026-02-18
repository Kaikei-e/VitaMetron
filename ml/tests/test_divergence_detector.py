"""Tests for the divergence detector model."""

import tempfile

import numpy as np
import pytest

from app.models.divergence_detector import DivergenceDetector


@pytest.fixture
def model_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def feature_names():
    return ["resting_hr", "hrv_ln_rmssd", "sleep_duration_min", "sleep_deep_min", "steps"]


@pytest.fixture
def training_data(feature_names):
    """Generate synthetic paired (biometric, condition) data on VAS 0-100 scale."""
    rng = np.random.RandomState(42)
    n = 50
    n_features = len(feature_names)
    X = rng.randn(n, n_features)
    # Target: VAS scale 0-100 with linear combination + noise
    y = 50.0 + 10.0 * X[:, 0] - 6.0 * X[:, 1] + 4.0 * rng.randn(n)
    y = np.clip(y, 1.0, 99.0)
    return X, y


def test_train_and_predict(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    assert not detector.is_ready

    metadata = detector.train(X, y, feature_names)
    assert detector.is_ready
    assert metadata["training_pairs"] == 50
    assert metadata["model_version"].startswith("divergence_v")
    assert len(metadata["feature_names"]) == 5
    assert metadata["r2_score"] is not None
    assert metadata["mae"] is not None

    # Predict on a normal point
    point = np.zeros(5)
    predicted, confidence = detector.predict(point)
    assert isinstance(predicted, float)
    assert 0.0 <= confidence <= 1.0


def test_predict_before_train(model_dir):
    detector = DivergenceDetector(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        detector.predict(np.zeros(5))


def test_compute_residual(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    residual = detector.compute_residual(70.0, 60.0)
    assert residual == 10.0

    residual = detector.compute_residual(40.0, 60.0)
    assert residual == -20.0


def test_cusum_aligned(model_dir, training_data, feature_names):
    """Small residuals should produce no alert."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    # Small residuals around mean
    residuals = [detector.residual_mean + 0.01 * i for i in range(10)]
    cusum_pos, cusum_neg, alert, div_type = detector.compute_cusum(residuals)
    assert not alert
    assert div_type == "aligned"


def test_cusum_positive_alert(model_dir, training_data, feature_names):
    """Large positive residuals should trigger positive CuSum alert."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    # Large positive residuals (feeling much better than expected)
    residuals = [detector.residual_mean + 3.0 * detector.residual_std] * 20
    cusum_pos, cusum_neg, alert, div_type = detector.compute_cusum(residuals)
    assert alert
    assert div_type == "feeling_better_than_expected"
    assert cusum_pos > detector.CUSUM_THRESHOLD


def test_cusum_negative_alert(model_dir, training_data, feature_names):
    """Large negative residuals should trigger negative CuSum alert."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    # Large negative residuals (feeling much worse than expected)
    residuals = [detector.residual_mean - 3.0 * detector.residual_std] * 20
    cusum_pos, cusum_neg, alert, div_type = detector.compute_cusum(residuals)
    assert alert
    assert div_type == "feeling_worse_than_expected"
    assert cusum_neg > detector.CUSUM_THRESHOLD


def test_cusum_empty_residuals(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    cusum_pos, cusum_neg, alert, div_type = detector.compute_cusum([])
    assert not alert
    assert div_type == "aligned"


def test_explain(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    features = np.zeros(5)
    contributions = detector.explain(features)
    assert isinstance(contributions, dict)
    assert len(contributions) == 5
    for name in feature_names:
        assert name in contributions
        assert isinstance(contributions[name], float)


def test_explain_before_train(model_dir):
    detector = DivergenceDetector(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        detector.explain(np.zeros(5))


def test_save_and_load(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    metadata = detector.train(X, y, feature_names)
    version = detector.save()
    assert version == metadata["model_version"]

    # Load into new instance
    detector2 = DivergenceDetector(model_dir)
    assert not detector2.is_ready
    loaded = detector2.load()
    assert loaded
    assert detector2.is_ready
    assert detector2.model_version == version
    assert detector2.feature_names == feature_names
    assert detector2.training_pairs == 50

    # Predictions should be consistent
    point = np.zeros(5)
    pred1, conf1 = detector.predict(point)
    pred2, conf2 = detector2.predict(point)
    assert abs(pred1 - pred2) < 1e-6
    assert abs(conf1 - conf2) < 1e-6


def test_load_missing_model(model_dir):
    detector = DivergenceDetector(model_dir)
    assert not detector.load()
    assert not detector.is_ready


def test_predict_with_nan(model_dir, training_data, feature_names):
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names)

    features = np.array([0.0, float("nan"), 0.0, float("nan"), 0.0])
    predicted, confidence = detector.predict(features)
    assert isinstance(predicted, float)
    # Confidence should be lower due to missing features
    full_features = np.zeros(5)
    _, full_confidence = detector.predict(full_features)
    assert confidence < full_confidence


def test_phase_cold_start(model_dir):
    detector = DivergenceDetector(model_dir)
    assert detector.get_phase(0) == "cold_start"
    assert detector.get_phase(13) == "cold_start"


def test_phase_initial(model_dir):
    detector = DivergenceDetector(model_dir)
    assert detector.get_phase(14) == "initial"
    assert detector.get_phase(27) == "initial"


def test_phase_baseline(model_dir):
    detector = DivergenceDetector(model_dir)
    assert detector.get_phase(28) == "baseline"
    assert detector.get_phase(59) == "baseline"


def test_phase_full(model_dir):
    detector = DivergenceDetector(model_dir)
    assert detector.get_phase(60) == "full"
    assert detector.get_phase(100) == "full"


def test_train_with_nan_features(model_dir, feature_names):
    """Training data with NaN should be handled via median imputation."""
    rng = np.random.RandomState(42)
    X = rng.randn(30, 5)
    y = 50.0 + 10.0 * X[:, 0] + 2.0 * rng.randn(30)
    y = np.clip(y, 1.0, 99.0)
    # Inject NaN
    X[0, 0] = float("nan")
    X[5, 2] = float("nan")

    detector = DivergenceDetector(model_dir)
    metadata = detector.train(X, y, feature_names)
    assert detector.is_ready
    assert metadata["training_pairs"] == 30


def test_train_with_logit_transform(model_dir, training_data, feature_names):
    """Logit transform should produce predictions within [0, 100]."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    metadata = detector.train(X, y, feature_names, use_logit=True)

    assert detector.is_ready
    assert metadata["r2_score"] is not None
    assert metadata["mae"] is not None

    # Predict on several points — all should be in [0, 100]
    for i in range(min(10, X.shape[0])):
        predicted, confidence = detector.predict(X[i])
        assert 0.0 <= predicted <= 100.0, f"Predicted {predicted} out of [0,100]"
        assert 0.0 <= confidence <= 1.0


def test_train_without_logit_transform(model_dir, training_data, feature_names):
    """Without logit transform, model should still train normally."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    metadata = detector.train(X, y, feature_names, use_logit=False)

    assert detector.is_ready
    assert metadata["training_pairs"] == 50


def test_train_with_sample_weights(model_dir, training_data, feature_names):
    """Training with sample weights should succeed."""
    X, y = training_data
    weights = np.ones(X.shape[0])
    weights[:10] = 0.2  # downweight first 10 samples

    detector = DivergenceDetector(model_dir)
    metadata = detector.train(X, y, feature_names, sample_weights=weights)

    assert detector.is_ready
    assert metadata["training_pairs"] == 50

    # Predictions should still be bounded
    point = np.zeros(5)
    predicted, _ = detector.predict(point)
    assert 0.0 <= predicted <= 100.0


def test_predictions_bounded(model_dir, feature_names):
    """Predictions should always be in [0, 100] even with extreme inputs."""
    rng = np.random.RandomState(42)
    X = rng.randn(50, 5)
    y = 50.0 + 10.0 * X[:, 0] - 6.0 * X[:, 1] + 4.0 * rng.randn(50)
    y = np.clip(y, 1.0, 99.0)

    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names, use_logit=True)

    # Test with extreme feature values
    extreme_high = np.full(5, 10.0)
    predicted, _ = detector.predict(extreme_high)
    assert 0.0 <= predicted <= 100.0

    extreme_low = np.full(5, -10.0)
    predicted, _ = detector.predict(extreme_low)
    assert 0.0 <= predicted <= 100.0


def test_save_and_load_preserves_logit(model_dir, training_data, feature_names):
    """Save/load should preserve use_logit flag."""
    X, y = training_data
    detector = DivergenceDetector(model_dir)
    detector.train(X, y, feature_names, use_logit=True)
    detector.save()

    # Load into new instance
    detector2 = DivergenceDetector(model_dir)
    assert detector2.load()
    assert detector2._use_logit is True

    # Predictions should match
    point = np.zeros(5)
    pred1, _ = detector.predict(point)
    pred2, _ = detector2.predict(point)
    assert abs(pred1 - pred2) < 1e-6
