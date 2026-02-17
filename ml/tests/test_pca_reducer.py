"""Tests for group-wise PCA reducer."""

import tempfile

import numpy as np
import pytest

from app.features.hrv_features import HRV_FEATURE_NAMES
from app.features.pca_reducer import FEATURE_GROUPS, PCAReducer


@pytest.fixture
def rng():
    return np.random.RandomState(42)


@pytest.fixture
def sample_data(rng):
    """Generate sample data with correct number of features."""
    n = 100
    n_feat = len(HRV_FEATURE_NAMES)
    X = rng.randn(n, n_feat)
    return X, list(HRV_FEATURE_NAMES)


def test_all_features_covered_by_groups():
    """Every feature in HRV_FEATURE_NAMES should belong to exactly one group."""
    grouped = set()
    for features in FEATURE_GROUPS.values():
        grouped.update(features)
    for name in HRV_FEATURE_NAMES:
        assert name in grouped, f"Feature '{name}' not in any group"


def test_no_duplicate_features_across_groups():
    """No feature should appear in more than one group."""
    seen = set()
    for group_name, features in FEATURE_GROUPS.items():
        for f in features:
            assert f not in seen, f"Feature '{f}' duplicated in group '{group_name}'"
            seen.add(f)


def test_fit_transform(sample_data):
    reducer = PCAReducer()
    X, names = sample_data

    reducer.fit(X, names)
    assert reducer.is_fitted
    assert reducer.n_features_out > 0
    assert reducer.n_features_out <= len(names)

    X_reduced = reducer.transform(X)
    assert X_reduced.shape == (X.shape[0], reducer.n_features_out)
    assert not np.any(np.isnan(X_reduced))


def test_dimensionality_reduction(sample_data):
    """Output should have fewer dimensions than input."""
    reducer = PCAReducer()
    X, names = sample_data
    reducer.fit(X, names)
    assert reducer.n_features_out < len(names)


def test_transform_single_sample(sample_data):
    """Transform should work on a 1D input (single sample)."""
    reducer = PCAReducer()
    X, names = sample_data
    reducer.fit(X, names)

    single = X[0]
    result = reducer.transform(single)
    assert result.ndim == 1
    assert result.shape[0] == reducer.n_features_out


def test_nan_handling(sample_data, rng):
    """NaN values should be imputed during both fit and transform."""
    reducer = PCAReducer()
    X, names = sample_data

    # Add NaN to training data
    X_nan = X.copy()
    X_nan[0, 0] = float("nan")
    X_nan[5, 3] = float("nan")
    X_nan[10, 7] = float("nan")

    reducer.fit(X_nan, names)
    assert reducer.is_fitted

    # Transform with NaN
    X_test = rng.randn(5, len(names))
    X_test[0, 1] = float("nan")
    result = reducer.transform(X_test)
    assert not np.any(np.isnan(result))
    assert result.shape == (5, reducer.n_features_out)


def test_save_and_load(sample_data):
    reducer = PCAReducer()
    X, names = sample_data
    reducer.fit(X, names)

    with tempfile.TemporaryDirectory() as tmpdir:
        reducer.save(tmpdir)

        reducer2 = PCAReducer()
        assert not reducer2.is_fitted
        loaded = reducer2.load(tmpdir)
        assert loaded
        assert reducer2.is_fitted
        assert reducer2.n_features_out == reducer.n_features_out

        # Outputs should match
        X_r1 = reducer.transform(X[:5])
        X_r2 = reducer2.transform(X[:5])
        np.testing.assert_array_almost_equal(X_r1, X_r2)


def test_load_missing():
    reducer = PCAReducer()
    assert not reducer.load("/nonexistent/path")
    assert not reducer.is_fitted


def test_transform_before_fit():
    reducer = PCAReducer()
    with pytest.raises(RuntimeError, match="not fitted"):
        reducer.transform(np.zeros(10))


def test_group_pca_counts(sample_data):
    """Each group should produce at least 1 and at most max_pcs components."""
    from app.features.pca_reducer import MAX_PCS_PER_GROUP

    reducer = PCAReducer()
    X, names = sample_data
    reducer.fit(X, names)

    total = 0
    for group_name, pca in reducer._group_pcas.items():
        n_components = pca.n_components_
        assert n_components >= 1
        assert n_components <= MAX_PCS_PER_GROUP.get(group_name, 3)
        total += n_components

    assert total == reducer.n_features_out
