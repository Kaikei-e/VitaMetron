package handler

import (
	"net/http"
	"strconv"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
)

type RetrainHandler struct {
	mlClient *mlclient.Client
}

func NewRetrainHandler(mlClient *mlclient.Client) *RetrainHandler {
	return &RetrainHandler{mlClient: mlClient}
}

func (h *RetrainHandler) Check(c echo.Context) error {
	result, err := h.mlClient.CheckRetrain(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, result)
}

func (h *RetrainHandler) Trigger(c echo.Context) error {
	result, err := h.mlClient.TriggerRetrain(c.Request().Context(), c.Request().Body)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, result)
}

func (h *RetrainHandler) Status(c echo.Context) error {
	result, err := h.mlClient.GetRetrainStatus(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, result)
}

func (h *RetrainHandler) Logs(c echo.Context) error {
	limit := 10
	offset := 0

	if v := c.QueryParam("limit"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
			limit = n
		}
	}
	if v := c.QueryParam("offset"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n >= 0 {
			offset = n
		}
	}

	result, err := h.mlClient.GetRetrainLogs(c.Request().Context(), limit, offset)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, result)
}

func (h *RetrainHandler) Register(g *echo.Group) {
	g.GET("/retrain/check", h.Check)
	g.POST("/retrain/trigger", h.Trigger)
	g.GET("/retrain/status", h.Status)
	g.GET("/retrain/logs", h.Logs)
}
