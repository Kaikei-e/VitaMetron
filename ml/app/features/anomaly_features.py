"""Anomaly detection feature extraction.

Extends the pipeline.py pattern with windowed/temporal features
to give Isolation Forest temporal awareness.
"""

import datetime
import logging
import math

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

# Ordered feature list (~20 dimensions)
ANOMALY_FEATURE_NAMES: list[str] = [
    # Current day metrics
    "resting_hr",
    "hrv_ln_rmssd",
    "sleep_duration_min",
    "sleep_deep_min",
    "spo2_avg",
    "br_full_sleep",
    "steps",
    "skin_temp_variation",
    # 7-day rolling deltas
    "resting_hr_delta",
    "hrv_delta",
    "sleep_delta",
    "steps_delta",
    "spo2_delta",
    # 3-day rolling standard deviations
    "rhr_3d_std",
    "hrv_3d_std",
    "sleep_3d_std",
    # Day-over-day change rates
    "rhr_change_rate",
    "hrv_change_rate",
    # Weekly rhythm
    "day_of_week",
]


SINGLE_DAY_QUERY = """
WITH avg_7d AS (
    SELECT
        avg(resting_hr)         AS rhr_7d,
        avg(hrv_daily_rmssd)    AS hrv_7d,
        avg(sleep_duration_min) AS sleep_7d,
        avg(steps)              AS steps_7d,
        avg(spo2_avg)           AS spo2_7d
    FROM daily_summaries
    WHERE date BETWEEN $1::date - INTERVAL '7 days' AND $1::date - INTERVAL '1 day'
),
std_3d AS (
    SELECT
        stddev_pop(resting_hr)         AS rhr_3d_std,
        stddev_pop(hrv_daily_rmssd)    AS hrv_3d_std,
        stddev_pop(sleep_duration_min) AS sleep_3d_std
    FROM daily_summaries
    WHERE date BETWEEN $1::date - INTERVAL '3 days' AND $1::date - INTERVAL '1 day'
),
prev_day AS (
    SELECT resting_hr, hrv_daily_rmssd
    FROM daily_summaries
    WHERE date = $1::date - INTERVAL '1 day'
)
SELECT
    ds.resting_hr,
    CASE WHEN ds.hrv_daily_rmssd > 0 THEN ln(ds.hrv_daily_rmssd) ELSE NULL END AS hrv_ln_rmssd,
    ds.sleep_duration_min,
    ds.sleep_deep_min,
    ds.spo2_avg,
    ds.br_full_sleep,
    ds.steps,
    ds.skin_temp_variation,
    ds.resting_hr - a.rhr_7d             AS resting_hr_delta,
    CASE WHEN ds.hrv_daily_rmssd > 0 AND a.hrv_7d > 0
         THEN ln(ds.hrv_daily_rmssd) - ln(a.hrv_7d)
         ELSE NULL END                    AS hrv_delta,
    ds.sleep_duration_min - a.sleep_7d    AS sleep_delta,
    ds.steps - a.steps_7d                AS steps_delta,
    ds.spo2_avg - a.spo2_7d             AS spo2_delta,
    s.rhr_3d_std,
    s.hrv_3d_std,
    s.sleep_3d_std,
    CASE WHEN p.resting_hr IS NOT NULL AND p.resting_hr > 0
         THEN (ds.resting_hr::real - p.resting_hr) / p.resting_hr
         ELSE NULL END                    AS rhr_change_rate,
    CASE WHEN p.hrv_daily_rmssd IS NOT NULL AND p.hrv_daily_rmssd > 0
              AND ds.hrv_daily_rmssd > 0
         THEN (ln(ds.hrv_daily_rmssd) - ln(p.hrv_daily_rmssd))
              / ln(p.hrv_daily_rmssd)
         ELSE NULL END                    AS hrv_change_rate,
    EXTRACT(DOW FROM ds.date)             AS day_of_week
FROM daily_summaries ds
CROSS JOIN avg_7d a
CROSS JOIN std_3d s
LEFT JOIN prev_day p ON TRUE
WHERE ds.date = $1::date
"""


