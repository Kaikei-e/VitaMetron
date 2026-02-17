"""Noon-to-noon analytical day boundary utilities."""

import datetime


def noon_to_noon_range(
    date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Return (start, end) for the noon-to-noon window containing the night of `date`.

    For date=2025-01-15:
      start = 2025-01-14 12:00:00
      end   = 2025-01-15 12:00:00

    This captures the sleep episode that Fitbit attributes to the wake-up date (Jan 15).
    """
    start = datetime.datetime.combine(
        date - datetime.timedelta(days=1), datetime.time(12, 0)
    )
    end = datetime.datetime.combine(date, datetime.time(12, 0))
    return start, end
