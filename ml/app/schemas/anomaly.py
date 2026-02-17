"""Pydantic schemas for anomaly detection endpoints."""

import datetime

from pydantic import BaseModel, Field


class AnomalyFeatureContribution(BaseModel):
    feature: str
    shap_value: float
    direction: str  # "anomalous" | "normal" | "neutral"
    description: str


class AnomalyDetectionResponse(BaseModel):
    date: str
    anomaly_score: float
    normalized_score: float = Field(ge=0, le=1)
    is_anomaly: bool
    quality_gate: str  # "pass" | "insufficient_data" | "sensor_issue"
    quality_confidence: float = Field(ge=0, le=1)
    quality_adjusted_score: float = Field(ge=0, le=1)
    top_drivers: list[AnomalyFeatureContribution] = []
    explanation: str = ""
    model_version: str = ""


class AnomalyRangeResponse(BaseModel):
    start: str
    end: str
    detections: list[AnomalyDetectionResponse]
    total_anomalies: int
    model_version: str = ""


class AnomalyTrainRequest(BaseModel):
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    contamination: float = Field(default=0.02, ge=0.001, le=0.1)
    n_estimators: int = Field(default=200, ge=50, le=1000)


class AnomalyTrainResponse(BaseModel):
    model_version: str
    training_days_used: int
    contamination: float
    pot_threshold: float
    feature_names: list[str]
    message: str
