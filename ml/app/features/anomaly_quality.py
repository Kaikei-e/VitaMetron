"""Multi-layer quality gating for anomaly detection.

Prevents false alarms from sensor failures and insufficient data.
Layers:
  1. Data completeness (reuses quality.py)
  2. Sensor artifact detection
  3. Missing value handling (in AnomalyDetector.score)
  4. Confidence scaling
"""

import logging

logger = logging.getLogger(__name__)

# Plausibility bounds aligned with api/domain/entity/plausibility.go
PLAUSIBILITY_BOUNDS = {
    "resting_hr": (30.0, 100.0),
    "hrv_ln_rmssd": (1.6, 5.7),  # ln(5) ~ 1.6, ln(300) ~ 5.7
    "sleep_duration_min": (0.0, 960.0),  # 0-16 hours
    "sleep_deep_min": (0.0, 480.0),
    "spo2_avg": (70.0, 100.0),
    "br_full_sleep": (5.0, 40.0),
    "steps": (0.0, 100000.0),
    "skin_temp_variation": (-5.0, 5.0),
}

# Metrics where 0.0 is a sentinel for "no data" (not a valid reading).
# These should be treated as missing, not as out-of-range artifacts.
ZERO_MEANS_MISSING = {
    "resting_hr", "hrv_ln_rmssd", "spo2_avg", "br_full_sleep",
}

# Minimum HR variance to detect flat-line (sensor artifact)
MIN_RHR_3D_STD = 0.5


def check_sensor_artifacts(features: dict) -> list[str]:
    """Layer 2: Detect sensor artifacts in feature values.

    Returns a list of issue descriptions. Empty list means no artifacts detected.
    """
    issues: list[str] = []

    # Check flat-line HR (very low variance over 3 days)
    rhr_std = features.get("rhr_3d_std")
    if rhr_std is not None and rhr_std < MIN_RHR_3D_STD:
        issues.append("flat_line_hr")

    # Check out-of-range values (skip zero sentinel values)
    for metric, (lo, hi) in PLAUSIBILITY_BOUNDS.items():
        val = features.get(metric)
        if val is not None and (val < lo or val > hi):
            if metric in ZERO_MEANS_MISSING and val == 0.0:
                continue  # 0.0 means data not available, not a sensor issue
            issues.append(f"out_of_range_{metric}")

    return issues


def compute_anomaly_confidence(
    quality_data: dict | None,
    features: dict,
) -> float:
    """Layer 4: Compute confidence factor for anomaly scoring.

    Combines:
      - completeness_pct from quality data
      - wear_time ratio (wear_time_hours / 24)
      - plausibility_pass flag

    Returns a float in [0, 1].
    """
    if quality_data is None:
        # No quality data available — assign moderate confidence
        return 0.5

    factors = []

    # Completeness contribution
    completeness = quality_data.get("completeness_pct")
    if completeness is not None:
        factors.append(min(1.0, completeness / 100.0))

    # Wear time contribution
    wear_hours = quality_data.get("wear_time_hours")
    if wear_hours is not None:
        factors.append(min(1.0, wear_hours / 20.0))  # 20h = full confidence

    # Plausibility contribution
    plausibility_pass = quality_data.get("plausibility_pass")
    if plausibility_pass is not None:
        factors.append(1.0 if plausibility_pass else 0.3)

    if not factors:
        return 0.5

    # Use minimum of all factors (most conservative)
    return min(factors)


async def apply_quality_gates(
    pool,
    date,
    features: dict,
) -> tuple[str, float]:
    """Apply Layer 1 + Layer 2 quality gates.

    Returns (gate_result, confidence) where gate_result is one of:
      - "pass" — all gates passed
      - "insufficient_data" — Layer 1 failed
      - "sensor_issue" — Layer 2 failed
    """
    from app.features.quality import check_minimum_compliance, get_day_quality

    # Layer 1: Data completeness
    quality_data = await get_day_quality(pool, date)

    if quality_data is not None:
        wear_hours = quality_data.get("wear_time_hours")
        if wear_hours is not None and wear_hours < 10:
            confidence = compute_anomaly_confidence(quality_data, features)
            return "insufficient_data", confidence

    compliance = await check_minimum_compliance(pool, date, window_days=7, min_valid=3)
    if not compliance:
        confidence = compute_anomaly_confidence(quality_data, features)
        return "insufficient_data", confidence

    # Layer 2: Sensor artifacts
    artifacts = check_sensor_artifacts(features)
    if artifacts:
        logger.warning("Sensor artifacts detected for %s: %s", date, artifacts)
        confidence = compute_anomaly_confidence(quality_data, features)
        return "sensor_issue", confidence

    # All gates passed
    confidence = compute_anomaly_confidence(quality_data, features)
    return "pass", confidence
