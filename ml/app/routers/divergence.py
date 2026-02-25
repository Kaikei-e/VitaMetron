"""Divergence detection API endpoints."""

import datetime
import json
import logging

import numpy as np
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.divergence_features import (
    DIVERGENCE_FEATURE_NAMES,
    count_paired_observations,
    extract_divergence_features,
)
from app.schemas.divergence import (
    DivergenceDetectionResponse,
    DivergenceFeatureContribution,
    DivergenceRangeResponse,
    DivergenceStatusResponse,
    DivergenceTrainResponse,
)
from app.training.divergence import train_divergence
from app.training.errors import InsufficientDataError

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_DIVERGENCE_QUERY = """
SELECT date, condition_log_id, actual_score, predicted_score, residual,
       cusum_positive, cusum_negative, cusum_alert,
       divergence_type, confidence, top_drivers, explanation,
       model_version, computed_at
FROM divergence_detections WHERE date = $1::date
"""

FETCH_DIVERGENCE_RANGE_QUERY = """
SELECT date, condition_log_id, actual_score, predicted_score, residual,
       cusum_positive, cusum_negative, cusum_alert,
       divergence_type, confidence, top_drivers, explanation,
       model_version, computed_at
FROM divergence_detections WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

FETCH_CONDITION_FOR_DATE_QUERY = """
SELECT id,
       overall_vas::float AS score
FROM condition_logs
WHERE logged_at::date = $1::date
ORDER BY logged_at DESC
LIMIT 1
"""

FETCH_RECENT_RESIDUALS_QUERY = """
SELECT residual
FROM divergence_detections
WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

UPSERT_DIVERGENCE_QUERY = """
INSERT INTO divergence_detections (
    date, condition_log_id, actual_score, predicted_score, residual,
    cusum_positive, cusum_negative, cusum_alert,
    divergence_type, confidence, top_drivers, explanation, model_version
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
ON CONFLICT (date) DO UPDATE SET
    condition_log_id=$2, actual_score=$3, predicted_score=$4, residual=$5,
    cusum_positive=$6, cusum_negative=$7, cusum_alert=$8,
    divergence_type=$9, confidence=$10, top_drivers=$11,
    explanation=$12, model_version=$13, computed_at=NOW()
"""



def _row_to_response(row) -> DivergenceDetectionResponse:
    drivers_raw = row["top_drivers"]
    if isinstance(drivers_raw, str):
        drivers_raw = json.loads(drivers_raw)

    drivers = []
    if drivers_raw:
        for d in drivers_raw:
            drivers.append(
                DivergenceFeatureContribution(
                    feature=d["feature"],
                    coefficient=d["coefficient"],
                    feature_value=d["feature_value"],
                    contribution=d["contribution"],
                    direction=d["direction"],
                )
            )

    return DivergenceDetectionResponse(
        date=str(row["date"]),
        actual_score=row["actual_score"],
        predicted_score=row["predicted_score"],
        residual=row["residual"],
        cusum_positive=row["cusum_positive"],
        cusum_negative=row["cusum_negative"],
        cusum_alert=row["cusum_alert"],
        divergence_type=row["divergence_type"],
        confidence=row["confidence"],
        top_drivers=drivers,
        explanation=row["explanation"] or "",
        model_version=row["model_version"] or "",
    )


def _generate_explanation(
    residual: float,
    divergence_type: str,
    cusum_alert: bool,
    top_contributions: list[DivergenceFeatureContribution],
) -> str:
    """Generate a human-readable explanation of divergence."""
    if divergence_type == "aligned":
        return "Your subjective condition aligns with your biometric data."

    abs_residual = abs(residual)

    if divergence_type == "feeling_better_than_expected":
        summary = f"You rated your condition {abs_residual:.1f} points higher than your biometrics suggest."
    else:
        summary = f"You rated your condition {abs_residual:.1f} points lower than your biometrics suggest."

    if cusum_alert:
        summary += " This pattern has been sustained over recent days."

    if top_contributions:
        top = top_contributions[0]
        summary += f" The largest factor is {top.feature} (contribution: {top.contribution:+.2f})."

    return summary


