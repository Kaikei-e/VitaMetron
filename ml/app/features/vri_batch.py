"""Batch backfill utility for VRI scores."""

import datetime
import logging

import asyncpg

logger = logging.getLogger(__name__)


async def backfill_vri(
    pool: asyncpg.Pool,
    start_date: datetime.date,
    end_date: datetime.date,
) -> int:
    """Compute and persist VRI scores for a date range.

    Returns the number of dates processed.
    """
    from app.routers.vri import _compute_and_persist

    count = 0
    current = start_date
    while current <= end_date:
        try:
            await _compute_and_persist(pool, current)
            count += 1
            logger.info("Backfilled VRI for %s", current)
        except Exception:
            logger.exception("Failed to backfill VRI for %s", current)
        current += datetime.timedelta(days=1)

    logger.info("Backfill complete: %d dates processed", count)
    return count
