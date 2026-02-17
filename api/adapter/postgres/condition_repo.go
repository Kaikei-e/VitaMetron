package postgres

import (
	"context"
	"fmt"
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
		`INSERT INTO condition_logs (logged_at, overall, mental, physical, energy, overall_vas, note, tags)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
		log.LoggedAt, log.Overall, log.Mental, log.Physical, log.Energy, log.OverallVAS, log.Note, log.Tags)
	return err
}

func (r *ConditionRepo) GetByID(ctx context.Context, id int64) (*entity.ConditionLog, error) {
	var l entity.ConditionLog
	err := r.pool.QueryRow(ctx,
		`SELECT id, logged_at, overall, mental, physical, energy, overall_vas, note, tags, created_at
		 FROM condition_logs WHERE id = $1`, id).
		Scan(&l.ID, &l.LoggedAt, &l.Overall, &l.Mental, &l.Physical,
			&l.Energy, &l.OverallVAS, &l.Note, &l.Tags, &l.CreatedAt)
	if err != nil {
		if err.Error() == "no rows in result set" {
			return nil, nil
		}
		return nil, err
	}
	if l.Tags == nil {
		l.Tags = []string{}
	}
	return &l, nil
}

func (r *ConditionRepo) List(ctx context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error) {
	query := `SELECT id, logged_at, overall, mental, physical, energy, overall_vas, note, tags, created_at, COUNT(*) OVER() AS total FROM condition_logs`
	var args []interface{}
	argIdx := 1

	where := ""
	if !filter.From.IsZero() && !filter.To.IsZero() {
		where += fmt.Sprintf(" logged_at BETWEEN $%d AND $%d", argIdx, argIdx+1)
		args = append(args, filter.From, filter.To)
		argIdx += 2
	}
	if filter.Tag != "" {
		if where != "" {
			where += " AND"
		}
		where += fmt.Sprintf(" tags @> ARRAY[$%d]::text[]", argIdx)
		args = append(args, filter.Tag)
		argIdx++
	}
	if where != "" {
		query += " WHERE" + where
	}

	sortField := "logged_at"
	if filter.SortField == "overall" || filter.SortField == "created_at" {
		sortField = filter.SortField
	}
	sortDir := "DESC"
	if filter.SortDir == "asc" || filter.SortDir == "ASC" {
		sortDir = "ASC"
	}
	query += fmt.Sprintf(" ORDER BY %s %s", sortField, sortDir)

	query += fmt.Sprintf(" LIMIT $%d OFFSET $%d", argIdx, argIdx+1)
	args = append(args, filter.Limit, filter.Offset)

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []entity.ConditionLog
	var total int
	for rows.Next() {
		var l entity.ConditionLog
		if err := rows.Scan(&l.ID, &l.LoggedAt, &l.Overall, &l.Mental, &l.Physical,
			&l.Energy, &l.OverallVAS, &l.Note, &l.Tags, &l.CreatedAt, &total); err != nil {
			return nil, err
		}
		if l.Tags == nil {
			l.Tags = []string{}
		}
		logs = append(logs, l)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	return &entity.ConditionListResult{Items: logs, Total: total}, nil
}

func (r *ConditionRepo) Update(ctx context.Context, log *entity.ConditionLog) error {
	_, err := r.pool.Exec(ctx,
		`UPDATE condition_logs SET overall=$2, mental=$3, physical=$4, energy=$5, overall_vas=$6, note=$7, tags=$8, logged_at=$9
		 WHERE id=$1`,
		log.ID, log.Overall, log.Mental, log.Physical, log.Energy, log.OverallVAS, log.Note, log.Tags, log.LoggedAt)
	return err
}

func (r *ConditionRepo) Delete(ctx context.Context, id int64) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM condition_logs WHERE id = $1`, id)
	return err
}

func (r *ConditionRepo) GetTags(ctx context.Context) ([]entity.TagCount, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT unnest(tags) AS tag, COUNT(*) AS count FROM condition_logs GROUP BY tag ORDER BY count DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tags []entity.TagCount
	for rows.Next() {
		var tc entity.TagCount
		if err := rows.Scan(&tc.Tag, &tc.Count); err != nil {
			return nil, err
		}
		tags = append(tags, tc)
	}
	return tags, rows.Err()
}

func (r *ConditionRepo) GetSummary(ctx context.Context, from, to time.Time) (*entity.ConditionSummary, error) {
	var s entity.ConditionSummary
	err := r.pool.QueryRow(ctx,
		`SELECT COUNT(*),
		        COALESCE(AVG(overall), 0), COALESCE(MIN(overall), 0), COALESCE(MAX(overall), 0),
		        COALESCE(AVG(mental), 0), COALESCE(MIN(mental), 0), COALESCE(MAX(mental), 0),
		        COALESCE(AVG(physical), 0), COALESCE(MIN(physical), 0), COALESCE(MAX(physical), 0),
		        COALESCE(AVG(energy), 0), COALESCE(MIN(energy), 0), COALESCE(MAX(energy), 0)
		 FROM condition_logs WHERE logged_at BETWEEN $1 AND $2`, from, to).
		Scan(&s.TotalCount,
			&s.OverallAvg, &s.OverallMin, &s.OverallMax,
			&s.MentalAvg, &s.MentalMin, &s.MentalMax,
			&s.PhysicalAvg, &s.PhysicalMin, &s.PhysicalMax,
			&s.EnergyAvg, &s.EnergyMin, &s.EnergyMax)
	if err != nil {
		return nil, err
	}
	return &s, nil
}
