"""Tests for HRV prediction API endpoints."""

import json
import tempfile
from unittest.mock import AsyncMock

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from xgboost import XGBRegressor

from app.main import app
from app.models.hrv_predictor import HRVPredictor
from tests.conftest import MockPool


def _make_ready_predictor(model_dir: str) -> HRVPredictor:
    """Create a predictor with a dummy model (no Optuna / CV)."""
    predictor = HRVPredictor(model_dir)
    rng = np.random.RandomState(42)
    n, n_feat = 40, 5
    X = rng.randn(n, n_feat)
    y = 0.5 * X[:, 0] - 0.3 * X[:, 1] + rng.randn(n) * 0.3

    predictor._feature_names = [f"feat_{i}" for i in range(n_feat)]
    predictor._feature_medians = np.nanmedian(X, axis=0)
    predictor._feature_stds = np.nanstd(X, axis=0)
    predictor._feature_stds[predictor._feature_stds == 0] = 1.0
    predictor._training_days = n
    predictor._cv_metrics = {
        "mae": 0.3, "rmse": 0.4, "r2": 0.6,
        "directional_accuracy": 0.8, "n_folds": 5,
    }
    predictor._best_params = {"max_depth": 3}
    predictor._stable_features = ["feat_0", "feat_1"]
    predictor._model_version = "hrv_v_test"

    X_norm = (X - predictor._feature_medians) / predictor._feature_stds
    model = XGBRegressor(n_estimators=10, max_depth=2, random_state=42)
    model.fit(X_norm, y, verbose=False)
    predictor._model = model

    return predictor


@pytest.fixture
def trained_predictor():
    with tempfile.TemporaryDirectory() as d:
        yield _make_ready_predictor(d)


@pytest.fixture
def test_app_with_predictor(test_app, trained_predictor):
    test_app.state.hrv_predictor = trained_predictor
    yield test_app


@pytest.fixture
def test_app_no_hrv_model(test_app):
    with tempfile.TemporaryDirectory() as d:
        test_app.state.hrv_predictor = HRVPredictor(d)
        yield test_app


async def test_hrv_status_ready(test_app_with_predictor):
    transport = ASGITransport(app=test_app_with_predictor)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/hrv/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is True
    assert data["model_version"].startswith("hrv_v")
    assert data["training_days"] == 40
    assert "mae" in data["cv_metrics"]


async def test_hrv_status_not_ready(test_app_no_hrv_model):
    transport = ASGITransport(app=test_app_no_hrv_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/hrv/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is False
    assert data["model_version"] == ""


async def test_predict_returns_cached(test_app_with_predictor, mock_pool):
    cached_row = {
        "date": "2026-01-15",
        "target_date": "2026-01-16",
        "predicted_zscore": 0.45,
        "predicted_direction": "above_baseline",
        "confidence": 0.72,
        "top_drivers": json.dumps([{
            "feature": "resting_hr",
            "shap_value": 0.15,
            "direction": "positive",
        }]),
        "model_version": "hrv_v123",
        "computed_at": "2026-01-15T12:00:00Z",
    }
    mock_pool.conn.fetchrow = AsyncMock(return_value=cached_row)

    transport = ASGITransport(app=test_app_with_predictor)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/hrv/predict?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_hrv_zscore"] == 0.45
    assert data["predicted_direction"] == "above_baseline"
    assert len(data["top_drivers"]) == 1


async def test_predict_503_when_no_model(test_app_no_hrv_model, mock_pool):
    mock_pool.conn.fetchrow = AsyncMock(return_value=None)
    test_app_no_hrv_model.state.db_pool = mock_pool

    transport = ASGITransport(app=test_app_no_hrv_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/hrv/predict?date=2026-01-15")
    assert resp.status_code == 503


async def test_train_insufficient_data(test_app_with_predictor, mock_pool):
    mock_pool.conn.fetch = AsyncMock(return_value=[])

    transport = ASGITransport(app=test_app_with_predictor)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/hrv/train", json={})
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


async def test_backfill_503_when_no_model(test_app_no_hrv_model, mock_pool):
    test_app_no_hrv_model.state.db_pool = mock_pool

    transport = ASGITransport(app=test_app_no_hrv_model)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/hrv/backfill?start=2026-01-01&end=2026-01-05")
    assert resp.status_code == 503
