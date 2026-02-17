"""Tests for the core anomaly detector model."""

import tempfile

import numpy as np
import pytest

from app.models.anomaly_detector import AnomalyDetector


@pytest.fixture
def model_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def feature_names():
    return ["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"]


@pytest.fixture
def training_data(feature_names):
    """Generate synthetic normal data with a few outliers."""
    rng = np.random.RandomState(42)
    n_normal = 100
    n_features = len(feature_names)
    X_normal = rng.randn(n_normal, n_features)
    # Add 2 outliers
    X_outliers = rng.randn(2, n_features) * 10
    X = np.vstack([X_normal, X_outliers])
    return X


def test_train_and_score(model_dir, training_data, feature_names):
    detector = AnomalyDetector(model_dir)
    assert not detector.is_ready

    metadata = detector.train(training_data, feature_names)
    assert detector.is_ready
    assert metadata["training_days"] == 102
    assert metadata["model_version"].startswith("anomaly_v")
    assert len(metadata["feature_names"]) == 5

    # Score a normal point
    normal_point = np.zeros(5)
    raw, normalized, is_anomaly = detector.score(normal_point)
    assert isinstance(raw, float)
    assert 0.0 <= normalized <= 1.0


def test_score_anomalous_point(model_dir, training_data, feature_names):
    detector = AnomalyDetector(model_dir)
    detector.train(training_data, feature_names)

    # Extreme outlier should get higher normalized score
    extreme = np.array([50.0, 50.0, 50.0, 50.0, 50.0])
    raw_extreme, norm_extreme, _ = detector.score(extreme)

    normal = np.zeros(5)
    raw_normal, norm_normal, _ = detector.score(normal)

    # Extreme point should be more anomalous (higher normalized score)
    assert norm_extreme > norm_normal


def test_score_with_nan(model_dir, training_data, feature_names):
    detector = AnomalyDetector(model_dir)
    detector.train(training_data, feature_names)

    # Score with NaN values (should be imputed)
    features = np.array([0.0, float("nan"), 0.0, float("nan"), 0.0])
    raw, normalized, is_anomaly = detector.score(features)
    assert isinstance(raw, float)
    assert 0.0 <= normalized <= 1.0


def test_explain(model_dir, training_data, feature_names):
    detector = AnomalyDetector(model_dir)
    detector.train(training_data, feature_names)

    features = np.zeros(5)
    shap_values = detector.explain(features)
    assert isinstance(shap_values, dict)
    assert len(shap_values) == 5
    for name in feature_names:
        assert name in shap_values
        assert isinstance(shap_values[name], float)


def test_save_and_load(model_dir, training_data, feature_names):
    detector = AnomalyDetector(model_dir)
    metadata = detector.train(training_data, feature_names)
    version = detector.save()
    assert version == metadata["model_version"]

    # Load into new instance
    detector2 = AnomalyDetector(model_dir)
    assert not detector2.is_ready
    loaded = detector2.load()
    assert loaded
    assert detector2.is_ready
    assert detector2.model_version == version
    assert detector2.feature_names == feature_names

    # Scores should be consistent
    point = np.zeros(5)
    raw1, norm1, anom1 = detector.score(point)
    raw2, norm2, anom2 = detector2.score(point)
    assert abs(raw1 - raw2) < 1e-6
    assert abs(norm1 - norm2) < 1e-6
    assert anom1 == anom2


def test_load_missing_model(model_dir):
    detector = AnomalyDetector(model_dir)
    assert not detector.load()
    assert not detector.is_ready


def test_score_before_train(model_dir):
    detector = AnomalyDetector(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        detector.score(np.zeros(5))


def test_explain_before_train(model_dir):
    detector = AnomalyDetector(model_dir)
    with pytest.raises(RuntimeError, match="not trained"):
        detector.explain(np.zeros(5))


def test_train_with_nan_features(model_dir, feature_names):
    """Training data with NaN should be handled via median imputation."""
    rng = np.random.RandomState(42)
    X = rng.randn(50, 5)
    # Inject NaN
    X[0, 0] = float("nan")
    X[5, 2] = float("nan")
    X[10, 4] = float("nan")

    detector = AnomalyDetector(model_dir)
    metadata = detector.train(X, feature_names)
    assert detector.is_ready
    assert metadata["training_days"] == 50
