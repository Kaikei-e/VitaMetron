package port

import "context"

type OAuthProvider interface {
	AuthorizationURL(state string) string
	ExchangeCode(ctx context.Context, code string) error
	RefreshTokenIfNeeded(ctx context.Context) error
	IsAuthorized(ctx context.Context) (bool, error)
}
