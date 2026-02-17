package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type VRIRepo struct {
	pool *pgxpool.Pool
}

func NewVRIRepo(pool *pgxpool.Pool) *VRIRepo {
	return &VRIRepo{pool: pool}
}

func (r *VRIRepo) GetByDate(ctx context.Context, date time.Time) (*entity.VRIScore, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, vri_score, vri_confidence,
			z_ln_rmssd, z_resting_hr, z_sleep_duration, z_sri, z_spo2, z_deep_sleep, z_br,
			sri_value, sri_days_used, baseline_window_days, metrics_included, computed_at
		 FROM vri_scores WHERE date = $1`, date)

	var s entity.VRIScore
	err := row.Scan(
		&s.Date, &s.VRIScore, &s.VRIConfidence,
		&s.ZLnRMSSD, &s.ZRestingHR, &s.ZSleepDuration, &s.ZSRI, &s.ZSpO2, &s.ZDeepSleep, &s.ZBR,
		&s.SRIValue, &s.SRIDaysUsed, &s.BaselineWindowDays, &s.MetricsIncluded, &s.ComputedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *VRIRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.VRIScore, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, vri_score, vri_confidence,
			z_ln_rmssd, z_resting_hr, z_sleep_duration, z_sri, z_spo2, z_deep_sleep, z_br,
			sri_value, sri_days_used, baseline_window_days, metrics_included, computed_at
		 FROM vri_scores WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var scores []entity.VRIScore
	for rows.Next() {
		var s entity.VRIScore
		if err := rows.Scan(
			&s.Date, &s.VRIScore, &s.VRIConfidence,
			&s.ZLnRMSSD, &s.ZRestingHR, &s.ZSleepDuration, &s.ZSRI, &s.ZSpO2, &s.ZDeepSleep, &s.ZBR,
			&s.SRIValue, &s.SRIDaysUsed, &s.BaselineWindowDays, &s.MetricsIncluded, &s.ComputedAt); err != nil {
			return nil, err
		}
		scores = append(scores, s)
	}
	return scores, rows.Err()
}
