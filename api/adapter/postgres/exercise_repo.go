package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type ExerciseRepo struct {
	pool *pgxpool.Pool
}

func NewExerciseRepo(pool *pgxpool.Pool) *ExerciseRepo {
	return &ExerciseRepo{pool: pool}
}

func (r *ExerciseRepo) Upsert(ctx context.Context, log *entity.ExerciseLog) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO exercise_logs (external_id, activity_name, started_at, duration_ms, calories, avg_hr, distance_km, zone_minutes)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		 ON CONFLICT (external_id) DO UPDATE SET
			activity_name=$2, started_at=$3, duration_ms=$4, calories=$5, avg_hr=$6, distance_km=$7, zone_minutes=$8, synced_at=NOW()`,
		log.ExternalID, log.ActivityName, log.StartedAt, log.DurationMS,
		log.Calories, log.AvgHR, log.DistanceKM, log.ZoneMinutes)
	return err
}

func (r *ExerciseRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.ExerciseLog, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT id, external_id, activity_name, started_at, duration_ms, calories, avg_hr, distance_km, synced_at
		 FROM exercise_logs WHERE started_at BETWEEN $1 AND $2 ORDER BY started_at DESC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []entity.ExerciseLog
	for rows.Next() {
		var l entity.ExerciseLog
		if err := rows.Scan(&l.ID, &l.ExternalID, &l.ActivityName, &l.StartedAt,
			&l.DurationMS, &l.Calories, &l.AvgHR, &l.DistanceKM, &l.SyncedAt); err != nil {
			return nil, err
		}
		logs = append(logs, l)
	}
	return logs, rows.Err()
}
