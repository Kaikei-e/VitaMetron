"""Circadian rhythm metric computation from wearable data.

Implements four families of circadian biomarkers using existing HR intraday
and sleep data:

1. **HR Cosinor Analysis** — Cornelissen (2014) "Cosinor-based rhythmometry"
   Parametric fit of 24h HR profile: MESOR, amplitude, acrophase.

2. **Non-Parametric Rest-Activity Rhythm (NPAR)** — Van Someren et al. (1999)
   IS (interdaily stability), IV (intradaily variability), RA (relative
   amplitude), M10/L5.

3. **Sleep Timing Metrics** — Roenneberg et al. (2004), Phillips et al. (2017)
   Sleep midpoint, midpoint variability, social jetlag.

4. **Nocturnal HR Dip** — Ohkubo et al. (2002)
   % drop from daytime to nighttime HR; healthy range 10-20%.
"""

import datetime
import logging
import math
from dataclasses import dataclass

import asyncpg
import numpy as np

UTC = datetime.timezone.utc

logger = logging.getLogger(__name__)

# Minimum HR samples required for cosinor (50% of 1440 minutes in 24h)
MIN_HR_SAMPLES_COSINOR = 720

# Minimum HR samples per hour-bin for NPAR (at least 30 min coverage)
MIN_SAMPLES_PER_HOUR = 30

# Minimum days for multi-day metrics (IS, IV, sleep timing)
MIN_DAYS_MULTIDAY = 3

HR_INTRADAY_QUERY = """
SELECT time, bpm FROM heart_rate_intraday
WHERE time BETWEEN $1 AND $2
ORDER BY time
"""

HR_INTRADAY_MULTIDAY_QUERY = """
SELECT time, bpm FROM heart_rate_intraday
WHERE time BETWEEN $1 AND $2
ORDER BY time
"""

SLEEP_TIMING_QUERY = """
SELECT date, sleep_start, sleep_end, sleep_duration_min
FROM daily_summaries
WHERE date BETWEEN $1::date AND $2::date
  AND sleep_start IS NOT NULL AND sleep_end IS NOT NULL
ORDER BY date
"""

SLEEP_STAGES_QUERY = """
SELECT time, stage, seconds FROM sleep_stages
WHERE time BETWEEN $1 AND $2
ORDER BY time
"""


# ── Result dataclasses ──────────────────────────────────────────────


@dataclass
class CosinorResult:
    mesor: float
    amplitude: float
    acrophase_hour: float  # 0-24


@dataclass
class NPARResult:
    is_value: float       # interdaily stability, 0-1
    iv_value: float       # intradaily variability, 0-2
    ra_value: float       # relative amplitude, 0-1
    m10_value: float      # mean HR during 10 most active hours
    m10_start_hour: float
    l5_value: float       # mean HR during 5 least active hours
    l5_start_hour: float


@dataclass
class SleepTimingResult:
    midpoint_hour: float          # today's sleep midpoint (0-24)
    midpoint_variability_min: float  # SD of midpoints in minutes
    social_jetlag_min: float      # |weekend - weekday| midpoint diff


@dataclass
class NocturnalDipResult:
    dip_pct: float
    daytime_mean_hr: float
    nighttime_mean_hr: float


# ── 1. HR Cosinor Analysis ──────────────────────────────────────────


