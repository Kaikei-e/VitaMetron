"""Divergence model training logic extracted from router."""

import datetime
import json
import logging

import numpy as np

from app.features.divergence_features import extract_divergence_training_pairs
from app.training.errors import InsufficientDataError

logger = logging.getLogger(__name__)

LEGACY_DATES = {
    datetime.date(2026, 2, 15),
    datetime.date(2026, 2, 16),
    datetime.date(2026, 2, 17),
}

UPSERT_MODEL_METADATA_QUERY = """
INSERT INTO divergence_model_metadata (
    model_version, training_pairs, r2_score, mae, rmse,
    residual_mean, residual_std, feature_names, config
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (model_version) DO UPDATE SET
    training_pairs=$2, r2_score=$3, mae=$4, rmse=$5,
    residual_mean=$6, residual_std=$7, feature_names=$8,
    config=$9, trained_at=NOW()
"""


async def train_divergence(
    pool,
    detector,
    *,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> dict:
    """Train divergence detection model and persist metadata.

    Returns metadata dict.
    Raises InsufficientDataError if not enough paired observations.
    """
    end_date = end_date or datetime.date.today()
    if start_date is None:
        async with pool.acquire() as conn:
            earliest = await conn.fetchval("SELECT MIN(date) FROM daily_summaries")
        start_date = earliest or (end_date - datetime.timedelta(days=365))

    X, y, feature_names, dates, log_ids = await extract_divergence_training_pairs(
        pool, start_date, end_date
    )

    # Exclude legacy backfill dates
    mask = np.array([d not in LEGACY_DATES for d in dates], dtype=bool)
    n_excluded = int(np.sum(~mask))
    X, y = X[mask], y[mask]
    dates = [d for d, m in zip(dates, mask) if m]
    log_ids = [lid for lid, m in zip(log_ids, mask) if m]

    if X.shape[0] < detector.MIN_PAIRS_INITIAL:
        raise InsufficientDataError("divergence", X.shape[0], detector.MIN_PAIRS_INITIAL)

    logger.info("Training divergence: %d pairs (%d legacy excluded)", X.shape[0], n_excluded)

    metadata = detector.train(X, y, feature_names, use_logit=True)
    detector.save()

    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_MODEL_METADATA_QUERY,
            metadata["model_version"],
            metadata["training_pairs"],
            metadata["r2_score"],
            metadata["mae"],
            metadata["rmse"],
            metadata["residual_mean"],
            metadata["residual_std"],
            metadata["feature_names"],
            json.dumps({
                "alpha": 1.0,
                "logit_transform": True,
                "legacy_excluded_dates": sorted(str(d) for d in LEGACY_DATES),
                "n_excluded": n_excluded,
            }),
        )

    logger.info(
        "Divergence model trained: %s (%d pairs)",
        metadata["model_version"], metadata["training_pairs"],
    )
    return metadata
