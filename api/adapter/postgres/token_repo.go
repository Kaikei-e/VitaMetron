package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type TokenRepo struct {
	pool *pgxpool.Pool
}

func NewTokenRepo(pool *pgxpool.Pool) *TokenRepo {
	return &TokenRepo{pool: pool}
}

func (r *TokenRepo) Get(ctx context.Context, provider string) (accessToken, refreshToken []byte, expiresAt time.Time, err error) {
	err = r.pool.QueryRow(ctx,
		`SELECT access_token, refresh_token, expires_at
		 FROM oauth_tokens WHERE provider = $1`, provider).
		Scan(&accessToken, &refreshToken, &expiresAt)
	if err == pgx.ErrNoRows {
		return nil, nil, time.Time{}, fmt.Errorf("token not found for provider %q", provider)
	}
	return
}

func (r *TokenRepo) Save(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO oauth_tokens (provider, access_token, refresh_token, expires_at, updated_at)
		 VALUES ($1, $2, $3, $4, NOW())
		 ON CONFLICT (provider) DO UPDATE SET
		   access_token = $2,
		   refresh_token = $3,
		   expires_at = $4,
		   updated_at = NOW()`,
		provider, accessToken, refreshToken, expiresAt)
	return err
}

func (r *TokenRepo) Delete(ctx context.Context, provider string) error {
	_, err := r.pool.Exec(ctx,
		`DELETE FROM oauth_tokens WHERE provider = $1`, provider)
	return err
}
