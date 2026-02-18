package fitbit

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"vitametron/api/domain/entity"
)

// jst is the Asia/Tokyo timezone (UTC+9) used for parsing Fitbit timestamps.
// Fitbit API returns times in the user's profile timezone (JST).
var jst = time.FixedZone("JST", 9*60*60)

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

// mapActivityToSummary converts Fitbit activity response to a DailySummary entity.
func mapActivityToSummary(resp *ActivityResponse, date time.Time) *entity.DailySummary {
	s := &entity.DailySummary{
		Date:             date,
		Provider:         "fitbit",
		Steps:            resp.Summary.Steps,
		CaloriesTotal:    resp.Summary.CaloriesOut,
		CaloriesBMR:      resp.Summary.CaloriesBMR,
		Floors:           resp.Summary.Floors,
		RestingHR:        resp.Summary.RestingHeartRate,
		ActiveZoneMin:    resp.Summary.ActiveZoneMinutes,
		MinutesSedentary: resp.Summary.SedentaryMinutes,
		MinutesLightly:   resp.Summary.LightlyActiveMinutes,
		MinutesFairly:    resp.Summary.FairlyActiveMinutes,
		MinutesVery:      resp.Summary.VeryActiveMinutes,
		SyncedAt:         time.Now(),
	}

	// Calculate calories active = total - BMR
	if s.CaloriesTotal > s.CaloriesBMR {
		s.CaloriesActive = s.CaloriesTotal - s.CaloriesBMR
	}

	// Distance — use "total" activity distance
	for _, d := range resp.Summary.Distances {
		if d.Activity == "total" {
			s.DistanceKM = float32(d.Distance)
			break
		}
	}

	// Heart rate zones
	for _, zone := range resp.Summary.HeartRateZones {
		switch strings.ToLower(zone.Name) {
		case "out of range":
			s.HRZoneOutMin = zone.Minutes
		case "fat burn":
			s.HRZoneFatMin = zone.Minutes
		case "cardio":
			s.HRZoneCardioMin = zone.Minutes
		case "peak":
			s.HRZonePeakMin = zone.Minutes
		}
	}

	return s
}

// mapSleepStages extracts sleep stage data from the main sleep record.
func mapSleepStages(resp *SleepResponse, date time.Time) []entity.SleepStage {
	var stages []entity.SleepStage

	for _, sleep := range resp.Sleep {
		if !sleep.IsMainSleep {
			continue
		}

		for _, d := range sleep.Levels.Data {
			t, err := time.ParseInLocation("2006-01-02T15:04:05.000", d.DateTime, jst)
			if err != nil {
				t = date // fallback
			}
			stages = append(stages, entity.SleepStage{
				Time:    t,
				Stage:   MapSleepStage(d.Level),
				Seconds: d.Seconds,
				LogID:   sleep.LogID,
			})
		}
		break // only main sleep
	}

	return stages
}

// mapSleepRecord extracts a SleepRecord from the main sleep entry.
func mapSleepRecord(resp *SleepResponse) *entity.SleepRecord {
	for _, sleep := range resp.Sleep {
		if !sleep.IsMainSleep {
			continue
		}

		startTime, _ := time.ParseInLocation("2006-01-02T15:04:05.000", sleep.StartTime, jst)
		endTime, _ := time.ParseInLocation("2006-01-02T15:04:05.000", sleep.EndTime, jst)

		rec := &entity.SleepRecord{
			LogID:         sleep.LogID,
			StartTime:     startTime,
			EndTime:       endTime,
			DurationMin:   int(sleep.Duration / 60000),
			MinutesAsleep: sleep.MinutesAsleep,
			MinutesAwake:  sleep.MinutesAwake,
			Type:          MapSleepType(sleep.Type),
			IsMainSleep:   true,
		}

		if sleep.Levels.Summary.Deep != nil {
			rec.DeepMin = sleep.Levels.Summary.Deep.Minutes
		}
		if sleep.Levels.Summary.Light != nil {
			rec.LightMin = sleep.Levels.Summary.Light.Minutes
		}
		if sleep.Levels.Summary.REM != nil {
			rec.REMMin = sleep.Levels.Summary.REM.Minutes
		}
		if sleep.Levels.Summary.Wake != nil {
			rec.WakeMin = sleep.Levels.Summary.Wake.Minutes
		}

		return rec
	}
	return nil
}

// mapHRIntraday converts HR intraday data to HeartRateSample entities.
func mapHRIntraday(resp *HRIntradayResponse, date time.Time) []entity.HeartRateSample {
	dateStr := date.Format("2006-01-02")
	samples := make([]entity.HeartRateSample, 0, len(resp.ActivitiesHeartIntraday.Dataset))

	for _, d := range resp.ActivitiesHeartIntraday.Dataset {
		t, err := time.ParseInLocation("2006-01-02 15:04:05", dateStr+" "+d.Time, jst)
		if err != nil {
			continue
		}
		samples = append(samples, entity.HeartRateSample{
			Time: t,
			BPM:  d.Value,
		})
	}

	return samples
}

// mapExerciseLogs converts activity entries to ExerciseLog entities.
func mapExerciseLogs(resp *ActivityResponse, date time.Time) []entity.ExerciseLog {
	dateStr := date.Format("2006-01-02")
	logs := make([]entity.ExerciseLog, 0, len(resp.Activities))

	for _, a := range resp.Activities {
		startedAt, err := time.ParseInLocation("2006-01-02T15:04", dateStr+"T"+a.StartTime, jst)
		if err != nil {
			startedAt, err = time.Parse("2006-01-02T15:04:05.000+00:00", a.StartTime)
			if err != nil {
				startedAt = date
			}
		}

		log := entity.ExerciseLog{
			ExternalID:   fmt.Sprintf("%d", a.LogID),
			ActivityName: a.ActivityName,
			StartedAt:    startedAt,
			DurationMS:   a.Duration,
			Calories:     a.Calories,
			AvgHR:        a.AverageHeartRate,
			DistanceKM:   float32(a.Distance),
			SyncedAt:     time.Now(),
		}

		if a.ActiveZoneMinutes != nil {
			if zoneJSON, err := json.Marshal(a.ActiveZoneMinutes); err == nil {
				log.ZoneMinutes = zoneJSON
			}
		}

		logs = append(logs, log)
	}

	return logs
}
