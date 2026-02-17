"""Pydantic schemas for divergence detection endpoints."""

import datetime

from pydantic import BaseModel, Field


class DivergenceFeatureContribution(BaseModel):
    feature: str
    coefficient: float
    feature_value: float
    contribution: float
    direction: str  # "positive" | "negative"


class DivergenceDetectionResponse(BaseModel):
    date: str
    actual_score: float
    predicted_score: float
    residual: float
    cusum_positive: float = 0.0
    cusum_negative: float = 0.0
    cusum_alert: bool = False
    divergence_type: str = "aligned"
    confidence: float = Field(ge=0, le=1, default=0.0)
    top_drivers: list[DivergenceFeatureContribution] = []
    explanation: str = ""
    model_version: str = ""


class DivergenceRangeResponse(BaseModel):
    start: str
    end: str
    detections: list[DivergenceDetectionResponse]
    total_alerts: int
    model_version: str = ""


class DivergenceStatusResponse(BaseModel):
    is_ready: bool
    model_version: str = ""
    training_pairs: int = 0
    min_pairs_needed: int = 14
    r2_score: float | None = None
    mae: float | None = None
    phase: str = "cold_start"
    message: str = ""


class DivergenceTrainResponse(BaseModel):
    model_version: str
    training_pairs_used: int
    r2_score: float | None = None
    mae: float | None = None
    rmse: float | None = None
    message: str
