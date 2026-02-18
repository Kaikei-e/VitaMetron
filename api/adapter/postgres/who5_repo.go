package postgres

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type WHO5Repo struct {
	pool *pgxpool.Pool
}

func NewWHO5Repo(pool *pgxpool.Pool) *WHO5Repo {
	return &WHO5Repo{pool: pool}
}

func (r *WHO5Repo) Create(ctx context.Context, a *entity.WHO5Assessment) error {
	return r.pool.QueryRow(ctx,
		`INSERT INTO who5_assessments (assessed_at, period_start, period_end, item1, item2, item3, item4, item5, note)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		 RETURNING id, raw_score, percentage, created_at`,
		a.AssessedAt, a.PeriodStart, a.PeriodEnd,
		a.Items[0], a.Items[1], a.Items[2], a.Items[3], a.Items[4],
		a.Note).
		Scan(&a.ID, &a.RawScore, &a.Percentage, &a.CreatedAt)
}

func (r *WHO5Repo) GetByID(ctx context.Context, id int64) (*entity.WHO5Assessment, error) {
	var a entity.WHO5Assessment
	err := r.pool.QueryRow(ctx,
		`SELECT id, assessed_at, period_start, period_end, item1, item2, item3, item4, item5, raw_score, percentage, note, created_at
		 FROM who5_assessments WHERE id = $1`, id).
		Scan(&a.ID, &a.AssessedAt, &a.PeriodStart, &a.PeriodEnd,
			&a.Items[0], &a.Items[1], &a.Items[2], &a.Items[3], &a.Items[4],
			&a.RawScore, &a.Percentage, &a.Note, &a.CreatedAt)
	if err != nil {
		if err.Error() == "no rows in result set" {
			return nil, nil
		}
		return nil, err
	}
	return &a, nil
}

func (r *WHO5Repo) GetLatest(ctx context.Context) (*entity.WHO5Assessment, error) {
	var a entity.WHO5Assessment
	err := r.pool.QueryRow(ctx,
		`SELECT id, assessed_at, period_start, period_end, item1, item2, item3, item4, item5, raw_score, percentage, note, created_at
		 FROM who5_assessments ORDER BY assessed_at DESC LIMIT 1`).
		Scan(&a.ID, &a.AssessedAt, &a.PeriodStart, &a.PeriodEnd,
			&a.Items[0], &a.Items[1], &a.Items[2], &a.Items[3], &a.Items[4],
			&a.RawScore, &a.Percentage, &a.Note, &a.CreatedAt)
	if err != nil {
		if err.Error() == "no rows in result set" {
			return nil, nil
		}
		return nil, err
	}
	return &a, nil
}

func (r *WHO5Repo) List(ctx context.Context, limit, offset int) ([]entity.WHO5Assessment, int, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT id, assessed_at, period_start, period_end, item1, item2, item3, item4, item5, raw_score, percentage, note, created_at, COUNT(*) OVER() AS total
		 FROM who5_assessments ORDER BY assessed_at DESC LIMIT $1 OFFSET $2`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var assessments []entity.WHO5Assessment
	var total int
	for rows.Next() {
		var a entity.WHO5Assessment
		if err := rows.Scan(&a.ID, &a.AssessedAt, &a.PeriodStart, &a.PeriodEnd,
			&a.Items[0], &a.Items[1], &a.Items[2], &a.Items[3], &a.Items[4],
			&a.RawScore, &a.Percentage, &a.Note, &a.CreatedAt, &total); err != nil {
			return nil, 0, err
		}
		assessments = append(assessments, a)
	}
	return assessments, total, rows.Err()
}
