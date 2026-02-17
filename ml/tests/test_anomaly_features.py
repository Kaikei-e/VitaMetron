"""Tests for anomaly feature extraction."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.features.anomaly_features import (
    ANOMALY_FEATURE_NAMES,
    extract_anomaly_features,
    extract_anomaly_training_matrix,
)
from tests.conftest import MockPool


def _make_row(overrides=None):
    """Create a mock DB row with all anomaly features."""
    base = {name: float(i + 1) for i, name in enumerate(ANOMALY_FEATURE_NAMES)}
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture
def pool_with_row():
    pool = MockPool()
    pool.conn.fetchrow = AsyncMock(return_value=_make_row())
    return pool


async def test_extract_anomaly_features_returns_dict(pool_with_row):
    result = await extract_anomaly_features(pool_with_row, "2026-01-15")
    assert result is not None
    assert isinstance(result, dict)
    for name in ANOMALY_FEATURE_NAMES:
        assert name in result


async def test_extract_anomaly_features_none_when_no_data():
    pool = MockPool()
    pool.conn.fetchrow = AsyncMock(return_value=None)
    result = await extract_anomaly_features(pool, "2026-01-15")
    assert result is None


async def test_extract_anomaly_features_handles_nan():
    """Non-finite values should be replaced with None."""
    pool = MockPool()
    row = _make_row({"resting_hr": float("inf")})
    pool.conn.fetchrow = AsyncMock(return_value=row)
    result = await extract_anomaly_features(pool, "2026-01-15")
    assert result["resting_hr"] is None


async def test_extract_anomaly_features_handles_null():
    pool = MockPool()
    row = _make_row({"spo2_avg": None})
    pool.conn.fetchrow = AsyncMock(return_value=row)
    result = await extract_anomaly_features(pool, "2026-01-15")
    assert result["spo2_avg"] is None


async def test_extract_training_matrix_shape():
    import datetime

    pool = MockPool()
    rows = []
    for i in range(5):
        row = _make_row()
        row["date"] = datetime.date(2026, 1, 10 + i)
        row["is_valid_day"] = True
        rows.append(row)
    pool.conn.fetch = AsyncMock(return_value=rows)

    X, names, dates = await extract_anomaly_training_matrix(
        pool, datetime.date(2026, 1, 10), datetime.date(2026, 1, 14)
    )
    assert X.shape == (5, len(ANOMALY_FEATURE_NAMES))
    assert names == ANOMALY_FEATURE_NAMES
    assert len(dates) == 5


async def test_extract_training_matrix_skips_invalid_days():
    import datetime

    pool = MockPool()
    rows = [
        {**_make_row(), "date": datetime.date(2026, 1, 10), "is_valid_day": True},
        {**_make_row(), "date": datetime.date(2026, 1, 11), "is_valid_day": False},
        {**_make_row(), "date": datetime.date(2026, 1, 12), "is_valid_day": True},
    ]
    pool.conn.fetch = AsyncMock(return_value=rows)

    X, _, dates = await extract_anomaly_training_matrix(
        pool, datetime.date(2026, 1, 10), datetime.date(2026, 1, 12)
    )
    assert X.shape[0] == 2
    assert len(dates) == 2


async def test_extract_training_matrix_empty():
    import datetime

    pool = MockPool()
    pool.conn.fetch = AsyncMock(return_value=[])

    X, names, dates = await extract_anomaly_training_matrix(
        pool, datetime.date(2026, 1, 10), datetime.date(2026, 1, 14)
    )
    assert X.shape == (0, len(ANOMALY_FEATURE_NAMES))
    assert dates == []


def test_feature_names_count():
    """Verify we have the expected ~20 features."""
    assert len(ANOMALY_FEATURE_NAMES) == 19
    assert len(set(ANOMALY_FEATURE_NAMES)) == 19  # no duplicates
