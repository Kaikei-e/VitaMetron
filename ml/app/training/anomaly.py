"""Anomaly model training logic extracted from router."""

import datetime
import json
import logging

from app.features.anomaly_features import extract_anomaly_training_matrix
from app.training.errors import InsufficientDataError

logger = logging.getLogger(__name__)

UPSERT_MODEL_METADATA_QUERY = """
INSERT INTO anomaly_model_metadata (
    model_version, training_days, contamination, pot_threshold, feature_names, config
) VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (model_version) DO UPDATE SET
    training_days=$2, contamination=$3, pot_threshold=$4,
    feature_names=$5, config=$6, trained_at=NOW()
"""

MIN_TRAINING_DAYS = 30


async def train_anomaly(
    pool,
    detector,
    *,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    contamination: float = 0.02,
    n_estimators: int = 200,
) -> dict:
    """Train anomaly detection model and persist metadata.

    Returns metadata dict with model_version, training_days, etc.
    Raises InsufficientDataError if not enough data.
    """
    end_date = end_date or datetime.date.today()
    if start_date is None:
        async with pool.acquire() as conn:
            earliest = await conn.fetchval("SELECT MIN(date) FROM daily_summaries")
        start_date = earliest or (end_date - datetime.timedelta(days=180))

    X, feature_names, valid_dates = await extract_anomaly_training_matrix(
        pool, start_date, end_date
    )

    if X.shape[0] < MIN_TRAINING_DAYS:
        raise InsufficientDataError("anomaly", X.shape[0], MIN_TRAINING_DAYS)

    logger.info("Training anomaly model: %d days", X.shape[0])

    metadata = detector.train(
        X, feature_names, contamination=contamination, n_estimators=n_estimators
    )
    detector.save()

    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_MODEL_METADATA_QUERY,
            metadata["model_version"],
            metadata["training_days"],
            metadata["contamination"],
            metadata["pot_threshold"],
            metadata["feature_names"],
            json.dumps({"n_estimators": metadata["n_estimators"]}),
        )

    logger.info("Anomaly model trained: %s (%d days)", metadata["model_version"], metadata["training_days"])
    return metadata
