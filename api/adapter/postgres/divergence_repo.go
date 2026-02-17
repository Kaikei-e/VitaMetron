package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type DivergenceRepo struct {
	pool *pgxpool.Pool
}

func NewDivergenceRepo(pool *pgxpool.Pool) *DivergenceRepo {
	return &DivergenceRepo{pool: pool}
}

func (r *DivergenceRepo) GetByDate(ctx context.Context, date time.Time) (*entity.DivergenceDetection, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, condition_log_id, actual_score, predicted_score, residual,
			cusum_positive, cusum_negative, cusum_alert,
			divergence_type, confidence, top_drivers, explanation,
			model_version, computed_at
		 FROM divergence_detections WHERE date = $1`, date)

	var d entity.DivergenceDetection
	err := row.Scan(
		&d.Date, &d.ConditionLogID, &d.ActualScore, &d.PredictedScore, &d.Residual,
		&d.CuSumPositive, &d.CuSumNegative, &d.CuSumAlert,
		&d.DivergenceType, &d.Confidence, &d.TopDrivers, &d.Explanation,
		&d.ModelVersion, &d.ComputedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &d, nil
}

func (r *DivergenceRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, condition_log_id, actual_score, predicted_score, residual,
			cusum_positive, cusum_negative, cusum_alert,
			divergence_type, confidence, top_drivers, explanation,
			model_version, computed_at
		 FROM divergence_detections WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var detections []entity.DivergenceDetection
	for rows.Next() {
		var d entity.DivergenceDetection
		if err := rows.Scan(
			&d.Date, &d.ConditionLogID, &d.ActualScore, &d.PredictedScore, &d.Residual,
			&d.CuSumPositive, &d.CuSumNegative, &d.CuSumAlert,
			&d.DivergenceType, &d.Confidence, &d.TopDrivers, &d.Explanation,
			&d.ModelVersion, &d.ComputedAt); err != nil {
			return nil, err
		}
		detections = append(detections, d)
	}
	return detections, rows.Err()
}
