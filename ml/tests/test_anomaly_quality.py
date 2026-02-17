"""Tests for anomaly quality gating."""

import pytest

from app.features.anomaly_quality import (
    check_sensor_artifacts,
    compute_anomaly_confidence,
)


class TestCheckSensorArtifacts:
    def test_no_artifacts(self):
        features = {
            "resting_hr": 60.0,
            "rhr_3d_std": 3.0,
            "spo2_avg": 97.0,
        }
        assert check_sensor_artifacts(features) == []

    def test_flat_line_hr(self):
        features = {"rhr_3d_std": 0.1}
        issues = check_sensor_artifacts(features)
        assert "flat_line_hr" in issues

    def test_out_of_range_resting_hr_high(self):
        features = {"resting_hr": 120.0, "rhr_3d_std": 5.0}
        issues = check_sensor_artifacts(features)
        assert "out_of_range_resting_hr" in issues

    def test_out_of_range_resting_hr_low(self):
        features = {"resting_hr": 20.0, "rhr_3d_std": 5.0}
        issues = check_sensor_artifacts(features)
        assert "out_of_range_resting_hr" in issues

    def test_out_of_range_spo2(self):
        features = {"spo2_avg": 60.0, "rhr_3d_std": 5.0}
        issues = check_sensor_artifacts(features)
        assert "out_of_range_spo2_avg" in issues

    def test_missing_values_ignored(self):
        features = {"resting_hr": None, "rhr_3d_std": None}
        assert check_sensor_artifacts(features) == []


class TestComputeAnomalyConfidence:
    def test_no_quality_data(self):
        assert compute_anomaly_confidence(None, {}) == 0.5

    def test_full_confidence(self):
        quality = {
            "completeness_pct": 100.0,
            "wear_time_hours": 22.0,
            "plausibility_pass": True,
        }
        conf = compute_anomaly_confidence(quality, {})
        assert conf == 1.0

    def test_low_completeness(self):
        quality = {
            "completeness_pct": 40.0,
            "wear_time_hours": 22.0,
            "plausibility_pass": True,
        }
        conf = compute_anomaly_confidence(quality, {})
        assert conf == 0.4

    def test_low_wear_time(self):
        quality = {
            "completeness_pct": 100.0,
            "wear_time_hours": 10.0,
            "plausibility_pass": True,
        }
        conf = compute_anomaly_confidence(quality, {})
        assert conf == 0.5  # 10/20

    def test_plausibility_fail(self):
        quality = {
            "completeness_pct": 100.0,
            "wear_time_hours": 22.0,
            "plausibility_pass": False,
        }
        conf = compute_anomaly_confidence(quality, {})
        assert conf == 0.3

    def test_empty_quality_fields(self):
        quality = {}
        conf = compute_anomaly_confidence(quality, {})
        assert conf == 0.5  # fallback
