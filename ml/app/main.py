import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import create_pool
from app.models.anomaly_detector import AnomalyDetector
from app.models.divergence_detector import DivergenceDetector
from app.models.ensemble_hrv import HRVEnsemble
from app.models.hrv_predictor import HRVPredictor
from app.models.lstm_predictor import LSTMHRVPredictor
from app.routers import advice, anomaly, divergence, health, hrv_predict, insights, predict, retrain, risk, vri
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting ML service...")
    app.state.settings = settings
    app.state.db_pool = await create_pool(settings)

    # Load anomaly detector
    detector = AnomalyDetector(settings.model_store_path)
    if detector.load():
        logger.info("Anomaly model loaded: %s", detector.model_version)
    else:
        logger.info("No anomaly model found, POST /anomaly/train to create one")
    app.state.anomaly_detector = detector

    # Load HRV predictor
    hrv_predictor = HRVPredictor(settings.model_store_path)
    if hrv_predictor.load():
        logger.info("HRV prediction model loaded: %s", hrv_predictor.model_version)
    else:
        logger.info("No HRV model found, POST /hrv/train to create one")
    app.state.hrv_predictor = hrv_predictor

    # Load LSTM predictor and ensemble
    lstm_predictor = LSTMHRVPredictor(settings.model_store_path)
    ensemble_config = HRVEnsemble.load_config(settings.model_store_path)

    if lstm_predictor.load():
        alpha = ensemble_config.get("alpha", 0.5) if ensemble_config else 0.5
        ensemble = HRVEnsemble(hrv_predictor, lstm_predictor, alpha=alpha)
        logger.info(
            "HRV ensemble loaded: LSTM=%s, alpha=%.2f",
            lstm_predictor.model_version, alpha,
        )
    else:
        ensemble = HRVEnsemble(hrv_predictor, lstm_predictor=None)
        logger.info("No LSTM model found, ensemble uses XGBoost only")
    app.state.hrv_ensemble = ensemble

    # Load divergence detector
    div_detector = DivergenceDetector(settings.model_store_path)
    if div_detector.load():
        logger.info("Divergence model loaded: %s", div_detector.model_version)
    else:
        logger.info("No divergence model found, POST /divergence/train to create one")
    app.state.divergence_detector = div_detector

    # Start retrain scheduler
    retrain_scheduler = start_scheduler(app, settings)
    app.state.retrain_scheduler = retrain_scheduler

    logger.info("ML service ready")

    yield

    logger.info("Shutting down ML service...")
    stop_scheduler(retrain_scheduler)
    await app.state.db_pool.close()
    logger.info("ML service stopped")


app = FastAPI(title="VitaMetron ML", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(predict.router)
app.include_router(risk.router)
app.include_router(insights.router)
app.include_router(vri.router)
app.include_router(anomaly.router)
app.include_router(hrv_predict.router)
app.include_router(divergence.router)
app.include_router(advice.router)
app.include_router(retrain.router)
