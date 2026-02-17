package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type VRIHandler struct {
	mlClient *mlclient.Client
	vriRepo  port.VRIRepository
}

func NewVRIHandler(mlClient *mlclient.Client, vriRepo port.VRIRepository) *VRIHandler {
	return &VRIHandler{mlClient: mlClient, vriRepo: vriRepo}
}

func (h *VRIHandler) GetVRI(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (pre-computed)
	score, err := h.vriRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if score != nil {
		return c.JSON(http.StatusOK, score)
	}

	// Fall back to ML client for on-demand compute
	score, err = h.mlClient.GetVRI(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, score)
}

func (h *VRIHandler) GetVRIRange(c echo.Context) error {
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

	scores, err := h.vriRepo.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if scores == nil {
		scores = []entity.VRIScore{}
	}

	return c.JSON(http.StatusOK, scores)
}

func (h *VRIHandler) Register(g *echo.Group) {
	g.GET("/vri", h.GetVRI)
	g.GET("/vri/range", h.GetVRIRange)
}
