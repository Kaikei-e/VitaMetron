"""Tests for HRV prediction feature extraction."""

import datetime
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.features.hrv_features import (
    HRV_FEATURE_NAMES,
    extract_hrv_prediction_features,
    extract_hrv_training_matrix,
)
from tests.conftest import MockPool


class FakeRecord(dict):
    """Simulate asyncpg Record."""

    def get(self, key, default=None):
        return super().get(key, default)


def _make_single_day_row(**overrides):
    """Create a mock row for single-day feature extraction."""
    base = {
        "resting_hr": 62.0,
        "hrv_ln_rmssd": 3.8,
        "sleep_duration_min": 420.0,
        "sleep_deep_min": 80.0,
        "sleep_rem_min": 90.0,
        "spo2_avg": 97.0,
        "br_full_sleep": 15.0,
        "steps": 8000.0,
        "calories_active": 350.0,
        "active_zone_min": 30.0,
        "skin_temp_variation": 0.5,
        "resting_hr_delta": -1.0,
        "hrv_delta": 0.1,
        "sleep_delta": 10.0,
        "steps_delta": 500.0,
        "spo2_delta": 0.2,
        "rhr_3d_std": 2.0,
        "hrv_3d_std": 5.0,
        "sleep_3d_std": 15.0,
        "rhr_change_rate": -0.015,
        "hrv_change_rate": 0.02,
        "dow_sin": 0.866,
        "dow_cos": 0.5,
        "z_rhr": -0.5,
        "z_hrv": 0.3,
        "z_sleep_dur": 0.1,
    }
    base.update(overrides)
    return FakeRecord(base)


def _make_training_row(date, target_zscore=0.5, **overrides):
    """Create a mock row for training data extraction."""
    row = _make_single_day_row(**overrides)
    row["date"] = date
    row["target_hrv_zscore"] = target_zscore
    row["is_valid_day"] = True
    return row


async def test_extract_prediction_features_returns_array(mock_pool):
    row = _make_single_day_row()
    mock_pool.conn.fetchrow = AsyncMock(return_value=row)

    result = await extract_hrv_prediction_features(mock_pool, datetime.date(2026, 1, 15))

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (len(HRV_FEATURE_NAMES),)
    assert np.all(np.isfinite(result))


async def test_extract_prediction_features_none_when_no_data(mock_pool):
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)

    result = await extract_hrv_prediction_features(mock_pool, datetime.date(2026, 1, 15))
    assert result is None


async def test_extract_prediction_features_handles_null_values(mock_pool):
    row = _make_single_day_row(spo2_avg=None, skin_temp_variation=None)
    mock_pool.conn.fetchrow = AsyncMock(return_value=row)

    result = await extract_hrv_prediction_features(mock_pool, datetime.date(2026, 1, 15))

    assert result is not None
    # spo2_avg and skin_temp_variation should be NaN
    spo2_idx = HRV_FEATURE_NAMES.index("spo2_avg")
    skin_idx = HRV_FEATURE_NAMES.index("skin_temp_variation")
    assert np.isnan(result[spo2_idx])
    assert np.isnan(result[skin_idx])


async def test_extract_prediction_features_handles_inf(mock_pool):
    row = _make_single_day_row(hrv_change_rate=float("inf"))
    mock_pool.conn.fetchrow = AsyncMock(return_value=row)

    result = await extract_hrv_prediction_features(mock_pool, datetime.date(2026, 1, 15))

    assert result is not None
    idx = HRV_FEATURE_NAMES.index("hrv_change_rate")
    assert np.isnan(result[idx])


async def test_extract_training_matrix_shape(mock_pool):
    rows = [
        _make_training_row(datetime.date(2026, 1, i), target_zscore=0.1 * i)
        for i in range(1, 11)
    ]
    mock_pool.conn.fetch = AsyncMock(return_value=rows)

    X, y, names, dates = await extract_hrv_training_matrix(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 10)
    )

    assert X.shape == (10, len(HRV_FEATURE_NAMES))
    assert y.shape == (10,)
    assert len(names) == len(HRV_FEATURE_NAMES)
    assert len(dates) == 10


async def test_extract_training_matrix_skips_invalid_days(mock_pool):
    rows = [
        _make_training_row(datetime.date(2026, 1, 1)),
        _make_training_row(datetime.date(2026, 1, 2), is_valid_day=False),
        _make_training_row(datetime.date(2026, 1, 3)),
    ]
    # Override is_valid_day for the second row
    rows[1]["is_valid_day"] = False

    mock_pool.conn.fetch = AsyncMock(return_value=rows)

    X, y, names, dates = await extract_hrv_training_matrix(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 3)
    )

    assert X.shape[0] == 2  # skipped invalid day


async def test_extract_training_matrix_skips_null_target(mock_pool):
    rows = [
        _make_training_row(datetime.date(2026, 1, 1)),
        _make_training_row(datetime.date(2026, 1, 2)),
    ]
    rows[1]["target_hrv_zscore"] = None

    mock_pool.conn.fetch = AsyncMock(return_value=rows)

    X, y, names, dates = await extract_hrv_training_matrix(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 2)
    )

    assert X.shape[0] == 1  # skipped null target


async def test_extract_training_matrix_empty(mock_pool):
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    X, y, names, dates = await extract_hrv_training_matrix(
        mock_pool, datetime.date(2026, 1, 1), datetime.date(2026, 1, 10)
    )

    assert X.shape == (0, len(HRV_FEATURE_NAMES))
    assert y.shape == (0,)
    assert dates == []


def test_feature_names_count():
    assert len(HRV_FEATURE_NAMES) == 26


def test_feature_names_unique():
    assert len(HRV_FEATURE_NAMES) == len(set(HRV_FEATURE_NAMES))
