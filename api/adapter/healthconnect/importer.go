package healthconnect

import (
	"database/sql"
	"encoding/hex"
	"fmt"
	"log"
	"sort"
	"time"

	_ "modernc.org/sqlite"

	"vitametron/api/domain/entity"
)

const (
	appFitbit   = 3
	appNothingX = 5
)

// ImportData holds all extracted and merged data from a Health Connect DB.
type ImportData struct {
	Summaries   []entity.DailySummary
	HRSamples   []entity.HeartRateSample
	SleepStages []entity.SleepStage
	Exercises   []entity.ExerciseLog
}

// Importer reads a Health Connect SQLite export and extracts biometric data.
type Importer struct{}

// Extract opens the SQLite DB at dbPath and returns merged ImportData.
func (imp *Importer) Extract(dbPath string) (*ImportData, error) {
	db, err := sql.Open("sqlite", dbPath+"?mode=ro")
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	defer db.Close()

	data := &ImportData{}

	summaries, err := imp.extractSummaries(db)
	if err != nil {
		return nil, fmt.Errorf("extract summaries: %w", err)
	}
	data.Summaries = summaries

	hrSamples, err := imp.extractHR(db)
	if err != nil {
		return nil, fmt.Errorf("extract HR: %w", err)
	}
	data.HRSamples = hrSamples

	sleepStages, err := imp.extractSleep(db)
	if err != nil {
		return nil, fmt.Errorf("extract sleep: %w", err)
	}
	data.SleepStages = sleepStages

	exercises, err := imp.extractExercises(db)
	if err != nil {
		return nil, fmt.Errorf("extract exercises: %w", err)
	}
	data.Exercises = exercises

	return data, nil
}

// priorityPick returns the Fitbit value if present, otherwise Nothing X.
func priorityPick[T any](m map[int]T) (T, bool) {
	if v, ok := m[appFitbit]; ok {
		return v, true
	}
	if v, ok := m[appNothingX]; ok {
		return v, true
	}
	var zero T
	return zero, false
}

// extractSummaries builds per-day DailySummary by querying each metric table
// with app_info_id filtering and applying Fitbit > Nothing X priority.
func (imp *Importer) extractSummaries(db *sql.DB) ([]entity.DailySummary, error) {
	dates := make(map[string]*entity.DailySummary)
	now := time.Now()

	// Steps (Fitbit priority)
	if err := imp.queryDailyInt(db, `
		SELECT date(start_time/1000,'unixepoch','+9 hours') AS day, app_info_id, SUM(count)
		FROM steps_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`, dates, func(s *entity.DailySummary, v int) { s.Steps = v },
	); err != nil {
		log.Printf("warn: steps query: %v", err)
	}

	// Distance (Fitbit priority, meters → km)
	if err := imp.queryDailyFloat(db, `
		SELECT date(start_time/1000,'unixepoch','+9 hours') AS day, app_info_id, SUM(distance)
		FROM distance_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`, dates, func(s *entity.DailySummary, v float64) { s.DistanceKM = float32(v / 1000) },
	); err != nil {
		log.Printf("warn: distance query: %v", err)
	}

	// Calories (Fitbit priority, small cal → kcal)
	if err := imp.queryDailyFloat(db, `
		SELECT date(start_time/1000,'unixepoch','+9 hours') AS day, app_info_id, SUM(energy)
		FROM total_calories_burned_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`, dates, func(s *entity.DailySummary, v float64) { s.CaloriesTotal = int(v / 1000) },
	); err != nil {
		log.Printf("warn: calories query: %v", err)
	}

	// AvgHR / MaxHR from heart_rate_record series (Fitbit priority)
	if err := imp.queryDailyHR(db, dates); err != nil {
		log.Printf("warn: avg/max HR query: %v", err)
	}

	// RestingHR (Nothing X only)
	if err := imp.queryDailyFloat(db, `
		SELECT date(time/1000,'unixepoch','+9 hours') AS day, app_info_id, AVG(beats_per_minute)
		FROM resting_heart_rate_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`, dates, func(s *entity.DailySummary, v float64) { s.RestingHR = int(v) },
	); err != nil {
		log.Printf("warn: resting HR query: %v", err)
	}

	// SpO2 (Nothing X only)
	if err := imp.queryDailySpO2(db, dates); err != nil {
		log.Printf("warn: SpO2 query: %v", err)
	}

	// HRV (Fitbit only)
	if err := imp.queryDailyFloat(db, `
		SELECT date(time/1000,'unixepoch','+9 hours') AS day, app_info_id, AVG(heart_rate_variability_millis)
		FROM heart_rate_variability_rmssd_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`, dates, func(s *entity.DailySummary, v float64) { s.HRVDailyRMSSD = float32(v) },
	); err != nil {
		log.Printf("warn: HRV query: %v", err)
	}

	// SkinTemp (Fitbit only) — join delta child table with parent record table
	if err := imp.queryDailyFloat(db, `
		SELECT date(d.epoch_millis/1000,'unixepoch','+9 hours') AS day, s.app_info_id, AVG(d.delta)
		FROM skin_temperature_delta_table d
		JOIN skin_temperature_record_table s ON d.parent_key = s.row_id
		WHERE s.app_info_id IN (3,5)
		GROUP BY day, s.app_info_id`, dates, func(s *entity.DailySummary, v float64) { s.SkinTempVariation = float32(v) },
	); err != nil {
		log.Printf("warn: skin temp query: %v", err)
	}

	// Sleep summary (Fitbit priority) — uses sleep session records
	if err := imp.queryDailySleep(db, dates); err != nil {
		log.Printf("warn: sleep summary query: %v", err)
	}

	// Build result slice
	result := make([]entity.DailySummary, 0, len(dates))
	for _, s := range dates {
		s.Provider = "health_connect"
		s.SyncedAt = now
		result = append(result, *s)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Date.Before(result[j].Date)
	})
	return result, nil
}

