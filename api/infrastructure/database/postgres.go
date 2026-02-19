package database

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
	"vitametron/api/infrastructure/config"
)

func NewPool(ctx context.Context, cfg config.DBConfig) (*pgxpool.Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.DSN())
	if err != nil {
		return nil, fmt.Errorf("database: unable to parse config: %w", err)
	}
	poolCfg.ConnConfig.RuntimeParams["TimeZone"] = "Asia/Tokyo"

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("database: unable to create pool: %w", err)
	}
	return pool, nil
}
