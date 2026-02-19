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

    def test_metric_none_no_floor(self):
        """Without metric name, no MAD floor is applied."""
        z = robust_zscore(97.0, 96.5, 0.5, metric=None)
        # 0.6745 * 0.5 / 0.5 = 0.6745
        assert abs(z - 0.6745) < 1e-4

    def test_spo2_mad_floor(self):
        """SpO2 should use MAD floor of 1.0 when actual MAD is smaller."""
        # Without floor: 0.6745 * 1.0 / 0.5 = 1.349
        # With floor:    0.6745 * 1.0 / 1.0 = 0.6745
        z = robust_zscore(97.5, 96.5, 0.5, metric="spo2")
        assert abs(z - 0.6745) < 1e-4

    def test_spo2_mad_above_floor(self):
        """When actual MAD exceeds the floor, the floor has no effect."""
        z_with = robust_zscore(97.5, 96.5, 1.5, metric="spo2")
        z_without = robust_zscore(97.5, 96.5, 1.5)
        assert abs(z_with - z_without) < 1e-10

    def test_unknown_metric_no_floor(self):
        """Unknown metric names should not apply any MAD floor."""
        z = robust_zscore(97.0, 96.5, 0.5, metric="resting_hr")
        # 0.6745 * 0.5 / 0.5 = 0.6745
        assert abs(z - 0.6745) < 1e-4

    def test_spo2_mad_zero_uses_floor(self):
        """SpO2 with MAD=0 should use the floor instead of returning 0."""
        z = robust_zscore(97.5, 96.5, 0.0, metric="spo2")
        # 0.6745 * 1.0 / 1.0 = 0.6745
        assert abs(z - 0.6745) < 1e-4


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

    def test_exclude_zero_filters_zeros(self):
        """With exclude_zero=True, zeros should be filtered out."""
        result = _extract_valid([0.0, 1.0, 0.0, 3.0, 0, 5.0], exclude_zero=True)
        np.testing.assert_array_equal(result, [1.0, 3.0, 5.0])

    def test_exclude_zero_false_keeps_zeros(self):
        """With exclude_zero=False (default), zeros are kept."""
        result = _extract_valid([0.0, 1.0, 0.0, 3.0])
        np.testing.assert_array_equal(result, [0.0, 1.0, 0.0, 3.0])

    def test_exclude_zero_with_transform(self):
        """Zeros should be filtered before transform is applied."""
        # math.log(0) would be -inf, but it should never be called
        result = _extract_valid([0.0, 1.0, 10.0], transform=math.log, exclude_zero=True)
        np.testing.assert_allclose(result, [math.log(1.0), math.log(10.0)])

    def test_exclude_zero_all_zeros_returns_empty(self):
        """All zeros with exclude_zero=True should return empty array."""
        result = _extract_valid([0.0, 0, 0.0], exclude_zero=True)
        assert len(result) == 0

    def test_exclude_zero_combined_with_none(self):
        """Both None and zero should be filtered."""
        result = _extract_valid([None, 0.0, 1.0, None, 0, 3.0], exclude_zero=True)
        np.testing.assert_array_equal(result, [1.0, 3.0])