func (imp *Importer) ensureDate(dates map[string]*entity.DailySummary, day string) *entity.DailySummary {
	if s, ok := dates[day]; ok {
		return s
	}
	d, _ := time.Parse("2006-01-02", day)
	s := &entity.DailySummary{Date: d}
	dates[day] = s
	return s
}

// queryDailyInt queries for day, app_info_id, int_value and applies priority merge.
func (imp *Importer) queryDailyInt(db *sql.DB, query string, dates map[string]*entity.DailySummary, setter func(*entity.DailySummary, int)) error {
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	dayMap := make(map[string]map[int]int)
	for rows.Next() {
		var day string
		var appID, val int
		if err := rows.Scan(&day, &appID, &val); err != nil {
			return err
		}
		if dayMap[day] == nil {
			dayMap[day] = make(map[int]int)
		}
		dayMap[day][appID] = val
	}
	if err := rows.Err(); err != nil {
		return err
	}

	for day, apps := range dayMap {
		if v, ok := priorityPick(apps); ok {
			setter(imp.ensureDate(dates, day), v)
		}
	}
	return nil
}

// queryDailyFloat queries for day, app_info_id, float_value and applies priority merge.
func (imp *Importer) queryDailyFloat(db *sql.DB, query string, dates map[string]*entity.DailySummary, setter func(*entity.DailySummary, float64)) error {
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	dayMap := make(map[string]map[int]float64)
	for rows.Next() {
		var day string
		var appID int
		var val float64
		if err := rows.Scan(&day, &appID, &val); err != nil {
			return err
		}
		if dayMap[day] == nil {
			dayMap[day] = make(map[int]float64)
		}
		dayMap[day][appID] = val
	}
	if err := rows.Err(); err != nil {
		return err
	}

	for day, apps := range dayMap {
		if v, ok := priorityPick(apps); ok {
			setter(imp.ensureDate(dates, day), v)
		}
	}
	return nil
}

