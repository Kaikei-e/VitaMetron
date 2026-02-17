"""HRV prediction feature extraction.

Builds feature vectors for next-morning HRV Z-score prediction.
Follows the anomaly_features.py pattern with SQL-based extraction.
"""

import datetime
import logging
import math

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

# Ordered feature list (~25 dimensions)
HRV_FEATURE_NAMES: list[str] = [
    # Current day metrics
    "resting_hr",
    "hrv_ln_rmssd",
    "sleep_duration_min",
    "sleep_deep_min",
    "sleep_rem_min",
    "spo2_avg",
    "br_full_sleep",
    "steps",
    "calories_active",
    "active_zone_min",
    "skin_temp_variation",
    # 7-day rolling deltas (vs 7d avg)
    "resting_hr_delta",
    "hrv_delta",
    "sleep_delta",
    "steps_delta",
    "spo2_delta",
    # 3-day rolling std devs
    "rhr_3d_std",
    "hrv_3d_std",
    "sleep_3d_std",
    # Day-over-day change rates
    "rhr_change_rate",
    "hrv_change_rate",
    # Temporal (sin/cos encoded day of week)
    "dow_sin",
    "dow_cos",
    # Personal Z-scores (60-day rolling baseline)
    "z_rhr",
    "z_hrv",
    "z_sleep_dur",
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
),
baseline_60d AS (
    SELECT
        percentile_cont(0.5) WITHIN GROUP (ORDER BY resting_hr)
            FILTER (WHERE resting_hr IS NOT NULL)             AS rhr_median,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY abs(resting_hr - sub.rhr_med))
            FILTER (WHERE resting_hr IS NOT NULL)             AS rhr_mad,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY ln(hrv_daily_rmssd))
            FILTER (WHERE hrv_daily_rmssd > 0)                AS hrv_median,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY abs(ln(hrv_daily_rmssd) - sub.hrv_med))
            FILTER (WHERE hrv_daily_rmssd > 0)                AS hrv_mad,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY sleep_duration_min)
            FILTER (WHERE sleep_duration_min IS NOT NULL)     AS sleep_median,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY abs(sleep_duration_min - sub.sleep_med))
            FILTER (WHERE sleep_duration_min IS NOT NULL)     AS sleep_mad
    FROM daily_summaries ds,
    LATERAL (
        SELECT
            percentile_cont(0.5) WITHIN GROUP (ORDER BY resting_hr)
                FILTER (WHERE resting_hr IS NOT NULL) AS rhr_med,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY ln(hrv_daily_rmssd))
                FILTER (WHERE hrv_daily_rmssd > 0)    AS hrv_med,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY sleep_duration_min)
                FILTER (WHERE sleep_duration_min IS NOT NULL) AS sleep_med
        FROM daily_summaries
        WHERE date BETWEEN $1::date - INTERVAL '60 days' AND $1::date - INTERVAL '1 day'
    ) sub
    WHERE ds.date BETWEEN $1::date - INTERVAL '60 days' AND $1::date - INTERVAL '1 day'
)
SELECT
    ds.resting_hr,
    CASE WHEN ds.hrv_daily_rmssd > 0 THEN ln(ds.hrv_daily_rmssd) ELSE NULL END AS hrv_ln_rmssd,
    ds.sleep_duration_min,
    ds.sleep_deep_min,
    ds.sleep_rem_min,
    ds.spo2_avg,
    ds.br_full_sleep,
    ds.steps,
    ds.calories_active,
    ds.active_zone_min,
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
    sin(2 * pi() * EXTRACT(DOW FROM ds.date) / 7.0)  AS dow_sin,
    cos(2 * pi() * EXTRACT(DOW FROM ds.date) / 7.0)  AS dow_cos,
    CASE WHEN b.rhr_mad > 0 AND ds.resting_hr IS NOT NULL
         THEN 0.6745 * (ds.resting_hr - b.rhr_median) / b.rhr_mad
         ELSE NULL END                    AS z_rhr,
    CASE WHEN b.hrv_mad > 0 AND ds.hrv_daily_rmssd > 0
         THEN 0.6745 * (ln(ds.hrv_daily_rmssd) - b.hrv_median) / b.hrv_mad
         ELSE NULL END                    AS z_hrv,
    CASE WHEN b.sleep_mad > 0 AND ds.sleep_duration_min IS NOT NULL
         THEN 0.6745 * (ds.sleep_duration_min - b.sleep_median) / b.sleep_mad
         ELSE NULL END                    AS z_sleep_dur
