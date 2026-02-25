"""HRV prediction API endpoints."""

import datetime
import json
import logging

import numpy as np
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.hrv_features import (
    extract_hrv_prediction_features,
    extract_hrv_sequence_features,
)
from app.features.quality import check_minimum_compliance
from app.models.ensemble_hrv import HRVEnsemble
from app.schemas.hrv_prediction import (
    HRVFeatureContribution,
    HRVModelStatusResponse,
    HRVPredictionResponse,
    HRVTrainRequest,
    HRVTrainResponse,
)
from app.training.errors import InsufficientDataError
from app.training.hrv import train_hrv

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_PREDICTION_QUERY = """
SELECT date, target_date, predicted_zscore, predicted_direction,
       confidence, top_drivers, model_version, computed_at
FROM hrv_predictions WHERE date = $1::date
"""

UPSERT_PREDICTION_QUERY = """
INSERT INTO hrv_predictions (
    date, target_date, predicted_zscore, predicted_direction,
    confidence, top_drivers, model_version
) VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (date) DO UPDATE SET
    target_date=$2, predicted_zscore=$3, predicted_direction=$4,
    confidence=$5, top_drivers=$6, model_version=$7, computed_at=NOW()
"""



def _row_to_response(row) -> HRVPredictionResponse:
    drivers_raw = row["top_drivers"]
    if isinstance(drivers_raw, str):
        drivers_raw = json.loads(drivers_raw)

    drivers = []
    if drivers_raw:
        for d in drivers_raw:
            drivers.append(
                HRVFeatureContribution(
                    feature=d["feature"],
                    shap_value=d["shap_value"],
                    direction=d["direction"],
                )
            )

    return HRVPredictionResponse(
        date=str(row["date"]),
        target_date=str(row["target_date"]),
        predicted_hrv_zscore=row["predicted_zscore"],
        predicted_direction=row["predicted_direction"],
        confidence=row["confidence"],
        top_drivers=drivers,
        model_version=row["model_version"] or "",
    )


async def _predict_single(
    pool, predictor, date: datetime.date, ensemble: HRVEnsemble | None = None,
) -> HRVPredictionResponse:
    """Compute HRV prediction for a single date."""
    target_date = date + datetime.timedelta(days=1)

    features = await extract_hrv_prediction_features(pool, date)
    if features is None:
        return HRVPredictionResponse(
            date=str(date),
            target_date=str(target_date),
            predicted_hrv_zscore=0.0,
            predicted_direction="above_baseline",
            confidence=0.0,
            model_version=predictor.model_version if predictor.is_ready else "",
        )

    # Quality gate
    compliance = await check_minimum_compliance(pool, date, window_days=7, min_valid=3)
    if not compliance:
        return HRVPredictionResponse(
            date=str(date),
            target_date=str(target_date),
            predicted_hrv_zscore=0.0,
            predicted_direction="above_baseline",
            confidence=0.0,
            model_version=predictor.model_version,
        )

    # Predict — use ensemble if available
    sequence = None
    if ensemble is not None and ensemble.has_lstm:
        seq_raw = await extract_hrv_sequence_features(pool, date)
        if seq_raw is not None:
            sequence = ensemble._lstm.prepare_sequence(
                [seq_raw[i] for i in range(seq_raw.shape[0])]
            )

    if ensemble is not None:
        z_score, confidence = ensemble.predict(features, sequence)
        shap_values = ensemble.explain(features)
    else:
        z_score, confidence = predictor.predict(features)
        shap_values = predictor.explain(features)

    direction = "above_baseline" if z_score >= 0 else "below_baseline"

    # Build top drivers (top 5 by absolute SHAP value)
    sorted_features = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
    top_drivers = []
    for feat_name, shap_val in sorted_features[:5]:
        if shap_val > 0:
            feat_direction = "positive"
        elif shap_val < 0:
            feat_direction = "negative"
        else:
            feat_direction = "neutral"
        top_drivers.append(
            HRVFeatureContribution(
                feature=feat_name,
                shap_value=round(shap_val, 4),
                direction=feat_direction,
            )
        )

    result = HRVPredictionResponse(
        date=str(date),
        target_date=str(target_date),
        predicted_hrv_zscore=round(z_score, 4),
        predicted_direction=direction,
        confidence=round(confidence, 4),
        top_drivers=top_drivers,
        model_version=predictor.model_version,
    )

    # Persist
    drivers_json = json.dumps([d.model_dump() for d in top_drivers])
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_PREDICTION_QUERY,
            date,
            target_date,
            result.predicted_hrv_zscore,
            result.predicted_direction,
            result.confidence,
            drivers_json,
            result.model_version,
        )

    return result


