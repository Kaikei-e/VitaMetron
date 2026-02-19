package handler

import (
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
	"vitametron/api/domain/entity"
)

type WHO5Handler struct {
	uc application.WHO5UseCaseInterface
}

func NewWHO5Handler(uc application.WHO5UseCaseInterface) *WHO5Handler {
	return &WHO5Handler{uc: uc}
}

type createWHO5Request struct {
	PeriodStart string `json:"period_start"`
	PeriodEnd   string `json:"period_end"`
	Items       [5]int `json:"items"`
	Note        string `json:"note,omitempty"`
}

func (h *WHO5Handler) Create(c echo.Context) error {
	var req createWHO5Request
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
	}

	periodStart, err := parseDate(req.PeriodStart)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid period_start format"})
	}
	periodEnd, err := parseDate(req.PeriodEnd)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid period_end format"})
	}

	assessment := &entity.WHO5Assessment{
		AssessedAt:  time.Now(),
		PeriodStart: periodStart,
		PeriodEnd:   periodEnd,
		Items:       req.Items,
		Note:        req.Note,
	}

	if err := h.uc.Create(c.Request().Context(), assessment); err != nil {
		return c.JSON(http.StatusUnprocessableEntity, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusCreated, assessment)
}

func (h *WHO5Handler) GetLatest(c echo.Context) error {
	a, err := h.uc.GetLatest(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if a == nil {
		return c.JSON(http.StatusOK, nil)
	}
	return c.JSON(http.StatusOK, a)
}

func (h *WHO5Handler) GetByID(c echo.Context) error {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid id"})
	}

	a, err := h.uc.GetByID(c.Request().Context(), id)
	if err != nil {
		if errors.Is(err, entity.ErrNotFound) {
			return c.JSON(http.StatusNotFound, map[string]string{"error": "not found"})
		}
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, a)
}

func (h *WHO5Handler) List(c echo.Context) error {
	limit, _ := strconv.Atoi(c.QueryParam("limit"))
	offset, _ := strconv.Atoi(c.QueryParam("offset"))

	items, total, err := h.uc.List(c.Request().Context(), limit, offset)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if items == nil {
		items = []entity.WHO5Assessment{}
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"items": items,
		"total": total,
	})
}

func (h *WHO5Handler) Register(g *echo.Group) {
	g.POST("/who5", h.Create)
	g.GET("/who5", h.List)
	g.GET("/who5/latest", h.GetLatest)
	g.GET("/who5/:id", h.GetByID)
}
