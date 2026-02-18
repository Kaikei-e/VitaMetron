"""Tests for plausibility-based source fallback in normalizer."""

from __future__ import annotations

from datetime import datetime, timezone

from app.healthkit.normalizer import (
    _avg_plausible,
    _float_sum_plausible,
    _resample_hr_plausible,
    _scalar_plausible,
    _sum_plausible,
)
from app.healthkit.parser import RawSample
from app.healthkit.plausibility import (
    RESTING_HR_MAX,
    RESTING_HR_MIN,
    RMSSD_MAX,
    RMSSD_MIN,
    STEPS_MAX,
)


def _sample(
    value: float,
    source: str = "Apple Watch",
    device: str = "Apple Watch Series 9",
    type_: str = "HKQuantityTypeIdentifierRestingHeartRate",
    minute: int = 0,
) -> RawSample:
    """Helper to create a RawSample with sensible defaults."""
    return RawSample(
        type=type_,
        source_name=source,
        device=device,
        start=datetime(2025, 1, 1, 10, minute, 0, tzinfo=timezone.utc),
        end=datetime(2025, 1, 1, 10, minute, 30, tzinfo=timezone.utc),
        value=str(value),
        unit="count/min",
    )


def _watch_sample(value: float, minute: int = 0, type_: str = "test") -> RawSample:
    return _sample(value, "Apple Watch", "Apple Watch Series 9", type_, minute)


def _iphone_sample(value: float, minute: int = 0, type_: str = "test") -> RawSample:
    return _sample(value, "iPhone", "iPhone 15", type_, minute)


def _rhr_plausible(v: float) -> bool:
    return RESTING_HR_MIN <= v <= RESTING_HR_MAX


def _steps_plausible(v: float) -> bool:
    return 0 < v <= STEPS_MAX


def _rmssd_plausible(v: float) -> bool:
    return RMSSD_MIN <= v <= RMSSD_MAX


def _hr_range_plausible(v: float) -> bool:
    return 25 <= v <= 200


def _distance_plausible(v: float) -> bool:
    return 0 < v <= 300


def _always_true(v: float) -> bool:
    return True


# --- _scalar_plausible tests ---


def test_scalar_plausible_best_source_plausible():
    """Apple Watch has plausible value → use it."""
    records = [_watch_sample(65), _iphone_sample(60)]
    result = _scalar_plausible(records, _rhr_plausible)
    assert result == 65.0


def test_scalar_plausible_best_source_implausible_fallback():
    """Apple Watch has implausible value, iPhone is plausible → fallback to iPhone."""
    records = [_watch_sample(250), _iphone_sample(60)]
    result = _scalar_plausible(records, _rhr_plausible)
    assert result == 60.0


def test_scalar_plausible_all_implausible_keeps_best():
    """Both sources implausible → keep highest priority (Apple Watch)."""
    records = [_watch_sample(250), _iphone_sample(5)]
    result = _scalar_plausible(records, _rhr_plausible)
    assert result == 250.0


def test_scalar_plausible_single_source():
    """Single source → return without plausibility check."""
    records = [_watch_sample(250)]
    result = _scalar_plausible(records, _rhr_plausible)
    # Single source: no check applied, returns even if implausible
    assert result == 250.0


def test_scalar_plausible_empty():
    """No records → None."""
    result = _scalar_plausible([], _always_true)
    assert result is None


def test_scalar_plausible_no_check():
    """No plausibility check → use best source."""
    records = [_watch_sample(999), _iphone_sample(60)]
    result = _scalar_plausible(records)
    assert result == 999.0


# --- _sum_plausible tests ---


def test_sum_plausible_fallback():
    """Apple Watch sum is implausible, iPhone sum is plausible → fallback."""
    watch_records = [_watch_sample(300_000, minute=i) for i in range(1)]
    iphone_records = [_iphone_sample(8000, minute=i) for i in range(1)]
    records = watch_records + iphone_records
    result = _sum_plausible(records, _steps_plausible)
    assert result == 8000


