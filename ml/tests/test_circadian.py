"""Tests for circadian rhythm feature computation and scoring."""

import datetime
import math

import numpy as np
import pytest

from app.features.circadian import (
    CosinorResult,
    NPARResult,
    NocturnalDipResult,
    SleepTimingResult,
    _circular_mean_minutes,
    _circular_std_minutes,
    _sliding_window_mean,
)
from app.models.circadian_scorer import (
    OPTIMAL_DIP_PCT,
    _transform_value,
    baseline_maturity_label,
    compute_chs,
)


# ── Circular statistics tests ──────────────────────────────────────


class TestCircularMeanMinutes:
    def test_no_crossing(self):
        """Times around 3:00 AM (180 min from midnight)."""
        minutes = [170.0, 180.0, 190.0]
        mean = _circular_mean_minutes(minutes)
        assert abs(mean - 180.0) < 5.0

    def test_midnight_crossing(self):
        """Times straddling midnight: 23:30 (1410) and 00:30 (30)."""
        minutes = [1410.0, 30.0]
        mean = _circular_mean_minutes(minutes)
        # Mean should be near 0:00 (0 or 1440)
        assert mean < 60 or mean > 1380

    def test_single_value(self):
        mean = _circular_mean_minutes([120.0])
        assert abs(mean - 120.0) < 1.0

    def test_empty(self):
        assert _circular_mean_minutes([]) == 0.0


class TestCircularStdMinutes:
    def test_identical_values(self):
        std = _circular_std_minutes([180.0, 180.0, 180.0])
        assert std < 1.0

    def test_spread_values(self):
        std = _circular_std_minutes([120.0, 180.0, 240.0])
        assert std > 10.0

    def test_single_value(self):
        assert _circular_std_minutes([100.0]) == 0.0


# ── Sliding window mean tests ──────────────────────────────────────


class TestSlidingWindowMean:
    def test_basic(self):
        hourly = np.array([float(i) for i in range(24)])
        result = _sliding_window_mean(hourly, 5)
        assert len(result) == 24
        # First window (hours 0-4): mean = 2.0
        assert abs(result[0] - 2.0) < 0.01

    def test_circular_wraparound(self):
        """Window wrapping around from hour 23 to hour 2 should work."""
        hourly = np.zeros(24)
        hourly[23] = 100.0
        hourly[0] = 100.0
        hourly[1] = 100.0
        result = _sliding_window_mean(hourly, 5)
        # Window starting at 22: hours 22,23,0,1,2 = (0+100+100+100+0)/5 = 60
        assert abs(result[22] - 60.0) < 0.01


# ── Phase alignment transform tests ────────────────────────────────


class TestTransformValue:
    def test_optimal_dip(self):
        """15% dip should give 0 (optimal)."""
        assert _transform_value("phase_alignment", 15.0) == 0.0

    def test_low_dip(self):
        """5% dip → -10 (distance from optimal)."""
        assert _transform_value("phase_alignment", 5.0) == -10.0

    def test_high_dip(self):
        """25% dip → -10."""
        assert _transform_value("phase_alignment", 25.0) == -10.0

    def test_non_phase_passthrough(self):
        """Non-phase_alignment metrics pass through unchanged."""
        assert _transform_value("rhythm_strength", 7.5) == 7.5


# ── CHS Scorer tests ───────────────────────────────────────────────


class TestComputeCHS:
    def _make_baseline(self, **kwargs):
        base = {
            "amplitude_median": 10.0, "amplitude_mad": 2.0, "amplitude_count": 30,
            "is_median": 0.6, "is_mad": 0.05, "is_count": 30,
            "iv_median": 0.5, "iv_mad": 0.1, "iv_count": 30,
            "midpoint_var_median": 30.0, "midpoint_var_mad": 5.0, "midpoint_var_count": 30,
            "dip_pct_median": -2.0, "dip_pct_mad": 1.5, "dip_pct_count": 30,
            "window_days": 60,
            "total_valid_days": 30,
        }
        base.update(kwargs)
        return base

    def test_average_day(self):
        """All metrics at baseline median → CHS ≈ 50."""
        data = {
            "cosinor_amplitude": 10.0,
            "npar_is": 0.6,
            "npar_iv": 0.5,
            "sleep_midpoint_var_min": 30.0,
            "nocturnal_dip_pct": OPTIMAL_DIP_PCT + 2.0,  # → -2.0 after transform = median
        }
        baseline = self._make_baseline()
        score, confidence, z_scores, factors = compute_chs(data, baseline)
        assert 40 <= score <= 60
        assert confidence > 0

    def test_no_data(self):
        """All metrics missing → CHS = 50, confidence = 0."""
        data = {}
        baseline = self._make_baseline()
        score, confidence, z_scores, factors = compute_chs(data, baseline)
        assert score == 50.0
        assert confidence == 0.0

    def test_good_day(self):
        """Better-than-baseline values → CHS > 50."""
        data = {
            "cosinor_amplitude": 15.0,  # higher than median 10
            "npar_is": 0.8,             # higher than median 0.6
            "npar_iv": 0.3,             # lower than median 0.5 (lower is better)
            "sleep_midpoint_var_min": 15.0,  # lower than median 30 (lower is better)
            "nocturnal_dip_pct": OPTIMAL_DIP_PCT,  # exactly optimal → 0.0, better than -2.0
        }
        baseline = self._make_baseline()
        score, confidence, z_scores, factors = compute_chs(data, baseline)
        assert score > 55

    def test_bad_day(self):
        """Worse-than-baseline values → CHS < 50."""
        data = {
            "cosinor_amplitude": 5.0,   # lower
            "npar_is": 0.3,              # lower
            "npar_iv": 0.9,              # higher (worse)
            "sleep_midpoint_var_min": 60.0,  # higher (worse)
            "nocturnal_dip_pct": 2.0,    # extreme non-dipper
        }
        baseline = self._make_baseline()
        score, confidence, z_scores, factors = compute_chs(data, baseline)
        assert score < 45

    def test_partial_data(self):
        """Only some metrics available → still produces a score."""
        data = {
            "cosinor_amplitude": 12.0,
            "npar_is": 0.7,
        }
        baseline = self._make_baseline()
        score, confidence, z_scores, factors = compute_chs(data, baseline)
        assert 0 <= score <= 100
        assert len(factors) == 2


# ── Baseline maturity label tests ──────────────────────────────────


class TestBaselineMaturityLabel:
    def test_cold(self):
        assert baseline_maturity_label({"total_valid_days": 5}) == "cold"

    def test_warming(self):
        assert baseline_maturity_label({"total_valid_days": 20}) == "warming"

    def test_warm(self):
        assert baseline_maturity_label({"total_valid_days": 60}) == "warm"
