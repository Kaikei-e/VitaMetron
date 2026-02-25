package fitbit

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"time"

	"vitametron/api/domain/entity"
)

const baseURL = "https://api.fitbit.com"

type FitbitClient struct {
	oauth      *FitbitOAuth
	httpClient *http.Client
	baseURL    string
}

func NewFitbitClient(oauth *FitbitOAuth) *FitbitClient {
	return &FitbitClient{
		oauth: oauth,
		httpClient: &http.Client{
			Timeout: 20 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:          10,
				MaxIdleConnsPerHost:   5,
				IdleConnTimeout:       90 * time.Second,
				TLSHandshakeTimeout:   5 * time.Second,
				ResponseHeaderTimeout: 10 * time.Second,
			},
		},
		baseURL: baseURL,
	}
}

func (c *FitbitClient) ProviderName() string {
	return "fitbit"
}

func (c *FitbitClient) doGet(ctx context.Context, path string, out any) error {
	if err := c.oauth.RefreshTokenIfNeeded(ctx); err != nil {
		return fmt.Errorf("fitbit: refresh token: %w", err)
	}

	accessToken, err := c.oauth.GetAccessToken(ctx)
	if err != nil {
		return fmt.Errorf("fitbit: get access token: %w", err)
	}

	resp, err := c.executeRequest(ctx, path, accessToken)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Handle 401 — retry after token refresh
	if resp.StatusCode == http.StatusUnauthorized {
		resp.Body.Close()
		if err := c.oauth.RefreshTokenIfNeeded(ctx); err != nil {
			return fmt.Errorf("fitbit: refresh after 401: %w", err)
		}
		accessToken, err = c.oauth.GetAccessToken(ctx)
		if err != nil {
			return fmt.Errorf("fitbit: get token after 401: %w", err)
		}
		resp, err = c.executeRequest(ctx, path, accessToken)
		if err != nil {
			return err
		}
		defer resp.Body.Close()
	}

	// Handle 429 — rate limit
	if resp.StatusCode == http.StatusTooManyRequests {
		resp.Body.Close()
		retryAfter := resp.Header.Get("Retry-After")
		seconds, _ := strconv.Atoi(retryAfter)
		if seconds <= 0 || seconds > 300 {
			seconds = 60
		}

		// If context doesn't have enough time left to wait + execute, fail fast
		if deadline, ok := ctx.Deadline(); ok {
			remaining := time.Until(deadline)
			if remaining < time.Duration(seconds)*time.Second+5*time.Second {
				return fmt.Errorf("fitbit: rate limited (retry after %ds), insufficient context time (%v remaining)", seconds, remaining.Round(time.Second))
			}
		}

		log.Printf("fitbit: rate limited, waiting %ds", seconds)
		select {
		case <-time.After(time.Duration(seconds) * time.Second):
		case <-ctx.Done():
			return ctx.Err()
		}
		resp, err = c.executeRequest(ctx, path, accessToken)
		if err != nil {
			return err
		}
		defer resp.Body.Close()
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("fitbit: %s returned %d: %s", path, resp.StatusCode, string(body))
	}

	// Log rate limit headers
	if remaining := resp.Header.Get("Fitbit-Rate-Limit-Remaining"); remaining != "" {
		log.Printf("fitbit: rate limit remaining: %s", remaining)
	}

	return json.NewDecoder(resp.Body).Decode(out)
}

func (c *FitbitClient) executeRequest(ctx context.Context, path, accessToken string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+path, nil)
	if err != nil {
		return nil, fmt.Errorf("fitbit: create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)
	req.Header.Set("User-Agent", "VitaMetron/0.1")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fitbit: request %s: %w", path, err)
	}
	return resp, nil
}

func (c *FitbitClient) FetchDailySummary(ctx context.Context, date time.Time) (*entity.DailySummary, error) {
	dateStr := date.Format("2006-01-02")

	var actResp ActivityResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/activities/date/%s.json", dateStr), &actResp); err != nil {
		return nil, fmt.Errorf("fitbit: fetch activity: %w", err)
	}

	summary := mapActivityToSummary(&actResp, date)

	// Fetch VO2Max separately
	var cardioResp CardioScoreResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/cardioscore/date/%s.json", dateStr), &cardioResp); err != nil {
		log.Printf("warn: fetch cardioscore failed for %s: %v", dateStr, err)
	} else if len(cardioResp.CardioScore) > 0 {
		if v := ParseVO2MaxRange(cardioResp.CardioScore[0].Value.VO2Max); v != nil {
			f := float32(*v)
			summary.VO2Max = &f
		}
	}

	return summary, nil
}

