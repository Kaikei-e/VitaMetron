package handler

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
	"vitametron/api/domain/port"
)

type OAuthHandler struct {
	oauth  port.OAuthProvider
	syncUC application.SyncUseCase
}

func NewOAuthHandler(oauth port.OAuthProvider, syncUC application.SyncUseCase) *OAuthHandler {
	return &OAuthHandler{oauth: oauth, syncUC: syncUC}
}

func (h *OAuthHandler) Authorize(c echo.Context) error {
	url, _, err := h.oauth.AuthorizationURL(c.Request().Context())
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, map[string]string{"url": url})
}

func (h *OAuthHandler) Callback(c echo.Context) error {
	if errParam := c.QueryParam("error"); errParam != "" {
		return c.Redirect(http.StatusFound, "/settings?fitbit=error&reason=denied")
	}

	code := c.QueryParam("code")
	if code == "" {
		return c.Redirect(http.StatusFound, "/settings?fitbit=error&reason=missing_code")
	}

	state := c.QueryParam("state")
	if state == "" {
		return c.Redirect(http.StatusFound, "/settings?fitbit=error&reason=missing_state")
	}

	if err := h.oauth.ExchangeCode(c.Request().Context(), code, state); err != nil {
		return c.Redirect(http.StatusFound, "/settings?fitbit=error")
	}

	// Trigger initial sync in background after successful token exchange
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
		defer cancel()
		if err := h.syncUC.SyncDate(ctx, time.Now()); err != nil {
			log.Printf("warn: initial sync after OAuth failed: %v", err)
		}
	}()

	return c.Redirect(http.StatusFound, "/settings?fitbit=connected")
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

func (h *OAuthHandler) Disconnect(c echo.Context) error {
	if err := h.oauth.Disconnect(c.Request().Context()); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, map[string]string{"status": "disconnected"})
}

func (h *OAuthHandler) Register(g *echo.Group) {
	g.GET("/auth/fitbit", h.Authorize)
	g.GET("/auth/fitbit/callback", h.Callback)
	g.GET("/auth/fitbit/status", h.Status)
	g.DELETE("/auth/fitbit", h.Disconnect)
}
