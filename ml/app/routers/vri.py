"""VRI (Vitality Recovery Index) API endpoints."""

import datetime
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.quality import get_day_quality
from app.features.sri import compute_sri
from app.features.zscore import compute_rolling_baseline
from app.models.vri_scorer import baseline_maturity_label, compute_vri
from app.schemas.vri import VRIResponse

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_VRI_QUERY = """
SELECT date, vri_score, vri_confidence,
       z_ln_rmssd, z_resting_hr, z_sleep_duration, z_sri, z_spo2, z_deep_sleep, z_br,
       sri_value, sri_days_used, baseline_window_days, metrics_included, computed_at
FROM vri_scores WHERE date = $1::date
"""

FETCH_VRI_RANGE_QUERY = """
SELECT date, vri_score, vri_confidence,
       z_ln_rmssd, z_resting_hr, z_sleep_duration, z_sri, z_spo2, z_deep_sleep, z_br,
       sri_value, sri_days_used, baseline_window_days, metrics_included, computed_at
FROM vri_scores WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

FETCH_TODAY_DATA_QUERY = """
SELECT hrv_daily_rmssd, resting_hr, sleep_duration_min,
       spo2_avg, sleep_deep_min, br_full_sleep
FROM daily_summaries WHERE date = $1::date
"""

UPSERT_VRI_QUERY = """
INSERT INTO vri_scores (
    date, vri_score, vri_confidence,
    z_ln_rmssd, z_resting_hr, z_sleep_duration, z_sri, z_spo2, z_deep_sleep, z_br,
    sri_value, sri_days_used, baseline_window_days, metrics_included
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
ON CONFLICT (date) DO UPDATE SET
    vri_score=$2, vri_confidence=$3,
    z_ln_rmssd=$4, z_resting_hr=$5, z_sleep_duration=$6, z_sri=$7,
    z_spo2=$8, z_deep_sleep=$9, z_br=$10,
    sri_value=$11, sri_days_used=$12, baseline_window_days=$13,
    metrics_included=$14, computed_at=NOW()
"""

UPSERT_BASELINE_QUERY = """
INSERT INTO rolling_baselines (
    date,
    ln_rmssd_median, ln_rmssd_mad, ln_rmssd_count,
    rhr_median, rhr_mad, rhr_count,
    sleep_dur_median, sleep_dur_mad, sleep_dur_count,
    sri_median, sri_mad, sri_count,
    spo2_median, spo2_mad, spo2_count,
    deep_sleep_median, deep_sleep_mad, deep_sleep_count,
    br_median, br_mad, br_count
) VALUES ($1, $2,$3,$4, $5,$6,$7, $8,$9,$10, $11,$12,$13, $14,$15,$16, $17,$18,$19, $20,$21,$22)
ON CONFLICT (date) DO UPDATE SET
    ln_rmssd_median=$2, ln_rmssd_mad=$3, ln_rmssd_count=$4,
    rhr_median=$5, rhr_mad=$6, rhr_count=$7,
    sleep_dur_median=$8, sleep_dur_mad=$9, sleep_dur_count=$10,
    sri_median=$11, sri_mad=$12, sri_count=$13,
    spo2_median=$14, spo2_mad=$15, spo2_count=$16,
    deep_sleep_median=$17, deep_sleep_mad=$18, deep_sleep_count=$19,
    br_median=$20, br_mad=$21, br_count=$22,
    computed_at=NOW()
"""


def _row_to_response(row) -> VRIResponse:
    z_scores = {
        "z_ln_rmssd": row["z_ln_rmssd"],
        "z_resting_hr": row["z_resting_hr"],
        "z_sleep_duration": row["z_sleep_duration"],
        "z_sri": row["z_sri"],
        "z_spo2": row["z_spo2"],
        "z_deep_sleep": row["z_deep_sleep"],
        "z_br": row["z_br"],
    }
    return VRIResponse(
        date=str(row["date"]),
        vri_score=row["vri_score"],
        vri_confidence=row["vri_confidence"],
        sri_value=row["sri_value"],
        sri_days_used=row["sri_days_used"] or 0,
        z_scores=z_scores,
        baseline_window_days=row["baseline_window_days"] or 0,
        metrics_included=row["metrics_included"] or [],
    )


async def _compute_and_persist(pool, date: datetime.date) -> VRIResponse:
    """Compute VRI for a date, persist results, and return response."""
    # 1. Compute baseline
    baseline = await compute_rolling_baseline(pool, date)

    # 2. Compute SRI
    sri_value, sri_days_used = await compute_sri(pool, date)

    # 3. Get today's data
    async with pool.acquire() as conn:
        today_row = await conn.fetchrow(FETCH_TODAY_DATA_QUERY, date)

    if today_row is None:
        return VRIResponse(
            date=str(date),
            vri_score=50.0,
            vri_confidence=0.0,
            baseline_maturity=baseline_maturity_label(baseline),
        )

    today_data = dict(today_row)

    # 4. Get quality confidence
    quality = await get_day_quality(pool, date)
    quality_confidence = quality.get("confidence_score") if quality else None

    # 5. Compute VRI
    vri_score, vri_confidence, z_scores, factors = compute_vri(
        today_data, baseline, sri_value, quality_confidence
    )

    maturity = baseline_maturity_label(baseline)
    metrics_included = [f.metric for f in factors]

    # 6. Persist baseline
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_BASELINE_QUERY,
            date,
            baseline.get("ln_rmssd_median"), baseline.get("ln_rmssd_mad"), baseline.get("ln_rmssd_count"),
            baseline.get("rhr_median"), baseline.get("rhr_mad"), baseline.get("rhr_count"),
            baseline.get("sleep_dur_median"), baseline.get("sleep_dur_mad"), baseline.get("sleep_dur_count"),
            baseline.get("sri_median"), baseline.get("sri_mad"), baseline.get("sri_count"),
            baseline.get("spo2_median"), baseline.get("spo2_mad"), baseline.get("spo2_count"),
            baseline.get("deep_sleep_median"), baseline.get("deep_sleep_mad"), baseline.get("deep_sleep_count"),
            baseline.get("br_median"), baseline.get("br_mad"), baseline.get("br_count"),
        )

        # 7. Persist VRI score
        await conn.execute(
            UPSERT_VRI_QUERY,
            date, vri_score, vri_confidence,
            z_scores.get("z_ln_rmssd"), z_scores.get("z_resting_hr"),
            z_scores.get("z_sleep_duration"), z_scores.get("z_sri"),
            z_scores.get("z_spo2"), z_scores.get("z_deep_sleep"), z_scores.get("z_br"),
            sri_value, sri_days_used, baseline.get("window_days", 60),
            metrics_included,
        )

    return VRIResponse(
        date=str(date),
        vri_score=vri_score,
        vri_confidence=vri_confidence,
        sri_value=sri_value,
        sri_days_used=sri_days_used,
        z_scores=z_scores,
        contributing_factors=factors,
        baseline_window_days=baseline.get("window_days", 60),
        baseline_maturity=maturity,
        metrics_included=metrics_included,
    )


@router.get("/vri", response_model=VRIResponse)
async def get_vri(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    # Check cache first
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_VRI_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    # Compute on demand
    return await _compute_and_persist(pool, date)


@router.get("/vri/range", response_model=list[VRIResponse])
async def get_vri_range(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        rows = await conn.fetch(FETCH_VRI_RANGE_QUERY, start, end)

    return [_row_to_response(row) for row in rows]


@router.post("/vri/backfill")
async def backfill_vri(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    from app.features.vri_batch import backfill_vri as do_backfill

    count = await do_backfill(pool, start, end)
    return {"backfilled": count, "start": str(start), "end": str(end)}
