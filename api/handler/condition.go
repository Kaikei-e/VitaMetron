package handler

import (
	"net/http"
	"strconv"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
	"vitametron/api/domain/entity"
)

type ConditionHandler struct {
	uc application.ConditionUseCase
}

func NewConditionHandler(uc application.ConditionUseCase) *ConditionHandler {
	return &ConditionHandler{uc: uc}
}

type createConditionRequest struct {
	Overall  int    `json:"overall"`
	Mental   *int   `json:"mental,omitempty"`
	Physical *int   `json:"physical,omitempty"`
	Energy   *int   `json:"energy,omitempty"`
	Note     string `json:"note,omitempty"`
	Tags     []string `json:"tags,omitempty"`
}

func (h *ConditionHandler) Create(c echo.Context) error {
	var req createConditionRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
	}

	log := &entity.ConditionLog{
		Overall:  req.Overall,
		Mental:   req.Mental,
		Physical: req.Physical,
		Energy:   req.Energy,
		Note:     req.Note,
		Tags:     req.Tags,
		LoggedAt: time.Now(),
	}

	if err := h.uc.Create(c.Request().Context(), log); err != nil {
		return c.JSON(http.StatusUnprocessableEntity, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusCreated, log)
}

func (h *ConditionHandler) List(c echo.Context) error {
	from, _ := time.Parse("2006-01-02", c.QueryParam("from"))
	to, _ := time.Parse("2006-01-02", c.QueryParam("to"))

	if from.IsZero() {
		from = time.Now().AddDate(0, -1, 0)
	}
	if to.IsZero() {
		to = time.Now()
	}

	logs, err := h.uc.List(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, logs)
}

func (h *ConditionHandler) Delete(c echo.Context) error {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid id"})
	}

	if err := h.uc.Delete(c.Request().Context(), id); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.NoContent(http.StatusNoContent)
}

func (h *ConditionHandler) GetTags(c echo.Context) error {
	tags, err := h.uc.GetTags(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, tags)
}

func (h *ConditionHandler) Register(g *echo.Group) {
	g.POST("/conditions", h.Create)
	g.GET("/conditions", h.List)
	g.DELETE("/conditions/:id", h.Delete)
	g.GET("/conditions/tags", h.GetTags)
}
