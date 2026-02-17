import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.database import create_pool
from app.healthkit.parser import parse_healthkit_zip
from app.healthkit.normalizer import normalize_day
from app.healthkit.sleep import build_sleep_sessions
from app.healthkit.aggregator import aggregate_daily_summary
from app.healthkit.writer import BatchWriter


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting preprocessor service...")
    app.state.db_pool = await create_pool(settings)
    app.state.redis = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )

    logger.info("Preprocessor service ready")
    yield

    logger.info("Shutting down preprocessor service...")
    await app.state.redis.close()
    await app.state.db_pool.close()
    logger.info("Preprocessor service stopped")


app = FastAPI(title="VitaMetron Preprocessor", version="0.1.0", lifespan=lifespan)

logger = logging.getLogger(__name__)


@app.get("/health")
async def health():
    return {"status": "ok"}


class ProcessRequest(BaseModel):
    zip_path: str
    job_id: str


class ProcessResponse(BaseModel):
    job_id: str
    status: str


@app.post("/process", response_model=ProcessResponse, status_code=202)
async def process(req: ProcessRequest, background_tasks: BackgroundTasks):
    rds = app.state.redis
    # Initialize progress
    await rds.set(
        f"hk_import:{req.job_id}",
        json.dumps({
            "status": "queued",
            "stage": "queued",
            "records_processed": 0,
            "records_total": 0,
            "days_written": 0,
            "current_date": "",
            "errors": [],
        }),
    )
    background_tasks.add_task(run_import, req.zip_path, req.job_id)
    return ProcessResponse(job_id=req.job_id, status="queued")


@app.get("/status/{job_id}")
async def status(job_id: str):
    rds = app.state.redis
    data = await rds.get(f"hk_import:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(data)


async def run_import(zip_path: str, job_id: str):
    """Main import pipeline: parse -> normalize -> aggregate -> write."""
    rds = app.state.redis
    pool = app.state.db_pool
    progress_key = f"hk_import:{job_id}"

    async def update_progress(**kwargs):
        data = await rds.get(progress_key)
        current = json.loads(data) if data else {}
        current.update(kwargs)
        await rds.set(progress_key, json.dumps(current))

    try:
        await update_progress(status="processing", stage="parsing")

        # Stage 1: Parse the HealthKit ZIP (CPU-bound, run in thread pool)
        loop = asyncio.get_running_loop()
        parsed = await loop.run_in_executor(None, parse_healthkit_zip, zip_path)
        dob = parsed.date_of_birth
        raw_by_date = parsed.records_by_date
        all_sleep_records = parsed.sleep_records
        workouts_by_date = parsed.workouts_by_date
        total_records = parsed.total_records

        # Collect all unique dates (from records, sleep endDates, and workouts)
        all_dates: set[str] = set(raw_by_date.keys())
        for sr in all_sleep_records:
            all_dates.add(sr.end.strftime("%Y-%m-%d"))
        all_dates.update(workouts_by_date.keys())
        dates = sorted(all_dates)

        await update_progress(
            records_total=total_records,
            stage="processing",
        )

        writer = BatchWriter(pool)
        days_written = 0
        records_processed = 0
        errors: list[str] = []

        for date_str in dates:
            try:
                day_records = raw_by_date.get(date_str, [])
                records_processed += len(day_records)

                # Stage 2: Normalize (1-min resampling, source dedup)
                normalized = normalize_day(day_records)

                # Stage 3: Build sleep sessions (uses all sleep records,
                # filters by dateOfSleep = endDate matching target_date)
                sleep_sessions = build_sleep_sessions(
                    all_sleep_records, date_str
                )

                # Stage 4: Aggregate daily summary
                summary = aggregate_daily_summary(
                    date_str=date_str,
                    normalized=normalized,
                    sleep_sessions=sleep_sessions,
                    dob=dob,
                )

                # Stage 5: Write to DB
                day_workouts = workouts_by_date.get(date_str, [])
                await writer.write_day(
                    date_str=date_str,
                    summary=summary,
                    hr_intraday=normalized.hr_1min,
                    sleep_sessions=sleep_sessions,
                    workouts=day_workouts,
                )

                days_written += 1
                await update_progress(
                    records_processed=records_processed,
                    days_written=days_written,
                    current_date=date_str,
                )

            except Exception as e:
                err_msg = f"{date_str}: {e}"
                logger.exception("Error processing %s", date_str)
                errors.append(err_msg)
                await update_progress(errors=errors)

        # Collect result stats
        result = await writer.get_stats()
        await update_progress(
            status="completed",
            stage="done",
            records_processed=records_processed,
            days_written=days_written,
            result=result,
            errors=errors,
        )
        logger.info("Import completed: %d days, %d records", days_written, records_processed)

    except Exception as e:
        logger.exception("Import failed")
        await update_progress(
            status="failed",
            stage="error",
            errors=[str(e)],
        )
    finally:
        # Clean up uploaded zip file
        try:
            os.remove(zip_path)
            logger.info("Cleaned up %s", zip_path)
        except OSError:
            pass
