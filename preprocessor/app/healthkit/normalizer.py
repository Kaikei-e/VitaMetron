"""Normalize HealthKit records: 1-min resampling, source dedup, TZ handling."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.healthkit.parser import RawSample
from app.healthkit.plausibility import (
    AVG_HR_MAX,
    AVG_HR_MIN,
    CALORIES_TOTAL_MAX,
    DISTANCE_KM_MAX,
    RESTING_HR_MAX,
    RESTING_HR_MIN,
    RMSSD_MAX,
    RMSSD_MIN,
    SKIN_TEMP_DELTA_MAX,
    SKIN_TEMP_DELTA_MIN,
    STEPS_MAX,
)

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

    # Heart Rate: 1-min resampling with plausibility fallback
    result.hr_1min = _resample_hr_plausible(
        by_type.get("HKQuantityTypeIdentifierHeartRate", []),
        lambda v: AVG_HR_MIN <= v <= AVG_HR_MAX,
    )

    # Steps: daily sum with plausibility fallback
    result.steps = _sum_plausible(
        by_type.get("HKQuantityTypeIdentifierStepCount", []),
        lambda v: 0 < v <= STEPS_MAX,
    )

    # Distance: daily sum with plausibility fallback
    result.distance_km = _float_sum_plausible(
        by_type.get("HKQuantityTypeIdentifierDistanceWalkingRunning", []),
        lambda v: 0 < v <= DISTANCE_KM_MAX,
    )

    # Active Energy with plausibility fallback
    result.calories_active = _sum_plausible(
        by_type.get("HKQuantityTypeIdentifierActiveEnergyBurned", []),
        lambda v: 0 < v <= CALORIES_TOTAL_MAX,
    )

    # Basal Energy with plausibility fallback
    result.calories_bmr = _sum_plausible(
        by_type.get("HKQuantityTypeIdentifierBasalEnergyBurned", []),
        lambda v: 0 < v <= CALORIES_TOTAL_MAX,
    )

    # Floors (low anomaly risk — no plausibility check)
    result.floors = _sum_plausible(
        by_type.get("HKQuantityTypeIdentifierFlightsClimbed", []),
    )

    # Resting HR with plausibility fallback
    rhr_val = _scalar_plausible(
        by_type.get("HKQuantityTypeIdentifierRestingHeartRate", []),
        lambda v: RESTING_HR_MIN <= v <= RESTING_HR_MAX,
    )
    if rhr_val is not None:
        result.resting_hr = round(rhr_val)

    # HRV SDNN: daily average with plausibility fallback
    result.hrv_rmssd = _avg_plausible(
        by_type.get("HKQuantityTypeIdentifierHeartRateVariabilitySDNN", []),
        lambda v: RMSSD_MIN <= v <= RMSSD_MAX,
    )

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

    # Skin Temperature with plausibility fallback
    result.skin_temp = _scalar_plausible(
        by_type.get("HKQuantityTypeIdentifierAppleSleepingWristTemperature", []),
        lambda v: SKIN_TEMP_DELTA_MIN <= v <= SKIN_TEMP_DELTA_MAX,
    )

    # VO2Max (low anomaly risk — no plausibility check)
    result.vo2_max = _scalar_plausible(
        by_type.get("HKQuantityTypeIdentifierVO2Max", []),
    )

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


def _source_groups_by_priority(records: list[RawSample]) -> list[list[RawSample]]:
    """Group records by source priority, return groups ordered highest-first."""
    if not records:
        return []
    by_priority: dict[int, list[RawSample]] = defaultdict(list)
    for r in records:
        p = _source_priority(r.source_name, r.device)
        by_priority[p].append(r)
    groups = []
    for priority in sorted(by_priority.keys(), reverse=True):
        group = sorted(by_priority[priority], key=lambda r: r.start)
        groups.append(group)
    return groups


def _scalar_plausible(
    records: list[RawSample],
    is_plausible: Callable[[float], bool] | None = None,
) -> float | None:
    """Get last value from the best plausible source, with fallback."""
    groups = _source_groups_by_priority(records)
    if not groups:
        return None
    if len(groups) == 1 or is_plausible is None:
        return groups[0][-1].numeric_value
    for group in groups:
        val = group[-1].numeric_value
        if is_plausible(val):
            return val
    return groups[0][-1].numeric_value  # all implausible → best source


def _avg_plausible(
    records: list[RawSample],
    is_plausible: Callable[[float], bool] | None = None,
) -> float | None:
    """Average from best plausible source, with fallback."""
    groups = _source_groups_by_priority(records)
    if not groups:
        return None
    if len(groups) == 1 or is_plausible is None:
        return sum(r.numeric_value for r in groups[0]) / len(groups[0])
    for group in groups:
        avg = sum(r.numeric_value for r in group) / len(group)
        if is_plausible(avg):
            return avg
    return sum(r.numeric_value for r in groups[0]) / len(groups[0])


def _sum_plausible(
    records: list[RawSample],
    is_plausible: Callable[[float], bool] | None = None,
) -> int:
    """Sum from best plausible source, with fallback."""
    groups = _source_groups_by_priority(records)
    if not groups:
        return 0
    if len(groups) == 1 or is_plausible is None:
        return round(sum(r.numeric_value for r in groups[0]))
    for group in groups:
        total = round(sum(r.numeric_value for r in group))
        if is_plausible(total):
            return total
    return round(sum(r.numeric_value for r in groups[0]))


def _float_sum_plausible(
    records: list[RawSample],
    is_plausible: Callable[[float], bool] | None = None,
) -> float:
    """Float sum from best plausible source, with fallback."""
    groups = _source_groups_by_priority(records)
    if not groups:
        return 0.0
    if len(groups) == 1 or is_plausible is None:
        return sum(r.numeric_value for r in groups[0])
    for group in groups:
        total = sum(r.numeric_value for r in group)
        if is_plausible(total):
            return total
    return sum(r.numeric_value for r in groups[0])


def _resample_from_records(records: list[RawSample]) -> list[MinuteBucket]:
    """Resample a list of HR records into 1-minute buckets."""
    minute_groups: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in records:
        try:
            bpm = r.numeric_value
        except ValueError:
            continue
        minute_key = r.start.strftime("%Y-%m-%d %H:%M")
        minute_groups[minute_key].append((r.start, bpm))

    buckets: list[MinuteBucket] = []
    for minute_key in sorted(minute_groups.keys()):
        samples = minute_groups[minute_key]
        avg_bpm = sum(v for _, v in samples) / len(samples)
        ts = samples[0][0].replace(second=0, microsecond=0)
        hhmm = ts.strftime("%H:%M")
        buckets.append(MinuteBucket(
            minute_key=hhmm,
            timestamp=ts,
            bpm=round(avg_bpm),
        ))
    return buckets


def _resample_hr_plausible(
    records: list[RawSample],
    is_plausible: Callable[[float], bool] | None = None,
) -> list[MinuteBucket]:
    """Resample HR with plausibility-based source fallback."""
    groups = _source_groups_by_priority(records)
    if not groups:
        return []
    if len(groups) == 1 or is_plausible is None:
        return _resample_from_records(groups[0])
    for group in groups:
        buckets = _resample_from_records(group)
        if buckets:
            avg_bpm = sum(b.bpm for b in buckets) / len(buckets)
            if is_plausible(avg_bpm):
                return buckets
    return _resample_from_records(groups[0])


def _resample_hr(records: list[RawSample]) -> list[MinuteBucket]:
    """Resample heart rate records into 1-minute buckets using average."""
    return _resample_hr_plausible(records)


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
