package postgres

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type DataQualityRepo struct {
	pool *pgxpool.Pool
}

func NewDataQualityRepo(pool *pgxpool.Pool) *DataQualityRepo {
	return &DataQualityRepo{pool: pool}
}

func (r *DataQualityRepo) Upsert(ctx context.Context, q *entity.DataQuality) error {
	flagsJSON, err := json.Marshal(q.PlausibilityFlags)
	if err != nil {
		return fmt.Errorf("marshal plausibility_flags: %w", err)
	}

	_, err = r.pool.Exec(ctx,
		`INSERT INTO daily_data_quality (
			date, wear_time_hours, hr_sample_count,
			completeness_pct, metrics_present, metrics_missing,
			plausibility_flags, plausibility_pass,
			is_valid_day,
			baseline_days, baseline_maturity,
			confidence_score, confidence_level,
			computed_at
		) VALUES (
			$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14
		) ON CONFLICT (date) DO UPDATE SET
			wear_time_hours=$2, hr_sample_count=$3,
			completeness_pct=$4, metrics_present=$5, metrics_missing=$6,
			plausibility_flags=$7, plausibility_pass=$8,
			is_valid_day=$9,
			baseline_days=$10, baseline_maturity=$11,
			confidence_score=$12, confidence_level=$13,
			computed_at=$14`,
		q.Date, q.WearTimeHours, q.HRSampleCount,
		q.CompletenessPct, q.MetricsPresent, q.MetricsMissing,
		flagsJSON, q.PlausibilityPass,
		q.IsValidDay,
		q.BaselineDays, q.BaselineMaturity,
		q.ConfidenceScore, q.ConfidenceLevel,
		q.ComputedAt)
	return err
}

func (r *DataQualityRepo) GetByDate(ctx context.Context, date time.Time) (*entity.DataQuality, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, wear_time_hours, hr_sample_count,
			completeness_pct, metrics_present, metrics_missing,
			plausibility_flags, plausibility_pass,
			is_valid_day,
			baseline_days, baseline_maturity,
			confidence_score, confidence_level,
			computed_at
		FROM daily_data_quality WHERE date = $1`, date)

	return scanDataQuality(row)
}

func (r *DataQualityRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.DataQuality, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, wear_time_hours, hr_sample_count,
			completeness_pct, metrics_present, metrics_missing,
			plausibility_flags, plausibility_pass,
			is_valid_day,
			baseline_days, baseline_maturity,
			confidence_score, confidence_level,
			computed_at
		FROM daily_data_quality WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []entity.DataQuality
	for rows.Next() {
		q, err := scanDataQualityRows(rows)
		if err != nil {
			return nil, err
		}
		result = append(result, *q)
	}
	return result, rows.Err()
}

func (r *DataQualityRepo) CountValidDays(ctx context.Context, before time.Time, windowDays int) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM daily_data_quality
		 WHERE date BETWEEN $1::date - ($2 || ' days')::interval AND $1::date - INTERVAL '1 day'
		   AND is_valid_day = TRUE`,
		before, fmt.Sprintf("%d", windowDays)).Scan(&count)
	return count, err
}

func scanDataQuality(row pgx.Row) (*entity.DataQuality, error) {
	var q entity.DataQuality
	var flagsJSON []byte
	err := row.Scan(
		&q.Date, &q.WearTimeHours, &q.HRSampleCount,
		&q.CompletenessPct, &q.MetricsPresent, &q.MetricsMissing,
		&flagsJSON, &q.PlausibilityPass,
		&q.IsValidDay,
		&q.BaselineDays, &q.BaselineMaturity,
		&q.ConfidenceScore, &q.ConfidenceLevel,
		&q.ComputedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if flagsJSON != nil {
		if err := json.Unmarshal(flagsJSON, &q.PlausibilityFlags); err != nil {
			return nil, fmt.Errorf("unmarshal plausibility_flags: %w", err)
		}
	}
	return &q, nil
}

func scanDataQualityRows(rows pgx.Rows) (*entity.DataQuality, error) {
	var q entity.DataQuality
	var flagsJSON []byte
	err := rows.Scan(
		&q.Date, &q.WearTimeHours, &q.HRSampleCount,
		&q.CompletenessPct, &q.MetricsPresent, &q.MetricsMissing,
		&flagsJSON, &q.PlausibilityPass,
		&q.IsValidDay,
		&q.BaselineDays, &q.BaselineMaturity,
		&q.ConfidenceScore, &q.ConfidenceLevel,
		&q.ComputedAt)
	if err != nil {
		return nil, err
	}
	if flagsJSON != nil {
		if err := json.Unmarshal(flagsJSON, &q.PlausibilityFlags); err != nil {
			return nil, fmt.Errorf("unmarshal plausibility_flags: %w", err)
		}
	}
	return &q, nil
}
