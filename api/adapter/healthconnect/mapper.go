package healthconnect

import "time"

// MapSleepStage converts Health Connect integer sleep stage to domain string.
func MapSleepStage(stageType int) string {
	switch stageType {
	case 1:
		return "wake"
	case 2:
		return "light" // SLEEPING maps to light
	case 4:
		return "light"
	case 5:
		return "deep"
	case 6:
		return "rem"
	default:
		return ""
	}
}

// MapExerciseType converts Health Connect exercise type int to activity name.
func MapExerciseType(exerciseType int) string {
	switch exerciseType {
	case 2:
		return "Badminton"
	case 4:
		return "Basketball"
	case 5:
		return "Biking"
	case 8:
		return "Boot Camp"
	case 10:
		return "Boxing"
	case 14:
		return "Calisthenics"
	case 16:
		return "Cricket"
	case 24:
		return "Elliptical"
	case 26:
		return "Fencing"
	case 29:
		return "Football (American)"
	case 31:
		return "Golf"
	case 32:
		return "Guided Breathing"
	case 33:
		return "Gymnastics"
	case 34:
		return "Handball"
	case 35:
		return "HIIT"
	case 36:
		return "Hiking"
	case 37:
		return "Ice Hockey"
	case 38:
		return "Ice Skating"
	case 43:
		return "Martial Arts"
	case 46:
		return "Pilates"
	case 48:
		return "Racquetball"
	case 49:
		return "Running"
	case 50:
		return "Running (Treadmill)"
	case 51:
		return "Rowing"
	case 52:
		return "Rugby"
	case 53:
		return "Walking"
	case 54:
		return "Sailing"
	case 56:
		return "Skating"
	case 57:
		return "Skiing"
	case 58:
		return "Snowboarding"
	case 59:
		return "Snowshoeing"
	case 60:
		return "Soccer"
	case 61:
		return "Softball"
	case 62:
		return "Squash"
	case 63:
		return "Stair Climbing"
	case 64:
		return "Stair Climbing (Machine)"
	case 65:
		return "Strength Training"
	case 67:
		return "Surfing"
	case 68:
		return "Swimming (Open Water)"
	case 69:
		return "Swimming (Pool)"
	case 70:
		return "Table Tennis"
	case 71:
		return "Tennis"
	case 73:
		return "Volleyball"
	case 75:
		return "Weightlifting"
	case 76:
		return "Wheelchair"
	case 78:
		return "Yoga"
	default:
		return "Other"
	}
}

var jst = time.FixedZone("JST", 9*3600)

// EpochMillisToJST converts epoch millis to a time.Time in the JST timezone.
func EpochMillisToJST(ms int64) time.Time {
	return time.UnixMilli(ms).In(jst)
}

// LocalDate returns midnight of the local date for epoch millis with zone offset in seconds.
func LocalDate(ms int64, zoneOffsetSec int) time.Time {
	loc := time.FixedZone("", zoneOffsetSec)
	t := time.UnixMilli(ms).In(loc)
	return time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, loc)
}
