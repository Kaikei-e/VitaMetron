package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type AdviceRepo struct {
	pool *pgxpool.Pool
}

func NewAdviceRepo(pool *pgxpool.Pool) *AdviceRepo {
	return &AdviceRepo{pool: pool}
}

func (r *AdviceRepo) GetByDate(ctx context.Context, date time.Time) (*entity.DailyAdvice, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, advice_text, model_name, generation_ms, generated_at
		 FROM daily_advice WHERE date = $1`, date)

	var a entity.DailyAdvice
	err := row.Scan(&a.Date, &a.AdviceText, &a.ModelName, &a.GenerationMs, &a.GeneratedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	a.Cached = true
	return &a, nil
}
