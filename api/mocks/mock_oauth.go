package mocks

import "context"

type MockOAuthProvider struct {
	AuthorizationURLFunc     func(state string) string
	ExchangeCodeFunc         func(ctx context.Context, code string) error
	RefreshTokenIfNeededFunc func(ctx context.Context) error
	IsAuthorizedFunc         func(ctx context.Context) (bool, error)
}

func (m *MockOAuthProvider) AuthorizationURL(state string) string {
	return m.AuthorizationURLFunc(state)
}

func (m *MockOAuthProvider) ExchangeCode(ctx context.Context, code string) error {
	return m.ExchangeCodeFunc(ctx, code)
}

func (m *MockOAuthProvider) RefreshTokenIfNeeded(ctx context.Context) error {
	return m.RefreshTokenIfNeededFunc(ctx)
}

func (m *MockOAuthProvider) IsAuthorized(ctx context.Context) (bool, error) {
	return m.IsAuthorizedFunc(ctx)
}
