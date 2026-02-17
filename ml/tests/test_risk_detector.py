import pytest

from app.models.risk_detector import detect_risks


def _base_features(**overrides):
    features = {
        "resting_hr": 62,
        "hrv_daily_rmssd": 45.0,
        "spo2_avg": 97.0,
        "spo2_min": 94.0,
        "sleep_duration_min": 450,
        "sleep_deep_min": 65,
        "steps": 8000,
        "rhr_7d": 60.0,
        "hrv_7d": 42.0,
        "sleep_7d": 430.0,
        "steps_7d": 8000.0,
        "spo2_7d": 97.0,
        "br_full_sleep": 15.0,
        "resting_hr_delta": 2.0,
        "hrv_delta": 3.0,
    }
    features.update(overrides)
    return features


class TestDetectRisks:
    def test_no_risks_for_healthy_metrics(self):
        risks = detect_risks(_base_features())
        assert risks == []

    def test_hrv_significant_drop(self):
        risks = detect_risks(_base_features(hrv_delta=-16.0))
        assert "hrv_significant_drop" in risks

    def test_hrv_no_trigger_at_threshold(self):
        risks = detect_risks(_base_features(hrv_delta=-15.0))
        assert "hrv_significant_drop" not in risks

    def test_rhr_elevated(self):
        risks = detect_risks(_base_features(resting_hr_delta=9.0))
        assert "rhr_elevated" in risks

    def test_rhr_no_trigger_at_threshold(self):
        risks = detect_risks(_base_features(resting_hr_delta=8.0))
        assert "rhr_elevated" not in risks

    def test_sleep_deficit(self):
        risks = detect_risks(_base_features(sleep_7d=350.0))
        assert "sleep_deficit" in risks

    def test_spo2_low(self):
        risks = detect_risks(_base_features(spo2_min=88.0))
        assert "spo2_low" in risks

    def test_deep_sleep_low(self):
        risks = detect_risks(_base_features(sleep_deep_min=25))
        assert "deep_sleep_low" in risks

    def test_severe_sleep_deprivation(self):
        risks = detect_risks(_base_features(sleep_duration_min=200))
        assert "severe_sleep_deprivation" in risks

    def test_breathing_rate_elevated(self):
        risks = detect_risks(_base_features(br_full_sleep=22.0))
        assert "breathing_rate_elevated" in risks

    def test_multiple_risks(self):
        risks = detect_risks(_base_features(
            hrv_delta=-20.0,
            resting_hr_delta=10.0,
            spo2_min=85.0,
        ))
        assert len(risks) >= 3

    def test_empty_features(self):
        risks = detect_risks({})
        assert risks == []

    def test_none_values_no_trigger(self):
        features = {
            "hrv_delta": None,
            "resting_hr_delta": None,
            "sleep_7d": None,
            "spo2_min": None,
            "sleep_deep_min": None,
            "sleep_duration_min": None,
            "br_full_sleep": None,
        }
        risks = detect_risks(features)
        assert risks == []
