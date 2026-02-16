package fitbit

import (
	"strconv"
	"strings"

	"vitametron/api/domain/entity"
)

// ParseVO2MaxRange parses a Fitbit VO2 Max string like "42.5-46.4" and returns the midpoint.
func ParseVO2MaxRange(s string) *float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}

	parts := strings.SplitN(s, "-", 2)
	if len(parts) != 2 {
		// Try single value
		v, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return nil
		}
		return &v
	}

	low, err1 := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
	high, err2 := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
	if err1 != nil || err2 != nil {
		return nil
	}

	mid := (low + high) / 2
	return &mid
}

// MapSleepType returns "stages" or "classic" based on Fitbit's type field.
func MapSleepType(fitbitType string) string {
	if fitbitType == "stages" {
		return "stages"
	}
	return "classic"
}

// MapSleepStage normalizes Fitbit sleep stage names.
func MapSleepStage(stage string) string {
	switch strings.ToLower(stage) {
	case "deep":
		return "deep"
	case "light":
		return "light"
	case "rem":
		return "rem"
	case "wake":
		return "wake"
	case "restless":
		return "wake"
	case "asleep":
		return "light"
	case "awake":
		return "wake"
	default:
		return stage
	}
}

// NewDailySummaryFromActivity creates a partial DailySummary from Fitbit activity data.
func NewDailySummaryFromActivity(data map[string]any) *entity.DailySummary {
	s := &entity.DailySummary{Provider: "fitbit"}
	// This is a scaffold — actual JSON parsing will be implemented
	// when the Fitbit adapter is fully built.
	_ = data
	return s
}
