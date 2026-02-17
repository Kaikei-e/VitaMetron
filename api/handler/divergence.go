package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type DivergenceHandler struct {
	mlClient       *mlclient.Client
	divergenceRepo port.DivergenceRepository
}

func NewDivergenceHandler(mlClient *mlclient.Client, divergenceRepo port.DivergenceRepository) *DivergenceHandler {
	return &DivergenceHandler{mlClient: mlClient, divergenceRepo: divergenceRepo}
}

func (h *DivergenceHandler) GetDivergence(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (pre-computed)
	detection, err := h.divergenceRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if detection != nil {
		return c.JSON(http.StatusOK, detection)
	}

	// Fall back to ML client for on-demand compute
	detection, err = h.mlClient.DetectDivergence(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, detection)
}

func (h *DivergenceHandler) GetDivergenceRange(c echo.Context) error {
	fromStr := c.QueryParam("from")
	toStr := c.QueryParam("to")
	if fromStr == "" || toStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "from and to are required"})
	}

	from, err := time.Parse("2006-01-02", fromStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid from date"})
	}
	to, err := time.Parse("2006-01-02", toStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid to date"})
	}

	detections, err := h.divergenceRepo.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if detections == nil {
		detections = []entity.DivergenceDetection{}
	}

	return c.JSON(http.StatusOK, detections)
}

func (h *DivergenceHandler) GetDivergenceStatus(c echo.Context) error {
	status, err := h.mlClient.GetDivergenceStatus(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, status)
}

func (h *DivergenceHandler) TrainDivergenceModel(c echo.Context) error {
	result, err := h.mlClient.TrainDivergenceModel(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

func (h *DivergenceHandler) Register(g *echo.Group) {
	g.GET("/divergence", h.GetDivergence)
	g.GET("/divergence/range", h.GetDivergenceRange)
	g.GET("/divergence/status", h.GetDivergenceStatus)
	g.POST("/divergence/train", h.TrainDivergenceModel)
}
