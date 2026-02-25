"""Tests for trainability checks."""

from unittest.mock import AsyncMock

import pytest

from app.training.checks import (
    TrainabilityResult,
    check_anomaly_trainability,
    check_divergence_trainability,
    check_hrv_trainability,
)


class MockConnection:
    """Mock asyncpg connection with configurable return values."""

    def __init__(self):
        self._fetchval_returns = []
        self._fetchrow_returns = []
        self._fetchval_idx = 0
        self._fetchrow_idx = 0

    async def fetchval(self, query, *args):
        if self._fetchval_idx < len(self._fetchval_returns):
            val = self._fetchval_returns[self._fetchval_idx]
            self._fetchval_idx += 1
            return val
        return None

    async def fetchrow(self, query, *args):
        if self._fetchrow_idx < len(self._fetchrow_returns):
            val = self._fetchrow_returns[self._fetchrow_idx]
            self._fetchrow_idx += 1
            return val
        return None


class MockPoolAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class MockPool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return MockPoolAcquire(self._conn)


# --- Anomaly trainability ---


async def test_anomaly_insufficient_data():
    conn = MockConnection()
    conn._fetchval_returns = [10]  # total_valid = 10 < 30
    pool = MockPool(conn)

    result = await check_anomaly_trainability(pool)
    assert not result.trainable
    assert "Insufficient" in result.reason
    assert result.available_count == 10


async def test_anomaly_no_new_data():
    import datetime
    conn = MockConnection()
    conn._fetchval_returns = [
        50,  # total_valid
        datetime.datetime(2026, 2, 20),  # last_trained
        0,   # new_count
    ]
    pool = MockPool(conn)

    result = await check_anomaly_trainability(pool)
    assert not result.trainable
    assert "No new data" in result.reason


async def test_anomaly_low_quality():
    import datetime
    conn = MockConnection()
    conn._fetchval_returns = [
        50,  # total_valid
        datetime.datetime(2026, 2, 20),  # last_trained
        5,   # new_count
    ]
    conn._fetchrow_returns = [
        {"valid_days": 1, "avg_completeness": 20.0},  # low quality
    ]
    pool = MockPool(conn)

    result = await check_anomaly_trainability(pool)
    assert not result.trainable
    assert "Low recent quality" in result.reason
    assert not result.recent_quality_ok


async def test_anomaly_trainable():
    import datetime
    conn = MockConnection()
    conn._fetchval_returns = [
        50,  # total_valid
        datetime.datetime(2026, 2, 20),  # last_trained
        3,   # new_count
    ]
    conn._fetchrow_returns = [
        {"valid_days": 5, "avg_completeness": 80.0},
    ]
    pool = MockPool(conn)

    result = await check_anomaly_trainability(pool)
    assert result.trainable
    assert result.available_count == 50
    assert result.new_since_last_train == 3


async def test_anomaly_never_trained():
    conn = MockConnection()
    conn._fetchval_returns = [
        50,   # total_valid
        None, # last_trained (never trained)
    ]
    conn._fetchrow_returns = [
        {"valid_days": 6, "avg_completeness": 90.0},
    ]
    pool = MockPool(conn)

    result = await check_anomaly_trainability(pool)
    assert result.trainable
    assert result.new_since_last_train == 50


# --- HRV trainability ---


async def test_hrv_insufficient_data():
    conn = MockConnection()
    conn._fetchval_returns = [50]  # total_valid = 50 < 90
    pool = MockPool(conn)

    result = await check_hrv_trainability(pool)
    assert not result.trainable
    assert "Insufficient" in result.reason


async def test_hrv_trainable():
    import datetime
    conn = MockConnection()
    conn._fetchval_returns = [
        100,  # total_valid
        datetime.datetime(2026, 2, 20),  # last_trained
        5,    # new_count
    ]
    conn._fetchrow_returns = [
        {"valid_days": 5, "avg_completeness": 80.0},
    ]
    pool = MockPool(conn)

    result = await check_hrv_trainability(pool)
    assert result.trainable


# --- Divergence trainability ---


async def test_divergence_insufficient_pairs():
    conn = MockConnection()
    conn._fetchval_returns = [8]  # total_pairs = 8 < 14
    pool = MockPool(conn)

    result = await check_divergence_trainability(pool)
    assert not result.trainable
    assert "Insufficient" in result.reason


async def test_divergence_trainable():
    import datetime
    conn = MockConnection()
    conn._fetchval_returns = [
        20,  # total_pairs
        datetime.datetime(2026, 2, 20),  # last_trained
        3,   # new_count
    ]
    conn._fetchrow_returns = [
        {"valid_days": 5, "avg_completeness": 75.0},
    ]
    pool = MockPool(conn)

    result = await check_divergence_trainability(pool)
    assert result.trainable
    assert result.available_count == 20
