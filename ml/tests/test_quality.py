"""Tests for quality gating in the ML layer."""

from app.models.condition_scorer import rule_based_score
from app.models.risk_detector import detect_risks


def _base_features(**overrides):
    features = {
        "resting_hr": 62,
        "hrv_daily_rmssd": 45.0,
        "spo2_avg": 97.0,
        "sleep_duration_min": 450,
        "sleep_deep_min": 65,
        "steps": 8000,
        "rhr_7d": 60.0,
        "hrv_7d": 42.0,
        "sleep_7d": 430.0,
        "steps_7d": 8000.0,
        "spo2_7d": 97.0,
        "deep_sleep_7d": 60.0,
        "br_full_sleep": 15.0,
        "resting_hr_delta": 2.0,
        "hrv_delta": 3.0,
        "sleep_delta": 20.0,
        "steps_delta": 0.0,
        "spo2_delta": 0.0,
        "spo2_min": 94.0,
    }
    features.update(overrides)
    return features


class TestQualityGatedScoring:
    def test_invalid_day_returns_neutral_score(self):
        features = _base_features(is_valid_day=False)
        score, confidence, factors = rule_based_score(features)
        assert score == 3.0
        assert confidence == 0.1
        assert factors == []

    def test_valid_day_scores_normally(self):
        features = _base_features(is_valid_day=True, confidence_score=0.8)
        score, confidence, factors = rule_based_score(features)
        assert score != 3.0 or len(factors) > 0
        assert confidence <= 0.8

    def test_confidence_capped_by_quality(self):
        features = _base_features(
            is_valid_day=True,
            confidence_score=0.3,
            hrv_delta=8.0,
        )
        _, confidence, _ = rule_based_score(features)
        assert confidence <= 0.3

    def test_missing_quality_fields_defaults_to_normal(self):
        features = _base_features()
        # No is_valid_day or confidence_score keys
        if "is_valid_day" in features:
            del features["is_valid_day"]
        if "confidence_score" in features:
            del features["confidence_score"]
        score, confidence, _ = rule_based_score(features)
        assert 1.0 <= score <= 5.0
        assert confidence == 0.4  # default rule-based confidence


class TestQualityGatedRiskDetection:
    def test_invalid_day_suppresses_risks(self):
        features = _base_features(
            is_valid_day=False,
            hrv_delta=-20.0,
            resting_hr_delta=10.0,
            spo2_min=85.0,
        )
        risks = detect_risks(features)
        assert risks == []

    def test_valid_day_detects_risks(self):
        features = _base_features(
            is_valid_day=True,
            hrv_delta=-20.0,
            resting_hr_delta=10.0,
            spo2_min=85.0,
        )
        risks = detect_risks(features)
        assert len(risks) >= 3

    def test_missing_validity_defaults_to_detecting(self):
        features = _base_features(hrv_delta=-20.0)
        if "is_valid_day" in features:
            del features["is_valid_day"]
        risks = detect_risks(features)
        assert "hrv_significant_drop" in risks
