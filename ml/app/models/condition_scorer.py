import logging

from app.schemas.prediction import ContributingFactor

logger = logging.getLogger(__name__)


def rule_based_score(
    features: dict,
) -> tuple[float, float, list[ContributingFactor]]:
    """Rule-based condition scoring (v0.1 fallback).

    Returns: (predicted_score, confidence, contributing_factors)
    """
    # Quality gate: if the day is invalid, return neutral score with very low confidence
    if features.get("is_valid_day") is False:
        return 50.0, 0.1, []

    score = 50.0  # neutral baseline (VAS 0-100)
    factors: list[ContributingFactor] = []

    # HRV: higher = better recovery
    hrv = features.get("hrv_daily_rmssd")
    hrv_7d = features.get("hrv_7d")
    hrv_delta = features.get("hrv_delta")
    if hrv_delta is not None:
        if hrv_delta > 5:
            score += 6
            factors.append(ContributingFactor(
                feature="hrv",
                importance=6,
                direction="positive",
                value=float(hrv) if hrv else 0.0,
                baseline=float(hrv_7d) if hrv_7d else 0.0,
            ))
        elif hrv_delta < -10:
            score -= 10
            factors.append(ContributingFactor(
                feature="hrv",
                importance=10,
                direction="negative",
                value=float(hrv) if hrv else 0.0,
                baseline=float(hrv_7d) if hrv_7d else 0.0,
            ))

    # Sleep: 7-9 hours is ideal
    sleep_min = features.get("sleep_duration_min")
    sleep_7d = features.get("sleep_7d")
    if sleep_min is not None:
        hours = sleep_min / 60
        if 7 <= hours <= 9:
            score += 6
            factors.append(ContributingFactor(
                feature="sleep_duration",
                importance=6,
                direction="positive",
                value=float(sleep_min),
                baseline=float(sleep_7d) if sleep_7d else 0.0,
            ))
        elif hours < 5:
            score -= 16
            factors.append(ContributingFactor(
                feature="sleep_duration",
                importance=16,
                direction="negative",
                value=float(sleep_min),
                baseline=float(sleep_7d) if sleep_7d else 0.0,
            ))

    # Deep sleep quality
    deep_min = features.get("sleep_deep_min")
    deep_7d = features.get("deep_sleep_7d")
    if deep_min is not None:
        if deep_min >= 60:
            score += 4
            factors.append(ContributingFactor(
                feature="deep_sleep",
                importance=4,
                direction="positive",
                value=float(deep_min),
                baseline=float(deep_7d) if deep_7d else 0.0,
            ))
        elif deep_min < 30:
            score -= 6
            factors.append(ContributingFactor(
                feature="deep_sleep",
                importance=6,
                direction="negative",
                value=float(deep_min),
                baseline=float(deep_7d) if deep_7d else 0.0,
            ))

    # Resting HR: elevated above baseline is bad
    rhr = features.get("resting_hr")
    rhr_7d = features.get("rhr_7d")
    rhr_delta = features.get("resting_hr_delta")
    if rhr_delta is not None and rhr_delta > 5:
        score -= 8
        factors.append(ContributingFactor(
            feature="resting_hr",
            importance=8,
            direction="negative",
            value=float(rhr) if rhr else 0.0,
            baseline=float(rhr_7d) if rhr_7d else 0.0,
        ))

    # SpO2: low is a warning
    spo2 = features.get("spo2_avg")
    spo2_7d = features.get("spo2_7d")
    if spo2 is not None and spo2 < 93:
        score -= 10
        factors.append(ContributingFactor(
            feature="spo2",
            importance=10,
            direction="negative",
            value=float(spo2),
            baseline=float(spo2_7d) if spo2_7d else 0.0,
        ))

    # Steps: activity level
    steps_delta = features.get("steps_delta")
    steps = features.get("steps")
    steps_7d = features.get("steps_7d")
    if steps_delta is not None:
        if steps_delta > 3000:
            score += 4
            factors.append(ContributingFactor(
                feature="steps",
                importance=4,
                direction="positive",
                value=float(steps) if steps else 0.0,
                baseline=float(steps_7d) if steps_7d else 0.0,
            ))
        elif steps_delta < -5000:
            score -= 4
            factors.append(ContributingFactor(
                feature="steps",
                importance=4,
                direction="negative",
                value=float(steps) if steps else 0.0,
                baseline=float(steps_7d) if steps_7d else 0.0,
            ))

    score = max(0.0, min(100.0, score))
    confidence = 0.4  # rule-based = low confidence

    # Cap confidence by data quality confidence score if available
    quality_confidence = features.get("confidence_score")
    if quality_confidence is not None:
        confidence = min(confidence, float(quality_confidence))

    # Sort factors by importance descending
    factors.sort(key=lambda f: f.importance, reverse=True)

    return score, confidence, factors
