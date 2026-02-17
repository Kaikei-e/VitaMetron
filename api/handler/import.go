package handler

import (
	"archive/zip"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
)

type ImportHandler struct {
	uc *application.ImportHealthConnectUseCase
}

func NewImportHandler(uc *application.ImportHealthConnectUseCase) *ImportHandler {
	return &ImportHandler{uc: uc}
}

func (h *ImportHandler) ImportHealthConnect(c echo.Context) error {
	file, err := c.FormFile("file")
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "file is required"})
	}

	src, err := file.Open()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to open uploaded file"})
	}
	defer src.Close()

	// Save to temp file for zip processing
	tmpDir, err := os.MkdirTemp("", "hc-import-*")
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create temp dir"})
	}
	defer os.RemoveAll(tmpDir)

	zipPath := filepath.Join(tmpDir, "upload.zip")
	dst, err := os.Create(zipPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create temp file"})
	}

	if _, err := io.Copy(dst, src); err != nil {
		dst.Close()
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to save uploaded file"})
	}
	dst.Close()

	// Extract health_connect_export.db from zip
	dbPath, err := extractDBFromZip(zipPath, tmpDir)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}

	result, err := h.uc.Execute(c.Request().Context(), dbPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": fmt.Sprintf("import failed: %v", err)})
	}

	return c.JSON(http.StatusOK, result)
}

func extractDBFromZip(zipPath, destDir string) (string, error) {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return "", fmt.Errorf("failed to open zip: %w", err)
	}
	defer r.Close()

	for _, f := range r.File {
		if filepath.Base(f.Name) == "health_connect_export.db" {
			rc, err := f.Open()
			if err != nil {
				return "", fmt.Errorf("failed to open db in zip: %w", err)
			}
			defer rc.Close()

			dbPath := filepath.Join(destDir, "health_connect_export.db")
			out, err := os.Create(dbPath)
			if err != nil {
				return "", fmt.Errorf("failed to create db file: %w", err)
			}
			defer out.Close()

			if _, err := io.Copy(out, rc); err != nil {
				return "", fmt.Errorf("failed to extract db: %w", err)
			}
			return dbPath, nil
		}
	}
	return "", fmt.Errorf("health_connect_export.db not found in zip")
}

func (h *ImportHandler) Register(g *echo.Group) {
	g.POST("/import/health-connect", h.ImportHealthConnect)
}
