"""Retrain orchestrator — coordinates model retraining with trainability checks."""

import logging
import time

from app.training.checks import (
    check_anomaly_trainability,
    check_divergence_trainability,
    check_hrv_trainability,
)
from app.training.anomaly import train_anomaly
from app.training.divergence import train_divergence
from app.training.hrv import train_hrv

logger = logging.getLogger(__name__)

INSERT_RETRAIN_LOG = """
INSERT INTO retrain_logs (
    started_at, trigger, retrain_mode,
    anomaly_status, anomaly_message, anomaly_model_version, anomaly_training_days,
    hrv_status, hrv_message, hrv_model_version, hrv_training_days,
    hrv_optuna_trials, hrv_cv_mae,
    divergence_status, divergence_message, divergence_model_version,
    divergence_training_pairs, divergence_r2,
    completed_at, duration_seconds
) VALUES (
    $1, $2, $3,
    $4, $5, $6, $7,
    $8, $9, $10, $11, $12, $13,
    $14, $15, $16, $17, $18,
    NOW(), $19
)
RETURNING id
"""


async def run_retrain(app, *, trigger: str = "scheduled", mode: str = "daily") -> dict:
    """Run retraining for all eligible models.

    Args:
        app: FastAPI app instance (for access to app.state).
        trigger: "scheduled" or "manual".
        mode: "daily" (lightweight) or "weekly" (full Optuna + LSTM).

    Returns dict with per-model results.
    """
    pool = app.state.db_pool
    t0 = time.monotonic()

    import datetime
    started_at = datetime.datetime.now(datetime.timezone.utc)

    logger.info("=== Retrain started: trigger=%s, mode=%s ===", trigger, mode)

    results = {
        "trigger": trigger,
        "mode": mode,
        "anomaly": {"status": "pending"},
        "hrv": {"status": "pending"},
        "divergence": {"status": "pending"},
    }

    # --- Anomaly ---
    try:
        check = await check_anomaly_trainability(pool)
        if check.trainable:
            detector = app.state.anomaly_detector
            metadata = await train_anomaly(pool, detector)
            results["anomaly"] = {
                "status": "success",
                "message": f"Trained on {metadata['training_days']} days",
                "model_version": metadata["model_version"],
                "training_days": metadata["training_days"],
            }
        else:
            results["anomaly"] = {
                "status": "skipped",
                "message": check.reason,
            }
    except Exception as e:
        logger.exception("Anomaly retrain failed")
        results["anomaly"] = {"status": "error", "message": str(e)}

    # --- HRV ---
    try:
        check = await check_hrv_trainability(pool)
        if check.trainable:
            predictor = app.state.hrv_predictor

            if mode == "weekly":
                optuna_trials = 50
                include_lstm = True
            else:
                optuna_trials = 0
                include_lstm = False

            metadata, ensemble = await train_hrv(
                pool,
                predictor,
                optuna_trials=optuna_trials,
                include_lstm=include_lstm,
            )

            if ensemble is not None:
                app.state.hrv_ensemble = ensemble

            results["hrv"] = {
                "status": "success",
                "message": f"Trained on {metadata['training_days']} days (optuna={optuna_trials})",
                "model_version": metadata["model_version"],
                "training_days": metadata["training_days"],
                "optuna_trials": optuna_trials,
                "cv_mae": metadata.get("cv_mae"),
            }
        else:
            results["hrv"] = {
                "status": "skipped",
                "message": check.reason,
            }
    except Exception as e:
        logger.exception("HRV retrain failed")
        results["hrv"] = {"status": "error", "message": str(e)}

    # --- Divergence ---
    try:
        check = await check_divergence_trainability(pool)
        if check.trainable:
            detector = app.state.divergence_detector
            metadata = await train_divergence(pool, detector)
            results["divergence"] = {
                "status": "success",
                "message": f"Trained on {metadata['training_pairs']} pairs",
                "model_version": metadata["model_version"],
                "training_pairs": metadata["training_pairs"],
                "r2": metadata.get("r2_score"),
            }
        else:
            results["divergence"] = {
                "status": "skipped",
                "message": check.reason,
            }
    except Exception as e:
        logger.exception("Divergence retrain failed")
        results["divergence"] = {"status": "error", "message": str(e)}

    duration = time.monotonic() - t0
    results["duration_seconds"] = round(duration, 2)

    # Persist audit log
    try:
        async with pool.acquire() as conn:
            log_id = await conn.fetchval(
                INSERT_RETRAIN_LOG,
                started_at,
                trigger,
                mode,
                # anomaly
                results["anomaly"]["status"],
                results["anomaly"].get("message"),
                results["anomaly"].get("model_version"),
                results["anomaly"].get("training_days"),
                # hrv
                results["hrv"]["status"],
                results["hrv"].get("message"),
                results["hrv"].get("model_version"),
                results["hrv"].get("training_days"),
                results["hrv"].get("optuna_trials"),
                results["hrv"].get("cv_mae"),
                # divergence
                results["divergence"]["status"],
                results["divergence"].get("message"),
                results["divergence"].get("model_version"),
                results["divergence"].get("training_pairs"),
                results["divergence"].get("r2"),
                # duration
                round(duration, 2),
            )
        results["log_id"] = log_id
        logger.info("Retrain log saved: id=%d", log_id)
    except Exception:
        logger.exception("Failed to save retrain log")

    logger.info(
        "=== Retrain completed: duration=%.1fs, anomaly=%s, hrv=%s, divergence=%s ===",
        duration,
        results["anomaly"]["status"],
        results["hrv"]["status"],
        results["divergence"]["status"],
    )

    return results
