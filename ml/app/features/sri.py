"""Sleep Regularity Index (SRI) computation.

Based on Phillips et al., 2017 — measures day-to-day consistency of
sleep/wake timing at 30-second epoch resolution.
"""

import datetime
import logging

import asyncpg
import numpy as np

from app.features.day_boundary import noon_to_noon_range

logger = logging.getLogger(__name__)

EPOCHS_PER_DAY = 2880  # 24h * 120 epochs/hour (30-second epochs)
SLEEP_STAGES = {"deep", "light", "rem"}

SLEEP_STAGES_QUERY = """
SELECT time, stage, seconds
FROM sleep_stages
WHERE time BETWEEN $1 AND $2
ORDER BY time
"""


def _build_epoch_array(
    rows: list[asyncpg.Record],
    window_start: datetime.datetime,
) -> np.ndarray:
    """Build binary sleep/wake array at 30-second epoch resolution.

    Returns array of shape (n_days, EPOCHS_PER_DAY) where 1=sleep, 0=wake.
    NaN marks epochs with no data for that day.
    """
    n_days = len(rows) // EPOCHS_PER_DAY if rows else 0
    # We don't know n_days yet; we'll figure it out from window_start
    # and the actual data span. Instead, we build per-epoch.
    return _fill_epochs(rows, window_start)


def _fill_epochs(
    rows: list,
    window_start: datetime.datetime,
) -> tuple[np.ndarray, int]:
    """Fill epoch arrays from sleep stage records.

    Returns (epochs_flat, n_days) where epochs_flat has shape (n_days * EPOCHS_PER_DAY,).
    Values: 1=sleep, 0=wake, NaN=no data.
    """
    if not rows:
        return np.array([]), 0

    # Determine the overall time span
    first_time = rows[0]["time"]
    last_row = rows[-1]
    last_end = last_row["time"] + datetime.timedelta(seconds=last_row["seconds"])

    # Calculate total days needed
    total_seconds = (last_end - window_start).total_seconds()
    n_days = max(1, int(np.ceil(total_seconds / 86400)))

    epochs = np.full(n_days * EPOCHS_PER_DAY, np.nan)

    for row in rows:
        stage_time = row["time"]
        stage = row["stage"]
        seconds = row["seconds"]

        is_sleep = 1.0 if stage in SLEEP_STAGES else 0.0

        offset_sec = (stage_time - window_start).total_seconds()
        start_epoch = int(offset_sec / 30)
        end_epoch = start_epoch + int(seconds / 30)

        start_epoch = max(0, start_epoch)
        end_epoch = min(len(epochs), end_epoch)

        if start_epoch < end_epoch:
            epochs[start_epoch:end_epoch] = is_sleep

    return epochs, n_days


async def compute_sri(
    pool: asyncpg.Pool,
    date: datetime.date,
    window_days: int = 7,
    min_days: int = 7,
) -> tuple[float | None, int]:
    """Compute Sleep Regularity Index for the given date.

    Args:
        pool: asyncpg connection pool
        date: target date
        window_days: number of trailing days to use
        min_days: minimum days with sleep data required

    Returns:
        (sri_value, days_used) where sri_value is 0-100 or None if insufficient data.
    """
    # Build the full window: we need window_days of noon-to-noon periods
    # For SRI we need consecutive days, so query the full range at once
    end_date = date
    start_date = date - datetime.timedelta(days=window_days)

    # Use noon-to-noon: from start_date's noon-to-noon start to end_date's noon-to-noon end
    window_start = datetime.datetime.combine(
        start_date - datetime.timedelta(days=1), datetime.time(12, 0),
        tzinfo=datetime.timezone.utc,
    )
    window_end = datetime.datetime.combine(
        end_date, datetime.time(12, 0),
        tzinfo=datetime.timezone.utc,
    )

    async with pool.acquire() as conn:
        rows = await conn.fetch(SLEEP_STAGES_QUERY, window_start, window_end)

    if not rows:
        logger.info("No sleep stage data for SRI computation on %s", date)
        return None, 0

    epochs, n_days = _fill_epochs(rows, window_start)
    if n_days < 2:
        return None, n_days

    # Reshape into (n_days, EPOCHS_PER_DAY)
    # Truncate to fit exactly
    usable_epochs = n_days * EPOCHS_PER_DAY
    epochs = epochs[:usable_epochs].reshape(n_days, EPOCHS_PER_DAY)

    # Count days that have at least some sleep data (not all NaN)
    days_with_data = 0
    for d in range(n_days):
        if not np.all(np.isnan(epochs[d])):
            days_with_data += 1

    if days_with_data < min_days:
        logger.info(
            "Insufficient sleep data for SRI: %d/%d days", days_with_data, min_days
        )
        return None, days_with_data

    # Compare each epoch t with t + 24h (next day same time)
    matches = 0
    total_pairs = 0

    for d in range(n_days - 1):
        for e in range(EPOCHS_PER_DAY):
            val_today = epochs[d, e]
            val_tomorrow = epochs[d + 1, e]

            # Skip if either day has no data for this epoch
            if np.isnan(val_today) or np.isnan(val_tomorrow):
                continue

            total_pairs += 1
            if val_today == val_tomorrow:
                matches += 1

    if total_pairs == 0:
        return None, days_with_data

    # SRI_raw ranges from -100 to +100
    sri_raw = (matches / total_pairs) * 200 - 100

    # Map to 0-100 display scale
    sri = (sri_raw + 100) / 2

    logger.info("SRI for %s: %.1f (days_used=%d, pairs=%d)", date, sri, days_with_data, total_pairs)
    return sri, days_with_data
