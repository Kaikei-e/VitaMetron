package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
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
)

type HealthKitHandler struct {
	rdb             *redis.Client
	preprocessorURL string
	uploadDir       string
}

func NewHealthKitHandler(rdb *redis.Client, preprocessorURL, uploadDir string) *HealthKitHandler {
	return &HealthKitHandler{
		rdb:             rdb,
		preprocessorURL: preprocessorURL,
		uploadDir:       uploadDir,
	}
}

func (h *HealthKitHandler) Upload(c echo.Context) error {
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

	// Ensure upload directory exists
	if err := os.MkdirAll(h.uploadDir, 0o755); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create upload dir"})
	}

	// Stream to shared volume
	jobID := uuid.New().String()
	zipPath := filepath.Join(h.uploadDir, jobID+".zip")
	dst, err := os.Create(zipPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create temp file"})
	}

	if _, err := io.Copy(dst, filePart); err != nil {
		dst.Close()
		os.Remove(zipPath)
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to save uploaded file"})
	}
	dst.Close()

	// Call preprocessor POST /process
	reqBody, _ := json.Marshal(map[string]string{
		"zip_path": zipPath,
		"job_id":   jobID,
	})

	resp, err := http.Post(
		h.preprocessorURL+"/process",
		"application/json",
		bytes.NewReader(reqBody),
	)
	if err != nil {
		os.Remove(zipPath)
		return c.JSON(http.StatusServiceUnavailable, map[string]string{
			"error": fmt.Sprintf("preprocessor unavailable: %v", err),
		})
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		os.Remove(zipPath)
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": fmt.Sprintf("preprocessor error: %s", string(body)),
		})
	}

	return c.JSON(http.StatusAccepted, map[string]string{
		"job_id": jobID,
		"status": "queued",
	})
}

func (h *HealthKitHandler) Status(c echo.Context) error {
	jobID := c.Param("jobId")
	if jobID == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "job_id is required"})
	}

	data, err := h.rdb.Get(c.Request().Context(), "hk_import:"+jobID).Result()
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

func (h *HealthKitHandler) StatusSSE(c echo.Context) error {
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
			data, err := h.rdb.Get(ctx, "hk_import:"+jobID).Result()
			if err != nil {
				continue
			}

			fmt.Fprintf(c.Response(), "data: %s\n\n", data)
			c.Response().Flush()

			// Check if completed or failed
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

// chunkMeta is stored in Redis to track multi-chunk upload state.
type chunkMeta struct {
	TotalChunks int      `json:"total_chunks"`
	Received    []int    `json:"received"`
	FileName    string   `json:"file_name"`
	CreatedAt   string   `json:"created_at"`
}

// InitUpload creates an upload session for chunked uploading.
// POST /api/import/healthkit/init
func (h *HealthKitHandler) InitUpload(c echo.Context) error {
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
	if err := h.rdb.Set(ctx, "hk_chunk:"+uploadID, string(metaJSON), 2*time.Hour).Err(); err != nil {
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
// PUT /api/import/healthkit/chunk/:uploadId/:chunkIndex
func (h *HealthKitHandler) UploadChunk(c echo.Context) error {
	uploadID := c.Param("uploadId")
	chunkIdxStr := c.Param("chunkIndex")
	chunkIdx, err := strconv.Atoi(chunkIdxStr)
	if err != nil || chunkIdx < 0 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid chunk index"})
	}

	ctx := c.Request().Context()

	// Load metadata from Redis
	metaJSON, err := h.rdb.Get(ctx, "hk_chunk:"+uploadID).Result()
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

	// Write chunk to disk
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

	// Update received set (idempotent — deduplicate)
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
	h.rdb.Set(ctx, "hk_chunk:"+uploadID, string(updatedJSON), 2*time.Hour)

	return c.JSON(http.StatusOK, map[string]interface{}{
		"chunk_index": chunkIdx,
		"received":    len(meta.Received),
		"total":       meta.TotalChunks,
	})
}

// CompleteUpload concatenates all chunks into a single ZIP and triggers processing.
// POST /api/import/healthkit/complete/:uploadId
func (h *HealthKitHandler) CompleteUpload(c echo.Context) error {
	uploadID := c.Param("uploadId")

	ctx := c.Request().Context()

	metaJSON, err := h.rdb.Get(ctx, "hk_chunk:"+uploadID).Result()
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

	// Concatenate chunk files in order
	chunkDir := filepath.Join(h.uploadDir, uploadID)
	entries, err := os.ReadDir(chunkDir)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read chunk dir"})
	}

	// Sort by filename (000000.part, 000001.part, ...)
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	jobID := uuid.New().String()
	zipPath := filepath.Join(h.uploadDir, jobID+".zip")
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

	// Cleanup: remove chunk directory and Redis metadata
	os.RemoveAll(chunkDir)
	h.rdb.Del(ctx, "hk_chunk:"+uploadID)

	// Call preprocessor POST /process
	reqBody, _ := json.Marshal(map[string]string{
		"zip_path": zipPath,
		"job_id":   jobID,
	})

	resp, err := http.Post(
		h.preprocessorURL+"/process",
		"application/json",
		bytes.NewReader(reqBody),
	)
	if err != nil {
		os.Remove(zipPath)
		return c.JSON(http.StatusServiceUnavailable, map[string]string{
			"error": fmt.Sprintf("preprocessor unavailable: %v", err),
		})
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		os.Remove(zipPath)
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": fmt.Sprintf("preprocessor error: %s", string(body)),
		})
	}

	return c.JSON(http.StatusAccepted, map[string]string{
		"job_id": jobID,
		"status": "queued",
	})
}

func (h *HealthKitHandler) Register(g *echo.Group) {
	// Chunked upload (Cloudflare Tunnel 100MB limit workaround)
	g.POST("/import/healthkit/init", h.InitUpload)
	g.PUT("/import/healthkit/chunk/:uploadId/:chunkIndex", h.UploadChunk)
	g.POST("/import/healthkit/complete/:uploadId", h.CompleteUpload)
	// Legacy single-request upload (LAN direct, etc.)
	g.POST("/import/healthkit", h.Upload)
	// Status
	g.GET("/import/healthkit/status/:jobId", h.Status)
	g.GET("/import/healthkit/stream/:jobId", h.StatusSSE)
}
