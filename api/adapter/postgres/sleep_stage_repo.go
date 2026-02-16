package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type SleepStageRepo struct {
	pool *pgxpool.Pool
}

func NewSleepStageRepo(pool *pgxpool.Pool) *SleepStageRepo {
	return &SleepStageRepo{pool: pool}
}

func (r *SleepStageRepo) BulkUpsert(ctx context.Context, stages []entity.SleepStage) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	for _, s := range stages {
		_, err := tx.Exec(ctx,
			`INSERT INTO sleep_stages (time, stage, seconds, log_id)
			 VALUES ($1, $2, $3, $4)
			 ON CONFLICT (time) DO UPDATE SET stage=$2, seconds=$3, log_id=$4`,
			s.Time, s.Stage, s.Seconds, s.LogID)
		if err != nil {
			return err
		}
	}
	return tx.Commit(ctx)
}

func (r *SleepStageRepo) ListByDate(ctx context.Context, date time.Time) ([]entity.SleepStage, error) {
	start := time.Date(date.Year(), date.Month(), date.Day(), 0, 0, 0, 0, date.Location())
	end := start.Add(24 * time.Hour)
	rows, err := r.pool.Query(ctx,
		`SELECT time, stage, seconds, log_id FROM sleep_stages
		 WHERE time >= $1 AND time < $2 ORDER BY time`, start, end)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var stages []entity.SleepStage
	for rows.Next() {
		var s entity.SleepStage
		if err := rows.Scan(&s.Time, &s.Stage, &s.Seconds, &s.LogID); err != nil {
			return nil, err
		}
		stages = append(stages, s)
	}
	return stages, rows.Err()
}
