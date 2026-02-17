"""Pydantic schemas for HRV prediction endpoints."""

import datetime

from pydantic import BaseModel, Field


class HRVFeatureContribution(BaseModel):
    feature: str
    shap_value: float
    direction: str  # "positive" | "negative" | "neutral"


class HRVPredictionResponse(BaseModel):
    date: str
    target_date: str  # next day
    predicted_hrv_zscore: float
    predicted_direction: str  # "above_baseline" | "below_baseline"
    confidence: float = Field(ge=0, le=1)
    top_drivers: list[HRVFeatureContribution] = []
    model_version: str = ""


class HRVTrainRequest(BaseModel):
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    optuna_trials: int = Field(default=50, ge=10, le=200)
    include_lstm: bool = True
    lstm_lookback_days: int = Field(default=7, ge=3, le=14)


class HRVTrainResponse(BaseModel):
    model_version: str
    training_days_used: int
    cv_mae: float
    cv_rmse: float
    cv_r2: float
    cv_directional_accuracy: float
    best_params: dict
    stable_features: list[str]
    message: str
    lstm_cv_mae: float | None = None
    ensemble_alpha: float | None = None
    ensemble_cv_mae: float | None = None


class HRVModelStatusResponse(BaseModel):
    is_ready: bool
    model_version: str = ""
    training_days: int = 0
    cv_metrics: dict = {}
    stable_features: list[str] = []
