package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
)

type WeeklyInsightsHandler struct {
	mlClient *mlclient.Client
}

func NewWeeklyInsightsHandler(mlClient *mlclient.Client) *WeeklyInsightsHandler {
	return &WeeklyInsightsHandler{mlClient: mlClient}
}

func (h *WeeklyInsightsHandler) GetWeekly(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = time.Parse("2006-01-02", dateStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
		}
	}

	insight, err := h.mlClient.GetWeeklyInsights(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, insight)
}

func (h *WeeklyInsightsHandler) Register(g *echo.Group) {
	g.GET("/insights/weekly", h.GetWeekly)
}
