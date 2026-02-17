"""Pydantic schemas for VRI (Vitality Recovery Index) responses."""

from pydantic import BaseModel, Field


class VRIMetricContribution(BaseModel):
    metric: str
    z_score: float
    directed_z: float
    direction: str  # "positive" | "negative"
    contribution: float


class VRIResponse(BaseModel):
    date: str
    vri_score: float = Field(ge=0, le=100)
    vri_confidence: float = Field(ge=0, le=1)
    sri_value: float | None = None
    sri_days_used: int = 0
    z_scores: dict[str, float | None] = {}
    contributing_factors: list[VRIMetricContribution] = []
    baseline_window_days: int = 0
    baseline_maturity: str = "cold"
    metrics_included: list[str] = []
