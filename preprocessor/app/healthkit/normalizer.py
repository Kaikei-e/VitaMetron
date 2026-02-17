"""Normalize HealthKit records: 1-min resampling, source dedup, TZ handling."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.healthkit.parser import RawSample

logger = logging.getLogger(__name__)


def _is_apple_watch_source(source_name: str, device: str) -> bool:
    """Check if record originates from Apple Watch (higher priority)."""
    check = (source_name + " " + device).lower()
    return "apple watch" in check or "watch" in check


def _source_priority(source_name: str, device: str) -> int:
    """Higher value = higher priority. Apple Watch > iPhone > other."""
    if _is_apple_watch_source(source_name, device):
        return 2
    check = (source_name + " " + device).lower()
    if "iphone" in check:
        return 1
    return 0


@dataclass
class MinuteBucket:
    """A 1-minute bucket for resampled heart rate."""
    minute_key: str  # "HH:MM"
    timestamp: datetime
    bpm: int


@dataclass
class NormalizedDay:
    """All normalized data for a single day."""
    hr_1min: list[MinuteBucket] = field(default_factory=list)
    steps: int = 0
    distance_km: float = 0.0
    calories_active: int = 0
    calories_bmr: int = 0
    floors: int = 0
    resting_hr: int | None = None
    hrv_rmssd: float | None = None
    spo2_samples: list[tuple[datetime, float]] = field(default_factory=list)
    respiratory_samples: list[tuple[datetime, float]] = field(default_factory=list)
    skin_temp: float | None = None
    vo2_max: float | None = None
    sleep_records: list = field(default_factory=list)  # passed through from main pipeline


def normalize_day(records: list[RawSample]) -> NormalizedDay:
    """Normalize a day's worth of HealthKit records."""
    result = NormalizedDay()

    # Group records by type
    by_type: dict[str, list[RawSample]] = defaultdict(list)
    for r in records:
        by_type[r.type].append(r)

    # Heart Rate: 1-min resampling with source dedup
    result.hr_1min = _resample_hr(
        by_type.get("HKQuantityTypeIdentifierHeartRate", [])
    )

    # Steps: daily sum with source dedup
    result.steps = _sum_with_dedup(
        by_type.get("HKQuantityTypeIdentifierStepCount", [])
    )

    # Distance: daily sum
    result.distance_km = _float_sum_with_dedup(
        by_type.get("HKQuantityTypeIdentifierDistanceWalkingRunning", [])
    )

    # Active Energy
    result.calories_active = _sum_with_dedup(
        by_type.get("HKQuantityTypeIdentifierActiveEnergyBurned", [])
    )

    # Basal Energy
    result.calories_bmr = _sum_with_dedup(
        by_type.get("HKQuantityTypeIdentifierBasalEnergyBurned", [])
    )

    # Floors
    result.floors = _sum_with_dedup(
        by_type.get("HKQuantityTypeIdentifierFlightsClimbed", [])
    )

    # Resting HR: use dedicated type, take last value of the day
    rhr_records = by_type.get("HKQuantityTypeIdentifierRestingHeartRate", [])
    if rhr_records:
        # Prefer Apple Watch source, take last reading
        best = _best_source_records(rhr_records)
        if best:
            result.resting_hr = round(best[-1].numeric_value)

    # HRV SDNN: daily average
    hrv_records = by_type.get("HKQuantityTypeIdentifierHeartRateVariabilitySDNN", [])
    if hrv_records:
        best = _best_source_records(hrv_records)
        if best:
            result.hrv_rmssd = sum(r.numeric_value for r in best) / len(best)

    # SpO2: keep all samples with timestamps (filtered by sleep later)
    spo2_records = by_type.get("HKQuantityTypeIdentifierOxygenSaturation", [])
    for r in spo2_records:
        try:
            # SpO2 in HealthKit is 0-1 fraction; convert to percentage
            val = r.numeric_value
            if val <= 1.0:
                val *= 100
            result.spo2_samples.append((r.start, val))
        except ValueError:
            continue

    # Respiratory Rate: keep samples for sleep filtering
    resp_records = by_type.get("HKQuantityTypeIdentifierRespiratoryRate", [])
    for r in resp_records:
        try:
            result.respiratory_samples.append((r.start, r.numeric_value))
        except ValueError:
            continue

    # Skin Temperature
    skin_records = by_type.get(
        "HKQuantityTypeIdentifierAppleSleepingWristTemperature", []
    )
    if skin_records:
        best = _best_source_records(skin_records)
        if best:
            result.skin_temp = best[-1].numeric_value

    # VO2Max: latest value of the day
    vo2_records = by_type.get("HKQuantityTypeIdentifierVO2Max", [])
    if vo2_records:
        best = _best_source_records(vo2_records)
        if best:
            result.vo2_max = best[-1].numeric_value

    return result


def _best_source_records(records: list[RawSample]) -> list[RawSample]:
    """Select records from the highest-priority source, sorted by time."""
    if not records:
        return []

    # Group by source priority
    by_priority: dict[int, list[RawSample]] = defaultdict(list)
    for r in records:
        p = _source_priority(r.source_name, r.device)
        by_priority[p].append(r)

    # Take the highest priority group
    best_priority = max(by_priority.keys())
    result = by_priority[best_priority]
    result.sort(key=lambda r: r.start)
    return result


def _resample_hr(records: list[RawSample]) -> list[MinuteBucket]:
    """Resample heart rate records into 1-minute buckets using average."""
    if not records:
        return []

    # Source dedup: prefer Apple Watch
    best = _best_source_records(records)

    # Group by minute
    minute_groups: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in best:
        try:
            bpm = r.numeric_value
        except ValueError:
            continue
        minute_key = r.start.strftime("%Y-%m-%d %H:%M")
        minute_groups[minute_key].append((r.start, bpm))

    # Average per minute
    buckets: list[MinuteBucket] = []
    for minute_key in sorted(minute_groups.keys()):
        samples = minute_groups[minute_key]
        avg_bpm = sum(v for _, v in samples) / len(samples)
        # Use the first sample's timestamp, truncated to minute
        ts = samples[0][0].replace(second=0, microsecond=0)
        hhmm = ts.strftime("%H:%M")
        buckets.append(MinuteBucket(
            minute_key=hhmm,
            timestamp=ts,
            bpm=round(avg_bpm),
        ))

    return buckets


def _sum_with_dedup(records: list[RawSample]) -> int:
    """Sum values with source dedup (no time-overlap double-counting)."""
    if not records:
        return 0

    # Group by source priority
    by_priority: dict[int, list[RawSample]] = defaultdict(list)
    for r in records:
        p = _source_priority(r.source_name, r.device)
        by_priority[p].append(r)

    best_priority = max(by_priority.keys())

    # If we have high-priority (Watch) data, use only that
    # If only low-priority data, use that
    selected = by_priority[best_priority]

    total = 0.0
    for r in selected:
        try:
            total += r.numeric_value
        except ValueError:
            continue

    return round(total)


def _float_sum_with_dedup(records: list[RawSample]) -> float:
    """Float sum with source dedup."""
    if not records:
        return 0.0

    by_priority: dict[int, list[RawSample]] = defaultdict(list)
    for r in records:
        p = _source_priority(r.source_name, r.device)
        by_priority[p].append(r)

    best_priority = max(by_priority.keys())
    selected = by_priority[best_priority]

    total = 0.0
    for r in selected:
        try:
            total += r.numeric_value
        except ValueError:
            continue

    return total
