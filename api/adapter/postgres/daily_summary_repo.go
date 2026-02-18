package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type DailySummaryRepo struct {
	pool *pgxpool.Pool
}

func NewDailySummaryRepo(pool *pgxpool.Pool) *DailySummaryRepo {
	return &DailySummaryRepo{pool: pool}
}

func (r *DailySummaryRepo) Upsert(ctx context.Context, s *entity.DailySummary) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO daily_summaries (
			date, provider,
			resting_hr, avg_hr, max_hr,
			hrv_daily_rmssd, hrv_deep_rmssd,
			spo2_avg, spo2_min, spo2_max,
			br_full_sleep, br_deep_sleep, br_light_sleep, br_rem_sleep,
			skin_temp_variation,
			sleep_start, sleep_end, sleep_duration_min, sleep_minutes_asleep, sleep_minutes_awake,
			sleep_onset_latency, sleep_type, sleep_deep_min, sleep_light_min, sleep_rem_min, sleep_wake_min, sleep_is_main,
			steps, distance_km, floors, calories_total, calories_active, calories_bmr,
			active_zone_min, minutes_sedentary, minutes_lightly, minutes_fairly, minutes_very,
			vo2_max,
			hr_zone_out_min, hr_zone_fat_min, hr_zone_cardio_min, hr_zone_peak_min,
			synced_at
		) VALUES (
			$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
			$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,$35,$36,$37,$38,$39,$40,$41,$42,$43,$44
		) ON CONFLICT (date) DO UPDATE SET
			provider=$2,
			resting_hr=$3, avg_hr=$4, max_hr=$5,
			hrv_daily_rmssd=COALESCE(NULLIF($6::real,0),daily_summaries.hrv_daily_rmssd),
			hrv_deep_rmssd=COALESCE(NULLIF($7::real,0),daily_summaries.hrv_deep_rmssd),
			spo2_avg=COALESCE(NULLIF($8::real,0),daily_summaries.spo2_avg),
			spo2_min=COALESCE(NULLIF($9::real,0),daily_summaries.spo2_min),
			spo2_max=COALESCE(NULLIF($10::real,0),daily_summaries.spo2_max),
			br_full_sleep=COALESCE(NULLIF($11::real,0),daily_summaries.br_full_sleep),
			br_deep_sleep=COALESCE(NULLIF($12::real,0),daily_summaries.br_deep_sleep),
			br_light_sleep=COALESCE(NULLIF($13::real,0),daily_summaries.br_light_sleep),
			br_rem_sleep=COALESCE(NULLIF($14::real,0),daily_summaries.br_rem_sleep),
			skin_temp_variation=COALESCE(NULLIF($15::real,0),daily_summaries.skin_temp_variation),
			sleep_start=$16, sleep_end=$17, sleep_duration_min=$18, sleep_minutes_asleep=$19, sleep_minutes_awake=$20,
			sleep_onset_latency=$21, sleep_type=$22, sleep_deep_min=$23, sleep_light_min=$24, sleep_rem_min=$25, sleep_wake_min=$26, sleep_is_main=$27,
			steps=$28, distance_km=$29, floors=$30, calories_total=$31, calories_active=$32, calories_bmr=$33,
			active_zone_min=$34, minutes_sedentary=$35, minutes_lightly=$36, minutes_fairly=$37, minutes_very=$38,
			vo2_max=$39,
			hr_zone_out_min=$40, hr_zone_fat_min=$41, hr_zone_cardio_min=$42, hr_zone_peak_min=$43,
			synced_at=$44`,
		s.Date, s.Provider,
		s.RestingHR, s.AvgHR, s.MaxHR,
		s.HRVDailyRMSSD, s.HRVDeepRMSSD,
		s.SpO2Avg, s.SpO2Min, s.SpO2Max,
		s.BRFullSleep, s.BRDeepSleep, s.BRLightSleep, s.BRREMSleep,
		s.SkinTempVariation,
		s.SleepStart, s.SleepEnd, s.SleepDurationMin, s.SleepMinutesAsleep, s.SleepMinutesAwake,
		s.SleepOnsetLatency, s.SleepType, s.SleepDeepMin, s.SleepLightMin, s.SleepREMMin, s.SleepWakeMin, s.SleepIsMain,
		s.Steps, s.DistanceKM, s.Floors, s.CaloriesTotal, s.CaloriesActive, s.CaloriesBMR,
		s.ActiveZoneMin, s.MinutesSedentary, s.MinutesLightly, s.MinutesFairly, s.MinutesVery,
		s.VO2Max,
		s.HRZoneOutMin, s.HRZoneFatMin, s.HRZoneCardioMin, s.HRZonePeakMin,
		s.SyncedAt)
	return err
}

func (r *DailySummaryRepo) GetByDate(ctx context.Context, date time.Time) (*entity.DailySummary, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, provider,
			resting_hr, avg_hr, max_hr,
			hrv_daily_rmssd, hrv_deep_rmssd,
			spo2_avg, spo2_min, spo2_max,
			br_full_sleep, br_deep_sleep, br_light_sleep, br_rem_sleep,
			skin_temp_variation,
			sleep_start, sleep_end, sleep_duration_min, sleep_minutes_asleep, sleep_minutes_awake,
			sleep_onset_latency, sleep_type, sleep_deep_min, sleep_light_min, sleep_rem_min, sleep_wake_min, sleep_is_main,
			steps, distance_km, floors, calories_total, calories_active, calories_bmr,
			active_zone_min, minutes_sedentary, minutes_lightly, minutes_fairly, minutes_very,
			vo2_max,
			hr_zone_out_min, hr_zone_fat_min, hr_zone_cardio_min, hr_zone_peak_min,
			synced_at
		 FROM daily_summaries WHERE date = $1`, date)

	var s entity.DailySummary
	err := row.Scan(
		&s.Date, &s.Provider,
		&s.RestingHR, &s.AvgHR, &s.MaxHR,
		&s.HRVDailyRMSSD, &s.HRVDeepRMSSD,
		&s.SpO2Avg, &s.SpO2Min, &s.SpO2Max,
		&s.BRFullSleep, &s.BRDeepSleep, &s.BRLightSleep, &s.BRREMSleep,
		&s.SkinTempVariation,
		&s.SleepStart, &s.SleepEnd, &s.SleepDurationMin, &s.SleepMinutesAsleep, &s.SleepMinutesAwake,
		&s.SleepOnsetLatency, &s.SleepType, &s.SleepDeepMin, &s.SleepLightMin, &s.SleepREMMin, &s.SleepWakeMin, &s.SleepIsMain,
		&s.Steps, &s.DistanceKM, &s.Floors, &s.CaloriesTotal, &s.CaloriesActive, &s.CaloriesBMR,
		&s.ActiveZoneMin, &s.MinutesSedentary, &s.MinutesLightly, &s.MinutesFairly, &s.MinutesVery,
		&s.VO2Max,
		&s.HRZoneOutMin, &s.HRZoneFatMin, &s.HRZoneCardioMin, &s.HRZonePeakMin,
		&s.SyncedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *DailySummaryRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.DailySummary, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, provider,
			resting_hr, avg_hr, max_hr,
			hrv_daily_rmssd, hrv_deep_rmssd,
			spo2_avg, spo2_min, spo2_max,
			br_full_sleep, br_deep_sleep, br_light_sleep, br_rem_sleep,
			skin_temp_variation,
			sleep_start, sleep_end, sleep_duration_min, sleep_minutes_asleep, sleep_minutes_awake,
			sleep_onset_latency, sleep_type, sleep_deep_min, sleep_light_min, sleep_rem_min, sleep_wake_min, sleep_is_main,
			steps, distance_km, floors, calories_total, calories_active, calories_bmr,
			active_zone_min, minutes_sedentary, minutes_lightly, minutes_fairly, minutes_very,
			vo2_max,
			hr_zone_out_min, hr_zone_fat_min, hr_zone_cardio_min, hr_zone_peak_min,
			synced_at
		 FROM daily_summaries WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var summaries []entity.DailySummary
	for rows.Next() {
		var s entity.DailySummary
		if err := rows.Scan(
			&s.Date, &s.Provider,
			&s.RestingHR, &s.AvgHR, &s.MaxHR,
			&s.HRVDailyRMSSD, &s.HRVDeepRMSSD,
			&s.SpO2Avg, &s.SpO2Min, &s.SpO2Max,
			&s.BRFullSleep, &s.BRDeepSleep, &s.BRLightSleep, &s.BRREMSleep,
			&s.SkinTempVariation,
			&s.SleepStart, &s.SleepEnd, &s.SleepDurationMin, &s.SleepMinutesAsleep, &s.SleepMinutesAwake,
			&s.SleepOnsetLatency, &s.SleepType, &s.SleepDeepMin, &s.SleepLightMin, &s.SleepREMMin, &s.SleepWakeMin, &s.SleepIsMain,
			&s.Steps, &s.DistanceKM, &s.Floors, &s.CaloriesTotal, &s.CaloriesActive, &s.CaloriesBMR,
			&s.ActiveZoneMin, &s.MinutesSedentary, &s.MinutesLightly, &s.MinutesFairly, &s.MinutesVery,
			&s.VO2Max,
			&s.HRZoneOutMin, &s.HRZoneFatMin, &s.HRZoneCardioMin, &s.HRZonePeakMin,
			&s.SyncedAt); err != nil {
			return nil, err
		}
		summaries = append(summaries, s)
	}
	return summaries, rows.Err()
}
