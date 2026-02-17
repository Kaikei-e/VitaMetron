"""Tests for divergence detection API endpoints."""

import json
import tempfile
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.models.divergence_detector import DivergenceDetector
from tests.conftest import MockPool


@pytest.fixture
def trained_detector():
    """Create a trained detector with synthetic data."""
    with tempfile.TemporaryDirectory() as d:
        detector = DivergenceDetector(d)
        rng = np.random.RandomState(42)
        X = rng.randn(50, 5)
        y = 3.0 + 0.5 * X[:, 0] - 0.3 * X[:, 1] + 0.2 * rng.randn(50)
        detector.train(X, y, ["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"])
        yield detector


@pytest.fixture
def test_app_with_detector(test_app, trained_detector):
    test_app.state.divergence_detector = trained_detector
    yield test_app


@pytest.fixture
def test_app_no_model(test_app):
    with tempfile.TemporaryDirectory() as d:
        test_app.state.divergence_detector = DivergenceDetector(d)
        yield test_app


async def test_divergence_status_ready(client, test_app_with_detector, mock_pool):
    mock_pool.conn.fetchval = AsyncMock(return_value=50)
    resp = await client.get("/divergence/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is True
    assert data["model_version"].startswith("divergence_v")
    assert data["training_pairs"] == 50
    assert data["phase"] == "baseline"


async def test_divergence_status_not_ready(test_app_no_model, mock_pool):
    mock_pool.conn.fetchval = AsyncMock(return_value=3)
    test_app_no_model.state.db_pool = mock_pool

    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=test_app_no_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/divergence/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is False
    assert data["phase"] == "cold_start"


async def test_detect_returns_cached(client, test_app_with_detector, mock_pool):
    """When a cached result exists, return it directly."""
    cached_row = {
        "date": "2026-01-15",
        "condition_log_id": 1,
        "actual_score": 3.5,
        "predicted_score": 3.0,
        "residual": 0.5,
        "cusum_positive": 1.2,
        "cusum_negative": 0.0,
        "cusum_alert": False,
        "divergence_type": "aligned",
        "confidence": 0.75,
        "top_drivers": json.dumps([{
            "feature": "resting_hr",
            "coefficient": 0.5,
            "feature_value": 62.0,
            "contribution": 0.3,
            "direction": "positive",
        }]),
        "explanation": "Aligned",
        "model_version": "divergence_v123",
        "computed_at": "2026-01-15T12:00:00Z",
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=cached_row)

    resp = await client.get("/divergence/detect?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["divergence_type"] == "aligned"
    assert data["actual_score"] == 3.5
    assert len(data["top_drivers"]) == 1


async def test_detect_503_when_no_model(test_app_no_model, mock_pool):
    """Should return 503 when model is not trained and no cache."""
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)
    mock_pool.conn.fetchval = AsyncMock(return_value=3)
    test_app_no_model.state.db_pool = mock_pool

    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=test_app_no_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/divergence/detect?date=2026-01-15")
    assert resp.status_code == 503


async def test_range_returns_empty(client, test_app_with_detector, mock_pool):
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    resp = await client.get("/divergence/range?start=2026-01-10&end=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detections"] == []
    assert data["total_alerts"] == 0


async def test_train_insufficient_data(client, test_app_with_detector, mock_pool):
    """Training with < 14 pairs should fail."""
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    resp = await client.post("/divergence/train")
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]
