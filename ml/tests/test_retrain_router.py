"""Tests for retrain HTTP endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app


def _test_settings() -> Settings:
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_name="test",
        db_user="test",
        db_password="test",
        model_store_path="/tmp/model_store",
        log_level="DEBUG",
        retrain_enabled=False,  # Disable scheduler in tests
    )


class MockConnection:
    def __init__(self):
        self.fetchval = AsyncMock(return_value=1)
        self.fetchrow = AsyncMock(return_value=None)
        self.fetch = AsyncMock(return_value=[])
        self.execute = AsyncMock()


class MockPoolAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class MockPool:
    def __init__(self):
        self.conn = MockConnection()
        self.close = AsyncMock()

    def acquire(self):
        return MockPoolAcquire(self.conn)


@pytest.fixture
def mock_pool():
    return MockPool()


@pytest.fixture
def test_app(mock_pool):
    app.dependency_overrides[get_settings] = _test_settings
    app.state.db_pool = mock_pool
    app.state.anomaly_detector = MagicMock()
    app.state.hrv_predictor = MagicMock()
    app.state.hrv_ensemble = MagicMock()
    app.state.divergence_detector = MagicMock()
    app.state.retrain_scheduler = None
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@patch("app.routers.retrain.check_anomaly_trainability")
@patch("app.routers.retrain.check_hrv_trainability")
@patch("app.routers.retrain.check_divergence_trainability")
async def test_retrain_check(mock_div, mock_hrv, mock_anom, client):
    from app.training.checks import TrainabilityResult

    mock_anom.return_value = TrainabilityResult(
        trainable=True, reason="Ready", available_count=50, new_since_last_train=3
    )
    mock_hrv.return_value = TrainabilityResult(
        trainable=False, reason="No new data", available_count=100
    )
    mock_div.return_value = TrainabilityResult(
        trainable=True, reason="Ready", available_count=25, new_since_last_train=2
    )

    resp = await client.get("/retrain/check")
    assert resp.status_code == 200

    data = resp.json()
    assert data["anomaly"]["trainable"] is True
    assert data["anomaly"]["available_count"] == 50
    assert data["hrv"]["trainable"] is False
    assert data["divergence"]["trainable"] is True


@patch("app.routers.retrain.run_retrain")
async def test_retrain_trigger(mock_run, client):
    mock_run.return_value = {
        "trigger": "manual",
        "mode": "daily",
        "anomaly": {"status": "success", "message": "Trained on 50 days", "model_version": "v1", "training_days": 50},
        "hrv": {"status": "skipped", "message": "No new data"},
        "divergence": {"status": "skipped", "message": "No new data"},
        "duration_seconds": 5.2,
        "log_id": 1,
    }

    resp = await client.post("/retrain/trigger", json={"mode": "daily"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["trigger"] == "manual"
    assert data["anomaly"]["status"] == "success"
    assert data["duration_seconds"] == 5.2


@patch("app.routers.retrain.run_retrain")
async def test_retrain_trigger_weekly(mock_run, client):
    mock_run.return_value = {
        "trigger": "manual",
        "mode": "weekly",
        "anomaly": {"status": "success"},
        "hrv": {"status": "success", "optuna_trials": 50, "cv_mae": 0.3},
        "divergence": {"status": "success"},
        "duration_seconds": 120.5,
    }

    resp = await client.post("/retrain/trigger", json={"mode": "weekly"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["mode"] == "weekly"


async def test_retrain_status_empty(client):
    """When no retrain has occurred, status should return null."""
    resp = await client.get("/retrain/status")
    assert resp.status_code == 200


async def test_retrain_logs_empty(client, mock_pool):
    """When no retrain logs exist, return empty list."""
    mock_pool.conn.fetchval = AsyncMock(return_value=0)
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    resp = await client.get("/retrain/logs")
    assert resp.status_code == 200

    data = resp.json()
    assert data["logs"] == []
    assert data["total"] == 0