// queryDailyHR extracts AVG and MAX heart rate per day with priority merge.
// Schema: heart_rate_record_table (parent, has app_info_id) →
//
//	heart_rate_record_series_table (child, parent_key → row_id, has beats_per_minute + epoch_millis)
func (imp *Importer) queryDailyHR(db *sql.DB, dates map[string]*entity.DailySummary) error {
	rows, err := db.Query(`
		SELECT date(h.start_time/1000,'unixepoch','+9 hours') AS day,
		       h.app_info_id,
		       AVG(s.beats_per_minute) AS avg_bpm,
		       MAX(s.beats_per_minute) AS max_bpm
		FROM heart_rate_record_series_table s
		JOIN heart_rate_record_table h ON s.parent_key = h.row_id
		WHERE h.app_info_id IN (3,5)
		GROUP BY day, h.app_info_id`)
	if err != nil {
		return err
	}
	defer rows.Close()

	type hrData struct {
		avg float64
		max int
	}
	dayMap := make(map[string]map[int]hrData)
	for rows.Next() {
		var day string
		var appID, maxBPM int
		var avgBPM float64
		if err := rows.Scan(&day, &appID, &avgBPM, &maxBPM); err != nil {
			return err
		}
		if dayMap[day] == nil {
			dayMap[day] = make(map[int]hrData)
		}
		dayMap[day][appID] = hrData{avg: avgBPM, max: maxBPM}
	}
	if err := rows.Err(); err != nil {
		return err
	}

	for day, apps := range dayMap {
		if v, ok := priorityPick(apps); ok {
			s := imp.ensureDate(dates, day)
			s.AvgHR = float32(v.avg)
			s.MaxHR = v.max
		}
	}
	return nil
}

// queryDailySpO2 extracts AVG/MIN/MAX SpO2 per day with priority merge.
func (imp *Importer) queryDailySpO2(db *sql.DB, dates map[string]*entity.DailySummary) error {
	rows, err := db.Query(`
		SELECT date(time/1000,'unixepoch','+9 hours') AS day,
		       app_info_id,
		       AVG(percentage), MIN(percentage), MAX(percentage)
		FROM oxygen_saturation_record_table WHERE app_info_id IN (3,5)
		GROUP BY day, app_info_id`)
	if err != nil {
		return err
	}
	defer rows.Close()

	type spo2Data struct {
		avg, min, max float64
	}
	dayMap := make(map[string]map[int]spo2Data)
	for rows.Next() {
		var day string
		var appID int
		var avg, min, max float64
		if err := rows.Scan(&day, &appID, &avg, &min, &max); err != nil {
			return err
		}
		if dayMap[day] == nil {
			dayMap[day] = make(map[int]spo2Data)
		}
		dayMap[day][appID] = spo2Data{avg: avg, min: min, max: max}
	}
	if err := rows.Err(); err != nil {
		return err
	}

	for day, apps := range dayMap {
		if v, ok := priorityPick(apps); ok {
			s := imp.ensureDate(dates, day)
			s.SpO2Avg = float32(v.avg)
			s.SpO2Min = float32(v.min)
			s.SpO2Max = float32(v.max)
		}
	}
	return nil
}

