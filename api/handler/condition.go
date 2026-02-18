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

type ConditionHandler struct {
	uc application.ConditionUseCase
}

func NewConditionHandler(uc application.ConditionUseCase) *ConditionHandler {
	return &ConditionHandler{uc: uc}
}

type createConditionRequest struct {
	// VAS 0-100 (primary)
	Wellbeing    int    `json:"wellbeing"`
	Mood         *int   `json:"mood,omitempty"`
	Energy       *int   `json:"energy,omitempty"`
	SleepQuality *int   `json:"sleep_quality,omitempty"`
	Stress       *int   `json:"stress,omitempty"`
	Note         string `json:"note,omitempty"`
	Tags         []string   `json:"tags,omitempty"`
	LoggedAt     *time.Time `json:"logged_at,omitempty"`
}

func (h *ConditionHandler) Create(c echo.Context) error {
	var req createConditionRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
	}

	loggedAt := time.Now()
	if req.LoggedAt != nil {
		loggedAt = *req.LoggedAt
	}

	log := &entity.ConditionLog{
		OverallVAS:      req.Wellbeing,
		MoodVAS:         req.Mood,
		EnergyVAS:       req.Energy,
		SleepQualityVAS: req.SleepQuality,
		StressVAS:       req.Stress,
		Note:            req.Note,
		Tags:            req.Tags,
		LoggedAt:        loggedAt,
	}

	if err := h.uc.Create(c.Request().Context(), log); err != nil {
		return c.JSON(http.StatusUnprocessableEntity, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusCreated, log)
}

func (h *ConditionHandler) GetByID(c echo.Context) error {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid id"})
	}

	log, err := h.uc.GetByID(c.Request().Context(), id)
	if err != nil {
		return conditionError(c, err)
	}

	return c.JSON(http.StatusOK, log)
}

func (h *ConditionHandler) List(c echo.Context) error {
	from, _ := time.Parse("2006-01-02", c.QueryParam("from"))
	to, toErr := time.Parse("2006-01-02", c.QueryParam("to"))

	if from.IsZero() {
		from = time.Now().AddDate(0, -1, 0)
	}
	if to.IsZero() {
		to = time.Now()
	} else if toErr == nil {
		// date-only string → include entire day (end of day)
		to = to.AddDate(0, 0, 1).Add(-time.Nanosecond)
	}

	limit, _ := strconv.Atoi(c.QueryParam("limit"))
	offset, _ := strconv.Atoi(c.QueryParam("offset"))

	filter := entity.ConditionFilter{
		From:      from,
		To:        to,
		Tag:       c.QueryParam("tag"),
		Limit:     limit,
		Offset:    offset,
		SortField: c.QueryParam("sort"),
		SortDir:   c.QueryParam("order"),
	}

	result, err := h.uc.List(c.Request().Context(), filter)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

type updateConditionRequest struct {
	Wellbeing    int    `json:"wellbeing"`
	Mood         *int   `json:"mood,omitempty"`
	Energy       *int   `json:"energy,omitempty"`
	SleepQuality *int   `json:"sleep_quality,omitempty"`
	Stress       *int   `json:"stress,omitempty"`
	Note         string `json:"note,omitempty"`
	Tags         []string   `json:"tags,omitempty"`
	LoggedAt     *time.Time `json:"logged_at,omitempty"`
}

func (h *ConditionHandler) Update(c echo.Context) error {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid id"})
	}

	var req updateConditionRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
	}

	log := &entity.ConditionLog{
		OverallVAS:      req.Wellbeing,
		MoodVAS:         req.Mood,
		EnergyVAS:       req.Energy,
		SleepQualityVAS: req.SleepQuality,
		StressVAS:       req.Stress,
		Note:            req.Note,
		Tags:            req.Tags,
	}
	if req.LoggedAt != nil {
		log.LoggedAt = *req.LoggedAt
	}

	if err := h.uc.Update(c.Request().Context(), id, log); err != nil {
		if errors.Is(err, entity.ErrNotFound) {
			return c.JSON(http.StatusNotFound, map[string]string{"error": "not found"})
		}
		return c.JSON(http.StatusUnprocessableEntity, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, log)
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

func (h *ConditionHandler) GetSummary(c echo.Context) error {
	from, _ := time.Parse("2006-01-02", c.QueryParam("from"))
	to, toErr := time.Parse("2006-01-02", c.QueryParam("to"))

	if from.IsZero() {
		from = time.Now().AddDate(0, -1, 0)
	}
	if to.IsZero() {
		to = time.Now()
	} else if toErr == nil {
		// date-only string → include entire day (end of day)
		to = to.AddDate(0, 0, 1).Add(-time.Nanosecond)
	}

	summary, err := h.uc.GetSummary(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, summary)
}

func (h *ConditionHandler) Register(g *echo.Group) {
	g.POST("/conditions", h.Create)
	g.GET("/conditions", h.List)
	g.GET("/conditions/tags", h.GetTags)
	g.GET("/conditions/summary", h.GetSummary)
	g.GET("/conditions/:id", h.GetByID)
	g.PUT("/conditions/:id", h.Update)
	g.DELETE("/conditions/:id", h.Delete)
}

func conditionError(c echo.Context, err error) error {
	if errors.Is(err, entity.ErrNotFound) {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "not found"})
	}
	return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
}
