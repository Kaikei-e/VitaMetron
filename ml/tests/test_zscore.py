import math

import numpy as np
import pytest

from app.features.zscore import (
    _extract_valid,
    median_absolute_deviation,
    robust_zscore,
)


class TestMedianAbsoluteDeviation:
    def test_basic(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        # median = 3.0
        # |1-3|=2, |2-3|=1, |3-3|=0, |4-3|=1, |5-3|=2
        # MAD = median([0, 1, 1, 2, 2]) = 1.0
        assert median_absolute_deviation(values) == 1.0

    def test_all_identical(self):
        """All identical values should give MAD=0."""
        values = np.array([5.0, 5.0, 5.0, 5.0])
        assert median_absolute_deviation(values) == 0.0

    def test_empty(self):
        assert median_absolute_deviation(np.array([])) == 0.0

    def test_single_value(self):
        assert median_absolute_deviation(np.array([42.0])) == 0.0

    def test_known_result(self):
        """Reference computation against known values."""
        values = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        # median = 6.0
        # |2-6|=4, |4-6|=2, |6-6|=0, |8-6|=2, |10-6|=4
        # MAD = median([0, 2, 2, 4, 4]) = 2.0
        assert median_absolute_deviation(values) == 2.0

    def test_matches_numpy_reference(self):
        """Cross-check with manual numpy computation."""
        rng = np.random.default_rng(42)
        values = rng.normal(50, 10, size=100)
        med = np.median(values)
        expected_mad = float(np.median(np.abs(values - med)))
        assert abs(median_absolute_deviation(values) - expected_mad) < 1e-10


class TestRobustZscore:
    def test_at_median(self):
        """Value at median should have Z=0."""
        assert robust_zscore(50.0, 50.0, 5.0) == 0.0

    def test_positive_deviation(self):
        """Value above median should have positive Z."""
        z = robust_zscore(55.0, 50.0, 5.0)
        assert z > 0
        # 0.6745 * (55 - 50) / 5 = 0.6745 * 1.0 = 0.6745
        assert abs(z - 0.6745) < 1e-4

    def test_negative_deviation(self):
        """Value below median should have negative Z."""
        z = robust_zscore(45.0, 50.0, 5.0)
        assert z < 0
        assert abs(z - (-0.6745)) < 1e-4

    def test_mad_zero_returns_zero(self):
        """MAD=0 (all identical values) should return Z=0."""
        assert robust_zscore(100.0, 50.0, 0.0) == 0.0

    def test_large_deviation(self):
        """Large deviation should give large Z."""
        z = robust_zscore(70.0, 50.0, 5.0)
        # 0.6745 * 20 / 5 = 0.6745 * 4 = 2.698
        assert abs(z - 2.698) < 0.01


class TestExtractValid:
    def test_filters_none(self):
        result = _extract_valid([1.0, None, 3.0, None, 5.0])
        np.testing.assert_array_equal(result, [1.0, 3.0, 5.0])

    def test_with_transform(self):
        result = _extract_valid([1.0, 10.0, 100.0], transform=math.log)
        expected = [math.log(1.0), math.log(10.0), math.log(100.0)]
        np.testing.assert_allclose(result, expected)

    def test_empty_list(self):
        result = _extract_valid([])
        assert len(result) == 0

    def test_all_none(self):
        result = _extract_valid([None, None, None])
        assert len(result) == 0

    def test_ln_rmssd_transform(self):
        """Verify ln(RMSSD) transform correctness."""
        rmssd_values = [20.0, 40.0, 60.0]
        result = _extract_valid(rmssd_values, transform=lambda v: math.log(float(v)))
        expected = [math.log(20), math.log(40), math.log(60)]
        np.testing.assert_allclose(result, expected)
