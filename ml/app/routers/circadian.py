"""Circadian Health Score (CHS) API endpoints."""

import datetime
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.circadian import (
    compute_hr_cosinor,
    compute_nocturnal_hr_dip,
    compute_npar_metrics,
    compute_sleep_timing,
)
from app.features.sri import compute_sri
from app.models.circadian_scorer import (
    baseline_maturity_label,
    compute_circadian_baseline,
    compute_chs,
)
from app.schemas.circadian import (
    CHSMetricContribution,
    CircadianResponse,
    CosinorDetail,
    NocturnalDipDetail,
    NPARDetail,
    SleepTimingDetail,
)

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_CHS_QUERY = """
SELECT date, chs_score, chs_confidence,
       cosinor_mesor, cosinor_amplitude, cosinor_acrophase_hour,
       npar_is, npar_iv, npar_ra, npar_m10, npar_m10_start, npar_l5, npar_l5_start,
       sleep_midpoint_hour, sleep_midpoint_var_min, social_jetlag_min,
       nocturnal_dip_pct, daytime_mean_hr, nighttime_mean_hr,
       z_rhythm_strength, z_rhythm_stability, z_rhythm_fragmentation,
       z_sleep_regularity, z_phase_alignment,
       sri_value, baseline_window_days, metrics_included, computed_at
FROM circadian_scores WHERE date = $1::date
"""

FETCH_CHS_RANGE_QUERY = """
SELECT date, chs_score, chs_confidence,
       cosinor_mesor, cosinor_amplitude, cosinor_acrophase_hour,
       npar_is, npar_iv, npar_ra, npar_m10, npar_m10_start, npar_l5, npar_l5_start,
       sleep_midpoint_hour, sleep_midpoint_var_min, social_jetlag_min,
       nocturnal_dip_pct, daytime_mean_hr, nighttime_mean_hr,
       z_rhythm_strength, z_rhythm_stability, z_rhythm_fragmentation,
       z_sleep_regularity, z_phase_alignment,
       sri_value, baseline_window_days, metrics_included, computed_at
FROM circadian_scores WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

UPSERT_CHS_QUERY = """
INSERT INTO circadian_scores (
    date, chs_score, chs_confidence,
    cosinor_mesor, cosinor_amplitude, cosinor_acrophase_hour,
    npar_is, npar_iv, npar_ra, npar_m10, npar_m10_start, npar_l5, npar_l5_start,
    sleep_midpoint_hour, sleep_midpoint_var_min, social_jetlag_min,
    nocturnal_dip_pct, daytime_mean_hr, nighttime_mean_hr,
    z_rhythm_strength, z_rhythm_stability, z_rhythm_fragmentation,
    z_sleep_regularity, z_phase_alignment,
    sri_value, baseline_window_days, metrics_included
) VALUES (
    $1, $2, $3,
    $4, $5, $6,
    $7, $8, $9, $10, $11, $12, $13,
    $14, $15, $16,
    $17, $18, $19,
    $20, $21, $22, $23, $24,
    $25, $26, $27
)
ON CONFLICT (date) DO UPDATE SET
    chs_score=$2, chs_confidence=$3,
    cosinor_mesor=$4, cosinor_amplitude=$5, cosinor_acrophase_hour=$6,
    npar_is=$7, npar_iv=$8, npar_ra=$9, npar_m10=$10, npar_m10_start=$11,
    npar_l5=$12, npar_l5_start=$13,
    sleep_midpoint_hour=$14, sleep_midpoint_var_min=$15, social_jetlag_min=$16,
    nocturnal_dip_pct=$17, daytime_mean_hr=$18, nighttime_mean_hr=$19,
    z_rhythm_strength=$20, z_rhythm_stability=$21, z_rhythm_fragmentation=$22,
    z_sleep_regularity=$23, z_phase_alignment=$24,
    sri_value=$25, baseline_window_days=$26, metrics_included=$27,
    computed_at=NOW()
"""

UPSERT_BASELINE_QUERY = """
INSERT INTO circadian_baselines (
    date,
    amplitude_median, amplitude_mad, amplitude_count,
    is_median, is_mad, is_count,
    iv_median, iv_mad, iv_count,
    midpoint_var_median, midpoint_var_mad, midpoint_var_count,
    dip_pct_median, dip_pct_mad, dip_pct_count
) VALUES ($1, $2,$3,$4, $5,$6,$7, $8,$9,$10, $11,$12,$13, $14,$15,$16)
ON CONFLICT (date) DO UPDATE SET
    amplitude_median=$2, amplitude_mad=$3, amplitude_count=$4,
    is_median=$5, is_mad=$6, is_count=$7,
    iv_median=$8, iv_mad=$9, iv_count=$10,
    midpoint_var_median=$11, midpoint_var_mad=$12, midpoint_var_count=$13,
    dip_pct_median=$14, dip_pct_mad=$15, dip_pct_count=$16,
    computed_at=NOW()
