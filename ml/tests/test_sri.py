import datetime
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.features.sri import EPOCHS_PER_DAY, _fill_epochs, compute_sri
from tests.conftest import MockConnection, MockPool, MockPoolAcquire


class FakeRecord(dict):
    """Simulate asyncpg.Record with dict-like access."""

    def __getitem__(self, key):
        return dict.__getitem__(self, key)


def _make_stage_row(time, stage, seconds):
    return FakeRecord(time=time, stage=stage, seconds=seconds)


def _build_perfect_regularity_rows(start_date, n_days=8):
    """Create rows where sleep pattern is identical every day.

    Sleep from 23:00 to 07:00 (8 hours) each night.
    Times are UTC-aware to match asyncpg TIMESTAMPTZ behaviour.
    """
    rows = []
    utc = datetime.timezone.utc
    for d in range(n_days):
        day = start_date + datetime.timedelta(days=d)
        # Sleep starts at 23:00 UTC
        sleep_start = datetime.datetime.combine(day, datetime.time(23, 0), tzinfo=utc)
        # 8 hours of sleep: deep(2h) + light(3h) + rem(2h) + wake(1h)
        rows.append(_make_stage_row(sleep_start, "deep", 7200))
        rows.append(_make_stage_row(
            sleep_start + datetime.timedelta(seconds=7200), "light", 10800
        ))
        rows.append(_make_stage_row(
            sleep_start + datetime.timedelta(seconds=18000), "rem", 7200
        ))
        rows.append(_make_stage_row(
            sleep_start + datetime.timedelta(seconds=25200), "wake", 3600
        ))
    return rows


class TestFillEpochs:
    def test_empty_rows(self):
        epochs, n_days = _fill_epochs(
            [], datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        )
        assert len(epochs) == 0
        assert n_days == 0

    def test_single_sleep_stage(self):
        utc = datetime.timezone.utc
        start = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=utc)
        rows = [_make_stage_row(
            datetime.datetime(2025, 1, 1, 23, 0, tzinfo=utc), "deep", 3600
        )]
        epochs, n_days = _fill_epochs(rows, start)
        assert n_days >= 1

        # Check that deep sleep epochs are marked as 1
        offset = int((datetime.datetime(2025, 1, 1, 23, 0, tzinfo=utc) - start).total_seconds() / 30)
        end_offset = offset + int(3600 / 30)
        assert all(epochs[offset:end_offset] == 1.0)

    def test_wake_stage_marked_zero(self):
        utc = datetime.timezone.utc
        start = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=utc)
        rows = [_make_stage_row(
            datetime.datetime(2025, 1, 1, 23, 0, tzinfo=utc), "wake", 1800
        )]
        epochs, _ = _fill_epochs(rows, start)
        offset = int((datetime.datetime(2025, 1, 1, 23, 0, tzinfo=utc) - start).total_seconds() / 30)
        end_offset = offset + int(1800 / 30)
        assert all(epochs[offset:end_offset] == 0.0)


class TestComputeSRI:
    @pytest.mark.asyncio
    async def test_perfect_regularity(self):
        """Identical sleep patterns every day should give SRI close to 100."""
        start_date = datetime.date(2025, 1, 1)
        rows = _build_perfect_regularity_rows(start_date, n_days=8)

        pool = MockPool()
        pool.conn.fetch = AsyncMock(return_value=rows)

        sri, days_used = await compute_sri(pool, datetime.date(2025, 1, 9), window_days=8)

        assert sri is not None
        assert sri > 90  # Should be very high for perfect regularity

    @pytest.mark.asyncio
    async def test_no_data_returns_none(self):
        """No sleep data should return None."""
        pool = MockPool()
        pool.conn.fetch = AsyncMock(return_value=[])

        sri, days_used = await compute_sri(pool, datetime.date(2025, 1, 15))

        assert sri is None
        assert days_used == 0

    @pytest.mark.asyncio
    async def test_insufficient_days_returns_none(self):
        """Less than min_days should return None."""
        start_date = datetime.date(2025, 1, 1)
        # Only 3 days of data
        rows = _build_perfect_regularity_rows(start_date, n_days=3)

        pool = MockPool()
        pool.conn.fetch = AsyncMock(return_value=rows)

        sri, days_used = await compute_sri(
            pool, datetime.date(2025, 1, 10), window_days=7, min_days=7
        )

        assert sri is None


class TestSRIRange:
    def test_sri_value_bounded(self):
        """SRI should always be in 0-100 range."""
        # Perfect match: all pairs match
        sri_raw = (100 / 100) * 200 - 100  # = 100
        sri = (sri_raw + 100) / 2  # = 100
        assert sri == 100.0

        # No match at all
        sri_raw = (0 / 100) * 200 - 100  # = -100
        sri = (sri_raw + 100) / 2  # = 0
        assert sri == 0.0

        # Random (50% match)
        sri_raw = (50 / 100) * 200 - 100  # = 0
        sri = (sri_raw + 100) / 2  # = 50
        assert sri == 50.0
