package handler

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/port"
)

type OAuthHandler struct {
	oauth port.OAuthProvider
}

func NewOAuthHandler(oauth port.OAuthProvider) *OAuthHandler {
	return &OAuthHandler{oauth: oauth}
}

func (h *OAuthHandler) Authorize(c echo.Context) error {
	state := generateState()
	url := h.oauth.AuthorizationURL(state)
	return c.JSON(http.StatusOK, map[string]string{"url": url})
}

func (h *OAuthHandler) Callback(c echo.Context) error {
	code := c.QueryParam("code")
	if code == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "missing code"})
	}

	if err := h.oauth.ExchangeCode(c.Request().Context(), code); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, map[string]string{"status": "connected"})
}

func (h *OAuthHandler) Status(c echo.Context) error {
	authorized, err := h.oauth.IsAuthorized(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	status := "disconnected"
	if authorized {
		status = "connected"
	}

	return c.JSON(http.StatusOK, map[string]string{"status": status})
}

func (h *OAuthHandler) Register(g *echo.Group) {
	g.GET("/auth/fitbit", h.Authorize)
	g.GET("/auth/fitbit/callback", h.Callback)
	g.GET("/auth/fitbit/status", h.Status)
}

func generateState() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}
