"""Retrain API endpoints — check trainability, trigger retrain, view logs."""

import logging

from fastapi import APIRouter, Query, Request

from app.retrain import run_retrain
from app.schemas.retrain import (
    ModelResult,
    RetrainCheckResponse,
    RetrainLogEntry,
    RetrainLogsResponse,
    RetrainResult,
    RetrainTriggerRequest,
    TrainabilityCheck,
)
from app.training.checks import (
    check_anomaly_trainability,
    check_divergence_trainability,
    check_hrv_trainability,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/retrain/check", response_model=RetrainCheckResponse)
async def retrain_check(request: Request):
    """Check trainability of all models (data sufficiency, new data, quality)."""
    pool = request.app.state.db_pool

    anomaly = await check_anomaly_trainability(pool)
    hrv = await check_hrv_trainability(pool)
    divergence = await check_divergence_trainability(pool)

    return RetrainCheckResponse(
        anomaly=TrainabilityCheck(
            model="anomaly",
            trainable=anomaly.trainable,
            reason=anomaly.reason,
            available_count=anomaly.available_count,
            new_since_last_train=anomaly.new_since_last_train,
            recent_quality_ok=anomaly.recent_quality_ok,
        ),
        hrv=TrainabilityCheck(
            model="hrv",
            trainable=hrv.trainable,
            reason=hrv.reason,
            available_count=hrv.available_count,
            new_since_last_train=hrv.new_since_last_train,
            recent_quality_ok=hrv.recent_quality_ok,
        ),
        divergence=TrainabilityCheck(
            model="divergence",
            trainable=divergence.trainable,
            reason=divergence.reason,
            available_count=divergence.available_count,
            new_since_last_train=divergence.new_since_last_train,
            recent_quality_ok=divergence.recent_quality_ok,
        ),
    )


@router.post("/retrain/trigger", response_model=RetrainResult)
async def retrain_trigger(
    request: Request,
    body: RetrainTriggerRequest | None = None,
):
    """Manually trigger retraining of all eligible models."""
    if body is None:
        body = RetrainTriggerRequest()

    result = await run_retrain(request.app, trigger="manual", mode=body.mode)

    return RetrainResult(
        trigger=result["trigger"],
        mode=result["mode"],
        anomaly=ModelResult(**result["anomaly"]),
        hrv=ModelResult(**result["hrv"]),
        divergence=ModelResult(**result["divergence"]),
        duration_seconds=result.get("duration_seconds"),
        log_id=result.get("log_id"),
    )


@router.get("/retrain/status", response_model=RetrainResult | None)
async def retrain_status(request: Request):
    """Get the most recent retrain result."""
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM retrain_logs
            ORDER BY started_at DESC LIMIT 1
        """)

    if row is None:
        return None

    return RetrainResult(
        trigger=row["trigger"],
        mode=row["retrain_mode"],
        anomaly=ModelResult(
            status=row["anomaly_status"],
            message=row["anomaly_message"],
            model_version=row["anomaly_model_version"],
            training_days=row["anomaly_training_days"],
        ),
        hrv=ModelResult(
            status=row["hrv_status"],
            message=row["hrv_message"],
            model_version=row["hrv_model_version"],
            training_days=row["hrv_training_days"],
            optuna_trials=row["hrv_optuna_trials"],
            cv_mae=row["hrv_cv_mae"],
        ),
        divergence=ModelResult(
            status=row["divergence_status"],
            message=row["divergence_message"],
            model_version=row["divergence_model_version"],
            training_pairs=row["divergence_training_pairs"],
            r2=row["divergence_r2"],
        ),
        duration_seconds=row["duration_seconds"],
        log_id=row["id"],
    )


@router.get("/retrain/logs", response_model=RetrainLogsResponse)
async def retrain_logs(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get retrain log history."""
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM retrain_logs")
        rows = await conn.fetch(
            "SELECT * FROM retrain_logs ORDER BY started_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )

    entries = []
    for row in rows:
        entries.append(RetrainLogEntry(
            id=row["id"],
            started_at=row["started_at"].isoformat(),
            completed_at=row["completed_at"].isoformat() if row["completed_at"] else None,
            trigger=row["trigger"],
            retrain_mode=row["retrain_mode"],
            anomaly_status=row["anomaly_status"],
            anomaly_message=row["anomaly_message"],
            anomaly_model_version=row["anomaly_model_version"],
            anomaly_training_days=row["anomaly_training_days"],
            hrv_status=row["hrv_status"],
            hrv_message=row["hrv_message"],
            hrv_model_version=row["hrv_model_version"],
            hrv_training_days=row["hrv_training_days"],
            hrv_optuna_trials=row["hrv_optuna_trials"],
            hrv_cv_mae=row["hrv_cv_mae"],
            divergence_status=row["divergence_status"],
            divergence_message=row["divergence_message"],
            divergence_model_version=row["divergence_model_version"],
            divergence_training_pairs=row["divergence_training_pairs"],
            divergence_r2=row["divergence_r2"],
            duration_seconds=row["duration_seconds"],
        ))

    return RetrainLogsResponse(logs=entries, total=total)
