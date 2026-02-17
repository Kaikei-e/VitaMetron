"""SAX/iterparse streaming parser for HealthKit export.xml."""

from __future__ import annotations

import logging
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import IO

from lxml import etree

logger = logging.getLogger(__name__)

RELEVANT_TYPES = {
    "HKQuantityTypeIdentifierHeartRate",
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierBasalEnergyBurned",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKQuantityTypeIdentifierOxygenSaturation",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierRespiratoryRate",
    "HKQuantityTypeIdentifierFlightsClimbed",
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature",
    "HKQuantityTypeIdentifierVO2Max",
}

WORKOUT_TYPE = "Workout"

# HealthKit date format: "2023-11-25 09:29:09 +0900"
HK_DATE_FMT = "%Y-%m-%d %H:%M:%S %z"


def parse_hk_datetime(s: str) -> datetime:
    """Parse HealthKit datetime string to timezone-aware datetime."""
    return datetime.strptime(s, HK_DATE_FMT)


def local_date_str(dt: datetime) -> str:
    """Get local date string (YYYY-MM-DD) preserving the original timezone."""
    return dt.strftime("%Y-%m-%d")


@dataclass
class RawSample:
    """A single HealthKit Record element."""
    type: str
    source_name: str
    device: str
    start: datetime
    end: datetime
    value: str
    unit: str

    @property
    def local_date(self) -> str:
        return local_date_str(self.start)

    @property
    def numeric_value(self) -> float:
        return float(self.value)


@dataclass
class RawSleepSample:
    """A SleepAnalysis record."""
    source_name: str
    device: str
    start: datetime
    end: datetime
    value: str  # e.g. "HKCategoryValueSleepAnalysisAsleepCore"

    @property
    def stage_type(self) -> str:
        """Map HealthKit sleep value to simplified stage name."""
        v = self.value
        if "AsleepCore" in v or "Asleep" in v:
            return "light"
        if "AsleepDeep" in v or "Deep" in v:
            return "deep"
        if "AsleepREM" in v or "REM" in v:
            return "rem"
        if "Awake" in v or "Wake" in v:
            return "wake"
        if "InBed" in v:
            return "inbed"
        return "unknown"


@dataclass
class RawWorkout:
    """A Workout element."""
    activity_type: str
    source_name: str
    device: str
    start: datetime
    end: datetime
    duration_sec: float
    total_distance_km: float | None
    total_energy_kcal: float | None

    @property
    def local_date(self) -> str:
        return local_date_str(self.start)


@dataclass
class ParsedData:
    """Result of parsing the entire HealthKit export."""
    date_of_birth: date | None
    records_by_date: dict[str, list[RawSample]]
    sleep_records: list[RawSleepSample]
    workouts_by_date: dict[str, list[RawWorkout]]
    total_records: int


def _is_apple_watch(source_name: str, device: str) -> bool:
    """Check if the record is from an Apple Watch."""
    check = (source_name + " " + device).lower()
    return "apple watch" in check or "watch" in check


