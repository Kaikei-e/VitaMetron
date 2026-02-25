"""APScheduler-based retrain scheduler.

Runs two cron jobs:
- Daily lightweight retraining (fixed params, no LSTM) at JST 03:00
- Weekly full retraining (Optuna + LSTM) on Monday at JST 03:00

On Mondays, only the weekly job runs (daily is skipped because weekly subsumes it).
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _create_scheduler(app, settings) -> AsyncIOScheduler | None:
    """Create and configure the retrain scheduler.

    Returns None if retrain is disabled.
    """
    if not settings.retrain_enabled:
        logger.info("Retrain scheduler disabled")
        return None

    scheduler = AsyncIOScheduler(
        job_defaults={
            "misfire_grace_time": 3600,
            "max_instances": 1,
            "coalesce": True,
        }
    )

    async def _daily_retrain():
        """Daily lightweight retrain — skipped on weekly day."""
        import datetime
        today = datetime.date.today()
        weekly_day_num = {
            "mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6,
        }.get(settings.retrain_weekly_day.lower(), 0)

        if today.weekday() == weekly_day_num:
            logger.info("Skipping daily retrain — weekly retrain runs today")
            return

        from app.retrain import run_retrain
        await run_retrain(app, trigger="scheduled", mode="daily")

    async def _weekly_retrain():
        """Weekly full retrain with Optuna + LSTM."""
        from app.retrain import run_retrain
        await run_retrain(app, trigger="scheduled", mode="weekly")

    # Daily: every day at configured hour
    scheduler.add_job(
        _daily_retrain,
        CronTrigger(
            hour=settings.retrain_daily_hour,
            minute=settings.retrain_daily_minute,
        ),
        id="retrain_daily",
        name="Daily lightweight retrain",
    )

    # Weekly: configured day at same time
    scheduler.add_job(
        _weekly_retrain,
        CronTrigger(
            day_of_week=settings.retrain_weekly_day,
            hour=settings.retrain_daily_hour,
            minute=settings.retrain_daily_minute,
        ),
        id="retrain_weekly",
        name="Weekly full retrain",
    )

    logger.info(
        "Retrain scheduler configured: daily at %02d:%02d, weekly on %s",
        settings.retrain_daily_hour,
        settings.retrain_daily_minute,
        settings.retrain_weekly_day,
    )

    return scheduler


def start_scheduler(app, settings) -> AsyncIOScheduler | None:
    """Create, start, and return the scheduler (or None if disabled)."""
    scheduler = _create_scheduler(app, settings)
    if scheduler is not None:
        scheduler.start()
        logger.info("Retrain scheduler started")
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler | None):
    """Gracefully shut down the scheduler."""
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Retrain scheduler stopped")