def test_sum_plausible_best_source_ok():
    """Apple Watch sum is plausible → use it."""
    records = [_watch_sample(5000), _iphone_sample(4000)]
    result = _sum_plausible(records, _steps_plausible)
    assert result == 5000


def test_sum_plausible_empty():
    result = _sum_plausible([], _always_true)
    assert result == 0


def test_sum_plausible_single_source_no_check():
    """Single source → no plausibility check."""
    records = [_watch_sample(999_999)]
    result = _sum_plausible(records, _steps_plausible)
    assert result == 999_999


# --- _float_sum_plausible tests ---


def test_float_sum_plausible_fallback():
    """Apple Watch sum implausible → fallback to iPhone."""
    records = [_watch_sample(500.0), _iphone_sample(10.5)]
    result = _float_sum_plausible(records, _distance_plausible)
    assert result == 10.5


def test_float_sum_plausible_empty():
    result = _float_sum_plausible([], _always_true)
    assert result == 0.0


# --- _avg_plausible tests ---


def test_avg_plausible_fallback():
    """Apple Watch avg implausible, iPhone avg plausible → fallback."""
    watch = [_watch_sample(500, minute=0), _watch_sample(600, minute=1)]
    iphone = [_iphone_sample(30, minute=0), _iphone_sample(40, minute=1)]
    records = watch + iphone
    result = _avg_plausible(records, _rmssd_plausible)
    assert result == 35.0  # avg of 30 and 40


def test_avg_plausible_best_source_ok():
    """Apple Watch avg plausible → use it."""
    watch = [_watch_sample(30, minute=0), _watch_sample(40, minute=1)]
    iphone = [_iphone_sample(25, minute=0)]
    records = watch + iphone
    result = _avg_plausible(records, _rmssd_plausible)
    assert result == 35.0  # avg of 30 and 40 from Watch


def test_avg_plausible_empty():
    result = _avg_plausible([], _always_true)
    assert result is None


def test_avg_plausible_single_source():
    """Single source → no check."""
    records = [_watch_sample(999)]
    result = _avg_plausible(records, _rmssd_plausible)
    assert result == 999.0


# --- _resample_hr_plausible tests ---


def _hr_sample(bpm: float, source: str, device: str, minute: int) -> RawSample:
    return RawSample(
        type="HKQuantityTypeIdentifierHeartRate",
        source_name=source,
        device=device,
        start=datetime(2025, 1, 1, 10, minute, 0, tzinfo=timezone.utc),
        end=datetime(2025, 1, 1, 10, minute, 30, tzinfo=timezone.utc),
        value=str(bpm),
        unit="count/min",
    )


def test_resample_hr_plausible_fallback():
    """Apple Watch HR avg implausible → fallback to iPhone."""
    watch = [_hr_sample(250, "Apple Watch", "Apple Watch Series 9", m) for m in range(3)]
    iphone = [_hr_sample(72, "iPhone", "iPhone 15", m) for m in range(3)]
    records = watch + iphone
    buckets = _resample_hr_plausible(records, _hr_range_plausible)
    assert len(buckets) == 3
    assert all(b.bpm == 72 for b in buckets)


def test_resample_hr_plausible_best_source_ok():
    """Apple Watch HR plausible → use it."""
    watch = [_hr_sample(80, "Apple Watch", "Apple Watch Series 9", m) for m in range(3)]
    iphone = [_hr_sample(72, "iPhone", "iPhone 15", m) for m in range(3)]
    records = watch + iphone
    buckets = _resample_hr_plausible(records, _hr_range_plausible)
    assert len(buckets) == 3
    assert all(b.bpm == 80 for b in buckets)


def test_resample_hr_plausible_empty():
    result = _resample_hr_plausible([], _always_true)
    assert result == []


def test_resample_hr_plausible_single_source():
    """Single source → no check, even if implausible."""
    watch = [_hr_sample(999, "Apple Watch", "Apple Watch Series 9", 0)]
    buckets = _resample_hr_plausible(watch, _hr_range_plausible)
    assert len(buckets) == 1
    assert buckets[0].bpm == 999