def parse_healthkit_zip(zip_path: str) -> ParsedData:
    """Parse a HealthKit export ZIP file using streaming iterparse."""
    logger.info("Opening ZIP: %s", zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find export.xml inside the zip
        xml_name = None
        for name in zf.namelist():
            if name.endswith("export.xml"):
                xml_name = name
                break

        if not xml_name:
            raise ValueError("export.xml not found in ZIP archive")

        logger.info("Parsing: %s", xml_name)
        with zf.open(xml_name) as xml_file:
            return _parse_xml_stream(xml_file)


def _parse_xml_stream(xml_file: IO[bytes]) -> ParsedData:
    """Stream-parse the XML, extracting only relevant records."""
    records_by_date: dict[str, list[RawSample]] = defaultdict(list)
    sleep_records: list[RawSleepSample] = []
    workouts_by_date: dict[str, list[RawWorkout]] = defaultdict(list)
    dob: date | None = None
    total_records = 0
    count = 0

    context = etree.iterparse(xml_file, events=("end",), tag=("Record", "Workout", "Me"))

    for event, elem in context:
        tag = elem.tag

        if tag == "Me":
            dob_str = elem.get("HKCharacteristicTypeIdentifierDateOfBirth")
            if dob_str:
                try:
                    dob = date.fromisoformat(dob_str)
                    logger.info("DateOfBirth: %s", dob)
                except ValueError:
                    logger.warning("Could not parse DateOfBirth: %s", dob_str)
            elem.clear()
            continue

        if tag == "Record":
            rec_type = elem.get("type", "")

            if rec_type in RELEVANT_TYPES:
                start_str = elem.get("startDate", "")
                end_str = elem.get("endDate", "")
                if not start_str or not end_str:
                    elem.clear()
                    continue

                try:
                    start = parse_hk_datetime(start_str)
                    end = parse_hk_datetime(end_str)
                except ValueError:
                    elem.clear()
                    continue

                source_name = elem.get("sourceName", "")
                device = elem.get("device", "")
                value = elem.get("value", "")
                unit = elem.get("unit", "")

                if rec_type == "HKCategoryTypeIdentifierSleepAnalysis":
                    sleep_records.append(RawSleepSample(
                        source_name=source_name,
                        device=device,
                        start=start,
                        end=end,
                        value=value,
                    ))
                else:
                    sample = RawSample(
                        type=rec_type,
                        source_name=source_name,
                        device=device,
                        start=start,
                        end=end,
                        value=value,
                        unit=unit,
                    )
                    records_by_date[sample.local_date].append(sample)

                total_records += 1

            elem.clear()
            continue

        if tag == "Workout":
            start_str = elem.get("startDate", "")
            end_str = elem.get("endDate", "")
            if not start_str or not end_str:
                elem.clear()
                continue

            try:
                start = parse_hk_datetime(start_str)
                end = parse_hk_datetime(end_str)
            except ValueError:
                elem.clear()
                continue

            duration_str = elem.get("duration", "0")
            try:
                duration_sec = float(duration_str) * 60  # duration is in minutes
            except ValueError:
                duration_sec = (end - start).total_seconds()

            # Extract distance and energy from WorkoutStatistics children
            total_distance_km: float | None = None
            total_energy_kcal: float | None = None
            for stat in elem.findall("WorkoutStatistics"):
                stat_type = stat.get("type", "")
                sum_val = stat.get("sum")
                if sum_val is not None:
                    try:
                        val = float(sum_val)
                    except ValueError:
                        continue
                    if "DistanceWalkingRunning" in stat_type:
                        total_distance_km = val
                    elif "ActiveEnergyBurned" in stat_type:
                        total_energy_kcal = val

            activity_type = elem.get("workoutActivityType", "")
            # Simplify activity type name
            activity_type = activity_type.replace(
                "HKWorkoutActivityType", ""
            )

            workout = RawWorkout(
                activity_type=activity_type,
                source_name=elem.get("sourceName", ""),
                device=elem.get("device", ""),
                start=start,
                end=end,
                duration_sec=duration_sec,
                total_distance_km=total_distance_km,
                total_energy_kcal=total_energy_kcal,
            )
            workouts_by_date[workout.local_date].append(workout)
            total_records += 1

            elem.clear()
            continue

        # Clear any other elements
        elem.clear()

        count += 1
        if count % 500_000 == 0:
            logger.info("Parsed %d elements...", count)

    logger.info(
        "Parse complete: %d total records, %d dates, %d sleep records, %d workout dates",
        total_records, len(records_by_date), len(sleep_records), len(workouts_by_date),
    )

    return ParsedData(
        date_of_birth=dob,
        records_by_date=dict(records_by_date),
        sleep_records=sleep_records,
        workouts_by_date=dict(workouts_by_date),
        total_records=total_records,
    )
