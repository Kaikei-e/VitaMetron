import datetime
import logging

from fastapi import APIRouter, Query, Request

from app.features.pipeline import extract_features
from app.models.risk_detector import detect_risks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/risk", response_model=list[str])
async def detect_risk_signals(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    features = await extract_features(pool, date)
    if features is None:
        return []

    return detect_risks(features)
