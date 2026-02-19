package handler

import (
	"net/http"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type AnomalyHandler struct {
	mlClient    *mlclient.Client
	anomalyRepo port.AnomalyRepository
}

func NewAnomalyHandler(mlClient *mlclient.Client, anomalyRepo port.AnomalyRepository) *AnomalyHandler {
	return &AnomalyHandler{mlClient: mlClient, anomalyRepo: anomalyRepo}
}

func (h *AnomalyHandler) GetAnomaly(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := parseDate(dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (pre-computed)
	detection, err := h.anomalyRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if detection != nil {
		return c.JSON(http.StatusOK, detection)
	}

	// Fall back to ML client for on-demand compute
	detection, err = h.mlClient.DetectAnomaly(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, detection)
}

func (h *AnomalyHandler) GetAnomalyRange(c echo.Context) error {
	fromStr := c.QueryParam("from")
	toStr := c.QueryParam("to")
	if fromStr == "" || toStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "from and to are required"})
	}

	from, err := parseDate(fromStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid from date"})
	}
	to, err := parseDate(toStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid to date"})
	}

	detections, err := h.anomalyRepo.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if detections == nil {
		detections = []entity.AnomalyDetection{}
	}

	return c.JSON(http.StatusOK, detections)
}

func (h *AnomalyHandler) GetAnomalyStatus(c echo.Context) error {
	status, err := h.mlClient.GetAnomalyStatus(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, status)
}

func (h *AnomalyHandler) TrainAnomalyModel(c echo.Context) error {
	result, err := h.mlClient.TrainAnomalyModel(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

func (h *AnomalyHandler) Register(g *echo.Group) {
	g.GET("/anomaly", h.GetAnomaly)
	g.GET("/anomaly/range", h.GetAnomalyRange)
	g.GET("/anomaly/status", h.GetAnomalyStatus)
	g.POST("/anomaly/train", h.TrainAnomalyModel)
}
