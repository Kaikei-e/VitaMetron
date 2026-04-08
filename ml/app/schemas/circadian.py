"""Pydantic schemas for Circadian Health Score (CHS) responses."""

from pydantic import BaseModel, Field


class CosinorDetail(BaseModel):
    mesor: float
    amplitude: float
    acrophase_hour: float  # 0-24


class NPARDetail(BaseModel):
    is_value: float  # interdaily stability 0-1
    iv_value: float  # intradaily variability 0-2
    ra_value: float  # relative amplitude 0-1
    m10_value: float
    m10_start_hour: float
    l5_value: float
    l5_start_hour: float


class SleepTimingDetail(BaseModel):
    midpoint_hour: float
    midpoint_variability_min: float
    social_jetlag_min: float


class NocturnalDipDetail(BaseModel):
    dip_pct: float
    daytime_mean_hr: float
    nighttime_mean_hr: float


class CHSMetricContribution(BaseModel):
    metric: str
    z_score: float
    directed_z: float
    direction: str  # "positive" | "negative"
    contribution: float


class CircadianResponse(BaseModel):
    date: str
    chs_score: float = Field(ge=0, le=100)
    chs_confidence: float = Field(ge=0, le=1)
    cosinor: CosinorDetail | None = None
    npar: NPARDetail | None = None
    sleep_timing: SleepTimingDetail | None = None
    nocturnal_dip: NocturnalDipDetail | None = None
    sri_value: float | None = None
    z_scores: dict[str, float | None] = {}
    contributing_factors: list[CHSMetricContribution] = []
    baseline_window_days: int = 0
    baseline_maturity: str = "cold"
    metrics_included: list[str] = []
