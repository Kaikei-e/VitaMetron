package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
)

type SyncHandler struct {
	uc application.SyncUseCase
}

func NewSyncHandler(uc application.SyncUseCase) *SyncHandler {
	return &SyncHandler{uc: uc}
}

func (h *SyncHandler) Sync(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = time.Parse("2006-01-02", dateStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format, use YYYY-MM-DD"})
		}
	}

	if err := h.uc.SyncDate(c.Request().Context(), date); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, map[string]string{
		"status": "ok",
		"date":   date.Format("2006-01-02"),
	})
}

func (h *SyncHandler) Register(g *echo.Group) {
	g.POST("/sync", h.Sync)
}
