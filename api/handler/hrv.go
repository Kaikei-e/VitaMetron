package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
)

type HRVHandler struct {
	mlClient *mlclient.Client
}

func NewHRVHandler(mlClient *mlclient.Client) *HRVHandler {
	return &HRVHandler{mlClient: mlClient}
}

func (h *HRVHandler) GetPrediction(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	prediction, err := h.mlClient.PredictHRV(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, prediction)
}

func (h *HRVHandler) GetStatus(c echo.Context) error {
	status, err := h.mlClient.GetHRVStatus(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, status)
}

func (h *HRVHandler) Train(c echo.Context) error {
	result, err := h.mlClient.TrainHRVModel(c.Request().Context(), c.Request().Body)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

func (h *HRVHandler) Register(g *echo.Group) {
	g.GET("/hrv/predict", h.GetPrediction)
	g.GET("/hrv/status", h.GetStatus)
	g.POST("/hrv/train", h.Train)
}