// queryDailySleep extracts sleep session summary per day with priority merge.
// Picks the longest session per app per day, then Fitbit > Nothing X.
// Schema: sleep_session_record_table has row_id (PK), sleep_stages_table uses parent_key → row_id.
func (imp *Importer) queryDailySleep(db *sql.DB, dates map[string]*entity.DailySummary) error {
	rows, err := db.Query(`
		SELECT date(start_time/1000,'unixepoch','+9 hours') AS day,
		       app_info_id, row_id,
		       start_time, end_time,
		       (end_time - start_time) AS duration_ms
		FROM sleep_session_record_table
		WHERE app_info_id IN (3,5)
		ORDER BY day, app_info_id, duration_ms DESC`)
	if err != nil {
		return err
	}
	defer rows.Close()

	type sessionInfo struct {
		rowID      int64
		startMS    int64
		endMS      int64
		durationMS int64
	}
	// day → appID → best session
	dayMap := make(map[string]map[int]sessionInfo)
	for rows.Next() {
		var day string
		var appID int
		var rowID, startMS, endMS, durationMS int64
		if err := rows.Scan(&day, &appID, &rowID, &startMS, &endMS, &durationMS); err != nil {
			return err
		}
		if dayMap[day] == nil {
			dayMap[day] = make(map[int]sessionInfo)
		}
		// First row per (day, appID) is the longest due to ORDER BY
		if _, exists := dayMap[day][appID]; !exists {
			dayMap[day][appID] = sessionInfo{rowID: rowID, startMS: startMS, endMS: endMS, durationMS: durationMS}
		}
	}
	if err := rows.Err(); err != nil {
		return err
	}

	// Apply priority and compute sleep stage totals
	for day, apps := range dayMap {
		session, ok := priorityPick(apps)
		if !ok {
			continue
		}

		s := imp.ensureDate(dates, day)
		startTime := EpochMillisToJSTInUTC(session.startMS)
		endTime := EpochMillisToJSTInUTC(session.endMS)
		s.SleepStart = &startTime
		s.SleepEnd = &endTime
		s.SleepDurationMin = int(session.durationMS / 60000)
		s.SleepType = "stages"
		s.SleepIsMain = true

		// Query sleep stages for this session to compute stage totals
		stageRows, err := db.Query(`
			SELECT stage_type, SUM(stage_end_time - stage_start_time) AS total_ms
			FROM sleep_stages_table WHERE parent_key = ?
			GROUP BY stage_type`, session.rowID)
		if err != nil {
			log.Printf("warn: sleep stages for session %d: %v", session.rowID, err)
			continue
		}

		var totalAsleep, totalAwake int64
		for stageRows.Next() {
			var stageType int
			var totalMS int64
			if err := stageRows.Scan(&stageType, &totalMS); err != nil {
				stageRows.Close()
				break
			}
			mins := int(totalMS / 60000)
			switch MapSleepStage(stageType) {
			case "deep":
				s.SleepDeepMin = mins
				totalAsleep += totalMS
			case "light":
				s.SleepLightMin += mins
				totalAsleep += totalMS
			case "rem":
				s.SleepREMMin = mins
				totalAsleep += totalMS
			case "wake":
				s.SleepWakeMin = mins
				totalAwake += totalMS
			}
		}
		stageRows.Close()

		s.SleepMinutesAsleep = int(totalAsleep / 60000)
		s.SleepMinutesAwake = int(totalAwake / 60000)
	}
	return nil
}

