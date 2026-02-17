"""Sleep session assembly from HealthKit SleepAnalysis records.

Implements Fitbit-compatible sleep processing:
- Groups continuous segments into sessions (30min gap = new session)
- dateOfSleep = endDate (wake time) date (Fitbit convention)
- isMainSleep = longest session of the day
- iOS 16+ stage mapping: InBed/Core→light, Deep→deep, REM→rem, Awake→wake
- Short wake (<3min) separated as shortData
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.healthkit.parser import RawSleepSample

logger = logging.getLogger(__name__)

# Gap threshold for splitting sessions
SESSION_GAP = timedelta(minutes=30)

# Short wake threshold (Fitbit separates <3min wakes)
SHORT_WAKE_THRESHOLD = timedelta(minutes=3)


@dataclass
class SleepStage:
    """A single stage within a sleep session."""
    start: datetime
    end: datetime
    stage: str  # "deep", "light", "rem", "wake"
    seconds: int
    is_short_data: bool = False  # True for <3min wake segments


@dataclass
class SleepSession:
    """A complete sleep session."""
    start: datetime
    end: datetime
    date_of_sleep: str  # YYYY-MM-DD (based on end/wake time)
    is_main_sleep: bool = False
    stages: list[SleepStage] = field(default_factory=list)

    @property
    def duration_min(self) -> int:
        return round((self.end - self.start).total_seconds() / 60)

    @property
    def minutes_asleep(self) -> int:
        return sum(
            s.seconds // 60 for s in self.stages
            if s.stage in ("deep", "light", "rem") and not s.is_short_data
        )

    @property
    def minutes_awake(self) -> int:
        return sum(
            s.seconds // 60 for s in self.stages
            if s.stage == "wake"
        )

    @property
    def deep_min(self) -> int:
        return sum(s.seconds // 60 for s in self.stages if s.stage == "deep")

    @property
    def light_min(self) -> int:
        return sum(s.seconds // 60 for s in self.stages if s.stage == "light")

    @property
    def rem_min(self) -> int:
        return sum(s.seconds // 60 for s in self.stages if s.stage == "rem")

    @property
    def wake_min(self) -> int:
        return sum(s.seconds // 60 for s in self.stages if s.stage == "wake")

    @property
    def sleep_onset_latency(self) -> int:
        """Minutes from session start to first non-wake stage."""
        if not self.stages:
            return 0
        for s in self.stages:
            if s.stage not in ("wake", "inbed"):
                diff = (s.start - self.start).total_seconds()
                return max(0, round(diff / 60))
        return 0

    @property
    def sleep_type(self) -> str:
        """Determine if this is a 'stages' or 'classic' sleep session."""
        stage_types = {s.stage for s in self.stages}
        if stage_types & {"deep", "rem"}:
            return "stages"
        return "classic"


def build_sleep_sessions(
    sleep_records: list[RawSleepSample],
    target_date: str,
) -> list[SleepSession]:
    """Build sleep sessions from raw SleepAnalysis records.

    Args:
        sleep_records: All sleep records (not pre-filtered by date).
        target_date: The date we're processing (YYYY-MM-DD).

    Returns:
        Sleep sessions whose dateOfSleep matches target_date.
    """
    if not sleep_records:
        return []

    # Filter out purely InBed records if we have stage data
    has_stages = any(r.stage_type in ("deep", "light", "rem", "wake") for r in sleep_records)

    filtered = []
    for r in sleep_records:
        stage = r.stage_type
        if stage == "unknown":
            continue
        # If we have iOS 16+ stage data, skip bare InBed records
        if has_stages and stage == "inbed":
            continue
        filtered.append(r)

    if not filtered:
        return []

    # Sort by start time
    filtered.sort(key=lambda r: r.start)

    # Group into sessions by 30-min gap
    sessions: list[list[RawSleepSample]] = []
    current_session: list[RawSleepSample] = [filtered[0]]

    for r in filtered[1:]:
        prev_end = current_session[-1].end
        if r.start - prev_end > SESSION_GAP:
            sessions.append(current_session)
            current_session = [r]
        else:
            current_session.append(r)

    if current_session:
        sessions.append(current_session)

    # Convert to SleepSession objects
    result: list[SleepSession] = []
    for seg_list in sessions:
        session_start = seg_list[0].start
        session_end = seg_list[-1].end

        # dateOfSleep = end (wake time) date
        date_of_sleep = session_end.strftime("%Y-%m-%d")

        stages: list[SleepStage] = []
        for r in seg_list:
            stage = r.stage_type
            if stage == "inbed":
                continue  # Skip InBed in stage-based sessions
            secs = round((r.end - r.start).total_seconds())
            if secs <= 0:
                continue

            is_short = (
                stage == "wake"
                and timedelta(seconds=secs) < SHORT_WAKE_THRESHOLD
            )

            stages.append(SleepStage(
                start=r.start,
                end=r.end,
                stage=stage,
                seconds=secs,
                is_short_data=is_short,
            ))

        if not stages:
            continue

        result.append(SleepSession(
            start=session_start,
            end=session_end,
            date_of_sleep=date_of_sleep,
            stages=stages,
        ))

    # Filter to target date
    target_sessions = [s for s in result if s.date_of_sleep == target_date]

    # Mark isMainSleep (longest session)
    if target_sessions:
        longest = max(target_sessions, key=lambda s: s.duration_min)
        longest.is_main_sleep = True

    return target_sessions
