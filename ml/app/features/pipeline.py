import datetime
import logging

import asyncpg

logger = logging.getLogger(__name__)

FEATURE_QUERY = """
WITH avg_7d AS (
    SELECT
        avg(resting_hr)         AS rhr_7d,
        avg(hrv_daily_rmssd)    AS hrv_7d,
        avg(sleep_duration_min) AS sleep_7d,
        avg(steps)              AS steps_7d,
        avg(spo2_avg)           AS spo2_7d,
        avg(sleep_deep_min)     AS deep_sleep_7d,
        avg(br_full_sleep)      AS br_7d
    FROM daily_summaries
    WHERE date BETWEEN $1::date - INTERVAL '7 days' AND $1::date - INTERVAL '1 day'
)
SELECT
    ds.date,
    ds.resting_hr,
    ds.hrv_daily_rmssd,
    ds.spo2_avg,
    ds.spo2_min,
    ds.sleep_duration_min,
    ds.sleep_deep_min,
    ds.sleep_rem_min,
    ds.sleep_light_min,
    ds.sleep_minutes_awake,
    ds.steps,
    ds.calories_active,
    ds.active_zone_min,
    ds.br_full_sleep,
    ds.skin_temp_variation,
    a.rhr_7d,
    a.hrv_7d,
    a.sleep_7d,
    a.steps_7d,
    a.spo2_7d,
    a.deep_sleep_7d,
    a.br_7d,
    ds.resting_hr - a.rhr_7d           AS resting_hr_delta,
    ds.hrv_daily_rmssd - a.hrv_7d      AS hrv_delta,
    ds.sleep_duration_min - a.sleep_7d  AS sleep_delta,
    ds.steps - a.steps_7d              AS steps_delta,
    ds.spo2_avg - a.spo2_7d            AS spo2_delta,
    EXTRACT(DOW FROM ds.date)           AS day_of_week,
    dq.is_valid_day,
    dq.confidence_score,
    dq.confidence_level,
    dq.completeness_pct,
    dq.wear_time_hours,
    dq.baseline_maturity
FROM daily_summaries ds
CROSS JOIN avg_7d a
LEFT JOIN daily_data_quality dq ON dq.date = ds.date
WHERE ds.date = $1::date
"""


async def extract_features(pool: asyncpg.Pool, date: datetime.date) -> dict | None:
    """Extract features for a given date from the database.

    Returns a dict of feature name -> value, or None if no data exists for the date.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FEATURE_QUERY, date)

    if row is None:
        logger.warning("No daily_summaries data for %s", date)
        return None

    return dict(row)


TRAINING_QUERY = """
WITH daily_avgs AS (
    SELECT
        date,
        resting_hr,
        hrv_daily_rmssd,
        spo2_avg,
        spo2_min,
        sleep_duration_min,
        sleep_deep_min,
        sleep_rem_min,
        sleep_light_min,
        sleep_minutes_awake,
        steps,
        calories_active,
        active_zone_min,
        br_full_sleep,
        skin_temp_variation,
        avg(resting_hr)         OVER w AS rhr_7d,
        avg(hrv_daily_rmssd)    OVER w AS hrv_7d,
        avg(sleep_duration_min) OVER w AS sleep_7d,
        avg(steps)              OVER w AS steps_7d,
        avg(spo2_avg)           OVER w AS spo2_7d,
        avg(sleep_deep_min)     OVER w AS deep_sleep_7d,
        avg(br_full_sleep)      OVER w AS br_7d
    FROM daily_summaries
    WINDOW w AS (ORDER BY date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)
)
SELECT
    d.*,
    d.resting_hr - d.rhr_7d           AS resting_hr_delta,
    d.hrv_daily_rmssd - d.hrv_7d      AS hrv_delta,
    d.sleep_duration_min - d.sleep_7d  AS sleep_delta,
    d.steps - d.steps_7d              AS steps_delta,
    d.spo2_avg - d.spo2_7d            AS spo2_delta,
    EXTRACT(DOW FROM d.date)           AS day_of_week,
    cl.overall                         AS condition_score
FROM daily_avgs d
INNER JOIN condition_logs cl ON cl.logged_at::date = d.date
WHERE d.date BETWEEN $1 AND $2
ORDER BY d.date
"""


async def extract_training_data(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[dict]:
    """Extract training features with labels (condition_score) for a date range."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(TRAINING_QUERY, start_date, end_date)

    return [dict(row) for row in rows]
