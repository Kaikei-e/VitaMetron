import datetime
import logging

from fastapi import APIRouter, Query, Request

from app.schemas.prediction import WeeklyInsightResponse

logger = logging.getLogger(__name__)

router = APIRouter()

WEEKLY_QUERY = """
SELECT
    date,
    resting_hr,
    hrv_daily_rmssd,
    sleep_duration_min,
    sleep_deep_min,
    steps,
    spo2_avg
FROM daily_summaries
WHERE date BETWEEN $1 AND $2
ORDER BY date
"""

CONDITION_QUERY = """
SELECT avg(overall) AS avg_score
FROM condition_logs
WHERE logged_at::date BETWEEN $1 AND $2
"""


@router.get("/insights/weekly", response_model=WeeklyInsightResponse)
async def weekly_insights(
    request: Request,
    date: datetime.date = Query(..., description="End date for the 7-day review window (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    # Past 7 days ending on the given date
    week_end = date
    week_start = date - datetime.timedelta(days=6)

    async with pool.acquire() as conn:
        rows = await conn.fetch(WEEKLY_QUERY, week_start, week_end)
        score_row = await conn.fetchrow(CONDITION_QUERY, week_start, week_end)

    avg_score = float(score_row["avg_score"]) if score_row and score_row["avg_score"] else None

    if len(rows) < 3:
        return WeeklyInsightResponse(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            avg_score=avg_score,
            trend="insufficient_data",
        )

    # Simple trend detection: compare first half vs second half averages
    mid = len(rows) // 2
    top_factors: list[str] = []
    risk_summary: list[str] = []

    def safe_avg(key: str, row_slice: list) -> float | None:
        vals = [r[key] for r in row_slice if r[key] is not None]
        return sum(vals) / len(vals) if vals else None

    hrv_first = safe_avg("hrv_daily_rmssd", rows[:mid])
    hrv_second = safe_avg("hrv_daily_rmssd", rows[mid:])
    if hrv_first is not None and hrv_second is not None:
        if hrv_second > hrv_first * 1.05:
            top_factors.append("HRV improving")
        elif hrv_second < hrv_first * 0.95:
            risk_summary.append("HRV declining through week")

    sleep_first = safe_avg("sleep_duration_min", rows[:mid])
    sleep_second = safe_avg("sleep_duration_min", rows[mid:])
    if sleep_first is not None and sleep_second is not None:
        if sleep_second > sleep_first:
            top_factors.append("Sleep duration improving")
        elif sleep_second < sleep_first * 0.9:
            risk_summary.append("Sleep duration declining")

    steps_first = safe_avg("steps", rows[:mid])
    steps_second = safe_avg("steps", rows[mid:])
    if steps_first is not None and steps_second is not None:
        if steps_second > steps_first * 1.1:
            top_factors.append("Activity level increasing")

    # Overall trend
    if len(top_factors) > len(risk_summary):
        trend = "improving"
    elif len(risk_summary) > len(top_factors):
        trend = "declining"
    else:
        trend = "stable"

    return WeeklyInsightResponse(
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        avg_score=round(avg_score, 2) if avg_score else None,
        trend=trend,
        top_factors=top_factors,
        risk_summary=risk_summary,
    )
