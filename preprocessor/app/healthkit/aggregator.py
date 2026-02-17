"""Daily summary aggregation from normalized HealthKit data.

Combines all metrics for a day into a single daily_summaries row.
Includes HR zone calculation, SpO2 main-sleep filtering, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from app.healthkit.normalizer import NormalizedDay
from app.healthkit.sleep import SleepSession

logger = logging.getLogger(__name__)


@dataclass
class DailySummary:
    """Maps directly to the daily_summaries table."""
    date: date
    provider: str = "apple_watch"
    resting_hr: int | None = None
    avg_hr: float | None = None
    max_hr: int | None = None
    hrv_daily_rmssd: float | None = None
    hrv_deep_rmssd: float | None = None
    spo2_avg: float | None = None
    spo2_min: float | None = None
    spo2_max: float | None = None
    br_full_sleep: float | None = None
    skin_temp_variation: float | None = None
    sleep_start: datetime | None = None
    sleep_end: datetime | None = None
    sleep_duration_min: int | None = None
    sleep_minutes_asleep: int | None = None
    sleep_minutes_awake: int | None = None
    sleep_onset_latency: int | None = None
    sleep_type: str | None = None
    sleep_deep_min: int | None = None
    sleep_light_min: int | None = None
    sleep_rem_min: int | None = None
    sleep_wake_min: int | None = None
    sleep_is_main: bool = True
    steps: int | None = None
    distance_km: float | None = None
    floors: int | None = None
    calories_total: int | None = None
    calories_active: int | None = None
    calories_bmr: int | None = None
    vo2_max: float | None = None
    hr_zone_out_min: int | None = None
    hr_zone_fat_min: int | None = None
    hr_zone_cardio_min: int | None = None
    hr_zone_peak_min: int | None = None


def _compute_age(dob: date, ref_date_str: str) -> int:
    """Compute age in years at a given date."""
    ref = date.fromisoformat(ref_date_str)
    age = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        age -= 1
    return age


def _compute_hr_zones(
    hr_buckets: list,
    dob: date | None,
    date_str: str,
) -> tuple[int, int, int, int]:
    """Compute HR zone minutes from 1-min resampled data.

    Uses age-based thresholds: max_hr = 220 - age
    Zones:
      Out of Range: < 40% max_hr
      Fat Burn:     40% - 60% max_hr
      Cardio:       60% - 75% max_hr
      Peak:         >= 75% max_hr
    """
    if not hr_buckets:
        return 0, 0, 0, 0

    if dob:
        age = _compute_age(dob, date_str)
        max_hr = 220 - age
    else:
        max_hr = 190  # fallback

    zone_fat_burn = round(max_hr * 0.4)
    zone_cardio = round(max_hr * 0.6)
    zone_peak = round(max_hr * 0.75)

    out_of_range = 0
    fat_burn = 0
    cardio = 0
    peak = 0

    for bucket in hr_buckets:
        bpm = bucket.bpm
        if bpm >= zone_peak:
            peak += 1
        elif bpm >= zone_cardio:
            cardio += 1
        elif bpm >= zone_fat_burn:
            fat_burn += 1
        else:
            out_of_range += 1

    return out_of_range, fat_burn, cardio, peak


def aggregate_daily_summary(
    date_str: str,
    normalized: NormalizedDay,
    sleep_sessions: list[SleepSession],
    dob: date | None,
) -> DailySummary:
    """Aggregate all metrics for a day into a DailySummary."""
    summary = DailySummary(date=date.fromisoformat(date_str))

    # Activity metrics
    if normalized.steps > 0:
        summary.steps = normalized.steps
    if normalized.distance_km > 0:
        summary.distance_km = round(normalized.distance_km, 3)
    if normalized.floors > 0:
        summary.floors = normalized.floors
    if normalized.calories_active > 0:
        summary.calories_active = normalized.calories_active
    if normalized.calories_bmr > 0:
        summary.calories_bmr = normalized.calories_bmr
    if normalized.calories_active > 0 or normalized.calories_bmr > 0:
        summary.calories_total = (normalized.calories_active or 0) + (normalized.calories_bmr or 0)

    # Heart rate from 1-min resampled data
    if normalized.hr_1min:
        bpms = [b.bpm for b in normalized.hr_1min]
        summary.avg_hr = round(sum(bpms) / len(bpms), 1)
        summary.max_hr = max(bpms)

    # Resting HR (dedicated type)
    summary.resting_hr = normalized.resting_hr

    # HRV
    if normalized.hrv_rmssd is not None:
        summary.hrv_daily_rmssd = round(normalized.hrv_rmssd, 2)

    # Skin temperature
    if normalized.skin_temp is not None:
        summary.skin_temp_variation = round(normalized.skin_temp, 2)

    # VO2Max
    if normalized.vo2_max is not None:
        summary.vo2_max = round(normalized.vo2_max, 1)

    # HR Zones
    out_r, fat, cardio, peak = _compute_hr_zones(
        normalized.hr_1min, dob, date_str
    )
    if normalized.hr_1min:
        summary.hr_zone_out_min = out_r
        summary.hr_zone_fat_min = fat
        summary.hr_zone_cardio_min = cardio
        summary.hr_zone_peak_min = peak

    # Sleep (main session)
    main_sleep = next((s for s in sleep_sessions if s.is_main_sleep), None)
    if main_sleep:
        summary.sleep_start = main_sleep.start
        summary.sleep_end = main_sleep.end
        summary.sleep_duration_min = main_sleep.duration_min
        summary.sleep_minutes_asleep = main_sleep.minutes_asleep
        summary.sleep_minutes_awake = main_sleep.minutes_awake
        summary.sleep_onset_latency = main_sleep.sleep_onset_latency
        summary.sleep_type = main_sleep.sleep_type
        summary.sleep_deep_min = main_sleep.deep_min
        summary.sleep_light_min = main_sleep.light_min
        summary.sleep_rem_min = main_sleep.rem_min
        summary.sleep_wake_min = main_sleep.wake_min
        summary.sleep_is_main = True

        # SpO2: filter to main sleep time window
        if normalized.spo2_samples:
            sleep_spo2 = [
                val for ts, val in normalized.spo2_samples
                if main_sleep.start <= ts <= main_sleep.end
            ]
            if sleep_spo2:
                summary.spo2_avg = round(sum(sleep_spo2) / len(sleep_spo2), 1)
                summary.spo2_min = round(min(sleep_spo2), 1)
                summary.spo2_max = round(max(sleep_spo2), 1)

        # Respiratory rate: filter to main sleep window
        if normalized.respiratory_samples:
            sleep_resp = [
                val for ts, val in normalized.respiratory_samples
                if main_sleep.start <= ts <= main_sleep.end
            ]
            if sleep_resp:
                summary.br_full_sleep = round(
                    sum(sleep_resp) / len(sleep_resp), 1
                )

    return summary
