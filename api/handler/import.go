package handler

import (
	"archive/zip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"github.com/redis/go-redis/v9"

	"vitametron/api/application"
)

type ImportHandler struct {
	uc        *application.ImportHealthConnectUseCase
	rdb       *redis.Client
	uploadDir string
}

func NewImportHandler(uc *application.ImportHealthConnectUseCase, rdb *redis.Client, uploadDir string) *ImportHandler {
	return &ImportHandler{uc: uc, rdb: rdb, uploadDir: uploadDir}
}

// hcImportProgress is the progress structure stored in Redis for async import tracking.
type hcImportProgress struct {
	Status string                   `json:"status"`
	Stage  string                   `json:"stage"`
	Error  string                   `json:"error,omitempty"`
	Result *application.ImportResult `json:"result,omitempty"`
}

func (h *ImportHandler) ImportHealthConnect(c echo.Context) error {
	mr, err := c.Request().MultipartReader()
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid multipart request"})
	}

	// Find the "file" part
	var filePart *multipart.Part
	for {
		part, err := mr.NextPart()
		if err == io.EOF {
			break
		}
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "failed to read multipart"})
		}
		if part.FormName() == "file" {
			filePart = part
			break
		}
		part.Close()
	}
	if filePart == nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "file is required"})
	}
	defer filePart.Close()

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

	if _, err := io.Copy(dst, filePart); err != nil {
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

// InitUpload creates an upload session for chunked HealthConnect uploading.
// POST /api/import/health-connect/init
func (h *ImportHandler) InitUpload(c echo.Context) error {
	var req struct {
		FileName  string `json:"file_name"`
		FileSize  int64  `json:"file_size"`
		ChunkSize int64  `json:"chunk_size"`
	}
	if err := c.Bind(&req); err != nil || req.FileName == "" || req.FileSize <= 0 || req.ChunkSize <= 0 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "file_name, file_size, and chunk_size are required"})
	}

	uploadID := uuid.New().String()
	totalChunks := int(math.Ceil(float64(req.FileSize) / float64(req.ChunkSize)))

	chunkDir := filepath.Join(h.uploadDir, uploadID)
	if err := os.MkdirAll(chunkDir, 0o755); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create upload dir"})
	}

	meta := chunkMeta{
		TotalChunks: totalChunks,
		Received:    []int{},
		FileName:    req.FileName,
		CreatedAt:   time.Now().UTC().Format(time.RFC3339),
	}
	metaJSON, _ := json.Marshal(meta)

	ctx := c.Request().Context()
	if err := h.rdb.Set(ctx, "hc_chunk:"+uploadID, string(metaJSON), 2*time.Hour).Err(); err != nil {
		os.RemoveAll(chunkDir)
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to init upload session"})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"upload_id":    uploadID,
		"chunk_size":   req.ChunkSize,
		"total_chunks": totalChunks,
	})
}

// UploadChunk receives a single chunk of binary data.
// PUT /api/import/health-connect/chunk/:uploadId/:chunkIndex
func (h *ImportHandler) UploadChunk(c echo.Context) error {
	uploadID := c.Param("uploadId")
	chunkIdxStr := c.Param("chunkIndex")
	chunkIdx, err := strconv.Atoi(chunkIdxStr)
	if err != nil || chunkIdx < 0 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid chunk index"})
	}

	ctx := c.Request().Context()

	metaJSON, err := h.rdb.Get(ctx, "hc_chunk:"+uploadID).Result()
	if err == redis.Nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "upload session not found"})
	}
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read upload session"})
	}

	var meta chunkMeta
	if err := json.Unmarshal([]byte(metaJSON), &meta); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "corrupted upload session"})
	}

	if chunkIdx >= meta.TotalChunks {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "chunk index out of range"})
	}

	partPath := filepath.Join(h.uploadDir, uploadID, fmt.Sprintf("%06d.part", chunkIdx))
	dst, err := os.Create(partPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create chunk file"})
	}

	if _, err := io.Copy(dst, c.Request().Body); err != nil {
		dst.Close()
		os.Remove(partPath)
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to write chunk"})
	}
	dst.Close()

	found := false
	for _, idx := range meta.Received {
		if idx == chunkIdx {
			found = true
			break
		}
	}
	if !found {
		meta.Received = append(meta.Received, chunkIdx)
	}

	updatedJSON, _ := json.Marshal(meta)
	h.rdb.Set(ctx, "hc_chunk:"+uploadID, string(updatedJSON), 2*time.Hour)

	return c.JSON(http.StatusOK, map[string]interface{}{
		"chunk_index": chunkIdx,
		"received":    len(meta.Received),
		"total":       meta.TotalChunks,
	})
}

