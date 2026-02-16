package server

import (
	"context"
	"net/http"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

// Pinger is a small interface for health check dependencies.
type Pinger interface {
	Ping(ctx context.Context) error
}

type Server struct {
	Echo *echo.Echo
}

func New() *Server {
	e := echo.New()
	e.HideBanner = true

	e.Use(middleware.Recover())
	e.Use(middleware.Logger())

	return &Server{Echo: e}
}

// Start starts the Echo server on the given address (e.g. ":8080").
func (s *Server) Start(address string) error {
	return s.Echo.Start(address)
}

// RegisterHealthRoutes sets up /health and /api/health endpoints.
func (s *Server) RegisterHealthRoutes(dbPinger, redisPinger Pinger) {
	s.Echo.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	s.Echo.GET("/api/health", func(c echo.Context) error {
		result := map[string]string{"status": "ok"}
		status := http.StatusOK

		if err := dbPinger.Ping(c.Request().Context()); err != nil {
			result["db"] = "error"
			result["status"] = "degraded"
			status = http.StatusServiceUnavailable
		} else {
			result["db"] = "ok"
		}

		if err := redisPinger.Ping(c.Request().Context()); err != nil {
			result["redis"] = "error"
			result["status"] = "degraded"
			status = http.StatusServiceUnavailable
		} else {
			result["redis"] = "ok"
		}

		return c.JSON(status, result)
	})
}
