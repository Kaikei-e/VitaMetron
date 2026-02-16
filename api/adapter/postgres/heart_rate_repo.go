package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type HeartRateRepo struct {
	pool *pgxpool.Pool
}

func NewHeartRateRepo(pool *pgxpool.Pool) *HeartRateRepo {
	return &HeartRateRepo{pool: pool}
}

func (r *HeartRateRepo) BulkUpsert(ctx context.Context, samples []entity.HeartRateSample) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	for _, s := range samples {
		_, err := tx.Exec(ctx,
			`INSERT INTO heart_rate_intraday (time, bpm, confidence)
			 VALUES ($1, $2, $3)
			 ON CONFLICT (time) DO UPDATE SET bpm=$2, confidence=$3`,
			s.Time, s.BPM, s.Confidence)
		if err != nil {
			return err
		}
	}
	return tx.Commit(ctx)
}

func (r *HeartRateRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.HeartRateSample, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT time, bpm, confidence FROM heart_rate_intraday
		 WHERE time BETWEEN $1 AND $2 ORDER BY time`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var samples []entity.HeartRateSample
	for rows.Next() {
		var s entity.HeartRateSample
		if err := rows.Scan(&s.Time, &s.BPM, &s.Confidence); err != nil {
			return nil, err
		}
		samples = append(samples, s)
	}
	return samples, rows.Err()
}
