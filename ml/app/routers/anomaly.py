"""Anomaly detection API endpoints."""

import datetime
import json
import logging

import numpy as np
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.anomaly_features import (
    ANOMALY_FEATURE_NAMES,
    extract_anomaly_features,
)
from app.features.anomaly_quality import apply_quality_gates, compute_anomaly_confidence
from app.features.quality import get_day_quality
from app.models.anomaly_explainer import generate_explanation
from app.schemas.anomaly import (
    AnomalyDetectionResponse,
    AnomalyFeatureContribution,
    AnomalyRangeResponse,
    AnomalyTrainRequest,
    AnomalyTrainResponse,
)
from app.training.anomaly import train_anomaly
from app.training.errors import InsufficientDataError

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_ANOMALY_QUERY = """
SELECT date, anomaly_score, normalized_score, is_anomaly,
       quality_gate, quality_confidence, quality_adjusted_score,
       top_drivers, explanation, model_version, computed_at
FROM anomaly_detections WHERE date = $1::date
"""

FETCH_ANOMALY_RANGE_QUERY = """
SELECT date, anomaly_score, normalized_score, is_anomaly,
       quality_gate, quality_confidence, quality_adjusted_score,
       top_drivers, explanation, model_version, computed_at
FROM anomaly_detections WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

UPSERT_ANOMALY_QUERY = """
INSERT INTO anomaly_detections (
    date, anomaly_score, normalized_score, is_anomaly,
    quality_gate, quality_confidence, quality_adjusted_score,
    top_drivers, explanation, model_version
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (date) DO UPDATE SET
    anomaly_score=$2, normalized_score=$3, is_anomaly=$4,
    quality_gate=$5, quality_confidence=$6, quality_adjusted_score=$7,
    top_drivers=$8, explanation=$9, model_version=$10, computed_at=NOW()
"""



def _row_to_response(row) -> AnomalyDetectionResponse:
    drivers_raw = row["top_drivers"]
    if isinstance(drivers_raw, str):
        drivers_raw = json.loads(drivers_raw)

    drivers = []
    if drivers_raw:
        for d in drivers_raw:
            drivers.append(
                AnomalyFeatureContribution(
                    feature=d["feature"],
                    shap_value=d["shap_value"],
                    direction=d["direction"],
                    description=d["description"],
                )
            )

    return AnomalyDetectionResponse(
        date=str(row["date"]),
        anomaly_score=row["anomaly_score"],
        normalized_score=row["normalized_score"],
        is_anomaly=row["is_anomaly"],
        quality_gate=row["quality_gate"],
        quality_confidence=row["quality_confidence"],
        quality_adjusted_score=row["quality_adjusted_score"],
        top_drivers=drivers,
        explanation=row["explanation"] or "",
        model_version=row["model_version"] or "",
    )


async def _detect_single(pool, detector, date: datetime.date) -> AnomalyDetectionResponse:
    """Compute anomaly detection for a single date."""
    # Extract features
    features = await extract_anomaly_features(pool, date)
    if features is None:
        return AnomalyDetectionResponse(
            date=str(date),
            anomaly_score=0.0,
            normalized_score=0.0,
            is_anomaly=False,
            quality_gate="insufficient_data",
            quality_confidence=0.0,
            quality_adjusted_score=0.0,
            explanation="No biometric data available for this date.",
        )

    # Apply quality gates (Layer 1 + 2)
    gate_result, confidence = await apply_quality_gates(pool, date, features)

    if gate_result != "pass":
        return AnomalyDetectionResponse(
            date=str(date),
            anomaly_score=0.0,
            normalized_score=0.0,
            is_anomaly=False,
            quality_gate=gate_result,
            quality_confidence=confidence,
            quality_adjusted_score=0.0,
            explanation=f"Quality gate failed: {gate_result}.",
        )

    # Build feature array
    feature_array = np.array(
        [features.get(name, float("nan")) if features.get(name) is not None else float("nan")
         for name in ANOMALY_FEATURE_NAMES],
        dtype=np.float64,
    )

    # Score
    raw_score, normalized, is_anomaly = detector.score(feature_array)

    # Layer 4: Quality-adjusted score
    quality_adjusted = normalized * confidence

    # Explain
    shap_values = detector.explain(feature_array)

    # Get baseline for explanation context
    quality_data = await get_day_quality(pool, date)
    summary, contributions = generate_explanation(shap_values, features)

    # Top 5 drivers
    top_drivers = [
        AnomalyFeatureContribution(
            feature=c.feature,
            shap_value=c.shap_value,
            direction=c.direction,
            description=c.description,
        )
        for c in contributions[:5]
    ]

    result = AnomalyDetectionResponse(
        date=str(date),
        anomaly_score=round(raw_score, 4),
        normalized_score=round(normalized, 4),
        is_anomaly=is_anomaly,
        quality_gate="pass",
        quality_confidence=round(confidence, 4),
        quality_adjusted_score=round(quality_adjusted, 4),
        top_drivers=top_drivers,
        explanation=summary,
        model_version=detector.model_version,
    )

    # Persist
    drivers_json = json.dumps([d.model_dump() for d in top_drivers])
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_ANOMALY_QUERY,
            date,
            result.anomaly_score,
            result.normalized_score,
            result.is_anomaly,
            result.quality_gate,
            result.quality_confidence,
            result.quality_adjusted_score,
            drivers_json,
            result.explanation,
            result.model_version,
        )

    return result


@router.get("/anomaly/detect", response_model=AnomalyDetectionResponse)
async def detect_anomaly(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    # Check model readiness
    detector = request.app.state.anomaly_detector
    if not detector.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Anomaly model not trained. POST /anomaly/train first."},
        )

    # Today → always recompute (data may have changed since last sync)
    if date >= datetime.date.today():
        return await _detect_single(pool, detector, date)

    # Past dates → serve cache if available
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_ANOMALY_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    return await _detect_single(pool, detector, date)


@router.get("/anomaly/range", response_model=AnomalyRangeResponse)
async def get_anomaly_range(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        rows = await conn.fetch(FETCH_ANOMALY_RANGE_QUERY, start, end)

    detections = [_row_to_response(row) for row in rows]
    total_anomalies = sum(1 for d in detections if d.is_anomaly)

    detector = request.app.state.anomaly_detector
    model_version = detector.model_version if detector.is_ready else ""

    return AnomalyRangeResponse(
        start=str(start),
        end=str(end),
        detections=detections,
        total_anomalies=total_anomalies,
        model_version=model_version,
    )


@router.post("/anomaly/train", response_model=AnomalyTrainResponse)
async def train_anomaly_model(
    request: Request,
    body: AnomalyTrainRequest | None = None,
):
    pool = request.app.state.db_pool
    detector = request.app.state.anomaly_detector

    if body is None:
        body = AnomalyTrainRequest()

    try:
        metadata = await train_anomaly(
            pool,
            detector,
            start_date=body.start_date,
            end_date=body.end_date,
            contamination=body.contamination,
            n_estimators=body.n_estimators,
        )
    except InsufficientDataError as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Insufficient training data: {e.available} valid days (need >= {e.required})."},
        )

    return AnomalyTrainResponse(
        model_version=metadata["model_version"],
        training_days_used=metadata["training_days"],
        contamination=metadata["contamination"],
        pot_threshold=metadata["pot_threshold"],
        feature_names=metadata["feature_names"],
        message=f"Model trained on {metadata['training_days']} days.",
    )


@router.get("/anomaly/status")
async def anomaly_status(request: Request):
    detector = request.app.state.anomaly_detector
    return {
        "is_ready": detector.is_ready,
        "model_version": detector.model_version if detector.is_ready else None,
        "feature_names": detector.feature_names if detector.is_ready else [],
    }


@router.post("/anomaly/backfill")
async def backfill_anomaly(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    detector = request.app.state.anomaly_detector

    if not detector.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Anomaly model not trained."},
        )

    count = 0
    current = start
    while current <= end:
        try:
            await _detect_single(pool, detector, current)
            count += 1
        except Exception:
            logger.exception("Failed to compute anomaly for %s", current)
        current += datetime.timedelta(days=1)

    return {"backfilled": count, "start": str(start), "end": str(end)}
