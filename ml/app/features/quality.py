"""Quality data access functions for the ML feature pipeline."""

import datetime
import json
import logging

import asyncpg

logger = logging.getLogger(__name__)

QUALITY_QUERY = """
SELECT date, is_valid_day, confidence_score, confidence_level,
       completeness_pct, wear_time_hours, baseline_maturity,
       plausibility_flags, metrics_missing
FROM daily_data_quality WHERE date = $1::date
"""

COMPLIANCE_QUERY = """
SELECT COUNT(*) AS valid_count
FROM daily_data_quality
WHERE date BETWEEN $1::date - ($2 || ' days')::interval AND $1::date - INTERVAL '1 day'
  AND is_valid_day = TRUE
"""


async def get_day_quality(pool: asyncpg.Pool, date: datetime.date) -> dict | None:
    """Fetch quality metadata for a single day.

    Returns a dict of quality fields or None if no quality data exists.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(QUALITY_QUERY, date)

    if row is None:
        logger.warning("No quality data for %s", date)
        return None

    result = dict(row)
    # Parse JSONB plausibility_flags if it's a string
    if isinstance(result.get("plausibility_flags"), str):
        result["plausibility_flags"] = json.loads(result["plausibility_flags"])
    return result


async def check_minimum_compliance(
    pool: asyncpg.Pool,
    date: datetime.date,
    window_days: int = 7,
    min_valid: int = 3,
) -> bool:
    """Check if at least `min_valid` days in the trailing window are valid.

    Returns True if compliance is met, False otherwise.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(COMPLIANCE_QUERY, date, str(window_days))

    if row is None:
        return False

    return row["valid_count"] >= min_valid
