"""Tests for daily advice API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings


@pytest.fixture
def test_app_with_settings(test_app):
    test_app.state.settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_name="test",
        db_user="test",
        db_password="test",
        model_store_path="/tmp/model_store",
        log_level="DEBUG",
        ollama_base_url="http://ollama:11434",
        ollama_model="gemma3:4b-it-qat",
        ollama_timeout=10.0,
    )
    yield test_app


async def test_get_advice_cached(client, test_app_with_settings, mock_pool):
    """When a cached result exists, return it directly."""
    cached_row = {
        "date": "2026-02-18",
        "advice_text": "おはようございます。本日のHRVは良好です。",
        "model_name": "gemma3:4b-it-qat",
        "generation_ms": 5000,
        "generated_at": "2026-02-18T08:00:00Z",
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=cached_row)

    resp = await client.get("/advice?date=2026-02-18")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert data["advice_text"] == "おはようございます。本日のHRVは良好です。"
    assert data["model_name"] == "gemma3:4b-it-qat"
    assert data["generation_ms"] == 5000


async def test_get_advice_missing_date(client, test_app_with_settings):
    """Missing date parameter should return 422."""
    resp = await client.get("/advice")
    assert resp.status_code == 422


async def test_get_advice_no_data(client, test_app_with_settings, mock_pool):
    """When no cached advice and no biometric data, return insufficient data message."""
    # First fetchrow (cache check) returns None, second (daily summary) returns None
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)

    resp = await client.get("/advice?date=2026-02-18")
    assert resp.status_code == 200
    data = resp.json()
    assert "不十分" in data["advice_text"]
    assert data["cached"] is False


async def test_regenerate_calls_ollama(client, test_app_with_settings, mock_pool):
    """Regenerate should call Ollama even when cache exists."""
    # daily summary exists
    summary_row = {
        "date": "2026-02-18",
        "resting_hr": 62,
        "hrv_daily_rmssd": 45.0,
        "hrv_deep_rmssd": 55.0,
        "spo2_avg": 97.0,
        "sleep_duration_min": 420,
        "deep_sleep_min": 90,
        "rem_sleep_min": 80,
        "light_sleep_min": 240,
        "sleep_minutes_asleep": 386,
        "sleep_onset_latency_min": 10,
        "steps": 8000,
        "active_zone_minutes": 30,
        "vo2max": 42.0,
    }

    call_count = 0

    async def mock_fetchrow(query, *args):
        nonlocal call_count
        call_count += 1
        # First call is daily summary, rest return None
        if call_count == 1:
            return summary_row
        return None

    mock_pool.conn.fetchrow = mock_fetchrow
    mock_pool.conn.fetch = AsyncMock(return_value=[])
    mock_pool.conn.execute = AsyncMock()

    with patch("app.routers.advice._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = (
            "おはようございます。HRVが45msと良好な状態です。",
            5000,
        )

        resp = await client.post("/advice/regenerate?date=2026-02-18")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert "HRV" in data["advice_text"]
        assert data["generation_ms"] == 5000
        mock_call.assert_called_once()


async def test_regenerate_missing_date(client, test_app_with_settings):
    """Missing date parameter should return 422."""
    resp = await client.post("/advice/regenerate")
    assert resp.status_code == 422
