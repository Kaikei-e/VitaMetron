"""HRV model training logic extracted from router."""

import datetime
import json
import logging

import numpy as np

from app.features.hrv_features import extract_hrv_training_matrix
from app.models.ensemble_hrv import HRVEnsemble, optimize_ensemble_weight
from app.models.lstm_predictor import LSTMHRVPredictor
from app.models.validation import walk_forward_cv, walk_forward_cv_lstm
from app.training.errors import InsufficientDataError

logger = logging.getLogger(__name__)

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

MIN_TRAINING_DAYS = 90


async def train_hrv(
    pool,
    predictor,
    *,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    optuna_trials: int = 100,
    include_lstm: bool = True,
    lstm_lookback_days: int = 7,
) -> tuple[dict, HRVEnsemble | None]:
    """Train HRV prediction model (XGBoost + optional LSTM).

    Args:
        optuna_trials: 0 to reuse previous best_params (daily mode), >0 for Optuna search.
        include_lstm: Whether to train LSTM and build ensemble.
        lstm_lookback_days: Lookback window for LSTM sequences.

    Returns:
        (metadata_dict, ensemble_or_none)
    Raises InsufficientDataError if not enough data.
    """
    end_date = end_date or datetime.date.today()
    if start_date is None:
        async with pool.acquire() as conn:
            earliest = await conn.fetchval("SELECT MIN(date) FROM daily_summaries")
        start_date = earliest or (end_date - datetime.timedelta(days=365))

    X, y, feature_names, valid_dates = await extract_hrv_training_matrix(
        pool, start_date, end_date
    )

    if X.shape[0] < MIN_TRAINING_DAYS:
        raise InsufficientDataError("hrv", X.shape[0], MIN_TRAINING_DAYS)

    # If optuna_trials=0, reuse previous best_params (daily lightweight mode)
    actual_trials = optuna_trials
    if optuna_trials == 0 and predictor.is_ready and predictor._best_params:
        logger.info("HRV daily mode: reusing previous best_params (skipping Optuna)")
        actual_trials = 0
    elif optuna_trials == 0:
        # No previous params available, use minimal search
        logger.info("HRV daily mode: no previous params, using minimal Optuna (10 trials)")
        actual_trials = 10

    logger.info("Training HRV model: %d days, optuna_trials=%d", X.shape[0], actual_trials)

    metadata = predictor.train(
        X, y, feature_names, valid_dates, optuna_trials=max(actual_trials, 1)
    )
    predictor.save()

    xgb_mae = metadata["cv_mae"]
    lstm_cv_mae = None
    ensemble_alpha = None
    ensemble_cv_mae = None
    ensemble = None

    # Optionally train LSTM
    if include_lstm and X.shape[0] >= lstm_lookback_days + 30:
        try:
            logger.info("Training LSTM with lookback=%d...", lstm_lookback_days)

            lstm_cv = walk_forward_cv_lstm(
                X, y, valid_dates, feature_names,
                lookback=lstm_lookback_days,
                min_train_days=90,
                gap_days=1,
                max_epochs=200,
                patience=15,
            )
            lstm_cv_mae = lstm_cv.mae

            if lstm_cv_mae <= 1.15 * xgb_mae:
                logger.info(
                    "LSTM included: MAE=%.4f (XGBoost=%.4f)",
                    lstm_cv_mae, xgb_mae,
                )

                lstm_predictor = LSTMHRVPredictor(predictor._store)
                lstm_predictor.train(
                    X, y, feature_names, valid_dates,
                    lookback_days=lstm_lookback_days,
                )
                lstm_predictor.save()

                xgb_cv = walk_forward_cv(
                    X, y, valid_dates, feature_names,
                    min_train_days=90, gap_days=1,
                    params=metadata["best_params"],
                    compute_shap=False,
                )

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
                    blended = ensemble_alpha * xgb_preds + (1 - ensemble_alpha) * lstm_preds
                    ensemble_cv_mae = float(np.mean(np.abs(blended - y_common)))
                else:
                    ensemble_alpha = 0.5

                ensemble = HRVEnsemble(predictor, lstm_predictor, alpha=ensemble_alpha)
                ensemble.save_config(predictor._store)
                logger.info("Ensemble ready: alpha=%.2f", ensemble_alpha)
            else:
                logger.info(
                    "LSTM excluded: MAE=%.4f > threshold=%.4f",
                    lstm_cv_mae, 1.15 * xgb_mae,
                )
                ensemble = HRVEnsemble(predictor, lstm_predictor=None)
                ensemble.save_config(predictor._store)

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
            json.dumps({
                "optuna_trials": actual_trials,
                "include_lstm": include_lstm,
                "lstm_cv_mae": lstm_cv_mae,
                "ensemble_alpha": ensemble_alpha,
                "ensemble_cv_mae": ensemble_cv_mae,
            }),
        )

    metadata["lstm_cv_mae"] = lstm_cv_mae
    metadata["ensemble_alpha"] = ensemble_alpha
    metadata["ensemble_cv_mae"] = ensemble_cv_mae

    logger.info(
        "HRV model trained: %s (%d days, optuna=%d)",
        metadata["model_version"], metadata["training_days"], actual_trials,
    )
    return metadata, ensemble
