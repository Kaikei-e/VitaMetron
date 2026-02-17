"""Tests for anomaly detection API endpoints."""

import json
import tempfile
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.models.anomaly_detector import AnomalyDetector
from tests.conftest import MockPool


@pytest.fixture
def trained_detector():
    """Create a trained detector with synthetic data."""
    with tempfile.TemporaryDirectory() as d:
        detector = AnomalyDetector(d)
        rng = np.random.RandomState(42)
        X = rng.randn(100, 5)
        detector.train(X, ["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"])
        yield detector


@pytest.fixture
def test_app_with_detector(test_app, trained_detector):
    test_app.state.anomaly_detector = trained_detector
    yield test_app


@pytest.fixture
def test_app_no_model(test_app):
    with tempfile.TemporaryDirectory() as d:
        test_app.state.anomaly_detector = AnomalyDetector(d)
        yield test_app


async def test_anomaly_status_ready(client, test_app_with_detector):
    resp = await client.get("/anomaly/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is True
    assert data["model_version"].startswith("anomaly_v")


async def test_anomaly_status_not_ready(test_app_no_model):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=test_app_no_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/anomaly/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is False


async def test_detect_returns_cached(client, test_app_with_detector, mock_pool):
    """When a cached result exists, return it directly."""
    cached_row = {
        "date": "2026-01-15",
        "anomaly_score": -0.1,
        "normalized_score": 0.7,
        "is_anomaly": True,
        "quality_gate": "pass",
        "quality_confidence": 0.9,
        "quality_adjusted_score": 0.63,
        "top_drivers": json.dumps([{
            "feature": "resting_hr",
            "shap_value": -0.05,
            "direction": "anomalous",
            "description": "Resting HR was elevated",
        }]),
        "explanation": "Test explanation",
        "model_version": "anomaly_v123",
        "computed_at": "2026-01-15T12:00:00Z",
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=cached_row)

    resp = await client.get("/anomaly/detect?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_anomaly"] is True
    assert data["quality_gate"] == "pass"
    assert len(data["top_drivers"]) == 1


async def test_detect_503_when_no_model(test_app_no_model, mock_pool):
    """Should return 503 when model is not trained and no cache."""
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)
    test_app_no_model.state.db_pool = mock_pool

    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=test_app_no_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/anomaly/detect?date=2026-01-15")
    assert resp.status_code == 503


async def test_range_returns_empty(client, test_app_with_detector, mock_pool):
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    resp = await client.get("/anomaly/range?start=2026-01-10&end=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detections"] == []
    assert data["total_anomalies"] == 0


async def test_train_insufficient_data(client, test_app_with_detector, mock_pool):
    """Training with < 30 days should fail."""
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    resp = await client.post("/anomaly/train", json={})
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]