FROM daily_summaries ds
CROSS JOIN avg_7d a
CROSS JOIN std_3d s
LEFT JOIN prev_day p ON TRUE
CROSS JOIN baseline_60d b
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
        sleep_rem_min,
        spo2_avg,
        br_full_sleep,
        steps,
        calories_active,
        active_zone_min,
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
        lag(hrv_daily_rmssd, 1)    OVER (ORDER BY date) AS prev_hrv,
        -- Next-day HRV for target variable
        lead(hrv_daily_rmssd, 1)   OVER (ORDER BY date) AS next_hrv
    FROM daily_summaries
    WINDOW
        w7 AS (ORDER BY date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING),
        w3 AS (ORDER BY date ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
),
-- Approximate MAD using stddev for rolling windows
-- (exact MAD via window is complex; σ * 0.6745 ≈ MAD for normal data)
daily_with_mad AS (
    SELECT d.*,
        stddev_pop(resting_hr) OVER (ORDER BY date ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING)
            * 0.6745  AS rhr_60d_mad_approx,
        stddev_pop(sleep_duration_min) OVER (ORDER BY date ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING)
            * 0.6745  AS sleep_60d_mad_approx,
        stddev_pop(CASE WHEN hrv_daily_rmssd > 0 THEN ln(hrv_daily_rmssd) END)
            OVER (ORDER BY date ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING)
            * 0.6745  AS hrv_14d_mad_approx
    FROM daily_data d
)
SELECT
    d.date,
    d.resting_hr,
    d.hrv_ln_rmssd,
    d.sleep_duration_min,
    d.sleep_deep_min,
    d.sleep_rem_min,
    d.spo2_avg,
    d.br_full_sleep,
    d.steps,
    d.calories_active,
    d.active_zone_min,
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
    sin(2 * pi() * EXTRACT(DOW FROM d.date) / 7.0) AS dow_sin,
    cos(2 * pi() * EXTRACT(DOW FROM d.date) / 7.0) AS dow_cos,
    -- Personal Z-scores using rolling baselines (LATERAL for rolling medians)
    CASE WHEN d.rhr_60d_mad_approx > 0 AND d.resting_hr IS NOT NULL
         THEN 0.6745 * (d.resting_hr - med60.rhr_60d_median) / d.rhr_60d_mad_approx
         ELSE NULL END                    AS z_rhr,
    CASE WHEN d.hrv_daily_rmssd > 0 AND d.hrv_14d_mad_approx > 0
         THEN 0.6745 * (ln(d.hrv_daily_rmssd) - med14.hrv_14d_median) / d.hrv_14d_mad_approx
         ELSE NULL END                    AS z_hrv,
    CASE WHEN d.sleep_60d_mad_approx > 0 AND d.sleep_duration_min IS NOT NULL
         THEN 0.6745 * (d.sleep_duration_min - med60.sleep_60d_median) / d.sleep_60d_mad_approx
         ELSE NULL END                    AS z_sleep_dur,
    -- Target: next-day ln(RMSSD) Z-score
    CASE WHEN d.next_hrv > 0 AND d.hrv_14d_mad_approx > 0
         THEN 0.6745 * (ln(d.next_hrv) - med14.hrv_14d_median) / d.hrv_14d_mad_approx
         ELSE NULL END                    AS target_hrv_zscore,
    dq.is_valid_day
