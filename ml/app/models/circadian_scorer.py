"""Circadian Health Score (CHS) composite scorer.

Combines 5 circadian rhythm dimensions into a single 0-100 score using
robust Z-score normalization and tanh mapping — same methodology as VRI.

Dimensions:
  1. Rhythm Strength   — HR cosinor amplitude (higher = stronger rhythm)
  2. Rhythm Stability   — IS, interdaily stability (higher = more consistent)
  3. Rhythm Fragmentation — IV, intradaily variability (lower = less fragmented)
  4. Sleep Regularity   — sleep midpoint variability (lower = more regular)
  5. Phase Alignment    — nocturnal HR dip optimality (closer to 15% = better)

References:
  - Cornelissen (2014), Cosinor-based rhythmometry. Theor Biol Med Model.
  - Van Someren et al. (1999), Bright light therapy. Biol Psychiatry.
  - Ohkubo et al. (2002), Nocturnal blood pressure dipping. Hypertension.
  - AHA (2025), Circadian Health in Cardiometabolic Disease. Circulation.
"""

import datetime
import logging
import math

import asyncpg
import numpy as np

from app.features.zscore import (
    MIN_BASELINE_COUNT,
    median_absolute_deviation,
    robust_zscore,
)
from app.schemas.circadian import CHSMetricContribution

logger = logging.getLogger(__name__)

# (key, direction)
# direction: 1 = higher is better, -1 = lower is better
CIRCADIAN_METRICS = [
    ("rhythm_strength", 1),       # HR cosinor amplitude
    ("rhythm_stability", 1),      # IS
    ("rhythm_fragmentation", -1), # IV
    ("sleep_regularity", -1),     # midpoint variability in min
    ("phase_alignment", 1),       # distance from optimal nocturnal dip
]

Z_CLAMP = 3.0

BASELINE_KEY_MAP = {
    "rhythm_strength": ("amplitude_median", "amplitude_mad"),
    "rhythm_stability": ("is_median", "is_mad"),
    "rhythm_fragmentation": ("iv_median", "iv_mad"),
    "sleep_regularity": ("midpoint_var_median", "midpoint_var_mad"),
    "phase_alignment": ("dip_pct_median", "dip_pct_mad"),
}

# Optimal nocturnal HR dip percentage (clinical reference: 10-20%, center=15)
OPTIMAL_DIP_PCT = 15.0

CIRCADIAN_BASELINE_QUERY = """
SELECT date, cosinor_amplitude, npar_is, npar_iv,
       sleep_midpoint_var_min, nocturnal_dip_pct
FROM circadian_scores
WHERE date BETWEEN $1::date - INTERVAL '60 days' AND $1::date - INTERVAL '1 day'
  AND cosinor_amplitude IS NOT NULL
ORDER BY date
"""


def _extract_circadian_value(
    data: dict,
    key: str,
) -> float | None:
    """Extract the raw metric value from circadian computation results."""
    mapping = {
        "rhythm_strength": "cosinor_amplitude",
        "rhythm_stability": "npar_is",
        "rhythm_fragmentation": "npar_iv",
        "sleep_regularity": "sleep_midpoint_var_min",
        "phase_alignment": "nocturnal_dip_pct",
    }
    field = mapping.get(key)
    if field is None:
        return None
    val = data.get(field)
    if val is None:
        return None
    return float(val)


def _transform_value(key: str, raw: float) -> float:
    """Apply metric-specific transforms before Z-scoring."""
    if key == "phase_alignment":
        # Distance from optimal: closer to 15% is better → negate distance
        return -abs(raw - OPTIMAL_DIP_PCT)
    return raw


