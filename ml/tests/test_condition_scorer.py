import pytest

from app.models.condition_scorer import rule_based_score


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
        "resting_hr_delta": 2.0,
        "hrv_delta": 3.0,
        "sleep_delta": 20.0,
        "steps_delta": 0.0,
        "spo2_delta": 0.0,
    }
    features.update(overrides)
    return features


class TestRuleBasedScore:
    def test_baseline_returns_moderate_score(self):
        """Neutral features should give score around 3.0."""
        features = _base_features(hrv_delta=0, steps_delta=0)
        score, confidence, factors = rule_based_score(features)
        assert 2.5 <= score <= 4.0
        assert confidence == 0.4

    def test_good_hrv_increases_score(self):
        features = _base_features(hrv_delta=8.0)
        score, _, factors = rule_based_score(features)
        assert score > 3.0
        hrv_factors = [f for f in factors if f.feature == "hrv"]
        assert len(hrv_factors) == 1
        assert hrv_factors[0].direction == "positive"

    def test_bad_hrv_decreases_score(self):
        features = _base_features(hrv_delta=-12.0)
        score, _, factors = rule_based_score(features)
        hrv_factors = [f for f in factors if f.feature == "hrv"]
        assert len(hrv_factors) == 1
        assert hrv_factors[0].direction == "negative"

    def test_good_sleep_increases_score(self):
        features = _base_features(sleep_duration_min=480)  # 8 hours
        score, _, factors = rule_based_score(features)
        sleep_factors = [f for f in factors if f.feature == "sleep_duration"]
        assert len(sleep_factors) == 1
        assert sleep_factors[0].direction == "positive"

    def test_poor_sleep_decreases_score(self):
        features = _base_features(sleep_duration_min=240)  # 4 hours
        score, _, _ = rule_based_score(features)
        assert score < 3.0

    def test_low_spo2_decreases_score(self):
        features = _base_features(spo2_avg=91.0)
        score, _, factors = rule_based_score(features)
        spo2_factors = [f for f in factors if f.feature == "spo2"]
        assert len(spo2_factors) == 1
        assert spo2_factors[0].direction == "negative"

    def test_elevated_rhr_decreases_score(self):
        features = _base_features(resting_hr_delta=7.0)
        score, _, factors = rule_based_score(features)
        rhr_factors = [f for f in factors if f.feature == "resting_hr"]
        assert len(rhr_factors) == 1
        assert rhr_factors[0].direction == "negative"

    def test_score_clamped_min(self):
        """Score should not go below 1.0."""
        features = _base_features(
            hrv_delta=-15.0,
            sleep_duration_min=180,
            spo2_avg=88.0,
            resting_hr_delta=10.0,
            sleep_deep_min=10,
            steps_delta=-8000,
        )
        score, _, _ = rule_based_score(features)
        assert score >= 1.0

    def test_score_clamped_max(self):
        """Score should not go above 5.0."""
        features = _base_features(
            hrv_delta=20.0,
            sleep_duration_min=510,
            sleep_deep_min=90,
            steps_delta=5000,
        )
        score, _, _ = rule_based_score(features)
        assert score <= 5.0

    def test_empty_features_returns_baseline(self):
        """Empty features should give baseline score 3.0."""
        score, confidence, factors = rule_based_score({})
        assert score == 3.0
        assert confidence == 0.4
        assert factors == []

    def test_none_values_handled(self):
        """None values should be safely skipped."""
        features = {
            "hrv_delta": None,
            "sleep_duration_min": None,
            "resting_hr_delta": None,
            "spo2_avg": None,
            "steps_delta": None,
            "sleep_deep_min": None,
        }
        score, _, _ = rule_based_score(features)
        assert score == 3.0

    def test_factors_sorted_by_importance(self):
        features = _base_features(
            hrv_delta=-12.0,        # importance=0.5
            sleep_duration_min=240,  # importance=0.8
            steps_delta=4000,        # importance=0.2
        )
        _, _, factors = rule_based_score(features)
        importances = [f.importance for f in factors]
        assert importances == sorted(importances, reverse=True)
