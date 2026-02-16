package handler

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
)

// stubConditionUseCase implements application.ConditionUseCase for testing.
type stubConditionUseCase struct {
	createErr error
	listItems []entity.ConditionLog
	listErr   error
	deleteErr error
	tags      []string
	tagsErr   error
}

func (s *stubConditionUseCase) Create(_ context.Context, _ *entity.ConditionLog) error {
	return s.createErr
}

func (s *stubConditionUseCase) List(_ context.Context, _, _ time.Time) ([]entity.ConditionLog, error) {
	return s.listItems, s.listErr
}

func (s *stubConditionUseCase) Delete(_ context.Context, _ int64) error {
	return s.deleteErr
}

func (s *stubConditionUseCase) GetTags(_ context.Context) ([]string, error) {
	return s.tags, s.tagsErr
}

func TestConditionHandler_Create_Success(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/conditions",
		strings.NewReader(`{"overall":3,"note":"feeling ok"}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.Create(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusCreated {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusCreated)
	}
}

func TestConditionHandler_Create_InvalidJSON(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/conditions",
		strings.NewReader(`{invalid}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.Create(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestConditionHandler_Create_ValidationError(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/conditions",
		strings.NewReader(`{"overall":0}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		createErr: errors.New("overall must be between 1 and 5"),
	})
	if err := h.Create(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusUnprocessableEntity {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusUnprocessableEntity)
	}
}

func TestConditionHandler_List(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		listItems: []entity.ConditionLog{
			{ID: 1, Overall: 4},
			{ID: 2, Overall: 3},
		},
	})
	if err := h.List(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var items []entity.ConditionLog
	if err := json.Unmarshal(rec.Body.Bytes(), &items); err != nil {
		t.Fatal(err)
	}
	if len(items) != 2 {
		t.Errorf("len(items) = %d, want 2", len(items))
	}
}

func TestConditionHandler_Delete(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodDelete, "/api/conditions/1", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("1")

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.Delete(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusNoContent {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNoContent)
	}
}