def _noon_to_noon_utc(date: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Return UTC-aware noon-to-noon window for the given date."""
    start = datetime.datetime.combine(
        date - datetime.timedelta(days=1), datetime.time(12, 0), tzinfo=UTC,
    )
    end = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=UTC)
    return start, end


async def compute_hr_cosinor(
    pool: asyncpg.Pool,
    date: datetime.date,
) -> CosinorResult | None:
    """Fit single-component cosinor model to 24h HR data.

    Linearized model: Y = M + beta1*cos(2*pi*t/24) + beta2*sin(2*pi*t/24)
    Solved via ordinary least squares (numpy.linalg.lstsq).
    """
    start, end = _noon_to_noon_utc(date)
    async with pool.acquire() as conn:
        rows = await conn.fetch(HR_INTRADAY_QUERY, start, end)

    if len(rows) < MIN_HR_SAMPLES_COSINOR:
        logger.info(
            "Insufficient HR data for cosinor on %s: %d/%d",
            date, len(rows), MIN_HR_SAMPLES_COSINOR,
        )
        return None

    # Convert to fractional hours from window start
    t = np.array([
        (r["time"] - start).total_seconds() / 3600.0 for r in rows
    ])
    y = np.array([float(r["bpm"]) for r in rows])

    # Build design matrix: [1, cos(2*pi*t/24), sin(2*pi*t/24)]
    omega = 2 * np.pi / 24.0
    cos_t = np.cos(omega * t)
    sin_t = np.sin(omega * t)
    A = np.column_stack([np.ones_like(t), cos_t, sin_t])

    # Least squares fit
    result, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    mesor = float(result[0])
    beta1 = float(result[1])
    beta2 = float(result[2])

    amplitude = math.sqrt(beta1**2 + beta2**2)

    # Acrophase in hours: atan2(-beta2, beta1) gives phase in radians
    # Convert to hours (0-24)
    acrophase_rad = math.atan2(-beta2, beta1)
    acrophase_hour = (acrophase_rad * 24 / (2 * math.pi)) % 24

    # Offset by window start (noon of previous day)
    # The time origin is noon, so add 12 to get clock hours
    acrophase_hour = (acrophase_hour + 12) % 24

    logger.info(
        "Cosinor for %s: MESOR=%.1f, amp=%.1f, acrophase=%.1fh",
        date, mesor, amplitude, acrophase_hour,
    )
    return CosinorResult(
        mesor=round(mesor, 2),
        amplitude=round(amplitude, 2),
        acrophase_hour=round(acrophase_hour, 2),
    )


# ── 2. Non-Parametric Rest-Activity Rhythm ──────────────────────────


def _sliding_window_mean(hourly: np.ndarray, window_hours: int) -> np.ndarray:
    """Compute mean over a sliding window on circular 24h data."""
    n = len(hourly)  # should be 24
    # Extend circularly for wrap-around
    extended = np.concatenate([hourly, hourly])
    cumsum = np.cumsum(extended)
    cumsum = np.insert(cumsum, 0, 0)
    sums = cumsum[window_hours:n + window_hours] - cumsum[:n]
    return sums / window_hours


async def compute_npar_metrics(
    pool: asyncpg.Pool,
    date: datetime.date,
    window_days: int = 7,
) -> NPARResult | None:
    """Compute IS, IV, RA, M10, L5 from multi-day HR data.

    Uses hourly HR bins over trailing `window_days` days.
    """
    end_dt = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=UTC)
    start_dt = end_dt - datetime.timedelta(days=window_days)

    async with pool.acquire() as conn:
        rows = await conn.fetch(HR_INTRADAY_MULTIDAY_QUERY, start_dt, end_dt)

    if not rows:
        return None

    # Bin into (day, hour) arrays
    # Day 0 = first noon-to-noon period
    day_hour_sums: dict[tuple[int, int], list[float]] = {}
    for r in rows:
        t = r["time"]
        elapsed = (t - start_dt).total_seconds()
        day = int(elapsed // 86400)
        hour = int((elapsed % 86400) // 3600)
        key = (day, hour)
        if key not in day_hour_sums:
            day_hour_sums[key] = []
        day_hour_sums[key].append(float(r["bpm"]))

    # Build day x hour matrix (n_days x 24)
    n_days = window_days
    hourly_matrix = np.full((n_days, 24), np.nan)
    for (d, h), vals in day_hour_sums.items():
        if 0 <= d < n_days and 0 <= h < 24 and len(vals) >= MIN_SAMPLES_PER_HOUR:
            hourly_matrix[d, h] = np.mean(vals)

    # Count days with sufficient coverage (at least 20 of 24 hours)
    valid_days = np.sum(np.sum(~np.isnan(hourly_matrix), axis=1) >= 20)
    if valid_days < MIN_DAYS_MULTIDAY:
        logger.info("Insufficient days for NPAR on %s: %d/%d", date, valid_days, MIN_DAYS_MULTIDAY)
        return None

    # Fill NaN with column (hour) mean for computation
    col_means = np.nanmean(hourly_matrix, axis=0)
    for h in range(24):
        mask = np.isnan(hourly_matrix[:, h])
        hourly_matrix[mask, h] = col_means[h]

    # ── IS (Interdaily Stability) ──
    # IS = (N * sum((x_bar_h - x_bar)^2)) / (p * sum((x_i - x_bar)^2))
    # x_bar_h = mean of each hour across days, x_bar = grand mean
    # N = total data points, p = number of hours (24)
    x_flat = hourly_matrix.flatten()
    x_bar = np.mean(x_flat)
    x_bar_h = np.mean(hourly_matrix, axis=0)  # mean per hour across days
    N = len(x_flat)
    p = 24

    numerator_is = N * np.sum((x_bar_h - x_bar) ** 2)
    denominator_is = p * np.sum((x_flat - x_bar) ** 2)
    is_val = float(numerator_is / denominator_is) if denominator_is > 0 else 0.0
    is_val = max(0.0, min(1.0, is_val))

    # ── IV (Intradaily Variability) ──
    # IV = (N * sum(diff(x_i)^2)) / ((N-1) * sum((x_i - x_bar)^2))
    diffs = np.diff(x_flat)
    numerator_iv = N * np.sum(diffs ** 2)
    denominator_iv = (N - 1) * np.sum((x_flat - x_bar) ** 2)
    iv_val = float(numerator_iv / denominator_iv) if denominator_iv > 0 else 0.0
    iv_val = max(0.0, min(2.0, iv_val))

    # ── M10 / L5 / RA ──
    # Use today's (last day's) hourly data for M10/L5
    today_hourly = hourly_matrix[-1]
    m10_means = _sliding_window_mean(today_hourly, 10)
    l5_means = _sliding_window_mean(today_hourly, 5)

    m10_start = int(np.argmax(m10_means))
    l5_start = int(np.argmin(l5_means))
    m10_val = float(m10_means[m10_start])
    l5_val = float(l5_means[l5_start])

    # Convert from noon-based to clock hours
    m10_start_clock = (m10_start + 12) % 24
    l5_start_clock = (l5_start + 12) % 24

    ra_val = (m10_val - l5_val) / (m10_val + l5_val) if (m10_val + l5_val) > 0 else 0.0
    ra_val = max(0.0, min(1.0, ra_val))

    logger.info(
        "NPAR for %s: IS=%.3f, IV=%.3f, RA=%.3f, M10=%.1f@%dh, L5=%.1f@%dh",
        date, is_val, iv_val, ra_val,
        m10_val, m10_start_clock, l5_val, l5_start_clock,
    )
    return NPARResult(
        is_value=round(is_val, 4),
        iv_value=round(iv_val, 4),
        ra_value=round(ra_val, 4),
        m10_value=round(m10_val, 2),
        m10_start_hour=float(m10_start_clock),
        l5_value=round(l5_val, 2),
        l5_start_hour=float(l5_start_clock),
    )


# ── 3. Sleep Timing Metrics ─────────────────────────────────────────


def _time_to_minutes_from_midnight(dt: datetime.datetime) -> float:
    """Convert datetime to minutes from midnight, handling sleep crossing midnight."""
    return dt.hour * 60 + dt.minute + dt.second / 60


def _circular_mean_minutes(minutes: list[float]) -> float:
    """Compute circular mean of times in minutes (handles midnight crossing).

    Uses circular statistics: convert to angles, compute mean angle, convert back.
    """
    if not minutes:
        return 0.0
    angles = [m * 2 * math.pi / 1440 for m in minutes]  # 1440 min/day
    sin_mean = sum(math.sin(a) for a in angles) / len(angles)
    cos_mean = sum(math.cos(a) for a in angles) / len(angles)
    mean_angle = math.atan2(sin_mean, cos_mean)
    return (mean_angle * 1440 / (2 * math.pi)) % 1440


def _circular_std_minutes(minutes: list[float]) -> float:
    """Compute circular standard deviation in minutes."""
    if len(minutes) < 2:
        return 0.0
    angles = [m * 2 * math.pi / 1440 for m in minutes]
    sin_mean = sum(math.sin(a) for a in angles) / len(angles)
    cos_mean = sum(math.cos(a) for a in angles) / len(angles)
    R = math.sqrt(sin_mean**2 + cos_mean**2)
    # Circular SD: sqrt(-2 * ln(R)) converted to minutes
    if R >= 1.0:
        return 0.0
    if R <= 0.0:
        return 720.0  # maximum possible
    return math.sqrt(-2 * math.log(R)) * 1440 / (2 * math.pi)


async def compute_sleep_timing(
    pool: asyncpg.Pool,
    date: datetime.date,
    window_days: int = 7,
) -> SleepTimingResult | None:
    """Compute sleep midpoint, variability, and social jetlag."""
    start_date = date - datetime.timedelta(days=window_days - 1)

    async with pool.acquire() as conn:
        rows = await conn.fetch(SLEEP_TIMING_QUERY, start_date, date)

    if len(rows) < MIN_DAYS_MULTIDAY:
        logger.info("Insufficient sleep data for timing on %s: %d days", date, len(rows))
        return None

    midpoints_min: list[float] = []
    weekday_midpoints: list[float] = []
    weekend_midpoints: list[float] = []
    today_midpoint: float | None = None

    for row in rows:
        sleep_start = row["sleep_start"]
        sleep_end = row["sleep_end"]
        row_date = row["date"]

        # Compute midpoint as average of start and end times
        start_min = _time_to_minutes_from_midnight(sleep_start)
        end_min = _time_to_minutes_from_midnight(sleep_end)

        # Handle midnight crossing: if start > end, start is before midnight
        if start_min > end_min:
            # e.g., 23:00 (1380) to 07:00 (420) → midpoint around 03:00
            mid = ((start_min + end_min + 1440) / 2) % 1440
        else:
            mid = (start_min + end_min) / 2

        midpoints_min.append(mid)

        # day_of_week: 0=Monday ... 6=Sunday
        dow = row_date.weekday()
        if dow >= 5:  # Saturday, Sunday
            weekend_midpoints.append(mid)
        else:
            weekday_midpoints.append(mid)

        if row_date == date:
            today_midpoint = mid

    if today_midpoint is None and midpoints_min:
        today_midpoint = midpoints_min[-1]

    if today_midpoint is None:
        return None

    # Midpoint variability (circular SD in minutes)
    variability = _circular_std_minutes(midpoints_min)

    # Social jetlag: |mean(weekend) - mean(weekday)|
    if weekday_midpoints and weekend_midpoints:
        wd_mean = _circular_mean_minutes(weekday_midpoints)
        we_mean = _circular_mean_minutes(weekend_midpoints)
        jetlag = abs(we_mean - wd_mean)
        # Handle circular distance
        if jetlag > 720:
            jetlag = 1440 - jetlag
    else:
        jetlag = 0.0

    midpoint_hour = today_midpoint / 60.0

    logger.info(
        "Sleep timing for %s: midpoint=%.1fh, variability=%.0fmin, jetlag=%.0fmin",
        date, midpoint_hour, variability, jetlag,
    )
    return SleepTimingResult(
        midpoint_hour=round(midpoint_hour, 2),
        midpoint_variability_min=round(variability, 1),
        social_jetlag_min=round(jetlag, 1),
    )


# ── 4. Nocturnal HR Dip ─────────────────────────────────────────────


async def compute_nocturnal_hr_dip(
    pool: asyncpg.Pool,
    date: datetime.date,
) -> NocturnalDipResult | None:
    """Compute nocturnal HR dip percentage.

    Daytime: HR samples between 10:00-22:00
    Nighttime: HR samples during sleep stages (deep/light/rem)
    Dip% = (daytime_mean - nighttime_mean) / daytime_mean * 100

    Healthy range: 10-20% (Ohkubo et al., 2002)
    """
    start, end = _noon_to_noon_utc(date)

    async with pool.acquire() as conn:
        hr_rows = await conn.fetch(HR_INTRADAY_QUERY, start, end)
        sleep_rows = await conn.fetch(SLEEP_STAGES_QUERY, start, end)

    if len(hr_rows) < MIN_HR_SAMPLES_COSINOR:
        return None

    # Build sleep period set (timestamps when asleep)
    sleep_periods: list[tuple[datetime.datetime, datetime.datetime]] = []
    sleep_stages = {"deep", "light", "rem"}
    for sr in sleep_rows:
        if sr["stage"] in sleep_stages:
            stage_start = sr["time"]
            stage_end = stage_start + datetime.timedelta(seconds=sr["seconds"])
            sleep_periods.append((stage_start, stage_end))

    if not sleep_periods:
        return None

    def _is_during_sleep(t: datetime.datetime) -> bool:
        for sp_start, sp_end in sleep_periods:
            if sp_start <= t < sp_end:
                return True
        return False

    # Compute daytime and nighttime HR
    daytime_hrs: list[float] = []
    nighttime_hrs: list[float] = []

    for r in hr_rows:
        t = r["time"]
        bpm = float(r["bpm"])
        hour = t.hour

        # Daytime: 10:00-22:00
        if 10 <= hour < 22:
            daytime_hrs.append(bpm)

        # Nighttime: during sleep
        if _is_during_sleep(t):
            nighttime_hrs.append(bpm)

    if not daytime_hrs or not nighttime_hrs:
        return None

    daytime_mean = float(np.mean(daytime_hrs))
    nighttime_mean = float(np.mean(nighttime_hrs))

    if daytime_mean == 0:
        return None

    dip_pct = (daytime_mean - nighttime_mean) / daytime_mean * 100

    logger.info(
        "Nocturnal dip for %s: %.1f%% (day=%.1f, night=%.1f)",
        date, dip_pct, daytime_mean, nighttime_mean,
    )
    return NocturnalDipResult(
        dip_pct=round(dip_pct, 2),
        daytime_mean_hr=round(daytime_mean, 1),
        nighttime_mean_hr=round(nighttime_mean, 1),
    )
