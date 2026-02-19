package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
)

type InsightsHandler struct {
	uc application.InsightsUseCase
}

func NewInsightsHandler(uc application.InsightsUseCase) *InsightsHandler {
	return &InsightsHandler{uc: uc}
}

func (h *InsightsHandler) GetWeekly(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = parseDate(dateStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
		}
	}

	result, err := h.uc.GetWeeklyInsights(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

func (h *InsightsHandler) Register(g *echo.Group) {
	g.GET("/insights", h.GetWeekly)
}
