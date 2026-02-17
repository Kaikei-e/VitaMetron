import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

RiskCheck = Callable[[dict], bool]

RISK_SIGNALS: dict[str, RiskCheck] = {
    "hrv_significant_drop": lambda f: (
        f.get("hrv_delta") is not None and f["hrv_delta"] < -15
    ),
    "rhr_elevated": lambda f: (
        f.get("resting_hr_delta") is not None and f["resting_hr_delta"] > 8
    ),
    "sleep_deficit": lambda f: (
        f.get("sleep_7d") is not None and f["sleep_7d"] < 360
    ),
    "spo2_low": lambda f: (
        f.get("spo2_min") is not None and f["spo2_min"] < 90
    ),
    "deep_sleep_low": lambda f: (
        f.get("sleep_deep_min") is not None and f["sleep_deep_min"] < 30
    ),
    "severe_sleep_deprivation": lambda f: (
        f.get("sleep_duration_min") is not None and f["sleep_duration_min"] < 240
    ),
    "breathing_rate_elevated": lambda f: (
        f.get("br_full_sleep") is not None and f["br_full_sleep"] > 20
    ),
}


def detect_risks(features: dict) -> list[str]:
    """Evaluate all risk signals against the given features.

    Returns a list of triggered risk signal names.
    Suppresses all risk signals when the day is invalid.
    """
    if features.get("is_valid_day") is False:
        return []

    triggered = []
    for name, check in RISK_SIGNALS.items():
        try:
            if check(features):
                triggered.append(name)
        except Exception:
            logger.exception("Error evaluating risk signal %s", name)
    return triggered