FROM daily_with_mad d
LEFT JOIN daily_data_quality dq ON dq.date = d.date
LEFT JOIN LATERAL (
    SELECT
        percentile_cont(0.5) WITHIN GROUP (ORDER BY resting_hr)
            FILTER (WHERE resting_hr IS NOT NULL) AS rhr_60d_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY sleep_duration_min)
            FILTER (WHERE sleep_duration_min IS NOT NULL) AS sleep_60d_median
    FROM daily_summaries
    WHERE date BETWEEN d.date - INTERVAL '60 days' AND d.date - INTERVAL '1 day'
) med60 ON TRUE
LEFT JOIN LATERAL (
    SELECT
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY CASE WHEN hrv_daily_rmssd > 0 THEN ln(hrv_daily_rmssd) END)
            FILTER (WHERE hrv_daily_rmssd > 0) AS hrv_14d_median
    FROM daily_summaries
    WHERE date BETWEEN d.date - INTERVAL '14 days' AND d.date - INTERVAL '1 day'
) med14 ON TRUE
WHERE d.date BETWEEN $1 AND $2
ORDER BY d.date
"""


async def extract_hrv_prediction_features(
    pool: asyncpg.Pool, date: datetime.date
) -> np.ndarray | None:
    """Extract single-day feature vector for HRV prediction.

    Returns a 1D numpy array of feature values, or None if no data exists.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(SINGLE_DAY_QUERY, date)

    if row is None:
        logger.warning("No daily_summaries data for %s", date)
        return None

    values = []
    for name in HRV_FEATURE_NAMES:
        val = row.get(name)
        if val is not None:
            fval = float(val)
            values.append(fval if math.isfinite(fval) else float("nan"))
        else:
            values.append(float("nan"))

    return np.array(values, dtype=np.float64)


async def extract_hrv_training_matrix(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[np.ndarray, np.ndarray, list[str], list[datetime.date]]:
    """Extract feature matrix and target vector for HRV prediction training.

    Returns (X, y, feature_names, dates).
    y = next-day ln(RMSSD) Z-score.
    Only includes rows where is_valid_day is True (or quality data unavailable)
    and target is not null.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(TRAINING_QUERY, start_date, end_date)

    valid_dates: list[datetime.date] = []
    feature_rows: list[list[float]] = []
    targets: list[float] = []

    for row in rows:
        # Skip invalid days
        is_valid = row.get("is_valid_day")
        if is_valid is not None and not is_valid:
            continue

        # Skip rows without target
        target = row.get("target_hrv_zscore")
        if target is None:
            continue

        target_val = float(target)
        if not math.isfinite(target_val):
            continue

        row_values = []
        for name in HRV_FEATURE_NAMES:
            val = row.get(name)
            if val is not None:
                fval = float(val)
                row_values.append(fval if math.isfinite(fval) else float("nan"))
            else:
                row_values.append(float("nan"))

        valid_dates.append(row["date"])
        feature_rows.append(row_values)
        targets.append(target_val)

    if not feature_rows:
        return (
            np.empty((0, len(HRV_FEATURE_NAMES))),
            np.empty(0),
            HRV_FEATURE_NAMES,
            [],
        )

    X = np.array(feature_rows, dtype=np.float64)
    y = np.array(targets, dtype=np.float64)
    return X, y, HRV_FEATURE_NAMES, valid_dates


async def extract_hrv_sequence_features(
    pool: asyncpg.Pool,
    target_date: datetime.date,
    lookback_days: int = 7,
) -> np.ndarray | None:
    """Extract a sequence of daily feature vectors for LSTM prediction.

    Extracts features for each day in [target_date - lookback_days, target_date - 1].

    Args:
        pool: asyncpg connection pool.
        target_date: Date to predict for. Features come from prior days.
        lookback_days: Number of past days in the sequence.

    Returns:
        (lookback_days, 26) array, or None if any day is missing.
    """
    sequence = []
    for offset in range(lookback_days, 0, -1):
        day = target_date - datetime.timedelta(days=offset)
        features = await extract_hrv_prediction_features(pool, day)
        if features is None:
            logger.debug("Missing features for %s in sequence for %s", day, target_date)
            return None
        sequence.append(features)

    return np.array(sequence, dtype=np.float64)
