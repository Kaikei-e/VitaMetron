"""Robust Z-score computation using median/MAD normalization.

Uses 60-day rolling baseline with median and MAD (Median Absolute Deviation)
for outlier-resistant normalization of biometric metrics.
"""

import datetime
import logging
import math

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

BASELINE_QUERY = """
SELECT ds.date, ds.hrv_daily_rmssd, ds.resting_hr, ds.sleep_duration_min,
       ds.spo2_avg, ds.sleep_deep_min, ds.br_full_sleep
FROM daily_summaries ds
LEFT JOIN daily_data_quality dq ON dq.date = ds.date
WHERE ds.date BETWEEN $1::date - INTERVAL '60 days' AND $1::date - INTERVAL '1 day'
  AND (dq.is_valid_day IS NULL OR dq.is_valid_day = TRUE)
ORDER BY ds.date
"""


def median_absolute_deviation(values: np.ndarray) -> float:
    """Compute the Median Absolute Deviation (MAD).

    MAD = median(|Xi - median(X)|)
    """
    if len(values) == 0:
        return 0.0
    med = np.median(values)
    return float(np.median(np.abs(values - med)))


def robust_zscore(value: float, median: float, mad: float) -> float:
    """Compute robust Z-score using median/MAD normalization.

    Formula: 0.6745 * (Xi - Median) / MAD

    The constant 0.6745 makes MAD consistent with standard deviation
    for normally distributed data.

    Returns 0.0 if MAD is 0 (all values identical).
    """
    if mad == 0.0:
        return 0.0
    return 0.6745 * (value - median) / mad


def _extract_valid(values: list, transform=None) -> np.ndarray:
    """Extract non-None values, optionally applying a transform."""
    result = []
    for v in values:
        if v is not None:
            try:
                val = transform(v) if transform else float(v)
                if math.isfinite(val):
                    result.append(val)
            except (ValueError, TypeError):
                continue
    return np.array(result)


async def compute_rolling_baseline(
    pool: asyncpg.Pool,
    date: datetime.date,
    window_days: int = 60,
) -> dict:
    """Compute 60-day rolling baseline statistics (median/MAD) per metric.

    Returns dict with keys like 'ln_rmssd_median', 'ln_rmssd_mad', 'ln_rmssd_count', etc.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(BASELINE_QUERY, date)

    # Extract values per metric
    hrv_vals = [r["hrv_daily_rmssd"] for r in rows]
    rhr_vals = [r["resting_hr"] for r in rows]
    sleep_dur_vals = [r["sleep_duration_min"] for r in rows]
    spo2_vals = [r["spo2_avg"] for r in rows]
    deep_sleep_vals = [r["sleep_deep_min"] for r in rows]
    br_vals = [r["br_full_sleep"] for r in rows]

    def _stats(values: np.ndarray) -> tuple[float | None, float | None, int]:
        if len(values) == 0:
            return None, None, 0
        return float(np.median(values)), median_absolute_deviation(values), len(values)

    # ln(RMSSD) transform
    ln_rmssd = _extract_valid(hrv_vals, transform=lambda v: math.log(float(v)))
    ln_med, ln_mad, ln_count = _stats(ln_rmssd)

    rhr = _extract_valid(rhr_vals)
    rhr_med, rhr_mad, rhr_count = _stats(rhr)

    sleep_dur = _extract_valid(sleep_dur_vals)
    sd_med, sd_mad, sd_count = _stats(sleep_dur)

    spo2 = _extract_valid(spo2_vals)
    spo2_med, spo2_mad, spo2_count = _stats(spo2)

    deep_sleep = _extract_valid(deep_sleep_vals)
    ds_med, ds_mad, ds_count = _stats(deep_sleep)

    br = _extract_valid(br_vals)
    br_med, br_mad, br_count = _stats(br)

    return {
        "ln_rmssd_median": ln_med,
        "ln_rmssd_mad": ln_mad,
        "ln_rmssd_count": ln_count,
        "rhr_median": rhr_med,
        "rhr_mad": rhr_mad,
        "rhr_count": rhr_count,
        "sleep_dur_median": sd_med,
        "sleep_dur_mad": sd_mad,
        "sleep_dur_count": sd_count,
        "sri_median": None,  # filled by caller after SRI computation
        "sri_mad": None,
        "sri_count": 0,
        "spo2_median": spo2_med,
        "spo2_mad": spo2_mad,
        "spo2_count": spo2_count,
        "deep_sleep_median": ds_med,
        "deep_sleep_mad": ds_mad,
        "deep_sleep_count": ds_count,
        "br_median": br_med,
        "br_mad": br_mad,
        "br_count": br_count,
        "window_days": window_days,
        "total_valid_days": len(rows),
    }
