"""Batch writer for HealthKit processed data -> PostgreSQL.

Uses asyncpg for direct DB writes with upsert semantics.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

import asyncpg

from app.healthkit.aggregator import DailySummary
from app.healthkit.normalizer import MinuteBucket
from app.healthkit.parser import RawWorkout
from app.healthkit.sleep import SleepSession, SleepStage

logger = logging.getLogger(__name__)


@dataclass
class WriteStats:
    """Accumulated write statistics."""
    days_written: int = 0
    hr_samples: int = 0
    sleep_stages: int = 0
    exercise_logs: int = 0


class BatchWriter:
    """Writes processed HealthKit data to PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._stats = WriteStats()

    async def write_day(
        self,
        date_str: str,
        summary: DailySummary,
        hr_intraday: list[MinuteBucket],
        sleep_sessions: list[SleepSession],
        workouts: list[RawWorkout],
    ) -> None:
        """Write all data for a single day."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await self._upsert_daily_summary(conn, summary)
                await self._write_hr_intraday(conn, date_str, hr_intraday)
                await self._write_sleep_stages(conn, date_str, sleep_sessions)
                await self._write_workouts(conn, workouts)

        self._stats.days_written += 1

    async def _upsert_daily_summary(
        self, conn: asyncpg.Connection, summary: DailySummary
    ) -> None:
        """Upsert a daily summary row."""
        await conn.execute(
            """
            INSERT INTO daily_summaries (
                date, provider, resting_hr, avg_hr, max_hr,
                hrv_daily_rmssd, hrv_deep_rmssd,
                spo2_avg, spo2_min, spo2_max,
                br_full_sleep, skin_temp_variation,
                sleep_start, sleep_end, sleep_duration_min,
                sleep_minutes_asleep, sleep_minutes_awake,
                sleep_onset_latency, sleep_type,
                sleep_deep_min, sleep_light_min, sleep_rem_min, sleep_wake_min,
                sleep_is_main,
                steps, distance_km, floors,
                calories_total, calories_active, calories_bmr,
                vo2_max,
                hr_zone_out_min, hr_zone_fat_min, hr_zone_cardio_min, hr_zone_peak_min,
                synced_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7,
                $8, $9, $10,
                $11, $12,
                $13, $14, $15,
                $16, $17,
                $18, $19,
                $20, $21, $22, $23,
                $24,
                $25, $26, $27,
                $28, $29, $30,
                $31,
                $32, $33, $34, $35,
                NOW()
            )
            ON CONFLICT (date) DO UPDATE SET
                provider = EXCLUDED.provider,
                resting_hr = COALESCE(EXCLUDED.resting_hr, daily_summaries.resting_hr),
                avg_hr = COALESCE(EXCLUDED.avg_hr, daily_summaries.avg_hr),
                max_hr = COALESCE(EXCLUDED.max_hr, daily_summaries.max_hr),
                hrv_daily_rmssd = COALESCE(EXCLUDED.hrv_daily_rmssd, daily_summaries.hrv_daily_rmssd),
                hrv_deep_rmssd = COALESCE(EXCLUDED.hrv_deep_rmssd, daily_summaries.hrv_deep_rmssd),
                spo2_avg = COALESCE(EXCLUDED.spo2_avg, daily_summaries.spo2_avg),
                spo2_min = COALESCE(EXCLUDED.spo2_min, daily_summaries.spo2_min),
                spo2_max = COALESCE(EXCLUDED.spo2_max, daily_summaries.spo2_max),
                br_full_sleep = COALESCE(EXCLUDED.br_full_sleep, daily_summaries.br_full_sleep),
                skin_temp_variation = COALESCE(EXCLUDED.skin_temp_variation, daily_summaries.skin_temp_variation),
                sleep_start = COALESCE(EXCLUDED.sleep_start, daily_summaries.sleep_start),
                sleep_end = COALESCE(EXCLUDED.sleep_end, daily_summaries.sleep_end),
                sleep_duration_min = COALESCE(EXCLUDED.sleep_duration_min, daily_summaries.sleep_duration_min),
                sleep_minutes_asleep = COALESCE(EXCLUDED.sleep_minutes_asleep, daily_summaries.sleep_minutes_asleep),
                sleep_minutes_awake = COALESCE(EXCLUDED.sleep_minutes_awake, daily_summaries.sleep_minutes_awake),
                sleep_onset_latency = COALESCE(EXCLUDED.sleep_onset_latency, daily_summaries.sleep_onset_latency),
                sleep_type = COALESCE(EXCLUDED.sleep_type, daily_summaries.sleep_type),
                sleep_deep_min = COALESCE(EXCLUDED.sleep_deep_min, daily_summaries.sleep_deep_min),
                sleep_light_min = COALESCE(EXCLUDED.sleep_light_min, daily_summaries.sleep_light_min),
                sleep_rem_min = COALESCE(EXCLUDED.sleep_rem_min, daily_summaries.sleep_rem_min),
                sleep_wake_min = COALESCE(EXCLUDED.sleep_wake_min, daily_summaries.sleep_wake_min),
                sleep_is_main = COALESCE(EXCLUDED.sleep_is_main, daily_summaries.sleep_is_main),
                steps = COALESCE(EXCLUDED.steps, daily_summaries.steps),
                distance_km = COALESCE(EXCLUDED.distance_km, daily_summaries.distance_km),
                floors = COALESCE(EXCLUDED.floors, daily_summaries.floors),
                calories_total = COALESCE(EXCLUDED.calories_total, daily_summaries.calories_total),
                calories_active = COALESCE(EXCLUDED.calories_active, daily_summaries.calories_active),
                calories_bmr = COALESCE(EXCLUDED.calories_bmr, daily_summaries.calories_bmr),
                vo2_max = COALESCE(EXCLUDED.vo2_max, daily_summaries.vo2_max),
                hr_zone_out_min = COALESCE(EXCLUDED.hr_zone_out_min, daily_summaries.hr_zone_out_min),
                hr_zone_fat_min = COALESCE(EXCLUDED.hr_zone_fat_min, daily_summaries.hr_zone_fat_min),
                hr_zone_cardio_min = COALESCE(EXCLUDED.hr_zone_cardio_min, daily_summaries.hr_zone_cardio_min),
                hr_zone_peak_min = COALESCE(EXCLUDED.hr_zone_peak_min, daily_summaries.hr_zone_peak_min),
                synced_at = NOW()
            """,
            summary.date,
            summary.provider,
            summary.resting_hr,
            summary.avg_hr,
            summary.max_hr,
            summary.hrv_daily_rmssd,
            summary.hrv_deep_rmssd,
            summary.spo2_avg,
            summary.spo2_min,
            summary.spo2_max,
            summary.br_full_sleep,
            summary.skin_temp_variation,
            summary.sleep_start,
            summary.sleep_end,
            summary.sleep_duration_min,
            summary.sleep_minutes_asleep,
            summary.sleep_minutes_awake,
            summary.sleep_onset_latency,
            summary.sleep_type,
            summary.sleep_deep_min,
            summary.sleep_light_min,
            summary.sleep_rem_min,
            summary.sleep_wake_min,
            summary.sleep_is_main,
            summary.steps,
            summary.distance_km,
            summary.floors,
            summary.calories_total,
            summary.calories_active,
            summary.calories_bmr,
            summary.vo2_max,
            summary.hr_zone_out_min,
            summary.hr_zone_fat_min,
            summary.hr_zone_cardio_min,
            summary.hr_zone_peak_min,
        )

    async def _write_hr_intraday(
        self,
        conn: asyncpg.Connection,
        date_str: str,
        hr_buckets: list[MinuteBucket],
    ) -> None:
        """Write heart rate intraday data using bulk insert."""
        if not hr_buckets:
            return

        # Delete existing data for this day to avoid conflicts
        await conn.execute(
            """
            DELETE FROM heart_rate_intraday
            WHERE time >= $1::date AND time < ($1::date + INTERVAL '1 day')
            """,
            date.fromisoformat(date_str),
        )

        # Bulk insert using copy
        records = [
            (b.timestamp, b.bpm, 0) for b in hr_buckets
        ]
        await conn.copy_records_to_table(
            "heart_rate_intraday",
            records=records,
            columns=["time", "bpm", "confidence"],
        )

        self._stats.hr_samples += len(hr_buckets)

    async def _write_sleep_stages(
        self,
        conn: asyncpg.Connection,
        date_str: str,
        sessions: list[SleepSession],
    ) -> None:
        """Write sleep stage data."""
        if not sessions:
            return

        # Delete existing data for overlapping time range
        for session in sessions:
            await conn.execute(
                """
                DELETE FROM sleep_stages
                WHERE time >= $1 AND time <= $2
                """,
                session.start,
                session.end,
            )

        # Insert all stages
        records: list[tuple] = []
        for session in sessions:
            for stage in session.stages:
                records.append((
                    stage.start,
                    stage.stage,
                    stage.seconds,
                    None,  # log_id
                ))

        if records:
            await conn.copy_records_to_table(
                "sleep_stages",
                records=records,
                columns=["time", "stage", "seconds", "log_id"],
            )
            self._stats.sleep_stages += len(records)

    async def _write_workouts(
        self,
        conn: asyncpg.Connection,
        workouts: list[RawWorkout],
    ) -> None:
        """Write exercise log entries."""
        for w in workouts:
            # Generate a stable external_id from workout attributes
            external_id = f"hk_{w.start.strftime('%Y%m%d%H%M%S')}_{w.activity_type}"

            await conn.execute(
                """
                INSERT INTO exercise_logs (
                    external_id, activity_name, started_at, duration_ms,
                    calories, distance_km, synced_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (external_id) DO UPDATE SET
                    activity_name = EXCLUDED.activity_name,
                    started_at = EXCLUDED.started_at,
                    duration_ms = EXCLUDED.duration_ms,
                    calories = COALESCE(EXCLUDED.calories, exercise_logs.calories),
                    distance_km = COALESCE(EXCLUDED.distance_km, exercise_logs.distance_km),
                    synced_at = NOW()
                """,
                external_id,
                w.activity_type,
                w.start,
                round(w.duration_sec * 1000),
                round(w.total_energy_kcal) if w.total_energy_kcal else None,
                round(w.total_distance_km, 3) if w.total_distance_km else None,
            )
            self._stats.exercise_logs += 1

    async def get_stats(self) -> dict:
        """Return accumulated write statistics."""
        return {
            "days_written": self._stats.days_written,
            "hr_samples": self._stats.hr_samples,
            "sleep_stages": self._stats.sleep_stages,
            "exercise_logs": self._stats.exercise_logs,
        }
