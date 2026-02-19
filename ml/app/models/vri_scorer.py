"""VRI (Vitality Recovery Index) composite scorer.

Combines 6 biometric dimensions into a single 0-100 score using
robust Z-score normalization and tanh mapping.

SpO2 is intentionally excluded — wearable measurement noise (±2-4%)
exceeds true biological variation (SD 0.5-1.0%), and clinical
guidelines treat SpO2 as a threshold metric, not a continuous one.
"""

import logging
import math

from app.schemas.vri import VRIMetricContribution

logger = logging.getLogger(__name__)

# Metric definitions: (key, source_field, transform, direction)
# direction: 1 = higher is better, -1 = lower is better
METRICS = [
    ("ln_rmssd", "hrv_daily_rmssd", lambda v: math.log(v), 1),
    ("resting_hr", "resting_hr", float, -1),
    ("sleep_duration", "sleep_duration_min", float, 1),
    ("sri", None, float, 1),  # computed separately
    ("deep_sleep", "sleep_deep_min", float, 1),
    ("br", "br_full_sleep", float, -1),
]

# Maximum absolute z-score for any single metric.
# Values beyond ±3 are treated as outliers (standard in medical statistics).
# Prevents any single metric from dominating the composite VRI score.
Z_CLAMP = 3.0

BASELINE_KEY_MAP = {
    "ln_rmssd": ("ln_rmssd_median", "ln_rmssd_mad"),
    "resting_hr": ("rhr_median", "rhr_mad"),
    "sleep_duration": ("sleep_dur_median", "sleep_dur_mad"),
    "sri": ("sri_median", "sri_mad"),
    "deep_sleep": ("deep_sleep_median", "deep_sleep_mad"),
    "br": ("br_median", "br_mad"),
}

# Source fields where 0 is a sentinel for "no data" (physiologically impossible)
_ZERO_IS_MISSING_FIELDS = {"hrv_daily_rmssd", "resting_hr", "br_full_sleep"}


def compute_vri(
    today_data: dict,
    baseline: dict,
    sri_value: float | None = None,
    quality_confidence: float | None = None,
) -> tuple[float, float, dict[str, float | None], list[VRIMetricContribution]]:
    """Compute VRI composite score.

    Args:
        today_data: dict with today's biometric values (from daily_summaries)
        baseline: dict with median/MAD statistics (from compute_rolling_baseline)
        sri_value: pre-computed SRI value (0-100) or None
        quality_confidence: data quality confidence score (0-1)

    Returns:
        (vri_score, vri_confidence, z_scores_dict, contributing_factors)
    """
    from app.features.zscore import robust_zscore

    z_scores: dict[str, float | None] = {}
    directed_zs: list[float] = []
    factors: list[VRIMetricContribution] = []
    metrics_included: list[str] = []

    for key, source_field, transform, direction in METRICS:
        # Get today's value
        if key == "sri":
            raw_value = sri_value
        else:
            raw_value = today_data.get(source_field)

        # Treat zero as missing for sentinel metrics
        if (
            raw_value is not None
            and source_field in _ZERO_IS_MISSING_FIELDS
            and float(raw_value) == 0.0
        ):
            raw_value = None

        if raw_value is None:
            z_scores[f"z_{key}"] = None
            continue

        # Transform the value
        try:
            value = transform(raw_value)
            if not math.isfinite(value):
                z_scores[f"z_{key}"] = None
                continue
        except (ValueError, TypeError, ZeroDivisionError):
            z_scores[f"z_{key}"] = None
            continue

        # Get baseline statistics
        med_key, mad_key = BASELINE_KEY_MAP[key]
        median = baseline.get(med_key)
        mad = baseline.get(mad_key)

        if median is None or mad is None:
            z_scores[f"z_{key}"] = None
            continue

        # Compute Z-score (pass metric name for MAD floor lookup)
        z = robust_zscore(value, median, mad, metric=key)
        z_scores[f"z_{key}"] = z

        # Apply direction (negate for "lower is better" metrics)
        # Clamp to ±Z_CLAMP to prevent any single outlier from dominating VRI
        directed_z = max(-Z_CLAMP, min(Z_CLAMP, z * direction))
        directed_zs.append(directed_z)
        metrics_included.append(key)

        factors.append(VRIMetricContribution(
            metric=key,
            z_score=round(z, 3),
            directed_z=round(directed_z, 3),
            direction="positive" if directed_z > 0 else "negative",
            contribution=abs(directed_z),
        ))

    if not directed_zs:
        return 50.0, 0.0, z_scores, []

    # Composite Z = mean of directed Z-scores (equal weighting)
    composite_z = sum(directed_zs) / len(directed_zs)

    # Map to 0-100 using tanh: VRI = 50 + 50 * tanh(composite_z / 2)
    vri_score = 50 + 50 * math.tanh(composite_z / 2)

    # Clamp to valid range
    vri_score = max(0.0, min(100.0, vri_score))

    # Confidence computation
    metric_coverage = len(directed_zs) / len(METRICS)
    baseline_maturity = _baseline_maturity_factor(baseline)
    confidence = min(
        quality_confidence if quality_confidence is not None else 1.0,
        metric_coverage,
        baseline_maturity,
    )

    # Sort factors by absolute contribution descending
    factors.sort(key=lambda f: f.contribution, reverse=True)

    return round(vri_score, 1), round(confidence, 3), z_scores, factors


def _baseline_maturity_factor(baseline: dict) -> float:
    """Compute baseline maturity as a confidence factor (0-1).

    < 14 days total → cold (low confidence)
    14-29 days → warming (medium)
    30+ days → warm (high)
    """
    total_days = baseline.get("total_valid_days", 0)
    if total_days < 14:
        return total_days / 14.0 * 0.5  # max 0.5 when cold
    if total_days < 30:
        return 0.5 + (total_days - 14) / 16.0 * 0.3  # 0.5-0.8
    return min(1.0, 0.8 + (total_days - 30) / 30.0 * 0.2)  # 0.8-1.0


def baseline_maturity_label(baseline: dict) -> str:
    """Return human-readable baseline maturity label."""
    total_days = baseline.get("total_valid_days", 0)
    if total_days < 14:
        return "cold"
    if total_days < 30:
        return "warming"
    return "warm"
