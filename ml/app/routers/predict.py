import datetime
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.features.hrv_features import extract_hrv_prediction_features
from app.features.pipeline import extract_features
from app.models.condition_scorer import rule_based_score
from app.models.risk_detector import detect_risks
from app.schemas.prediction import ContributingFactor, PredictionResponse

logger = logging.getLogger(__name__)

router = APIRouter()

FALLBACK_RESPONSE = PredictionResponse(
    predicted_score=50.0,
    confidence=0.0,
    contributing_factors=[],
    risk_signals=[],
)


@router.get("/predict", response_model=PredictionResponse)
async def predict_condition(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool

    features = await extract_features(pool, date)
    if features is None:
        return FALLBACK_RESPONSE

    score, confidence, factors = rule_based_score(features)
    risks = detect_risks(features)

    # Blend XGBoost HRV prediction if model is ready
    hrv_predictor = getattr(request.app.state, "hrv_predictor", None)
    if hrv_predictor is not None and hrv_predictor.is_ready:
        try:
            hrv_features = await extract_hrv_prediction_features(pool, date)
            if hrv_features is not None:
                z_score, hrv_confidence = hrv_predictor.predict(hrv_features)
                # Use higher confidence from XGBoost model
                confidence = max(confidence, hrv_confidence)
                # Add HRV prediction as a contributing factor
                direction = "positive" if z_score >= 0 else "negative"
                factors.append(
                    ContributingFactor(
                        feature="hrv_prediction",
                        importance=abs(z_score),
                        direction=direction,
                        value=round(z_score, 3),
                        baseline=0.0,
                    )
                )
        except Exception:
            logger.debug("HRV prediction failed for %s, using rule-based only", date)

    return PredictionResponse(
        predicted_score=score,
        confidence=confidence,
        contributing_factors=factors,
        risk_signals=risks,
    )
