package mocks

import "context"

type MockOAuthProvider struct {
	AuthorizationURLFunc     func(ctx context.Context) (string, string, error)
	ExchangeCodeFunc         func(ctx context.Context, code, state string) error
	RefreshTokenIfNeededFunc func(ctx context.Context) error
	IsAuthorizedFunc         func(ctx context.Context) (bool, error)
	DisconnectFunc           func(ctx context.Context) error
}

func (m *MockOAuthProvider) AuthorizationURL(ctx context.Context) (string, string, error) {
	return m.AuthorizationURLFunc(ctx)
}

func (m *MockOAuthProvider) ExchangeCode(ctx context.Context, code, state string) error {
	return m.ExchangeCodeFunc(ctx, code, state)
}

func (m *MockOAuthProvider) RefreshTokenIfNeeded(ctx context.Context) error {
	return m.RefreshTokenIfNeededFunc(ctx)
}

func (m *MockOAuthProvider) IsAuthorized(ctx context.Context) (bool, error) {
	return m.IsAuthorizedFunc(ctx)
}

func (m *MockOAuthProvider) Disconnect(ctx context.Context) error {
	return m.DisconnectFunc(ctx)
}
