"""Plausibility range constants for biometric data.

Mirrors api/domain/entity/plausibility.go.
"""

# Resting Heart Rate (bpm)
RESTING_HR_MIN = 30
RESTING_HR_MAX = 100

# Average Heart Rate (bpm)
AVG_HR_MIN = 25
AVG_HR_MAX = 200

# Max Heart Rate (bpm)
MAX_HR_MIN = 40
MAX_HR_MAX = 230

# HRV RMSSD (ms)
RMSSD_MIN = 5
RMSSD_MAX = 300

# SpO2 (%)
SPO2_MIN = 70
SPO2_MAX = 100

# Skin Temperature Delta (°C)
SKIN_TEMP_DELTA_MIN = -5
SKIN_TEMP_DELTA_MAX = 5

# Breathing Rate (breaths/min)
BR_MIN = 4
BR_MAX = 40

# Steps (daily total)
STEPS_MAX = 200_000

# Distance (km)
DISTANCE_KM_MAX = 300

# Calories (kcal)
CALORIES_TOTAL_MAX = 15_000

# Sleep Duration (minutes)
SLEEP_DURATION_MAX = 1440
