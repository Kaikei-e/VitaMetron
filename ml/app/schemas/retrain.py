"""Pydantic schemas for retrain endpoints."""

from pydantic import BaseModel, Field


class TrainabilityCheck(BaseModel):
    model: str
    trainable: bool
    reason: str
    available_count: int = 0
    new_since_last_train: int = 0
    recent_quality_ok: bool = True


class RetrainCheckResponse(BaseModel):
    anomaly: TrainabilityCheck
    hrv: TrainabilityCheck
    divergence: TrainabilityCheck


class RetrainTriggerRequest(BaseModel):
    mode: str = Field(default="daily", pattern="^(daily|weekly)$")


class ModelResult(BaseModel):
    status: str  # success | skipped | error | pending
    message: str | None = None
    model_version: str | None = None
    training_days: int | None = None
    training_pairs: int | None = None
    optuna_trials: int | None = None
    cv_mae: float | None = None
    r2: float | None = None


class RetrainResult(BaseModel):
    trigger: str
    mode: str
    anomaly: ModelResult
    hrv: ModelResult
    divergence: ModelResult
    duration_seconds: float | None = None
    log_id: int | None = None


class RetrainLogEntry(BaseModel):
    id: int
    started_at: str
    completed_at: str | None = None
    trigger: str
    retrain_mode: str
    anomaly_status: str
    anomaly_message: str | None = None
    anomaly_model_version: str | None = None
    anomaly_training_days: int | None = None
    hrv_status: str
    hrv_message: str | None = None
    hrv_model_version: str | None = None
    hrv_training_days: int | None = None
    hrv_optuna_trials: int | None = None
    hrv_cv_mae: float | None = None
    divergence_status: str
    divergence_message: str | None = None
    divergence_model_version: str | None = None
    divergence_training_pairs: int | None = None
    divergence_r2: float | None = None
    duration_seconds: float | None = None


class RetrainLogsResponse(BaseModel):
    logs: list[RetrainLogEntry]
    total: int