TRAINING_QUERY = """
WITH daily_data AS (
    SELECT
        date,
        resting_hr,
        hrv_daily_rmssd,
        CASE WHEN hrv_daily_rmssd > 0 THEN ln(hrv_daily_rmssd) ELSE NULL END AS hrv_ln_rmssd,
        sleep_duration_min,
        sleep_deep_min,
        spo2_avg,
        br_full_sleep,
        steps,
        skin_temp_variation,
        -- 7-day rolling averages
        avg(resting_hr)         OVER w7 AS rhr_7d,
        avg(hrv_daily_rmssd)    OVER w7 AS hrv_7d,
        avg(sleep_duration_min) OVER w7 AS sleep_7d,
        avg(steps)              OVER w7 AS steps_7d,
        avg(spo2_avg)           OVER w7 AS spo2_7d,
        -- 3-day rolling stddev
        stddev_pop(resting_hr)         OVER w3 AS rhr_3d_std,
        stddev_pop(hrv_daily_rmssd)    OVER w3 AS hrv_3d_std,
        stddev_pop(sleep_duration_min) OVER w3 AS sleep_3d_std,
        -- Previous day values for change rate
        lag(resting_hr, 1)         OVER (ORDER BY date) AS prev_rhr,
        lag(hrv_daily_rmssd, 1)    OVER (ORDER BY date) AS prev_hrv
    FROM daily_summaries
    WINDOW
        w7 AS (ORDER BY date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING),
        w3 AS (ORDER BY date ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
)
SELECT
    d.date,
    d.resting_hr,
    d.hrv_ln_rmssd,
    d.sleep_duration_min,
    d.sleep_deep_min,
    d.spo2_avg,
    d.br_full_sleep,
    d.steps,
    d.skin_temp_variation,
    d.resting_hr - d.rhr_7d              AS resting_hr_delta,
    CASE WHEN d.hrv_daily_rmssd > 0 AND d.hrv_7d > 0
         THEN ln(d.hrv_daily_rmssd) - ln(d.hrv_7d)
         ELSE NULL END                    AS hrv_delta,
    d.sleep_duration_min - d.sleep_7d     AS sleep_delta,
    d.steps - d.steps_7d                 AS steps_delta,
    d.spo2_avg - d.spo2_7d              AS spo2_delta,
    d.rhr_3d_std,
    d.hrv_3d_std,
    d.sleep_3d_std,
    CASE WHEN d.prev_rhr IS NOT NULL AND d.prev_rhr > 0
         THEN (d.resting_hr::real - d.prev_rhr) / d.prev_rhr
         ELSE NULL END                    AS rhr_change_rate,
    CASE WHEN d.prev_hrv IS NOT NULL AND d.prev_hrv > 0
              AND d.hrv_daily_rmssd > 0
         THEN (ln(d.hrv_daily_rmssd) - ln(d.prev_hrv)) / ln(d.prev_hrv)
         ELSE NULL END                    AS hrv_change_rate,
    EXTRACT(DOW FROM d.date)              AS day_of_week,
    dq.is_valid_day
FROM daily_data d
LEFT JOIN daily_data_quality dq ON dq.date = d.date
WHERE d.date BETWEEN $1 AND $2
ORDER BY d.date
"""


async def extract_anomaly_features(
    pool: asyncpg.Pool, date: datetime.date
) -> dict | None:
    """Extract anomaly detection features for a single date.

    Returns a dict of feature_name -> value, or None if no data exists.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(SINGLE_DAY_QUERY, date)

    if row is None:
        logger.warning("No daily_summaries data for %s", date)
        return None

    features = {}
    for name in ANOMALY_FEATURE_NAMES:
        val = row.get(name)
        if val is not None:
            fval = float(val)
            features[name] = fval if math.isfinite(fval) else None
        else:
            features[name] = None

    return features


async def extract_anomaly_training_matrix(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[np.ndarray, list[str], list[datetime.date]]:
    """Extract feature matrix for training.

    Returns (X matrix, feature_names, valid_dates).
    Only includes rows where is_valid_day is True (or quality data unavailable).
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(TRAINING_QUERY, start_date, end_date)

    valid_dates: list[datetime.date] = []
    feature_rows: list[list[float]] = []

    for row in rows:
        # Skip invalid days
        is_valid = row.get("is_valid_day")
        if is_valid is not None and not is_valid:
            continue

        row_values = []
        for name in ANOMALY_FEATURE_NAMES:
            val = row.get(name)
            if val is not None:
                fval = float(val)
                row_values.append(fval if math.isfinite(fval) else float("nan"))
            else:
                row_values.append(float("nan"))

        valid_dates.append(row["date"])
        feature_rows.append(row_values)

    if not feature_rows:
        return np.empty((0, len(ANOMALY_FEATURE_NAMES))), ANOMALY_FEATURE_NAMES, []

    X = np.array(feature_rows, dtype=np.float64)
    return X, ANOMALY_FEATURE_NAMES, valid_dates
