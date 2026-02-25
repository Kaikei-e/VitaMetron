"""Tests for the retrain orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.retrain import run_retrain


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

    def acquire(self):
        return MockPoolAcquire(self.conn)


def _make_app():
    """Create a mock app with required state."""
    app = MagicMock()
    app.state.db_pool = MockPool()
    app.state.anomaly_detector = MagicMock()
    app.state.hrv_predictor = MagicMock()
    app.state.hrv_ensemble = MagicMock()
    app.state.divergence_detector = MagicMock()
    return app


@patch("app.retrain.check_anomaly_trainability")
@patch("app.retrain.check_hrv_trainability")
@patch("app.retrain.check_divergence_trainability")
async def test_all_skipped(mock_div_check, mock_hrv_check, mock_anom_check):
    """When all models are not trainable, all should be skipped."""
    from app.training.checks import TrainabilityResult

    mock_anom_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )
    mock_hrv_check.return_value = TrainabilityResult(
        trainable=False, reason="Insufficient data"
    )
    mock_div_check.return_value = TrainabilityResult(
        trainable=False, reason="Low quality"
    )

    app = _make_app()
    result = await run_retrain(app, trigger="manual", mode="daily")

    assert result["anomaly"]["status"] == "skipped"
    assert result["hrv"]["status"] == "skipped"
    assert result["divergence"]["status"] == "skipped"
    assert result["trigger"] == "manual"
    assert result["mode"] == "daily"


@patch("app.retrain.check_anomaly_trainability")
@patch("app.retrain.train_anomaly")
@patch("app.retrain.check_hrv_trainability")
@patch("app.retrain.check_divergence_trainability")
async def test_anomaly_success(
    mock_div_check, mock_hrv_check, mock_train_anomaly, mock_anom_check
):
    """When anomaly is trainable, it should train and report success."""
    from app.training.checks import TrainabilityResult

    mock_anom_check.return_value = TrainabilityResult(
        trainable=True, reason="Ready"
    )
    mock_train_anomaly.return_value = {
        "model_version": "anomaly_v_20260225",
        "training_days": 50,
    }
    mock_hrv_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )
    mock_div_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )

    app = _make_app()
    result = await run_retrain(app, trigger="scheduled", mode="daily")

    assert result["anomaly"]["status"] == "success"
    assert result["anomaly"]["model_version"] == "anomaly_v_20260225"
    assert result["anomaly"]["training_days"] == 50
    assert result["hrv"]["status"] == "skipped"


@patch("app.retrain.check_anomaly_trainability")
@patch("app.retrain.train_anomaly")
@patch("app.retrain.check_hrv_trainability")
@patch("app.retrain.check_divergence_trainability")
async def test_anomaly_error(
    mock_div_check, mock_hrv_check, mock_train_anomaly, mock_anom_check
):
    """When training raises an error, it should be caught and reported."""
    from app.training.checks import TrainabilityResult

    mock_anom_check.return_value = TrainabilityResult(
        trainable=True, reason="Ready"
    )
    mock_train_anomaly.side_effect = RuntimeError("Training exploded")
    mock_hrv_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )
    mock_div_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )

    app = _make_app()
    result = await run_retrain(app, trigger="manual", mode="daily")

    assert result["anomaly"]["status"] == "error"
    assert "Training exploded" in result["anomaly"]["message"]


@patch("app.retrain.check_anomaly_trainability")
@patch("app.retrain.check_hrv_trainability")
@patch("app.retrain.train_hrv")
@patch("app.retrain.check_divergence_trainability")
async def test_weekly_mode_passes_optuna_trials(
    mock_div_check, mock_train_hrv, mock_hrv_check, mock_anom_check
):
    """Weekly mode should use optuna_trials=50 and include_lstm=True."""
    from app.training.checks import TrainabilityResult

    mock_anom_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )
    mock_hrv_check.return_value = TrainabilityResult(
        trainable=True, reason="Ready"
    )
    mock_train_hrv.return_value = (
        {"model_version": "hrv_v_test", "training_days": 100, "cv_mae": 0.3},
        None,
    )
    mock_div_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )

    app = _make_app()
    result = await run_retrain(app, trigger="scheduled", mode="weekly")

    # Check that train_hrv was called with weekly params
    mock_train_hrv.assert_called_once()
    call_kwargs = mock_train_hrv.call_args[1]
    assert call_kwargs["optuna_trials"] == 50
    assert call_kwargs["include_lstm"] is True

    assert result["hrv"]["status"] == "success"
    assert result["hrv"]["optuna_trials"] == 50


@patch("app.retrain.check_anomaly_trainability")
@patch("app.retrain.check_hrv_trainability")
@patch("app.retrain.train_hrv")
@patch("app.retrain.check_divergence_trainability")
async def test_daily_mode_skips_optuna(
    mock_div_check, mock_train_hrv, mock_hrv_check, mock_anom_check
):
    """Daily mode should use optuna_trials=0 and include_lstm=False."""
    from app.training.checks import TrainabilityResult

    mock_anom_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )
    mock_hrv_check.return_value = TrainabilityResult(
        trainable=True, reason="Ready"
    )
    mock_train_hrv.return_value = (
        {"model_version": "hrv_v_test", "training_days": 100, "cv_mae": 0.3},
        None,
    )
    mock_div_check.return_value = TrainabilityResult(
        trainable=False, reason="No new data"
    )

    app = _make_app()
    result = await run_retrain(app, trigger="scheduled", mode="daily")

    call_kwargs = mock_train_hrv.call_args[1]
    assert call_kwargs["optuna_trials"] == 0
    assert call_kwargs["include_lstm"] is False