async def _detect_single(
    pool, detector, date: datetime.date
) -> DivergenceDetectionResponse:
    """Compute divergence detection for a single date."""
    # Extract biometric features
    features = await extract_divergence_features(pool, date)
    if features is None:
        return DivergenceDetectionResponse(
            date=str(date),
            actual_score=0.0,
            predicted_score=0.0,
            residual=0.0,
            divergence_type="no_biometric_data",
            explanation="No biometric data available for this date.",
        )

    # Look up condition log for this date
    async with pool.acquire() as conn:
        cond_row = await conn.fetchrow(FETCH_CONDITION_FOR_DATE_QUERY, date)

    if cond_row is None:
        return DivergenceDetectionResponse(
            date=str(date),
            actual_score=0.0,
            predicted_score=0.0,
            residual=0.0,
            divergence_type="no_condition_log",
            explanation="No condition log recorded for this date.",
        )

    condition_log_id = int(cond_row["id"])
    actual_score = float(cond_row["score"])

    # Build feature array
    feature_array = np.array(
        [
            features.get(name, float("nan"))
            if features.get(name) is not None
            else float("nan")
            for name in DIVERGENCE_FEATURE_NAMES
        ],
        dtype=np.float64,
    )

    # Predict
    predicted_score, confidence = detector.predict(feature_array)
    residual = detector.compute_residual(actual_score, predicted_score)

    # CuSum: fetch last 28 days of residuals
    phase = detector.get_phase()
    cusum_pos, cusum_neg, cusum_alert, divergence_type = 0.0, 0.0, False, "aligned"

    if phase in ("baseline", "full"):
        cusum_start = date - datetime.timedelta(days=28)
        async with pool.acquire() as conn:
            residual_rows = await conn.fetch(
                FETCH_RECENT_RESIDUALS_QUERY, cusum_start, date - datetime.timedelta(days=1)
            )
        recent_residuals = [float(r["residual"]) for r in residual_rows]
        recent_residuals.append(residual)

        cusum_pos, cusum_neg, cusum_alert, divergence_type = detector.compute_cusum(
            recent_residuals
        )
    else:
        # Initial phase: simple threshold
        if abs(residual) > 20.0:
            divergence_type = (
                "feeling_better_than_expected" if residual > 0
                else "feeling_worse_than_expected"
            )

    # Explain
    contributions = detector.explain(feature_array)
    sorted_contribs = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)

    top_drivers = []
    for feat_name, contrib in sorted_contribs[:5]:
        feat_val = features.get(feat_name)
        top_drivers.append(
            DivergenceFeatureContribution(
                feature=feat_name,
                coefficient=float(detector._model.coef_[
                    detector._feature_names.index(feat_name)
                ]),
                feature_value=feat_val if feat_val is not None else 0.0,
                contribution=round(contrib, 4),
                direction="positive" if contrib > 0 else "negative",
            )
        )

    explanation = _generate_explanation(residual, divergence_type, cusum_alert, top_drivers)

    result = DivergenceDetectionResponse(
        date=str(date),
        actual_score=round(actual_score, 2),
        predicted_score=round(predicted_score, 2),
        residual=round(residual, 4),
        cusum_positive=round(cusum_pos, 4),
        cusum_negative=round(cusum_neg, 4),
        cusum_alert=cusum_alert,
        divergence_type=divergence_type,
        confidence=round(confidence, 4),
        top_drivers=top_drivers,
        explanation=explanation,
        model_version=detector.model_version,
    )

    # Persist
    drivers_json = json.dumps([d.model_dump() for d in top_drivers])
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_DIVERGENCE_QUERY,
            date,
            condition_log_id,
            result.actual_score,
            result.predicted_score,
            result.residual,
            result.cusum_positive,
            result.cusum_negative,
            result.cusum_alert,
            result.divergence_type,
            result.confidence,
            drivers_json,
            result.explanation,
            result.model_version,
        )

    return result