"""


def _factors_from_z_scores(
    z_scores: dict[str, float | None],
) -> list[CHSMetricContribution]:
    """Reconstruct contributing factors from cached z-scores."""
    _directions: dict[str, tuple[str, int]] = {
        "z_rhythm_strength": ("rhythm_strength", 1),
        "z_rhythm_stability": ("rhythm_stability", 1),
        "z_rhythm_fragmentation": ("rhythm_fragmentation", -1),
        "z_sleep_regularity": ("sleep_regularity", -1),
        "z_phase_alignment": ("phase_alignment", 1),
    }
    factors: list[CHSMetricContribution] = []
    for z_key, (metric, direction) in _directions.items():
        z = z_scores.get(z_key)
        if z is None:
            continue
        directed_z = z * direction
        factors.append(CHSMetricContribution(
            metric=metric,
            z_score=round(z, 3),
            directed_z=round(directed_z, 3),
            direction="positive" if directed_z > 0 else "negative",
            contribution=round(abs(directed_z), 3),
        ))
    factors.sort(key=lambda f: f.contribution, reverse=True)
    return factors


def _row_to_response(row) -> CircadianResponse:
    z_scores = {
        "z_rhythm_strength": row["z_rhythm_strength"],
        "z_rhythm_stability": row["z_rhythm_stability"],
        "z_rhythm_fragmentation": row["z_rhythm_fragmentation"],
        "z_sleep_regularity": row["z_sleep_regularity"],
        "z_phase_alignment": row["z_phase_alignment"],
    }

    cosinor = None
    if row["cosinor_mesor"] is not None:
        cosinor = CosinorDetail(
            mesor=row["cosinor_mesor"],
            amplitude=row["cosinor_amplitude"],
            acrophase_hour=row["cosinor_acrophase_hour"],
        )

    npar = None
    if row["npar_is"] is not None:
        npar = NPARDetail(
            is_value=row["npar_is"],
            iv_value=row["npar_iv"],
            ra_value=row["npar_ra"],
            m10_value=row["npar_m10"],
            m10_start_hour=row["npar_m10_start"],
            l5_value=row["npar_l5"],
            l5_start_hour=row["npar_l5_start"],
        )

    sleep_timing = None
    if row["sleep_midpoint_hour"] is not None:
        sleep_timing = SleepTimingDetail(
            midpoint_hour=row["sleep_midpoint_hour"],
            midpoint_variability_min=row["sleep_midpoint_var_min"],
            social_jetlag_min=row["social_jetlag_min"],
        )

    nocturnal_dip = None
    if row["nocturnal_dip_pct"] is not None:
        nocturnal_dip = NocturnalDipDetail(
            dip_pct=row["nocturnal_dip_pct"],
            daytime_mean_hr=row["daytime_mean_hr"],
            nighttime_mean_hr=row["nighttime_mean_hr"],
        )

    return CircadianResponse(
        date=str(row["date"]),
        chs_score=row["chs_score"],
        chs_confidence=row["chs_confidence"],
        cosinor=cosinor,
        npar=npar,
        sleep_timing=sleep_timing,
        nocturnal_dip=nocturnal_dip,
        sri_value=row["sri_value"],
        z_scores=z_scores,
        contributing_factors=_factors_from_z_scores(z_scores),
        baseline_window_days=row["baseline_window_days"] or 0,
        metrics_included=row["metrics_included"] or [],
    )


async def _compute_and_persist(pool, date: datetime.date) -> CircadianResponse:
    """Compute circadian metrics, persist results, and return response."""
    # 1. Compute all circadian features in parallel
    cosinor = await compute_hr_cosinor(pool, date)
    npar = await compute_npar_metrics(pool, date)
    sleep_timing = await compute_sleep_timing(pool, date)
    nocturnal_dip = await compute_nocturnal_hr_dip(pool, date)
    sri_value, _ = await compute_sri(pool, date)

    # 2. Build data dict for scorer
    circadian_data: dict = {}
    if cosinor:
        circadian_data["cosinor_amplitude"] = cosinor.amplitude
    if npar:
        circadian_data["npar_is"] = npar.is_value
        circadian_data["npar_iv"] = npar.iv_value
    if sleep_timing:
        circadian_data["sleep_midpoint_var_min"] = sleep_timing.midpoint_variability_min
    if nocturnal_dip:
        circadian_data["nocturnal_dip_pct"] = nocturnal_dip.dip_pct

    # 3. Compute baseline
    baseline = await compute_circadian_baseline(pool, date)

    # 4. Compute CHS
    chs_score, chs_confidence, z_scores, factors = compute_chs(
        circadian_data, baseline,
    )

    maturity = baseline_maturity_label(baseline)
    metrics_included = [f.metric for f in factors]

    # 5. Persist baseline
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_BASELINE_QUERY,
            date,
            baseline.get("amplitude_median"), baseline.get("amplitude_mad"),
            baseline.get("amplitude_count"),
            baseline.get("is_median"), baseline.get("is_mad"),
            baseline.get("is_count"),
            baseline.get("iv_median"), baseline.get("iv_mad"),
            baseline.get("iv_count"),
            baseline.get("midpoint_var_median"), baseline.get("midpoint_var_mad"),
            baseline.get("midpoint_var_count"),
            baseline.get("dip_pct_median"), baseline.get("dip_pct_mad"),
            baseline.get("dip_pct_count"),
        )

        # 6. Persist CHS score
        await conn.execute(
            UPSERT_CHS_QUERY,
            date, chs_score, chs_confidence,
            cosinor.mesor if cosinor else None,
            cosinor.amplitude if cosinor else None,
            cosinor.acrophase_hour if cosinor else None,
            npar.is_value if npar else None,
            npar.iv_value if npar else None,
            npar.ra_value if npar else None,
            npar.m10_value if npar else None,
            npar.m10_start_hour if npar else None,
            npar.l5_value if npar else None,
            npar.l5_start_hour if npar else None,
            sleep_timing.midpoint_hour if sleep_timing else None,
            sleep_timing.midpoint_variability_min if sleep_timing else None,
            sleep_timing.social_jetlag_min if sleep_timing else None,
            nocturnal_dip.dip_pct if nocturnal_dip else None,
            nocturnal_dip.daytime_mean_hr if nocturnal_dip else None,
            nocturnal_dip.nighttime_mean_hr if nocturnal_dip else None,
            z_scores.get("z_rhythm_strength"),
            z_scores.get("z_rhythm_stability"),
            z_scores.get("z_rhythm_fragmentation"),
            z_scores.get("z_sleep_regularity"),
            z_scores.get("z_phase_alignment"),
            sri_value,
            baseline.get("window_days", 60),
            metrics_included,
        )

    return CircadianResponse(
        date=str(date),
        chs_score=chs_score,
        chs_confidence=chs_confidence,
        cosinor=CosinorDetail(
            mesor=cosinor.mesor,
            amplitude=cosinor.amplitude,
            acrophase_hour=cosinor.acrophase_hour,
        ) if cosinor else None,
        npar=NPARDetail(
            is_value=npar.is_value,
            iv_value=npar.iv_value,
            ra_value=npar.ra_value,
            m10_value=npar.m10_value,
            m10_start_hour=npar.m10_start_hour,
            l5_value=npar.l5_value,
            l5_start_hour=npar.l5_start_hour,
        ) if npar else None,
        sleep_timing=SleepTimingDetail(
            midpoint_hour=sleep_timing.midpoint_hour,
            midpoint_variability_min=sleep_timing.midpoint_variability_min,
            social_jetlag_min=sleep_timing.social_jetlag_min,
        ) if sleep_timing else None,
        nocturnal_dip=NocturnalDipDetail(
            dip_pct=nocturnal_dip.dip_pct,
            daytime_mean_hr=nocturnal_dip.daytime_mean_hr,
            nighttime_mean_hr=nocturnal_dip.nighttime_mean_hr,
        ) if nocturnal_dip else None,
        sri_value=sri_value,
        z_scores=z_scores,
        contributing_factors=factors,
        baseline_window_days=baseline.get("window_days", 60),
        baseline_maturity=maturity,
        metrics_included=metrics_included,
    )


@router.get("/circadian", response_model=CircadianResponse)
async def get_circadian(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    # Today → always recompute
    if date >= datetime.date.today():
        return await _compute_and_persist(pool, date)

    # Past dates → serve cache if available
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_CHS_QUERY, date)

    if row is not None:
        return _row_to_response(row)

    return await _compute_and_persist(pool, date)


@router.get("/circadian/range", response_model=list[CircadianResponse])
async def get_circadian_range(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        rows = await conn.fetch(FETCH_CHS_RANGE_QUERY, start, end)

    return [_row_to_response(row) for row in rows]


@router.post("/circadian/backfill")
async def backfill_circadian(
    request: Request,
    start: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    from app.features.circadian_batch import backfill_circadian as do_backfill

    count = await do_backfill(pool, start, end)
    return {"backfilled": count, "start": str(start), "end": str(end)}
