"""Divergence detection feature extraction.

Extracts paired (biometric, condition) observations for training the
Ridge regression model that predicts subjective condition from objective biometrics.
"""

import datetime
import logging
import math

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

# Features used for divergence detection (simpler than anomaly — no windowed features)
DIVERGENCE_FEATURE_NAMES: list[str] = [
    "resting_hr",
    "hrv_ln_rmssd",
    "sleep_duration_min",
    "sleep_deep_min",
    "spo2_avg",
    "br_full_sleep",
    "steps",
    "skin_temp_variation",
    "vri_score",
    "day_of_week",
]


COUNT_PAIRED_QUERY = """
SELECT COUNT(*)
FROM condition_logs cl
JOIN daily_summaries ds ON ds.date = cl.logged_at::date
LEFT JOIN daily_data_quality dq ON dq.date = ds.date
WHERE dq.is_valid_day IS NOT FALSE
"""


TRAINING_PAIRS_QUERY = """
SELECT
    ds.date,
    cl.id AS condition_log_id,
    CASE
        WHEN cl.overall_vas IS NOT NULL THEN cl.overall_vas / 20.0
        ELSE cl.overall::real
    END AS target_score,
    ds.resting_hr,
    CASE WHEN ds.hrv_daily_rmssd > 0 THEN ln(ds.hrv_daily_rmssd) ELSE NULL END AS hrv_ln_rmssd,
    ds.sleep_duration_min,
    ds.sleep_deep_min,
    ds.spo2_avg,
    ds.br_full_sleep,
    ds.steps,
    ds.skin_temp_variation,
    vs.vri_score,
    EXTRACT(DOW FROM ds.date) AS day_of_week
FROM condition_logs cl
JOIN daily_summaries ds ON ds.date = cl.logged_at::date
LEFT JOIN daily_data_quality dq ON dq.date = ds.date
LEFT JOIN vri_scores vs ON vs.date = ds.date
WHERE dq.is_valid_day IS NOT FALSE
  AND ds.date BETWEEN $1 AND $2
ORDER BY ds.date
"""


SINGLE_DAY_QUERY = """
SELECT
    ds.resting_hr,
    CASE WHEN ds.hrv_daily_rmssd > 0 THEN ln(ds.hrv_daily_rmssd) ELSE NULL END AS hrv_ln_rmssd,
    ds.sleep_duration_min,
    ds.sleep_deep_min,
    ds.spo2_avg,
    ds.br_full_sleep,
    ds.steps,
    ds.skin_temp_variation,
    vs.vri_score,
    EXTRACT(DOW FROM ds.date) AS day_of_week
FROM daily_summaries ds
LEFT JOIN vri_scores vs ON vs.date = ds.date
WHERE ds.date = $1::date
"""


async def count_paired_observations(pool: asyncpg.Pool) -> int:
    """Count dates with both a condition log and a valid daily summary."""
    async with pool.acquire() as conn:
        count = await conn.fetchval(COUNT_PAIRED_QUERY)
    return count or 0


async def extract_divergence_training_pairs(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[np.ndarray, np.ndarray, list[str], list[datetime.date], list[int]]:
    """Extract paired biometric-condition observations for training.

    Returns:
        (X_features, y_scores, feature_names, dates, condition_log_ids)
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(TRAINING_PAIRS_QUERY, start_date, end_date)

    feature_rows: list[list[float]] = []
    scores: list[float] = []
    dates: list[datetime.date] = []
    log_ids: list[int] = []

    for row in rows:
        row_values = []
        for name in DIVERGENCE_FEATURE_NAMES:
            val = row.get(name)
            if val is not None:
                fval = float(val)
                row_values.append(fval if math.isfinite(fval) else float("nan"))
            else:
                row_values.append(float("nan"))

        feature_rows.append(row_values)
        scores.append(float(row["target_score"]))
        dates.append(row["date"])
        log_ids.append(int(row["condition_log_id"]))

    if not feature_rows:
        empty_X = np.empty((0, len(DIVERGENCE_FEATURE_NAMES)))
        return empty_X, np.empty(0), DIVERGENCE_FEATURE_NAMES, [], []

    X = np.array(feature_rows, dtype=np.float64)
    y = np.array(scores, dtype=np.float64)
    return X, y, DIVERGENCE_FEATURE_NAMES, dates, log_ids


async def extract_divergence_features(
    pool: asyncpg.Pool, date: datetime.date
) -> dict | None:
    """Extract biometric features for a single date.

    Returns a dict of feature_name -> value, or None if no data.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(SINGLE_DAY_QUERY, date)

    if row is None:
        logger.warning("No daily_summaries data for %s", date)
        return None

    features = {}
    for name in DIVERGENCE_FEATURE_NAMES:
        val = row.get(name)
        if val is not None:
            fval = float(val)
            features[name] = fval if math.isfinite(fval) else None
        else:
            features[name] = None

    return features
