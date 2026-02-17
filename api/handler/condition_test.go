package handler

import (
	"context"
	"encoding/json"
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
	createErr  error
	getByIDLog *entity.ConditionLog
	getByIDErr error
	listResult *entity.ConditionListResult
	listErr    error
	updateErr  error
	deleteErr  error
	tags       []entity.TagCount
	tagsErr    error
	summary    *entity.ConditionSummary
	summaryErr error
}

func (s *stubConditionUseCase) Create(_ context.Context, _ *entity.ConditionLog) error {
	return s.createErr
}

func (s *stubConditionUseCase) GetByID(_ context.Context, _ int64) (*entity.ConditionLog, error) {
	return s.getByIDLog, s.getByIDErr
}

func (s *stubConditionUseCase) List(_ context.Context, _ entity.ConditionFilter) (*entity.ConditionListResult, error) {
	return s.listResult, s.listErr
}

func (s *stubConditionUseCase) Update(_ context.Context, _ int64, _ *entity.ConditionLog) error {
	return s.updateErr
}

func (s *stubConditionUseCase) Delete(_ context.Context, _ int64) error {
	return s.deleteErr
}

func (s *stubConditionUseCase) GetTags(_ context.Context) ([]entity.TagCount, error) {
	return s.tags, s.tagsErr
}

func (s *stubConditionUseCase) GetSummary(_ context.Context, _, _ time.Time) (*entity.ConditionSummary, error) {
	return s.summary, s.summaryErr
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
		createErr: entity.ErrNotFound, // using any error to test 422
	})
	if err := h.Create(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusUnprocessableEntity {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusUnprocessableEntity)
	}
}

func TestConditionHandler_GetByID_Success(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions/1", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("1")

	h := NewConditionHandler(&stubConditionUseCase{
		getByIDLog: &entity.ConditionLog{ID: 1, Overall: 4},
	})
	if err := h.GetByID(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestConditionHandler_GetByID_NotFound(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions/999", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("999")

	h := NewConditionHandler(&stubConditionUseCase{
		getByIDErr: entity.ErrNotFound,
	})
	if err := h.GetByID(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestConditionHandler_GetByID_InvalidID(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions/abc", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("abc")

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.GetByID(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestConditionHandler_List(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		listResult: &entity.ConditionListResult{
			Items: []entity.ConditionLog{
				{ID: 1, Overall: 4},
				{ID: 2, Overall: 3},
			},
			Total: 2,
		},
	})
	if err := h.List(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var result entity.ConditionListResult
	if err := json.Unmarshal(rec.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if len(result.Items) != 2 {
		t.Errorf("len(items) = %d, want 2", len(result.Items))
	}
	if result.Total != 2 {
		t.Errorf("total = %d, want 2", result.Total)
	}
}

func TestConditionHandler_List_WithPagination(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions?limit=10&offset=5&tag=headache&sort=overall&order=asc", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		listResult: &entity.ConditionListResult{
			Items: []entity.ConditionLog{},
			Total: 0,
		},
	})
	if err := h.List(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestConditionHandler_Update_Success(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPut, "/api/conditions/1",
		strings.NewReader(`{"overall":4,"note":"updated"}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("1")

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.Update(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestConditionHandler_Update_InvalidJSON(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPut, "/api/conditions/1",
		strings.NewReader(`{invalid}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("1")

	h := NewConditionHandler(&stubConditionUseCase{})
	if err := h.Update(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestConditionHandler_Update_NotFound(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPut, "/api/conditions/999",
		strings.NewReader(`{"overall":4}`))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetParamNames("id")
	c.SetParamValues("999")

	h := NewConditionHandler(&stubConditionUseCase{
		updateErr: entity.ErrNotFound,
	})
	if err := h.Update(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
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

func TestConditionHandler_GetTags(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions/tags", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		tags: []entity.TagCount{
			{Tag: "headache", Count: 5},
			{Tag: "tired", Count: 3},
		},
	})
	if err := h.GetTags(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var tags []entity.TagCount
	if err := json.Unmarshal(rec.Body.Bytes(), &tags); err != nil {
		t.Fatal(err)
	}
	if len(tags) != 2 {
		t.Errorf("len(tags) = %d, want 2", len(tags))
	}
}

func TestConditionHandler_GetSummary(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/conditions/summary?from=2025-01-01&to=2025-01-31", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewConditionHandler(&stubConditionUseCase{
		summary: &entity.ConditionSummary{
			TotalCount: 10,
			OverallAvg: 3.5,
			OverallMin: 1,
			OverallMax: 5,
		},
	})
	if err := h.GetSummary(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var summary entity.ConditionSummary
	if err := json.Unmarshal(rec.Body.Bytes(), &summary); err != nil {
		t.Fatal(err)
	}
	if summary.TotalCount != 10 {
		t.Errorf("TotalCount = %d, want 10", summary.TotalCount)
	}
}
