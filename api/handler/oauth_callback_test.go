package handler

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
)

type stubOAuthProvider struct {
	authURL      string
	authState    string
	authErr      error
	exchangeErr  error
	isAuthorized bool
	statusErr    error
	disconnErr   error
}

func (s *stubOAuthProvider) AuthorizationURL(_ context.Context) (string, string, error) {
	return s.authURL, s.authState, s.authErr
}

func (s *stubOAuthProvider) ExchangeCode(_ context.Context, _, _ string) error {
	return s.exchangeErr
}

func (s *stubOAuthProvider) RefreshTokenIfNeeded(_ context.Context) error {
	return nil
}

func (s *stubOAuthProvider) IsAuthorized(_ context.Context) (bool, error) {
	return s.isAuthorized, s.statusErr
}

func (s *stubOAuthProvider) Disconnect(_ context.Context) error {
	return s.disconnErr
}

func TestOAuthHandler_Authorize(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{authURL: "https://fitbit.com/authorize", authState: "abc123"}, &stubSyncUseCase{})
	if err := h.Authorize(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["url"] != "https://fitbit.com/authorize" {
		t.Errorf("url = %q, want %q", body["url"], "https://fitbit.com/authorize")
	}
}

func TestOAuthHandler_Authorize_Error(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{authErr: errors.New("redis down")}, &stubSyncUseCase{})
	if err := h.Authorize(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusInternalServerError)
	}
}

func TestOAuthHandler_Callback(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?code=abc&state=xyz", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{}, &stubSyncUseCase{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusFound)
	}
	loc := rec.Header().Get("Location")
	if loc != "/settings?fitbit=connected" {
		t.Errorf("Location = %q, want %q", loc, "/settings?fitbit=connected")
	}
}

func TestOAuthHandler_Callback_MissingCode(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?state=xyz", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{}, &stubSyncUseCase{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusFound)
	}
	loc := rec.Header().Get("Location")
	if loc != "/settings?fitbit=error&reason=missing_code" {
		t.Errorf("Location = %q, want %q", loc, "/settings?fitbit=error&reason=missing_code")
	}
}

func TestOAuthHandler_Callback_MissingState(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?code=abc", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{}, &stubSyncUseCase{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusFound)
	}
	loc := rec.Header().Get("Location")
	if loc != "/settings?fitbit=error&reason=missing_state" {
		t.Errorf("Location = %q, want %q", loc, "/settings?fitbit=error&reason=missing_state")
	}
}

func TestOAuthHandler_Callback_ExchangeError(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?code=abc&state=xyz", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{exchangeErr: errors.New("invalid code")}, &stubSyncUseCase{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusFound)
	}
	loc := rec.Header().Get("Location")
	if loc != "/settings?fitbit=error" {
		t.Errorf("Location = %q, want %q", loc, "/settings?fitbit=error")
	}
}

func TestOAuthHandler_Callback_UserDenied(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?error=access_denied", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{}, &stubSyncUseCase{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusFound)
	}
	loc := rec.Header().Get("Location")
	if loc != "/settings?fitbit=error&reason=denied" {
		t.Errorf("Location = %q, want %q", loc, "/settings?fitbit=error&reason=denied")
	}
}

func TestOAuthHandler_Status(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/status", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{isAuthorized: true}, &stubSyncUseCase{})
	if err := h.Status(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "connected" {
		t.Errorf("status = %q, want %q", body["status"], "connected")
	}
}

func TestOAuthHandler_Disconnect(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodDelete, "/api/auth/fitbit", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{}, &stubSyncUseCase{})
	if err := h.Disconnect(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "disconnected" {
		t.Errorf("status = %q, want %q", body["status"], "disconnected")
	}
}
