"""Batch backfill utility for Circadian Health Scores."""

import datetime
import logging

import asyncpg

logger = logging.getLogger(__name__)


async def backfill_circadian(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> int:
    """Compute and persist CHS scores for a date range.

    Returns the number of dates processed.
    """
    from app.routers.circadian import _compute_and_persist

    count = 0
    current = start_date
    while current <= end_date:
        try:
            await _compute_and_persist(pool, current)
            count += 1
            logger.info("Backfilled circadian for %s", current)
        except Exception:
            logger.exception("Failed to backfill circadian for %s", current)
        current += datetime.timedelta(days=1)

    logger.info("Circadian backfill complete: %d dates processed", count)
    return count
