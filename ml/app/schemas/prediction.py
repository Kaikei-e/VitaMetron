from pydantic import BaseModel, Field


class ContributingFactor(BaseModel):
    feature: str
    importance: float
    direction: str  # "positive" | "negative"
    value: float
    baseline: float


class PredictionResponse(BaseModel):
    predicted_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_factors: list[ContributingFactor] = []
    risk_signals: list[str] = []


class WeeklyInsightResponse(BaseModel):
    week_start: str
    week_end: str
    avg_score: float | None = None
    trend: str  # "improving" | "declining" | "stable" | "insufficient_data"
    top_factors: list[str] = []
    risk_summary: list[str] = []
