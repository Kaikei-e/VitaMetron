package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type AnomalyRepo struct {
	pool *pgxpool.Pool
}

func NewAnomalyRepo(pool *pgxpool.Pool) *AnomalyRepo {
	return &AnomalyRepo{pool: pool}
}

func (r *AnomalyRepo) GetByDate(ctx context.Context, date time.Time) (*entity.AnomalyDetection, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, anomaly_score, normalized_score, is_anomaly,
			quality_gate, quality_confidence, quality_adjusted_score,
			top_drivers, explanation, model_version, computed_at
		 FROM anomaly_detections WHERE date = $1`, date)

	var d entity.AnomalyDetection
	err := row.Scan(
		&d.Date, &d.AnomalyScore, &d.NormalizedScore, &d.IsAnomaly,
		&d.QualityGate, &d.QualityConfidence, &d.QualityAdjustedScore,
		&d.TopDrivers, &d.Explanation, &d.ModelVersion, &d.ComputedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &d, nil
}

func (r *AnomalyRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, anomaly_score, normalized_score, is_anomaly,
			quality_gate, quality_confidence, quality_adjusted_score,
			top_drivers, explanation, model_version, computed_at
		 FROM anomaly_detections WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var detections []entity.AnomalyDetection
	for rows.Next() {
		var d entity.AnomalyDetection
		if err := rows.Scan(
			&d.Date, &d.AnomalyScore, &d.NormalizedScore, &d.IsAnomaly,
			&d.QualityGate, &d.QualityConfidence, &d.QualityAdjustedScore,
			&d.TopDrivers, &d.Explanation, &d.ModelVersion, &d.ComputedAt); err != nil {
			return nil, err
		}
		detections = append(detections, d)
	}
	return detections, rows.Err()
}