// extractHR reads heart rate intraday data, deduplicates by minute, and
// applies Fitbit > Nothing X priority for same-timestamp records.
// Schema: heart_rate_record_table (parent, row_id, app_info_id) →
//
//	heart_rate_record_series_table (child, parent_key, beats_per_minute, epoch_millis)
func (imp *Importer) extractHR(db *sql.DB) ([]entity.HeartRateSample, error) {
	rows, err := db.Query(`
		SELECT h.app_info_id, s.epoch_millis, s.beats_per_minute
		FROM heart_rate_record_series_table s
		JOIN heart_rate_record_table h ON s.parent_key = h.row_id
		WHERE h.app_info_id IN (3,5)
		ORDER BY s.epoch_millis`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Resample to 1-minute intervals: keep first sample per minute,
	// prefer Fitbit if both apps have data for the same minute.
	type minuteKey struct {
		year  int
		month time.Month
		day   int
		hour  int
		min   int
	}
	type sample struct {
		appID int
		bpm   int
		t     time.Time
	}
	minuteMap := make(map[minuteKey]sample)

	for rows.Next() {
		var appID, bpm int
		var epochMS int64
		if err := rows.Scan(&appID, &epochMS, &bpm); err != nil {
			return nil, err
		}
		t := EpochMillisToJSTInUTC(epochMS)
		key := minuteKey{t.Year(), t.Month(), t.Day(), t.Hour(), t.Minute()}

		existing, exists := minuteMap[key]
		if !exists {
			minuteMap[key] = sample{appID: appID, bpm: bpm, t: time.Date(t.Year(), t.Month(), t.Day(), t.Hour(), t.Minute(), 0, 0, time.UTC)}
		} else if appID == appFitbit && existing.appID != appFitbit {
			minuteMap[key] = sample{appID: appID, bpm: bpm, t: existing.t}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	result := make([]entity.HeartRateSample, 0, len(minuteMap))
	for _, s := range minuteMap {
		result = append(result, entity.HeartRateSample{
			Time: s.t,
			BPM:  s.bpm,
		})
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Time.Before(result[j].Time)
	})
	return result, nil
}

// extractSleep reads granular sleep stage transitions for each day's
// selected session (matching the sessions chosen in extractSummaries).
// Schema: sleep_stages_table uses parent_key → sleep_session_record_table.row_id,
// columns: stage_start_time, stage_end_time, stage_type.
func (imp *Importer) extractSleep(db *sql.DB) ([]entity.SleepStage, error) {
	// Identify the best session row_id per day (Fitbit priority, longest session)
	rows, err := db.Query(`
		SELECT date(start_time/1000,'unixepoch','+9 hours') AS day,
		       app_info_id, row_id,
		       (end_time - start_time) AS duration_ms
		FROM sleep_session_record_table
		WHERE app_info_id IN (3,5)
		ORDER BY day, app_info_id, duration_ms DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	type bestInfo struct {
		rowID int64
		appID int
	}
	bestSession := make(map[string]bestInfo)
	for rows.Next() {
		var day string
		var appID int
		var rowID, durationMS int64
		if err := rows.Scan(&day, &appID, &rowID, &durationMS); err != nil {
			return nil, err
		}
		existing, exists := bestSession[day]
		if !exists {
			bestSession[day] = bestInfo{rowID: rowID, appID: appID}
		} else if appID == appFitbit && existing.appID != appFitbit {
			bestSession[day] = bestInfo{rowID: rowID, appID: appID}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	var stages []entity.SleepStage
	for _, session := range bestSession {
		stageRows, err := db.Query(`
			SELECT stage_start_time, stage_end_time, stage_type
			FROM sleep_stages_table WHERE parent_key = ?
			ORDER BY stage_start_time`, session.rowID)
		if err != nil {
			log.Printf("warn: sleep stages query for row_id %d: %v", session.rowID, err)
			continue
		}

		for stageRows.Next() {
			var startMS, endMS int64
			var stageType int
			if err := stageRows.Scan(&startMS, &endMS, &stageType); err != nil {
				stageRows.Close()
				break
			}
			stageName := MapSleepStage(stageType)
			if stageName == "" {
				continue
			}
			stages = append(stages, entity.SleepStage{
				Time:    EpochMillisToJSTInUTC(startMS),
				Stage:   stageName,
				Seconds: int((endMS - startMS) / 1000),
			})
		}
		stageRows.Close()
	}

	sort.Slice(stages, func(i, j int) bool {
		return stages[i].Time.Before(stages[j].Time)
	})
	return stages, nil
}

// extractExercises reads exercise sessions from both Fitbit and Nothing X.
// Uses hex-encoded uuid as ExternalID for deduplication via ON CONFLICT.
func (imp *Importer) extractExercises(db *sql.DB) ([]entity.ExerciseLog, error) {
	rows, err := db.Query(`
		SELECT uuid, exercise_type, start_time, end_time, start_zone_offset
		FROM exercise_session_record_table
		WHERE app_info_id IN (3,5)
		ORDER BY start_time`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	now := time.Now()
	var exercises []entity.ExerciseLog

	for rows.Next() {
		var uuidBytes []byte
		var exerciseType, zoneOffset int
		var startMS, endMS int64
		if err := rows.Scan(&uuidBytes, &exerciseType, &startMS, &endMS, &zoneOffset); err != nil {
			return nil, err
		}

		externalID := hex.EncodeToString(uuidBytes)
		startTime := EpochMillisToJSTInUTC(startMS)
		durationMS := endMS - startMS

		exercises = append(exercises, entity.ExerciseLog{
			ExternalID:   fmt.Sprintf("hc-%s", externalID),
			ActivityName: MapExerciseType(exerciseType),
			StartedAt:    startTime,
			DurationMS:   durationMS,
			SyncedAt:     now,
		})
	}
	return exercises, rows.Err()
}
