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
    extract_hrv_training_matrix,
)
from app.features.quality import check_minimum_compliance
from app.models.ensemble_hrv import HRVEnsemble, optimize_ensemble_weight
from app.models.lstm_predictor import LSTMHRVPredictor
from app.models.validation import walk_forward_cv_lstm
from app.schemas.hrv_prediction import (
    HRVFeatureContribution,
    HRVModelStatusResponse,
    HRVPredictionResponse,
    HRVTrainRequest,
    HRVTrainResponse,
)

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

UPSERT_MODEL_METADATA_QUERY = """
INSERT INTO hrv_model_metadata (
    model_version, training_days, cv_mae, cv_rmse, cv_r2,
    cv_directional_accuracy, best_params, stable_features, feature_names, config
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (model_version) DO UPDATE SET
    training_days=$2, cv_mae=$3, cv_rmse=$4, cv_r2=$5,
    cv_directional_accuracy=$6, best_params=$7, stable_features=$8,
    feature_names=$9, config=$10, trained_at=NOW()
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

    # Check cache first
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_PREDICTION_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    # Check model readiness
    if not predictor.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "HRV model not trained. POST /hrv/train first."},
        )

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

    # Default date range: all available data
    end_date = body.end_date or datetime.date.today()
    if body.start_date:
        start_date = body.start_date
    else:
        async with pool.acquire() as conn:
            earliest = await conn.fetchval("SELECT MIN(date) FROM daily_summaries")
        start_date = earliest or (end_date - datetime.timedelta(days=365))

    # Extract training matrix
    X, y, feature_names, valid_dates = await extract_hrv_training_matrix(
        pool, start_date, end_date
    )

    if X.shape[0] < 90:
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Insufficient training data: {X.shape[0]} valid days (need >= 90)."
            },
        )

    # 1. Train XGBoost (existing logic)
    metadata = predictor.train(
        X, y, feature_names, valid_dates, optuna_trials=body.optuna_trials
    )
    predictor.save()

    xgb_mae = metadata["cv_mae"]
    lstm_cv_mae = None
    ensemble_alpha = None
    ensemble_cv_mae = None

    # 2. Optionally train LSTM
    if body.include_lstm and X.shape[0] >= body.lstm_lookback_days + 30:
        try:
            logger.info("Training LSTM with lookback=%d...", body.lstm_lookback_days)

            # LSTM walk-forward CV
            lstm_cv = walk_forward_cv_lstm(
                X, y, valid_dates, feature_names,
                lookback=body.lstm_lookback_days,
                min_train_days=90,
                gap_days=1,
                max_epochs=200,
                patience=15,
            )
            lstm_cv_mae = lstm_cv.mae

            # Check: LSTM MAE within 15% of XGBoost MAE?
            if lstm_cv_mae <= 1.15 * xgb_mae:
                logger.info(
                    "LSTM included: MAE=%.4f (XGBoost=%.4f, threshold=%.4f)",
                    lstm_cv_mae, xgb_mae, 1.15 * xgb_mae,
                )

                # Train final LSTM model
                lstm_predictor = LSTMHRVPredictor(predictor._store)
                lstm_predictor.train(
                    X, y, feature_names, valid_dates,
                    lookback_days=body.lstm_lookback_days,
                )
                lstm_predictor.save()

                # Optimize ensemble weight using CV predictions
                # Collect matched XGBoost and LSTM fold predictions
                from app.models.validation import walk_forward_cv
                xgb_cv = walk_forward_cv(
                    X, y, valid_dates, feature_names,
                    min_train_days=90, gap_days=1,
                    params=metadata["best_params"],
                    compute_shap=False,
                )

                # Match folds by test_date
                xgb_fold_map = {f.test_date: f.y_pred for f in xgb_cv.fold_results}
                lstm_fold_map = {f.test_date: f.y_pred for f in lstm_cv.fold_results}
                common_dates = sorted(set(xgb_fold_map) & set(lstm_fold_map))

                if len(common_dates) >= 5:
                    xgb_preds = np.array([xgb_fold_map[d] for d in common_dates])
                    lstm_preds = np.array([lstm_fold_map[d] for d in common_dates])
                    y_common = np.array([
                        next(f.y_true for f in xgb_cv.fold_results if f.test_date == d)
                        for d in common_dates
                    ])

                    ensemble_alpha = optimize_ensemble_weight(xgb_preds, lstm_preds, y_common)

                    # Compute ensemble CV MAE
                    blended = ensemble_alpha * xgb_preds + (1 - ensemble_alpha) * lstm_preds
                    ensemble_cv_mae = float(np.mean(np.abs(blended - y_common)))
                else:
                    ensemble_alpha = 0.5

                # Create and save ensemble
                ensemble = HRVEnsemble(predictor, lstm_predictor, alpha=ensemble_alpha)
                ensemble.save_config(predictor._store)
                request.app.state.hrv_ensemble = ensemble

                logger.info(
                    "Ensemble ready: alpha=%.2f, ensemble_MAE=%.4f",
                    ensemble_alpha, ensemble_cv_mae or 0,
                )
            else:
                logger.info(
                    "LSTM excluded: MAE=%.4f > threshold=%.4f (XGBoost MAE=%.4f)",
                    lstm_cv_mae, 1.15 * xgb_mae, xgb_mae,
                )
                # XGBoost-only ensemble
                ensemble = HRVEnsemble(predictor, lstm_predictor=None)
                ensemble.save_config(predictor._store)
                request.app.state.hrv_ensemble = ensemble

        except Exception:
            logger.exception("LSTM training failed, using XGBoost only")

    # Persist model metadata
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_MODEL_METADATA_QUERY,
            metadata["model_version"],
            metadata["training_days"],
            metadata["cv_mae"],
            metadata["cv_rmse"],
            metadata["cv_r2"],
            metadata["cv_directional_accuracy"],
            json.dumps(metadata["best_params"]),
            metadata["stable_features"],
            metadata["feature_names"],
            json.dumps({"optuna_trials": body.optuna_trials}),
        )

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
        lstm_cv_mae=lstm_cv_mae,
        ensemble_alpha=ensemble_alpha,
        ensemble_cv_mae=ensemble_cv_mae,
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
