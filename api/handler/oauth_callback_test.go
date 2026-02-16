package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
)

type stubOAuthProvider struct {
	authURL      string
	exchangeErr  error
	isAuthorized bool
	authErr      error
}

func (s *stubOAuthProvider) AuthorizationURL(_ string) string {
	return s.authURL
}

func (s *stubOAuthProvider) ExchangeCode(_ context.Context, _ string) error {
	return s.exchangeErr
}

func (s *stubOAuthProvider) RefreshTokenIfNeeded(_ context.Context) error {
	return nil
}

func (s *stubOAuthProvider) IsAuthorized(_ context.Context) (bool, error) {
	return s.isAuthorized, s.authErr
}

func TestOAuthHandler_Authorize(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{authURL: "https://fitbit.com/authorize"})
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

func TestOAuthHandler_Callback(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback?code=abc", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestOAuthHandler_Callback_MissingCode(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/callback", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{})
	if err := h.Callback(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestOAuthHandler_Status(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/auth/fitbit/status", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewOAuthHandler(&stubOAuthProvider{isAuthorized: true})
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
