"""Tests for divergence feature extraction."""

import datetime
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.features.divergence_features import (
    DIVERGENCE_FEATURE_NAMES,
    count_paired_observations,
    extract_divergence_features,
    extract_divergence_training_pairs,
)
from tests.conftest import MockPool


@pytest.fixture
def mock_pool():
    return MockPool()


async def test_count_paired_observations(mock_pool):
    mock_pool.conn.fetchval = AsyncMock(return_value=5)
    count = await count_paired_observations(mock_pool)
    assert count == 5


async def test_count_paired_observations_none(mock_pool):
    mock_pool.conn.fetchval = AsyncMock(return_value=None)
    count = await count_paired_observations(mock_pool)
    assert count == 0


async def test_extract_features_single_day(mock_pool):
    row = {
        "resting_hr": 62.0,
        "hrv_ln_rmssd": 3.5,
        "sleep_duration_min": 420.0,
        "sleep_deep_min": 85.0,
        "spo2_avg": 97.5,
        "br_full_sleep": 14.2,
        "steps": 8500.0,
        "skin_temp_variation": 0.3,
        "vri_score": 72.0,
        "day_of_week": 2.0,
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=row)

    features = await extract_divergence_features(mock_pool, datetime.date(2026, 1, 15))
    assert features is not None
    assert features["resting_hr"] == 62.0
    assert features["vri_score"] == 72.0
    assert features["day_of_week"] == 2.0
    assert len(features) == len(DIVERGENCE_FEATURE_NAMES)


async def test_extract_features_no_data(mock_pool):
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)

    features = await extract_divergence_features(mock_pool, datetime.date(2026, 1, 15))
    assert features is None


async def test_extract_features_with_nulls(mock_pool):
    row = {
        "resting_hr": 62.0,
        "hrv_ln_rmssd": None,
        "sleep_duration_min": 420.0,
        "sleep_deep_min": None,
        "spo2_avg": 97.5,
        "br_full_sleep": None,
        "steps": 8500.0,
        "skin_temp_variation": None,
        "vri_score": None,
        "day_of_week": 2.0,
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=row)

    features = await extract_divergence_features(mock_pool, datetime.date(2026, 1, 15))
    assert features is not None
    assert features["resting_hr"] == 62.0
    assert features["hrv_ln_rmssd"] is None
    assert features["vri_score"] is None


async def test_extract_training_pairs(mock_pool):
    rows = [
        {
            "date": datetime.date(2026, 1, 10),
            "condition_log_id": 1,
            "target_score": 65.0,
            "resting_hr": 62.0,
            "hrv_ln_rmssd": 3.5,
            "sleep_duration_min": 420.0,
            "sleep_deep_min": 85.0,
            "spo2_avg": 97.5,
            "br_full_sleep": 14.2,
            "steps": 8500.0,
            "skin_temp_variation": 0.3,
            "vri_score": 72.0,
            "day_of_week": 3.0,
        },
        {
            "date": datetime.date(2026, 1, 11),
            "condition_log_id": 2,
            "target_score": 72.0,
            "resting_hr": 60.0,
            "hrv_ln_rmssd": 3.7,
            "sleep_duration_min": 450.0,
            "sleep_deep_min": 90.0,
            "spo2_avg": 98.0,
            "br_full_sleep": 13.8,
            "steps": 10000.0,
            "skin_temp_variation": 0.2,
            "vri_score": 78.0,
            "day_of_week": 4.0,
        },
    ]
    mock_pool.conn.fetch = AsyncMock(return_value=rows)

    X, y, feature_names, dates, log_ids = await extract_divergence_training_pairs(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 31)
    )

    assert X.shape == (2, len(DIVERGENCE_FEATURE_NAMES))
    assert len(y) == 2
    assert y[0] == 65.0
    assert y[1] == 72.0
    assert dates == [datetime.date(2026, 1, 10), datetime.date(2026, 1, 11)]
    assert log_ids == [1, 2]
    assert feature_names == DIVERGENCE_FEATURE_NAMES


async def test_extract_training_pairs_empty(mock_pool):
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    X, y, feature_names, dates, log_ids = await extract_divergence_training_pairs(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 31)
    )

    assert X.shape[0] == 0
    assert len(y) == 0
    assert dates == []
    assert log_ids == []