@router.get("/divergence/detect", response_model=DivergenceDetectionResponse)
async def detect_divergence(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    # Check model readiness
    detector = request.app.state.divergence_detector
    if not detector.is_ready:
        phase = detector.get_phase(
            await count_paired_observations(pool)
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Divergence model not trained. POST /divergence/train first.",
                "phase": phase,
            },
        )

    # Today → always recompute (data may have changed since last sync)
    if date >= datetime.date.today():
        return await _detect_single(pool, detector, date)

    # Past dates → serve cache if available
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_DIVERGENCE_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    return await _detect_single(pool, detector, date)


@router.get("/divergence/range", response_model=DivergenceRangeResponse)
async def get_divergence_range(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        rows = await conn.fetch(FETCH_DIVERGENCE_RANGE_QUERY, start, end)

    detections = [_row_to_response(row) for row in rows]
    total_alerts = sum(1 for d in detections if d.cusum_alert)

    detector = request.app.state.divergence_detector
    model_version = detector.model_version if detector.is_ready else ""

    return DivergenceRangeResponse(
        start=str(start),
        end=str(end),
        detections=detections,
        total_alerts=total_alerts,
        model_version=model_version,
    )


@router.post("/divergence/train", response_model=DivergenceTrainResponse)
async def train_divergence_model(request: Request):
    pool = request.app.state.db_pool
    detector = request.app.state.divergence_detector

    try:
        metadata = await train_divergence(pool, detector)
    except InsufficientDataError as e:
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Insufficient paired observations: {e.available} (need >= {e.required}).",
                "current_pairs": e.available,
                "min_pairs_needed": e.required,
            },
        )

    return DivergenceTrainResponse(
        model_version=metadata["model_version"],
        training_pairs_used=metadata["training_pairs"],
        r2_score=metadata["r2_score"],
        mae=metadata["mae"],
        rmse=metadata["rmse"],
        message=f"Model trained on {metadata['training_pairs']} paired observations.",
    )


@router.get("/divergence/status", response_model=DivergenceStatusResponse)
async def divergence_status(request: Request):
    pool = request.app.state.db_pool
    detector = request.app.state.divergence_detector

    n_pairs = await count_paired_observations(pool)
    phase = detector.get_phase(n_pairs)

    messages = {
        "cold_start": f"{n_pairs} of {detector.MIN_PAIRS_INITIAL} condition logs needed. Keep logging!",
        "initial": f"Ridge model active ({n_pairs} pairs). CuSum needs {detector.MIN_PAIRS_CUSUM} pairs.",
        "baseline": f"Ridge + CuSum active ({n_pairs} pairs). Full calibration at {detector.MIN_PAIRS_FULL}.",
        "full": f"Fully calibrated with {n_pairs} paired observations.",
    }

    return DivergenceStatusResponse(
        is_ready=detector.is_ready,
        model_version=detector.model_version if detector.is_ready else "",
        training_pairs=n_pairs,
        min_pairs_needed=detector.MIN_PAIRS_INITIAL,
        r2_score=detector.r2_score,
        mae=detector.mae,
        phase=phase,
        message=messages.get(phase, ""),
    )


@router.post("/divergence/backfill")
async def backfill_divergence(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    detector = request.app.state.divergence_detector

    if not detector.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Divergence model not trained."},
        )

    count = 0
    current = start
    while current <= end:
        try:
            await _detect_single(pool, detector, current)
            count += 1
        except Exception:
            logger.exception("Failed to compute divergence for %s", current)
        current += datetime.timedelta(days=1)

    return {"backfilled": count, "start": str(start), "end": str(end)}
