"""Human-readable explanation generation for anomaly detections.

Translates SHAP values + feature values into natural language explanations.
"""

from dataclasses import dataclass

# Feature metadata: (display_name, unit, typical_direction)
# typical_direction: "higher" means higher value is more unusual/concerning
FEATURE_META: dict[str, tuple[str, str, str]] = {
    "resting_hr": ("Resting HR", "bpm", "higher"),
    "hrv_ln_rmssd": ("HRV (log RMSSD)", "", "lower"),
    "sleep_duration_min": ("Sleep duration", "min", "lower"),
    "sleep_deep_min": ("Deep sleep", "min", "lower"),
    "spo2_avg": ("SpO2", "%", "lower"),
    "br_full_sleep": ("Breathing rate", "br/min", "higher"),
    "steps": ("Steps", "steps", "lower"),
    "skin_temp_variation": ("Skin temp variation", "°C", "higher"),
    "resting_hr_delta": ("RHR 7d delta", "bpm", "higher"),
    "hrv_delta": ("HRV 7d delta", "", "lower"),
    "sleep_delta": ("Sleep 7d delta", "min", "lower"),
    "steps_delta": ("Steps 7d delta", "steps", "lower"),
    "spo2_delta": ("SpO2 7d delta", "%", "lower"),
    "rhr_3d_std": ("RHR 3d variability", "bpm", "higher"),
    "hrv_3d_std": ("HRV 3d variability", "", "higher"),
    "sleep_3d_std": ("Sleep 3d variability", "min", "higher"),
    "rhr_change_rate": ("RHR day-over-day change", "%", "higher"),
    "hrv_change_rate": ("HRV day-over-day change", "%", "lower"),
    "day_of_week": ("Day of week", "", "neutral"),
}


@dataclass
class AnomalyFeatureContribution:
    feature: str
    shap_value: float
    direction: str  # "higher" | "lower" | "neutral"
    description: str


def generate_explanation(
    shap_values: dict[str, float],
    features: dict,
    baseline: dict | None = None,
) -> tuple[str, list[AnomalyFeatureContribution]]:
    """Generate human-readable explanation from SHAP values.

    Args:
        shap_values: feature_name -> SHAP value
        features: feature_name -> current value
        baseline: feature_name -> typical value (optional)

    Returns:
        (summary_text, sorted_contributions)
    """
    contributions: list[AnomalyFeatureContribution] = []

    for name, shap_val in shap_values.items():
        meta = FEATURE_META.get(name)
        if meta is None:
            continue

        display_name, unit, _ = meta
        current = features.get(name)

        # Determine direction based on SHAP sign
        # Negative SHAP = pushes toward anomaly in IF
        if shap_val < 0:
            direction = "anomalous"
        elif shap_val > 0:
            direction = "normal"
        else:
            direction = "neutral"

        # Build description
        desc = _build_description(display_name, unit, current, baseline, name, shap_val)

        contributions.append(
            AnomalyFeatureContribution(
                feature=name,
                shap_value=round(shap_val, 4),
                direction=direction,
                description=desc,
            )
        )

    # Sort by absolute SHAP value descending
    contributions.sort(key=lambda c: abs(c.shap_value), reverse=True)

    # Build summary from top 3 drivers
    top_drivers = [c for c in contributions[:3] if c.direction == "anomalous"]
    summary = _build_summary(top_drivers)

    return summary, contributions


def _build_description(
    display_name: str,
    unit: str,
    current,
    baseline: dict | None,
    feature_name: str,
    shap_val: float,
) -> str:
    """Build a single-feature description string."""
    if current is None:
        return f"{display_name} data not available"

    val_str = f"{current:.0f}" if isinstance(current, float) and current == int(current) else f"{current:.1f}"
    if unit:
        val_str = f"{val_str} {unit}"

    if baseline and feature_name in baseline and baseline[feature_name] is not None:
        typical = baseline[feature_name]
        diff = current - typical
        typical_str = f"{typical:.1f}"
        if unit:
            typical_str = f"{typical_str} {unit}"
        if diff > 0:
            return f"{display_name} was {val_str} ({diff:.1f} above typical {typical_str})"
        elif diff < 0:
            return f"{display_name} was {val_str} ({abs(diff):.1f} below typical {typical_str})"
        else:
            return f"{display_name} was {val_str} (at typical level)"

    return f"{display_name} was {val_str}"


def _build_summary(top_drivers: list[AnomalyFeatureContribution]) -> str:
    """Build summary text from top anomalous drivers."""
    if not top_drivers:
        return "No strong anomaly drivers detected."

    if len(top_drivers) == 1:
        return f"Your health pattern today was unusual — the main driver was {top_drivers[0].description.lower()}."

    main = top_drivers[0].description.lower()
    secondary = top_drivers[1].description.lower()
    return f"Your health pattern today was unusual — the main driver was {main}, combined with {secondary}."