@router.get("/hrv/predict", response_model=HRVPredictionResponse)
async def predict_hrv(
    request: Request,
    date: datetime.date = Query(..., description="Feature date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    predictor = request.app.state.hrv_predictor
    ensemble = getattr(request.app.state, "hrv_ensemble", None)

    # Check model readiness
    if not predictor.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "HRV model not trained. POST /hrv/train first."},
        )

    # Today → always recompute (data may have changed since last sync)
    if date >= datetime.date.today():
        return await _predict_single(pool, predictor, date, ensemble=ensemble)

    # Past dates → serve cache if available
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_PREDICTION_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    return await _predict_single(pool, predictor, date, ensemble=ensemble)


@router.post("/hrv/train", response_model=HRVTrainResponse)
async def train_hrv_model(
    request: Request,
    body: HRVTrainRequest | None = None,
):
    pool = request.app.state.db_pool
    predictor = request.app.state.hrv_predictor

    if body is None:
        body = HRVTrainRequest()

    try:
        metadata, ensemble = await train_hrv(
            pool,
            predictor,
            start_date=body.start_date,
            end_date=body.end_date,
            optuna_trials=body.optuna_trials,
            include_lstm=body.include_lstm,
            lstm_lookback_days=body.lstm_lookback_days,
        )
    except InsufficientDataError as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Insufficient training data: {e.available} valid days (need >= {e.required})."},
        )

    if ensemble is not None:
        request.app.state.hrv_ensemble = ensemble

    return HRVTrainResponse(
        model_version=metadata["model_version"],
        training_days_used=metadata["training_days"],
        cv_mae=metadata["cv_mae"],
        cv_rmse=metadata["cv_rmse"],
        cv_r2=metadata["cv_r2"],
        cv_directional_accuracy=metadata["cv_directional_accuracy"],
        best_params=metadata["best_params"],
        stable_features=metadata["stable_features"],
        message=f"Model trained on {metadata['training_days']} days.",
        lstm_cv_mae=metadata.get("lstm_cv_mae"),
        ensemble_alpha=metadata.get("ensemble_alpha"),
        ensemble_cv_mae=metadata.get("ensemble_cv_mae"),
    )


@router.get("/hrv/status", response_model=HRVModelStatusResponse)
async def hrv_status(request: Request):
    predictor = request.app.state.hrv_predictor
    return HRVModelStatusResponse(
        is_ready=predictor.is_ready,
        model_version=predictor.model_version if predictor.is_ready else "",
        training_days=predictor.training_days if predictor.is_ready else 0,
        cv_metrics=predictor.cv_metrics if predictor.is_ready else {},
        stable_features=predictor.stable_features if predictor.is_ready else [],
    )


@router.post("/hrv/backfill")
async def backfill_hrv(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    predictor = request.app.state.hrv_predictor
    ensemble = getattr(request.app.state, "hrv_ensemble", None)

    if not predictor.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "HRV model not trained."},
        )

    count = 0
    current = start
    while current <= end:
        try:
            await _predict_single(pool, predictor, current, ensemble=ensemble)
            count += 1
        except Exception:
            logger.exception("Failed to predict HRV for %s", current)
        current += datetime.timedelta(days=1)

    return {"backfilled": count, "start": str(start), "end": str(end)}
