package mlclient

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"vitametron/api/domain/entity"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func New(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

type predictionResponse struct {
	PredictedScore      float64         `json:"predicted_score"`
	Confidence          float64         `json:"confidence"`
	ContributingFactors json.RawMessage `json:"contributing_factors"`
	RiskSignals         []string        `json:"risk_signals"`
}

func (c *Client) PredictCondition(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error) {
	url := fmt.Sprintf("%s/predict?date=%s", c.baseURL, date.Format("2006-01-02"))
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var pr predictionResponse
	if err := json.NewDecoder(resp.Body).Decode(&pr); err != nil {
		return nil, err
	}

	return &entity.ConditionPrediction{
		TargetDate:          date,
		PredictedScore:      float32(pr.PredictedScore),
		Confidence:          float32(pr.Confidence),
		ContributingFactors: pr.ContributingFactors,
		RiskSignals:         pr.RiskSignals,
		PredictedAt:         time.Now(),
	}, nil
}

func (c *Client) DetectRisk(ctx context.Context, date time.Time) ([]string, error) {
	url := fmt.Sprintf("%s/risk?date=%s", c.baseURL, date.Format("2006-01-02"))
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var risks []string
	if err := json.NewDecoder(resp.Body).Decode(&risks); err != nil {
		return nil, err
	}

	return risks, nil
}
