package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/port"
)

type AdviceHandler struct {
	mlClient   *mlclient.Client
	adviceRepo port.AdviceRepository
}

func NewAdviceHandler(mlClient *mlclient.Client, adviceRepo port.AdviceRepository) *AdviceHandler {
	return &AdviceHandler{mlClient: mlClient, adviceRepo: adviceRepo}
}

func (h *AdviceHandler) GetAdvice(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (cached)
	advice, err := h.adviceRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if advice != nil {
		return c.JSON(http.StatusOK, advice)
	}

	// Fall back to ML client (will generate via LLM)
	advice, err = h.mlClient.GetAdvice(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, advice)
}

func (h *AdviceHandler) RegenerateAdvice(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	advice, err := h.mlClient.RegenerateAdvice(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, advice)
}

func (h *AdviceHandler) Register(g *echo.Group) {
	g.GET("/advice", h.GetAdvice)
	g.POST("/advice/regenerate", h.RegenerateAdvice)
}