// CompleteUpload concatenates all chunks into a ZIP, then launches async import.
// Returns HTTP 202 immediately with a job_id for progress tracking.
// POST /api/import/health-connect/complete/:uploadId
func (h *ImportHandler) CompleteUpload(c echo.Context) error {
	uploadID := c.Param("uploadId")

	ctx := c.Request().Context()

	metaJSON, err := h.rdb.Get(ctx, "hc_chunk:"+uploadID).Result()
	if err == redis.Nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "upload session not found"})
	}
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read upload session"})
	}

	var meta chunkMeta
	if err := json.Unmarshal([]byte(metaJSON), &meta); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "corrupted upload session"})
	}

	if len(meta.Received) != meta.TotalChunks {
		return c.JSON(http.StatusBadRequest, map[string]interface{}{
			"error":    "not all chunks received",
			"received": len(meta.Received),
			"total":    meta.TotalChunks,
		})
	}

	// Concatenate chunk files in order (fast file I/O — stays synchronous)
	chunkDir := filepath.Join(h.uploadDir, uploadID)
	entries, err := os.ReadDir(chunkDir)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read chunk dir"})
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	zipPath := filepath.Join(h.uploadDir, uploadID+".zip")
	dstFile, err := os.Create(zipPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create output file"})
	}

	for _, entry := range entries {
		if filepath.Ext(entry.Name()) != ".part" {
			continue
		}
		partPath := filepath.Join(chunkDir, entry.Name())
		src, err := os.Open(partPath)
		if err != nil {
			dstFile.Close()
			os.Remove(zipPath)
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read chunk"})
		}
		if _, err := io.Copy(dstFile, src); err != nil {
			src.Close()
			dstFile.Close()
			os.Remove(zipPath)
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to concatenate chunks"})
		}
		src.Close()
	}
	dstFile.Close()

	// Cleanup chunks and Redis chunk metadata
	os.RemoveAll(chunkDir)
	h.rdb.Del(ctx, "hc_chunk:"+uploadID)

	// Create job and store initial status in Redis
	jobID := uuid.New().String()
	progress := hcImportProgress{Status: "processing", Stage: "extracting"}
	progressJSON, _ := json.Marshal(progress)
	h.rdb.Set(ctx, "hc_import:"+jobID, string(progressJSON), 1*time.Hour)

	// Launch async import in goroutine
	go h.runImport(jobID, zipPath)

	return c.JSON(http.StatusAccepted, map[string]string{
		"job_id": jobID,
		"status": "processing",
	})
}

// runImport extracts the DB from ZIP and runs the import use case in the background.
func (h *ImportHandler) runImport(jobID, zipPath string) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "hc-import-*")
	if err != nil {
		log.Printf("[hc-import] job %s: failed to create temp dir: %v", jobID, err)
		h.setImportFailed(ctx, jobID, fmt.Sprintf("failed to create temp dir: %v", err))
		os.Remove(zipPath)
		return
	}
	defer os.RemoveAll(tmpDir)
	defer os.Remove(zipPath)

	// Stage: extracting
	dbPath, err := extractDBFromZip(zipPath, tmpDir)
	if err != nil {
		log.Printf("[hc-import] job %s: extraction failed: %v", jobID, err)
		h.setImportFailed(ctx, jobID, err.Error())
		return
	}

	// Stage: importing
	progress := hcImportProgress{Status: "processing", Stage: "importing"}
	progressJSON, _ := json.Marshal(progress)
	h.rdb.Set(ctx, "hc_import:"+jobID, string(progressJSON), 1*time.Hour)

	result, err := h.uc.Execute(ctx, dbPath)
	if err != nil {
		log.Printf("[hc-import] job %s: import failed: %v", jobID, err)
		h.setImportFailed(ctx, jobID, fmt.Sprintf("import failed: %v", err))
		return
	}

	// Stage: completed
	completed := hcImportProgress{Status: "completed", Stage: "done", Result: result}
	completedJSON, _ := json.Marshal(completed)
	h.rdb.Set(ctx, "hc_import:"+jobID, string(completedJSON), 1*time.Hour)
	log.Printf("[hc-import] job %s: completed", jobID)
}

func (h *ImportHandler) setImportFailed(ctx context.Context, jobID, errMsg string) {
	failed := hcImportProgress{Status: "failed", Error: errMsg}
	failedJSON, _ := json.Marshal(failed)
	h.rdb.Set(ctx, "hc_import:"+jobID, string(failedJSON), 1*time.Hour)
}

// Status returns the current import progress from Redis.
// GET /api/import/health-connect/status/:jobId
func (h *ImportHandler) Status(c echo.Context) error {
	jobID := c.Param("jobId")
	if jobID == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "job_id is required"})
	}

	data, err := h.rdb.Get(c.Request().Context(), "hc_import:"+jobID).Result()
	if err == redis.Nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "job not found"})
	}
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to get status"})
	}

	var result map[string]interface{}
	if err := json.Unmarshal([]byte(data), &result); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to parse status"})
	}

	return c.JSON(http.StatusOK, result)
}

// StatusSSE streams import progress via Server-Sent Events.
// GET /api/import/health-connect/stream/:jobId
func (h *ImportHandler) StatusSSE(c echo.Context) error {
	jobID := c.Param("jobId")
	if jobID == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "job_id is required"})
	}

	c.Response().Header().Set("Content-Type", "text/event-stream")
	c.Response().Header().Set("Cache-Control", "no-cache")
	c.Response().Header().Set("Connection", "keep-alive")
	c.Response().Header().Set("X-Accel-Buffering", "no")

	ctx := c.Request().Context()
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			data, err := h.rdb.Get(ctx, "hc_import:"+jobID).Result()
			if err != nil {
				continue
			}

			fmt.Fprintf(c.Response(), "data: %s\n\n", data)
			c.Response().Flush()

			var status struct {
				Status string `json:"status"`
			}
			if json.Unmarshal([]byte(data), &status) == nil {
				if status.Status == "completed" || status.Status == "failed" {
					return nil
				}
			}
		}
	}
}

func (h *ImportHandler) Register(g *echo.Group) {
	// Chunked upload (Cloudflare Tunnel 100MB limit workaround)
	g.POST("/import/health-connect/init", h.InitUpload)
	g.PUT("/import/health-connect/chunk/:uploadId/:chunkIndex", h.UploadChunk)
	g.POST("/import/health-connect/complete/:uploadId", h.CompleteUpload)
	// Status / SSE
	g.GET("/import/health-connect/status/:jobId", h.Status)
	g.GET("/import/health-connect/stream/:jobId", h.StatusSSE)
	// Legacy single-request upload
	g.POST("/import/health-connect", h.ImportHealthConnect)
}
