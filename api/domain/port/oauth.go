package port

import "context"

type OAuthProvider interface {
	AuthorizationURL(ctx context.Context) (url, state string, err error)
	ExchangeCode(ctx context.Context, code, state string) error
	RefreshTokenIfNeeded(ctx context.Context) error
	IsAuthorized(ctx context.Context) (bool, error)
	Disconnect(ctx context.Context) error
}