async def compute_circadian_baseline(
    pool: asyncpg.Pool,
    date: datetime.date,
) -> dict:
    """Compute 60-day rolling baseline for circadian metrics."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(CIRCADIAN_BASELINE_QUERY, date)

    def _stats(values: list) -> tuple[float | None, float | None, int]:
        valid = [float(v) for v in values if v is not None]
        arr = np.array(valid)
        if len(arr) < MIN_BASELINE_COUNT:
            return None, None, len(arr)
        return float(np.median(arr)), median_absolute_deviation(arr), len(arr)

    # Extract and transform values
    amp_vals = [r["cosinor_amplitude"] for r in rows]
    is_vals = [r["npar_is"] for r in rows]
    iv_vals = [r["npar_iv"] for r in rows]
    midvar_vals = [r["sleep_midpoint_var_min"] for r in rows]
    dip_vals = [_transform_value("phase_alignment", float(r["nocturnal_dip_pct"]))
                for r in rows if r["nocturnal_dip_pct"] is not None]

    amp_med, amp_mad, amp_count = _stats(amp_vals)
    is_med, is_mad, is_count = _stats(is_vals)
    iv_med, iv_mad, iv_count = _stats(iv_vals)
    mv_med, mv_mad, mv_count = _stats(midvar_vals)
    dp_med, dp_mad, dp_count = _stats(dip_vals)

    return {
        "amplitude_median": amp_med,
        "amplitude_mad": amp_mad,
        "amplitude_count": amp_count,
        "is_median": is_med,
        "is_mad": is_mad,
        "is_count": is_count,
        "iv_median": iv_med,
        "iv_mad": iv_mad,
        "iv_count": iv_count,
        "midpoint_var_median": mv_med,
        "midpoint_var_mad": mv_mad,
        "midpoint_var_count": mv_count,
        "dip_pct_median": dp_med,
        "dip_pct_mad": dp_mad,
        "dip_pct_count": dp_count,
        "window_days": 60,
        "total_valid_days": len(rows),
    }


def compute_chs(
    circadian_data: dict,
    baseline: dict,
) -> tuple[float, float, dict[str, float | None], list[CHSMetricContribution]]:
    """Compute Circadian Health Score (CHS) composite.

    Args:
        circadian_data: dict with today's circadian metric values
        baseline: dict with median/MAD statistics from compute_circadian_baseline

    Returns:
        (chs_score, chs_confidence, z_scores_dict, contributing_factors)
    """
    z_scores: dict[str, float | None] = {}
    directed_zs: list[float] = []
    factors: list[CHSMetricContribution] = []

    for key, direction in CIRCADIAN_METRICS:
        raw_value = _extract_circadian_value(circadian_data, key)
        if raw_value is None:
            z_scores[f"z_{key}"] = None
            continue

        # Apply metric-specific transform
        value = _transform_value(key, raw_value)

        # Get baseline statistics
        med_key, mad_key = BASELINE_KEY_MAP[key]
        median = baseline.get(med_key)
        mad = baseline.get(mad_key)

        if median is None or mad is None:
            z_scores[f"z_{key}"] = None
            continue

        z = robust_zscore(value, median, mad)
        z_scores[f"z_{key}"] = z

        directed_z = max(-Z_CLAMP, min(Z_CLAMP, z * direction))
        directed_zs.append(directed_z)

        factors.append(CHSMetricContribution(
            metric=key,
            z_score=round(z, 3),
            directed_z=round(directed_z, 3),
            direction="positive" if directed_z > 0 else "negative",
            contribution=abs(directed_z),
        ))

    if not directed_zs:
        return 50.0, 0.0, z_scores, []

    composite_z = sum(directed_zs) / len(directed_zs)
    chs_score = 50 + 50 * math.tanh(composite_z / 2)
    chs_score = max(0.0, min(100.0, chs_score))

    # Confidence
    metric_coverage = len(directed_zs) / len(CIRCADIAN_METRICS)
    baseline_maturity = _baseline_maturity_factor(baseline)
    confidence = min(metric_coverage, baseline_maturity)

    factors.sort(key=lambda f: f.contribution, reverse=True)

    return round(chs_score, 1), round(confidence, 3), z_scores, factors


def _baseline_maturity_factor(baseline: dict) -> float:
    """Compute baseline maturity as a confidence factor (0-1)."""
    total_days = baseline.get("total_valid_days", 0)
    if total_days < 14:
        return total_days / 14.0 * 0.5
    if total_days < 30:
        return 0.5 + (total_days - 14) / 16.0 * 0.3
    return min(1.0, 0.8 + (total_days - 30) / 30.0 * 0.2)


def baseline_maturity_label(baseline: dict) -> str:
    """Return human-readable baseline maturity label."""
    total_days = baseline.get("total_valid_days", 0)
    if total_days < 14:
        return "cold"
    if total_days < 30:
        return "warming"
    return "warm"
