"""Tests for anomaly explanation generation."""

from app.models.anomaly_explainer import (
    AnomalyFeatureContribution,
    generate_explanation,
)


def test_generate_explanation_basic():
    shap_values = {
        "resting_hr": -0.05,
        "hrv_ln_rmssd": -0.02,
        "sleep_duration_min": 0.01,
        "spo2_avg": -0.03,
    }
    features = {
        "resting_hr": 72.0,
        "hrv_ln_rmssd": 3.5,
        "sleep_duration_min": 420.0,
        "spo2_avg": 94.0,
    }

    summary, contributions = generate_explanation(shap_values, features)

    assert isinstance(summary, str)
    assert len(contributions) == 4
    # Should be sorted by |shap_value| descending
    assert abs(contributions[0].shap_value) >= abs(contributions[1].shap_value)


def test_generate_explanation_with_baseline():
    shap_values = {"resting_hr": -0.05}
    features = {"resting_hr": 72.0}
    baseline = {"resting_hr": 60.0}

    summary, contributions = generate_explanation(shap_values, features, baseline)

    assert "12.0 above typical" in contributions[0].description


def test_generate_explanation_no_anomalous_drivers():
    shap_values = {
        "resting_hr": 0.05,
        "sleep_duration_min": 0.03,
    }
    features = {
        "resting_hr": 60.0,
        "sleep_duration_min": 480.0,
    }

    summary, contributions = generate_explanation(shap_values, features)

    assert "No strong anomaly drivers" in summary


def test_generate_explanation_single_driver():
    shap_values = {
        "resting_hr": -0.1,
        "sleep_duration_min": 0.02,
    }
    features = {
        "resting_hr": 85.0,
        "sleep_duration_min": 480.0,
    }

    summary, contributions = generate_explanation(shap_values, features)

    assert "main driver" in summary
    assert "combined with" not in summary


def test_generate_explanation_two_drivers():
    shap_values = {
        "resting_hr": -0.1,
        "spo2_avg": -0.08,
        "sleep_duration_min": 0.02,
    }
    features = {
        "resting_hr": 85.0,
        "spo2_avg": 93.0,
        "sleep_duration_min": 480.0,
    }

    summary, contributions = generate_explanation(shap_values, features)

    assert "main driver" in summary
    assert "combined with" in summary


def test_contribution_direction():
    shap_values = {
        "resting_hr": -0.05,  # anomalous
        "sleep_duration_min": 0.03,  # normal
        "day_of_week": 0.0,  # neutral
    }
    features = {
        "resting_hr": 72.0,
        "sleep_duration_min": 480.0,
        "day_of_week": 3.0,
    }

    _, contributions = generate_explanation(shap_values, features)

    by_name = {c.feature: c for c in contributions}
    assert by_name["resting_hr"].direction == "anomalous"
    assert by_name["sleep_duration_min"].direction == "normal"
    assert by_name["day_of_week"].direction == "neutral"


def test_missing_feature_value():
    shap_values = {"resting_hr": -0.05}
    features = {"resting_hr": None}

    _, contributions = generate_explanation(shap_values, features)

    assert "not available" in contributions[0].description


def test_unknown_feature_skipped():
    shap_values = {"unknown_feature": -0.05}
    features = {"unknown_feature": 42.0}

    _, contributions = generate_explanation(shap_values, features)

    assert len(contributions) == 0
