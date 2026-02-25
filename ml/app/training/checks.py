"""Trainability checks — 3-stage validation before retraining each model."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrainabilityResult:
    trainable: bool
    reason: str
    available_count: int = 0
    new_since_last_train: int = 0
    recent_quality_ok: bool = True


# --- Anomaly ---

async def check_anomaly_trainability(pool) -> TrainabilityResult:
    """Check if anomaly model can be retrained.

    1. Data sufficiency: >= 30 valid days
    2. New data: at least 1 new valid day since last training
    3. Recent quality: >= 3 valid days and >= 40% avg completeness in last 7 days
    """
    async with pool.acquire() as conn:
        # 1. Data sufficiency
        total_valid = await conn.fetchval("""
            SELECT COUNT(*) FROM daily_summaries ds
            JOIN daily_data_quality dq ON ds.date = dq.date
            WHERE dq.is_valid_day IS NOT FALSE
        """)
        if total_valid < 30:
            return TrainabilityResult(
                trainable=False,
                reason=f"Insufficient data: {total_valid} valid days (need >= 30)",
                available_count=total_valid,
            )

        # 2. New data since last training
        last_trained = await conn.fetchval("""
            SELECT trained_at FROM anomaly_model_metadata
            ORDER BY trained_at DESC LIMIT 1
        """)
        if last_trained is not None:
            new_count = await conn.fetchval("""
                SELECT COUNT(*) FROM daily_summaries ds
                JOIN daily_data_quality dq ON ds.date = dq.date
                WHERE ds.date > $1::date
                  AND dq.is_valid_day IS NOT FALSE
            """, last_trained)
        else:
            new_count = total_valid  # Never trained → all data is new

        if new_count == 0:
            return TrainabilityResult(
                trainable=False,
                reason="No new data since last training",
                available_count=total_valid,
                new_since_last_train=0,
            )

        # 3. Recent quality
        quality = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE is_valid_day IS NOT FALSE) AS valid_days,
                COALESCE(AVG(completeness_pct), 0) AS avg_completeness
            FROM daily_data_quality
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """)
        valid_days = quality["valid_days"]
        avg_completeness = quality["avg_completeness"]

        if valid_days < 3 or avg_completeness < 40:
            return TrainabilityResult(
                trainable=False,
                reason=(
                    f"Low recent quality: {valid_days} valid days, "
                    f"{avg_completeness:.0f}% avg completeness"
                ),
                available_count=total_valid,
                new_since_last_train=new_count,
                recent_quality_ok=False,
            )

    return TrainabilityResult(
        trainable=True,
        reason="Ready to train",
        available_count=total_valid,
        new_since_last_train=new_count,
        recent_quality_ok=True,
    )


# --- HRV ---

async def check_hrv_trainability(pool) -> TrainabilityResult:
    """Check if HRV model can be retrained.

    1. Data sufficiency: >= 90 valid days with non-null HRV target
    2. New data: at least 1 new valid day since last training
    3. Recent quality: >= 3 valid days and >= 40% avg completeness in last 7 days
    """
    async with pool.acquire() as conn:
        # 1. Data sufficiency (need HRV target)
        total_valid = await conn.fetchval("""
            SELECT COUNT(*) FROM daily_summaries ds
            JOIN daily_data_quality dq ON ds.date = dq.date
            WHERE dq.is_valid_day IS NOT FALSE
              AND ds.ln_rmssd_mean IS NOT NULL
        """)
        if total_valid < 90:
            return TrainabilityResult(
                trainable=False,
                reason=f"Insufficient data: {total_valid} valid days with HRV (need >= 90)",
                available_count=total_valid,
            )

        # 2. New data since last training
        last_trained = await conn.fetchval("""
            SELECT trained_at FROM hrv_model_metadata
            ORDER BY trained_at DESC LIMIT 1
        """)
        if last_trained is not None:
            new_count = await conn.fetchval("""
                SELECT COUNT(*) FROM daily_summaries ds
                JOIN daily_data_quality dq ON ds.date = dq.date
                WHERE ds.date > $1::date
                  AND dq.is_valid_day IS NOT FALSE
                  AND ds.ln_rmssd_mean IS NOT NULL
            """, last_trained)
        else:
            new_count = total_valid

        if new_count == 0:
            return TrainabilityResult(
                trainable=False,
                reason="No new data since last training",
                available_count=total_valid,
                new_since_last_train=0,
            )

        # 3. Recent quality
        quality = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE is_valid_day IS NOT FALSE) AS valid_days,
                COALESCE(AVG(completeness_pct), 0) AS avg_completeness
            FROM daily_data_quality
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """)
        valid_days = quality["valid_days"]
        avg_completeness = quality["avg_completeness"]

        if valid_days < 3 or avg_completeness < 40:
            return TrainabilityResult(
                trainable=False,
                reason=(
                    f"Low recent quality: {valid_days} valid days, "
                    f"{avg_completeness:.0f}% avg completeness"
                ),
                available_count=total_valid,
                new_since_last_train=new_count,
                recent_quality_ok=False,
            )

    return TrainabilityResult(
        trainable=True,
        reason="Ready to train",
        available_count=total_valid,
        new_since_last_train=new_count,
        recent_quality_ok=True,
    )


# --- Divergence ---

async def check_divergence_trainability(pool) -> TrainabilityResult:
    """Check if divergence model can be retrained.

    1. Data sufficiency: >= 14 paired observations (condition_logs + daily_summaries)
    2. New data: at least 1 new condition log since last training
    3. Recent quality: >= 3 valid days and >= 40% avg completeness in last 7 days
    """
    async with pool.acquire() as conn:
        # 1. Data sufficiency (paired observations)
        total_pairs = await conn.fetchval("""
            SELECT COUNT(*) FROM condition_logs cl
            JOIN daily_summaries ds ON cl.logged_at::date = ds.date
            JOIN daily_data_quality dq ON ds.date = dq.date
            WHERE dq.is_valid_day IS NOT FALSE
        """)
        if total_pairs < 14:
            return TrainabilityResult(
                trainable=False,
                reason=f"Insufficient paired data: {total_pairs} pairs (need >= 14)",
                available_count=total_pairs,
            )

        # 2. New data since last training
        last_trained = await conn.fetchval("""
            SELECT trained_at FROM divergence_model_metadata
            ORDER BY trained_at DESC LIMIT 1
        """)
        if last_trained is not None:
            new_count = await conn.fetchval("""
                SELECT COUNT(*) FROM condition_logs
                WHERE logged_at::date > $1::date
            """, last_trained)
        else:
            new_count = total_pairs

        if new_count == 0:
            return TrainabilityResult(
                trainable=False,
                reason="No new condition logs since last training",
                available_count=total_pairs,
                new_since_last_train=0,
            )

        # 3. Recent quality
        quality = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE is_valid_day IS NOT FALSE) AS valid_days,
                COALESCE(AVG(completeness_pct), 0) AS avg_completeness
            FROM daily_data_quality
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """)
        valid_days = quality["valid_days"]
        avg_completeness = quality["avg_completeness"]

        if valid_days < 3 or avg_completeness < 40:
            return TrainabilityResult(
                trainable=False,
                reason=(
                    f"Low recent quality: {valid_days} valid days, "
                    f"{avg_completeness:.0f}% avg completeness"
                ),
                available_count=total_pairs,
                new_since_last_train=new_count,
                recent_quality_ok=False,
            )

    return TrainabilityResult(
        trainable=True,
        reason="Ready to train",
        available_count=total_pairs,
        new_since_last_train=new_count,
        recent_quality_ok=True,
    )
