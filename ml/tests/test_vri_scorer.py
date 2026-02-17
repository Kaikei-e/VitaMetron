import math

import pytest

from app.models.vri_scorer import (
    baseline_maturity_label,
    compute_vri,
)


def _make_baseline(**overrides):
    base = {
        "ln_rmssd_median": math.log(40.0),
        "ln_rmssd_mad": 0.3,
        "ln_rmssd_count": 50,
        "rhr_median": 62.0,
        "rhr_mad": 3.0,
        "rhr_count": 50,
        "sleep_dur_median": 420.0,
        "sleep_dur_mad": 30.0,
        "sleep_dur_count": 50,
        "sri_median": 75.0,
        "sri_mad": 5.0,
        "sri_count": 50,
        "spo2_median": 96.5,
        "spo2_mad": 0.5,
        "spo2_count": 50,
        "deep_sleep_median": 60.0,
        "deep_sleep_mad": 10.0,
        "deep_sleep_count": 50,
        "br_median": 15.0,
        "br_mad": 1.0,
        "br_count": 50,
        "window_days": 60,
        "total_valid_days": 50,
    }
    base.update(overrides)
    return base


def _make_today(**overrides):
    base = {
        "hrv_daily_rmssd": 40.0,
        "resting_hr": 62,
        "sleep_duration_min": 420,
        "spo2_avg": 96.5,
        "sleep_deep_min": 60,
        "br_full_sleep": 15.0,
    }
    base.update(overrides)
    return base


class TestComputeVRI:
    def test_all_at_median_gives_50(self):
        """All metrics at median should give VRI close to 50."""
        baseline = _make_baseline()
        today = _make_today()

        vri, conf, z_scores, factors = compute_vri(today, baseline, sri_value=75.0, quality_confidence=0.8)

        assert 48 <= vri <= 52  # Close to 50

    def test_all_metrics_above_median(self):
        """All metrics above median (in good direction) should give VRI > 50."""
        baseline = _make_baseline()
        today = _make_today(
            hrv_daily_rmssd=60.0,  # higher HRV = better
            resting_hr=55,        # lower RHR = better
            sleep_duration_min=480,
            spo2_avg=98.0,
            sleep_deep_min=80,
            br_full_sleep=13.0,   # lower BR = better
        )

        vri, _, _, _ = compute_vri(today, baseline, sri_value=85.0, quality_confidence=0.8)

        assert vri > 60

    def test_all_metrics_below_median(self):
        """All metrics in bad direction should give VRI < 50."""
        baseline = _make_baseline()
        today = _make_today(
            hrv_daily_rmssd=20.0,
            resting_hr=72,
            sleep_duration_min=300,
            spo2_avg=93.0,
            sleep_deep_min=30,
            br_full_sleep=19.0,
        )

        vri, _, _, _ = compute_vri(today, baseline, sri_value=55.0, quality_confidence=0.8)

        assert vri < 40

    def test_partial_metrics(self):
        """Should work with some metrics missing."""
        baseline = _make_baseline()
        today = _make_today(spo2_avg=None, br_full_sleep=None)

        vri, conf, z_scores, factors = compute_vri(today, baseline, sri_value=75.0, quality_confidence=0.8)

        assert 0 <= vri <= 100
        assert z_scores["z_spo2"] is None
        assert z_scores["z_br"] is None
        # Confidence should be reduced due to missing metrics
        assert conf < 0.8

    def test_no_metrics_gives_50(self):
        """No data at all should give VRI=50 with confidence=0."""
        baseline = _make_baseline()
        today = {}

        vri, conf, _, _ = compute_vri(today, baseline, quality_confidence=0.5)

        assert vri == 50.0
        assert conf == 0.0

    def test_direction_inversion_rhr(self):
        """High RHR (bad) should produce negative directed Z-score."""
        baseline = _make_baseline()
        today = _make_today(resting_hr=72)  # 10 above median

        _, _, z_scores, factors = compute_vri(today, baseline, sri_value=75.0, quality_confidence=0.8)

        # RHR z_score should be positive (above median)
        assert z_scores["z_resting_hr"] is not None
        assert z_scores["z_resting_hr"] > 0
        # But the directed_z for RHR should be negative (higher is worse)
        rhr_factors = [f for f in factors if f.metric == "resting_hr"]
        assert len(rhr_factors) == 1
        assert rhr_factors[0].directed_z < 0

    def test_direction_inversion_br(self):
        """High BR (bad) should produce negative directed Z-score."""
        baseline = _make_baseline()
        today = _make_today(br_full_sleep=19.0)  # above median

        _, _, z_scores, factors = compute_vri(today, baseline, sri_value=75.0, quality_confidence=0.8)

        br_factors = [f for f in factors if f.metric == "br"]
        assert len(br_factors) == 1
        assert br_factors[0].directed_z < 0

    def test_extreme_positive_zscores(self):
        """Extreme positive Z-scores should still produce valid 0-100 VRI."""
        baseline = _make_baseline()
        today = _make_today(
            hrv_daily_rmssd=200.0,
            resting_hr=40,
            sleep_duration_min=600,
            spo2_avg=100.0,
            sleep_deep_min=120,
            br_full_sleep=10.0,
        )

        vri, _, _, _ = compute_vri(today, baseline, sri_value=100.0, quality_confidence=1.0)

        assert 0 <= vri <= 100
        assert vri > 80

    def test_extreme_negative_zscores(self):
        """Extreme negative Z-scores should still produce valid 0-100 VRI."""
        baseline = _make_baseline()
        today = _make_today(
            hrv_daily_rmssd=5.0,
            resting_hr=100,
            sleep_duration_min=120,
            spo2_avg=85.0,
            sleep_deep_min=5,
            br_full_sleep=25.0,
        )

        vri, _, _, _ = compute_vri(today, baseline, sri_value=10.0, quality_confidence=1.0)

        assert 0 <= vri <= 100
        assert vri < 20

    def test_tanh_mapping_z0_gives_50(self):
        """Verify tanh mapping: Z=0 -> VRI=50."""
        vri = 50 + 50 * math.tanh(0 / 2)
        assert vri == 50.0

    def test_tanh_mapping_z2_gives_96(self):
        """Verify tanh mapping: Z=+2 -> VRI approx 96."""
        vri = 50 + 50 * math.tanh(2 / 2)
        assert abs(vri - 88.08) < 0.1  # tanh(1) ≈ 0.7616 → 50+38.08=88.08

    def test_factors_sorted_by_contribution(self):
        """Contributing factors should be sorted by absolute contribution."""
        baseline = _make_baseline()
        today = _make_today(
            hrv_daily_rmssd=60.0,
            resting_hr=72,
            sleep_duration_min=300,
        )

        _, _, _, factors = compute_vri(today, baseline, sri_value=75.0, quality_confidence=0.8)

        contributions = [f.contribution for f in factors]
        assert contributions == sorted(contributions, reverse=True)


class TestBaselineMaturityLabel:
    def test_cold(self):
        assert baseline_maturity_label({"total_valid_days": 5}) == "cold"
        assert baseline_maturity_label({"total_valid_days": 0}) == "cold"

    def test_warming(self):
        assert baseline_maturity_label({"total_valid_days": 14}) == "warming"
        assert baseline_maturity_label({"total_valid_days": 25}) == "warming"

    def test_warm(self):
        assert baseline_maturity_label({"total_valid_days": 30}) == "warm"
        assert baseline_maturity_label({"total_valid_days": 60}) == "warm"
