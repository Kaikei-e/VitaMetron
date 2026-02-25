"""Tests for the retrain scheduler configuration."""

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.scheduler import _create_scheduler, start_scheduler, stop_scheduler


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        db_host="localhost",
        db_port=5432,
        db_name="test",
        db_user="test",
        db_password="test",
        model_store_path="/tmp/model_store",
        retrain_enabled=True,
        retrain_daily_hour=3,
        retrain_daily_minute=0,
        retrain_weekly_day="mon",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_scheduler_disabled():
    """When retrain_enabled=False, scheduler should return None."""
    settings = _make_settings(retrain_enabled=False)
    app = MagicMock()

    scheduler = _create_scheduler(app, settings)
    assert scheduler is None


def test_scheduler_creates_two_jobs():
    """Scheduler should have daily and weekly jobs."""
    settings = _make_settings()
    app = MagicMock()

    scheduler = _create_scheduler(app, settings)
    assert scheduler is not None

    jobs = scheduler.get_jobs()
    assert len(jobs) == 2

    job_ids = {j.id for j in jobs}
    assert "retrain_daily" in job_ids
    assert "retrain_weekly" in job_ids


def test_scheduler_job_config():
    """Verify job trigger configuration."""
    settings = _make_settings(retrain_daily_hour=4, retrain_daily_minute=30)
    app = MagicMock()

    scheduler = _create_scheduler(app, settings)
    jobs = {j.id: j for j in scheduler.get_jobs()}

    daily = jobs["retrain_daily"]
    weekly = jobs["retrain_weekly"]

    # Verify triggers are CronTrigger
    assert daily.trigger.__class__.__name__ == "CronTrigger"
    assert weekly.trigger.__class__.__name__ == "CronTrigger"


async def test_start_and_stop():
    """Scheduler should start and stop without error."""
    settings = _make_settings()
    app = MagicMock()

    scheduler = start_scheduler(app, settings)
    assert scheduler is not None
    assert scheduler.running

    # shutdown(wait=False) schedules shutdown; no error is the success criterion
    stop_scheduler(scheduler)


def test_stop_none_scheduler():
    """Stopping None scheduler should not raise."""
    stop_scheduler(None)
