import pytest


def _make_feature_row(**overrides):
    """Create a mock DB row dict with default feature values."""
    defaults = {
        "date": "2026-02-17",
        "resting_hr": 62,
        "hrv_daily_rmssd": 45.0,
        "spo2_avg": 97.0,
        "spo2_min": 94.0,
        "sleep_duration_min": 450,
        "sleep_deep_min": 70,
        "sleep_rem_min": 90,
        "sleep_light_min": 200,
        "sleep_minutes_awake": 30,
        "steps": 8500,
        "calories_active": 350,
        "active_zone_min": 25,
        "br_full_sleep": 15.0,
        "skin_temp_variation": 0.2,
        "rhr_7d": 60.0,
        "hrv_7d": 42.0,
        "sleep_7d": 430.0,
        "steps_7d": 8000.0,
        "spo2_7d": 97.0,
        "deep_sleep_7d": 65.0,
        "br_7d": 14.5,
        "resting_hr_delta": 2.0,
        "hrv_delta": 3.0,
        "sleep_delta": 20.0,
        "steps_delta": 500.0,
        "spo2_delta": 0.0,
        "day_of_week": 2,
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_predict_returns_score(client, mock_pool):
    mock_pool.conn.fetchrow.return_value = _make_feature_row()

    resp = await client.get("/predict?date=2026-02-17")
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_score" in data
    assert "confidence" in data
    assert "contributing_factors" in data
    assert "risk_signals" in data
    assert 1.0 <= data["predicted_score"] <= 5.0
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_predict_no_data_returns_fallback(client, mock_pool):
    mock_pool.conn.fetchrow.return_value = None

    resp = await client.get("/predict?date=2026-02-17")
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_score"] == 3.0
    assert data["confidence"] == 0.0
    assert data["contributing_factors"] == []
    assert data["risk_signals"] == []


@pytest.mark.asyncio
async def test_predict_good_sleep_hrv(client, mock_pool):
    """Good sleep + high HRV should produce score > 3.0."""
    mock_pool.conn.fetchrow.return_value = _make_feature_row(
        sleep_duration_min=480,  # 8 hours
        hrv_delta=8.0,           # above baseline
        sleep_deep_min=75,
    )

    resp = await client.get("/predict?date=2026-02-17")
    data = resp.json()
    assert data["predicted_score"] > 3.0


@pytest.mark.asyncio
async def test_predict_poor_metrics(client, mock_pool):
    """Poor sleep + low HRV + elevated RHR should produce score < 3.0."""
    mock_pool.conn.fetchrow.return_value = _make_feature_row(
        sleep_duration_min=240,  # 4 hours
        hrv_delta=-12.0,         # below baseline
        resting_hr_delta=7.0,    # elevated
        sleep_deep_min=20,
    )

    resp = await client.get("/predict?date=2026-02-17")
    data = resp.json()
    assert data["predicted_score"] < 3.0


@pytest.mark.asyncio
async def test_predict_missing_date_param(client):
    resp = await client.get("/predict")
    assert resp.status_code == 422
