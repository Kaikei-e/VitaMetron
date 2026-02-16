package mlclient

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestClient_PredictCondition(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/predict" {
			t.Errorf("path = %q, want /predict", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"predicted_score":      3.5,
			"confidence":           0.85,
			"contributing_factors": map[string]float64{"sleep": 0.3},
			"risk_signals":         []string{"low_hrv"},
		})
	}))
	defer ts.Close()

	client := New(ts.URL)
	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	pred, err := client.PredictCondition(context.Background(), date)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if pred.PredictedScore != 3.5 {
		t.Errorf("PredictedScore = %f, want 3.5", pred.PredictedScore)
	}
	if pred.Confidence != 0.85 {
		t.Errorf("Confidence = %f, want 0.85", pred.Confidence)
	}
}

func TestClient_DetectRisk(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/risk" {
			t.Errorf("path = %q, want /risk", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode([]string{"low_hrv", "poor_sleep"})
	}))
	defer ts.Close()

	client := New(ts.URL)
	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	risks, err := client.DetectRisk(context.Background(), date)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(risks) != 2 {
		t.Errorf("len(risks) = %d, want 2", len(risks))
	}
}

func TestClient_PredictCondition_ServerError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer ts.Close()

	client := New(ts.URL)
	_, err := client.PredictCondition(context.Background(), time.Now())
	if err == nil {
		t.Fatal("expected error for 500 response")
	}
}
