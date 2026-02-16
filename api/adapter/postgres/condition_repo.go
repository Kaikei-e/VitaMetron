package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type ConditionRepo struct {
	pool *pgxpool.Pool
}

func NewConditionRepo(pool *pgxpool.Pool) *ConditionRepo {
	return &ConditionRepo{pool: pool}
}

func (r *ConditionRepo) Create(ctx context.Context, log *entity.ConditionLog) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO condition_logs (logged_at, overall, mental, physical, energy, note, tags)
		 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		log.LoggedAt, log.Overall, log.Mental, log.Physical, log.Energy, log.Note, log.Tags)
	return err
}

func (r *ConditionRepo) List(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT id, logged_at, overall, mental, physical, energy, note, tags, created_at
		 FROM condition_logs WHERE logged_at BETWEEN $1 AND $2 ORDER BY logged_at DESC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []entity.ConditionLog
	for rows.Next() {
		var l entity.ConditionLog
		if err := rows.Scan(&l.ID, &l.LoggedAt, &l.Overall, &l.Mental, &l.Physical,
			&l.Energy, &l.Note, &l.Tags, &l.CreatedAt); err != nil {
			return nil, err
		}
		logs = append(logs, l)
	}
	return logs, rows.Err()
}

func (r *ConditionRepo) Delete(ctx context.Context, id int64) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM condition_logs WHERE id = $1`, id)
	return err
}

func (r *ConditionRepo) GetTags(ctx context.Context) ([]string, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT DISTINCT unnest(tags) AS tag FROM condition_logs ORDER BY tag`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tags []string
	for rows.Next() {
		var tag string
		if err := rows.Scan(&tag); err != nil {
			return nil, err
		}
		tags = append(tags, tag)
	}
	return tags, rows.Err()
}