func (c *FitbitClient) FetchSleepStages(ctx context.Context, date time.Time) ([]entity.SleepStage, *entity.SleepRecord, error) {
	dateStr := date.Format("2006-01-02")

	var sleepResp SleepResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1.2/user/-/sleep/date/%s.json", dateStr), &sleepResp); err != nil {
		return nil, nil, fmt.Errorf("fitbit: fetch sleep: %w", err)
	}

	return mapSleepStages(&sleepResp, date), mapSleepRecord(&sleepResp), nil
}

func (c *FitbitClient) FetchHeartRateIntraday(ctx context.Context, date time.Time) ([]entity.HeartRateSample, error) {
	dateStr := date.Format("2006-01-02")

	var hrResp HRIntradayResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/activities/heart/date/%s/1d/1min.json", dateStr), &hrResp); err != nil {
		return nil, fmt.Errorf("fitbit: fetch heart rate intraday: %w", err)
	}

	return mapHRIntraday(&hrResp, date), nil
}

func (c *FitbitClient) FetchHRV(ctx context.Context, date time.Time) (float32, float32, error) {
	dateStr := date.Format("2006-01-02")

	var hrvResp HRVResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/hrv/date/%s.json", dateStr), &hrvResp); err != nil {
		return 0, 0, fmt.Errorf("fitbit: fetch hrv: %w", err)
	}

	if len(hrvResp.HRV) == 0 {
		return 0, 0, fmt.Errorf("fitbit: no HRV data for %s", dateStr)
	}

	return hrvResp.HRV[0].HRV.DailyRMSSD, hrvResp.HRV[0].HRV.DeepRMSSD, nil
}

func (c *FitbitClient) FetchSpO2(ctx context.Context, date time.Time) (avg, min, max float32, err error) {
	dateStr := date.Format("2006-01-02")

	var spo2Resp SpO2Response
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/spo2/date/%s.json", dateStr), &spo2Resp); err != nil {
		return 0, 0, 0, fmt.Errorf("fitbit: fetch spo2: %w", err)
	}

	return spo2Resp.Value.Avg, spo2Resp.Value.Min, spo2Resp.Value.Max, nil
}

func (c *FitbitClient) FetchBreathingRate(ctx context.Context, date time.Time) (full, deep, light, rem float32, err error) {
	dateStr := date.Format("2006-01-02")

	var brResp BreathingRateResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/br/date/%s/all.json", dateStr), &brResp); err != nil {
		return 0, 0, 0, 0, fmt.Errorf("fitbit: fetch breathing rate: %w", err)
	}

	if len(brResp.BR) == 0 {
		return 0, 0, 0, 0, fmt.Errorf("fitbit: no breathing rate data for %s", dateStr)
	}

	v := brResp.BR[0].Value
	return v.FullSleepSummary.BreathingRate,
		v.DeepSleepSummary.BreathingRate,
		v.LightSleepSummary.BreathingRate,
		v.RemSleepSummary.BreathingRate,
		nil
}

func (c *FitbitClient) FetchSkinTemperature(ctx context.Context, date time.Time) (float32, error) {
	dateStr := date.Format("2006-01-02")

	var tempResp SkinTempResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/temp/skin/date/%s.json", dateStr), &tempResp); err != nil {
		return 0, fmt.Errorf("fitbit: fetch skin temp: %w", err)
	}

	if len(tempResp.TempSkin) == 0 {
		return 0, fmt.Errorf("fitbit: no skin temp data for %s", dateStr)
	}

	return tempResp.TempSkin[0].Value.NightlyRelative, nil
}

func (c *FitbitClient) FetchExerciseLogs(ctx context.Context, date time.Time) ([]entity.ExerciseLog, error) {
	dateStr := date.Format("2006-01-02")

	var actResp ActivityResponse
	if err := c.doGet(ctx, fmt.Sprintf("/1/user/-/activities/date/%s.json", dateStr), &actResp); err != nil {
		return nil, fmt.Errorf("fitbit: fetch activities: %w", err)
	}

	return mapExerciseLogs(&actResp, date), nil
}
