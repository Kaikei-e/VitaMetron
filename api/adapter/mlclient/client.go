package mlclient

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"vitametron/api/domain/entity"
)

type Client struct {
	baseURL       string
	httpClient    *http.Client
	trainClient   *http.Client
}

func New(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		trainClient: &http.Client{
			Timeout: 30 * time.Minute,
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

type vriResponse struct {
	Date                string              `json:"date"`
	VRIScore            float64             `json:"vri_score"`
	VRIConfidence       float64             `json:"vri_confidence"`
	SRIValue            *float64            `json:"sri_value"`
	SRIDaysUsed         int                 `json:"sri_days_used"`
	ZScores             map[string]*float64 `json:"z_scores"`
	ContributingFactors json.RawMessage     `json:"contributing_factors"`
	BaselineWindowDays  int                 `json:"baseline_window_days"`
	BaselineMaturity    string              `json:"baseline_maturity"`
	MetricsIncluded     []string            `json:"metrics_included"`
}

func (c *Client) GetVRI(ctx context.Context, date time.Time) (*entity.VRIScore, error) {
	url := fmt.Sprintf("%s/vri?date=%s", c.baseURL, date.Format("2006-01-02"))
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

	var vr vriResponse
	if err := json.NewDecoder(resp.Body).Decode(&vr); err != nil {
		return nil, err
	}

	return vriResponseToEntity(vr, date), nil
}

func (c *Client) GetVRIRange(ctx context.Context, from, to time.Time) ([]entity.VRIScore, error) {
	url := fmt.Sprintf("%s/vri/range?start=%s&end=%s", c.baseURL, from.Format("2006-01-02"), to.Format("2006-01-02"))
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

	var vrs []vriResponse
	if err := json.NewDecoder(resp.Body).Decode(&vrs); err != nil {
		return nil, err
	}

	scores := make([]entity.VRIScore, len(vrs))
	for i, vr := range vrs {
		scores[i] = *vriResponseToEntity(vr, from)
	}
	return scores, nil
}

func vriResponseToEntity(vr vriResponse, fallbackDate time.Time) *entity.VRIScore {
	s := &entity.VRIScore{
		Date:                fallbackDate,
		VRIScore:            float32(vr.VRIScore),
		VRIConfidence:       float32(vr.VRIConfidence),
		SRIDaysUsed:         vr.SRIDaysUsed,
		BaselineWindowDays:  vr.BaselineWindowDays,
		BaselineMaturity:    vr.BaselineMaturity,
		ContributingFactors: vr.ContributingFactors,
		MetricsIncluded:     vr.MetricsIncluded,
		ComputedAt:          time.Now(),
	}

	if vr.SRIValue != nil {
		v := float32(*vr.SRIValue)
		s.SRIValue = &v
	}

	if z, ok := vr.ZScores["z_ln_rmssd"]; ok && z != nil {
		v := float32(*z)
		s.ZLnRMSSD = &v
	}
	if z, ok := vr.ZScores["z_resting_hr"]; ok && z != nil {
		v := float32(*z)
		s.ZRestingHR = &v
	}
	if z, ok := vr.ZScores["z_sleep_duration"]; ok && z != nil {
		v := float32(*z)
		s.ZSleepDuration = &v
	}
	if z, ok := vr.ZScores["z_sri"]; ok && z != nil {
		v := float32(*z)
		s.ZSRI = &v
	}
	if z, ok := vr.ZScores["z_spo2"]; ok && z != nil {
		v := float32(*z)
		s.ZSpO2 = &v
	}
	if z, ok := vr.ZScores["z_deep_sleep"]; ok && z != nil {
		v := float32(*z)
		s.ZDeepSleep = &v
	}
	if z, ok := vr.ZScores["z_br"]; ok && z != nil {
		v := float32(*z)
		s.ZBR = &v
	}

	return s
}

// --- Anomaly Detection ---

type anomalyContribution struct {
	Feature   string  `json:"feature"`
	ShapValue float64 `json:"shap_value"`
	Direction string  `json:"direction"`
	Desc      string  `json:"description"`
}

type anomalyResponse struct {
	Date                 string                `json:"date"`
	AnomalyScore         float64               `json:"anomaly_score"`
	NormalizedScore      float64               `json:"normalized_score"`
	IsAnomaly            bool                  `json:"is_anomaly"`
	QualityGate          string                `json:"quality_gate"`
	QualityConfidence    float64               `json:"quality_confidence"`
	QualityAdjustedScore float64               `json:"quality_adjusted_score"`
	TopDrivers           []anomalyContribution `json:"top_drivers"`
	Explanation          string                `json:"explanation"`
	ModelVersion         string                `json:"model_version"`
}

func anomalyResponseToEntity(ar anomalyResponse, fallbackDate time.Time) *entity.AnomalyDetection {
	driversJSON, _ := json.Marshal(ar.TopDrivers)
	return &entity.AnomalyDetection{
		Date:                 fallbackDate,
		AnomalyScore:         float32(ar.AnomalyScore),
		NormalizedScore:      float32(ar.NormalizedScore),
		IsAnomaly:            ar.IsAnomaly,
		QualityGate:          ar.QualityGate,
		QualityConfidence:    float32(ar.QualityConfidence),
		QualityAdjustedScore: float32(ar.QualityAdjustedScore),
		TopDrivers:           driversJSON,
		Explanation:          ar.Explanation,
		ModelVersion:         ar.ModelVersion,
		ComputedAt:           time.Now(),
	}
}

func (c *Client) DetectAnomaly(ctx context.Context, date time.Time) (*entity.AnomalyDetection, error) {
	url := fmt.Sprintf("%s/anomaly/detect?date=%s", c.baseURL, date.Format("2006-01-02"))
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

	var ar anomalyResponse
	if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
		return nil, err
	}

	return anomalyResponseToEntity(ar, date), nil
}

func (c *Client) DetectAnomalyRange(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error) {
	url := fmt.Sprintf("%s/anomaly/range?start=%s&end=%s", c.baseURL, from.Format("2006-01-02"), to.Format("2006-01-02"))
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

	var rangeResp struct {
		Detections []anomalyResponse `json:"detections"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&rangeResp); err != nil {
		return nil, err
	}

	results := make([]entity.AnomalyDetection, len(rangeResp.Detections))
	for i, ar := range rangeResp.Detections {
		results[i] = *anomalyResponseToEntity(ar, from)
	}
	return results, nil
}

type anomalyTrainResponseML struct {
	ModelVersion     string   `json:"model_version"`
	TrainingDaysUsed int      `json:"training_days_used"`
	Contamination    float64  `json:"contamination"`
	PotThreshold     float64  `json:"pot_threshold"`
	FeatureNames     []string `json:"feature_names"`
	Message          string   `json:"message"`
}

func (c *Client) TrainAnomalyModel(ctx context.Context) (*entity.AnomalyTrainResult, error) {
	url := fmt.Sprintf("%s/anomaly/train", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.trainClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var tr anomalyTrainResponseML
	if err := json.NewDecoder(resp.Body).Decode(&tr); err != nil {
		return nil, err
	}

	return &entity.AnomalyTrainResult{
		ModelVersion:     tr.ModelVersion,
		TrainingDaysUsed: tr.TrainingDaysUsed,
		Contamination:    tr.Contamination,
		PotThreshold:     tr.PotThreshold,
		FeatureNames:     tr.FeatureNames,
		Message:          tr.Message,
	}, nil
}

type anomalyStatusResponse struct {
	IsReady      bool     `json:"is_ready"`
	ModelVersion *string  `json:"model_version"`
	FeatureNames []string `json:"feature_names"`
}

func (c *Client) GetAnomalyStatus(ctx context.Context) (*entity.AnomalyModelStatus, error) {
	url := fmt.Sprintf("%s/anomaly/status", c.baseURL)
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

	var sr anomalyStatusResponse
	if err := json.NewDecoder(resp.Body).Decode(&sr); err != nil {
		return nil, err
	}

	modelVersion := ""
	if sr.ModelVersion != nil {
		modelVersion = *sr.ModelVersion
	}

	return &entity.AnomalyModelStatus{
		IsReady:      sr.IsReady,
		ModelVersion: modelVersion,
		FeatureNames: sr.FeatureNames,
	}, nil
}

// --- HRV Prediction ---

type hrvContribution struct {
	Feature   string  `json:"feature"`
	ShapValue float64 `json:"shap_value"`
	Direction string  `json:"direction"`
}

type hrvPredictionResponse struct {
	Date               string            `json:"date"`
	TargetDate         string            `json:"target_date"`
	PredictedHRVZScore float64           `json:"predicted_hrv_zscore"`
	PredictedDirection string            `json:"predicted_direction"`
	Confidence         float64           `json:"confidence"`
	TopDrivers         []hrvContribution `json:"top_drivers"`
	ModelVersion       string            `json:"model_version"`
}

func (c *Client) PredictHRV(ctx context.Context, date time.Time) (*entity.HRVPrediction, error) {
	url := fmt.Sprintf("%s/hrv/predict?date=%s", c.baseURL, date.Format("2006-01-02"))
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

	var hr hrvPredictionResponse
	if err := json.NewDecoder(resp.Body).Decode(&hr); err != nil {
		return nil, err
	}

	driversJSON, _ := json.Marshal(hr.TopDrivers)

	targetDate, _ := time.Parse("2006-01-02", hr.TargetDate)

	return &entity.HRVPrediction{
		Date:               date,
		TargetDate:         targetDate,
		PredictedZScore:    hr.PredictedHRVZScore,
		PredictedDirection: hr.PredictedDirection,
		Confidence:         hr.Confidence,
		TopDrivers:         driversJSON,
		ModelVersion:       hr.ModelVersion,
		ComputedAt:         time.Now(),
	}, nil
}

type hrvTrainResponse struct {
	ModelVersion          string            `json:"model_version"`
	TrainingDaysUsed      int               `json:"training_days_used"`
	CVMAE                 float64           `json:"cv_mae"`
	CVRMSE                float64           `json:"cv_rmse"`
	CVR2                  float64           `json:"cv_r2"`
	CVDirectionalAccuracy float64           `json:"cv_directional_accuracy"`
	BestParams            map[string]any    `json:"best_params"`
	StableFeatures        []string          `json:"stable_features"`
	Message               string            `json:"message"`
}

func (c *Client) TrainHRVModel(ctx context.Context, body io.Reader) (*entity.HRVTrainResult, error) {
	url := fmt.Sprintf("%s/hrv/train", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.trainClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var tr hrvTrainResponse
	if err := json.NewDecoder(resp.Body).Decode(&tr); err != nil {
		return nil, err
	}

	return &entity.HRVTrainResult{
		ModelVersion:          tr.ModelVersion,
		TrainingDaysUsed:      tr.TrainingDaysUsed,
		CVMAE:                 tr.CVMAE,
		CVRMSE:                tr.CVRMSE,
		CVR2:                  tr.CVR2,
		CVDirectionalAccuracy: tr.CVDirectionalAccuracy,
		Message:               tr.Message,
	}, nil
}

// --- HRV Status ---

type hrvStatusResponse struct {
	IsReady        bool               `json:"is_ready"`
	ModelVersion   string             `json:"model_version"`
	TrainingDays   int                `json:"training_days"`
	CVMetrics      map[string]float64 `json:"cv_metrics"`
	StableFeatures []string           `json:"stable_features"`
}

func (c *Client) GetHRVStatus(ctx context.Context) (*entity.HRVModelStatus, error) {
	url := fmt.Sprintf("%s/hrv/status", c.baseURL)
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

	var sr hrvStatusResponse
	if err := json.NewDecoder(resp.Body).Decode(&sr); err != nil {
		return nil, err
	}

	return &entity.HRVModelStatus{
		IsReady:        sr.IsReady,
		ModelVersion:   sr.ModelVersion,
		TrainingDays:   sr.TrainingDays,
		CVMetrics:      sr.CVMetrics,
		StableFeatures: sr.StableFeatures,
	}, nil
}

// --- Weekly Insights ---

type weeklyInsightResponse struct {
	WeekStart   string   `json:"week_start"`
	WeekEnd     string   `json:"week_end"`
	AvgScore    *float64 `json:"avg_score"`
	Trend       string   `json:"trend"`
	TopFactors  []string `json:"top_factors"`
	RiskSummary []string `json:"risk_summary"`
}

func (c *Client) GetWeeklyInsights(ctx context.Context, date time.Time) (*entity.WeeklyInsight, error) {
	url := fmt.Sprintf("%s/insights/weekly?date=%s", c.baseURL, date.Format("2006-01-02"))
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

	var wr weeklyInsightResponse
	if err := json.NewDecoder(resp.Body).Decode(&wr); err != nil {
		return nil, err
	}

	weekStart, _ := time.Parse("2006-01-02", wr.WeekStart)
	weekEnd, _ := time.Parse("2006-01-02", wr.WeekEnd)

	return &entity.WeeklyInsight{
		WeekStart:   weekStart,
		WeekEnd:     weekEnd,
		AvgScore:    wr.AvgScore,
		Trend:       wr.Trend,
		TopFactors:  wr.TopFactors,
		RiskSummary: wr.RiskSummary,
	}, nil
}

// --- Divergence Detection ---

type divergenceContribution struct {
	Feature      string  `json:"feature"`
	Coefficient  float64 `json:"coefficient"`
	FeatureValue float64 `json:"feature_value"`
	Contribution float64 `json:"contribution"`
	Direction    string  `json:"direction"`
}

type divergenceResponse struct {
	Date           string                    `json:"date"`
	ActualScore    float64                   `json:"actual_score"`
	PredictedScore float64                   `json:"predicted_score"`
	Residual       float64                   `json:"residual"`
	CuSumPositive  float64                   `json:"cusum_positive"`
	CuSumNegative  float64                   `json:"cusum_negative"`
	CuSumAlert     bool                      `json:"cusum_alert"`
	DivergenceType string                    `json:"divergence_type"`
	Confidence     float64                   `json:"confidence"`
	TopDrivers     []divergenceContribution  `json:"top_drivers"`
	Explanation    string                    `json:"explanation"`
	ModelVersion   string                    `json:"model_version"`
}

func divergenceResponseToEntity(dr divergenceResponse, fallbackDate time.Time) *entity.DivergenceDetection {
	driversJSON, _ := json.Marshal(dr.TopDrivers)
	return &entity.DivergenceDetection{
		Date:           fallbackDate,
		ActualScore:    float32(dr.ActualScore),
		PredictedScore: float32(dr.PredictedScore),
		Residual:       float32(dr.Residual),
		CuSumPositive:  float32(dr.CuSumPositive),
		CuSumNegative:  float32(dr.CuSumNegative),
		CuSumAlert:     dr.CuSumAlert,
		DivergenceType: dr.DivergenceType,
		Confidence:     float32(dr.Confidence),
		TopDrivers:     driversJSON,
		Explanation:    dr.Explanation,
		ModelVersion:   dr.ModelVersion,
		ComputedAt:     time.Now(),
	}
}

func (c *Client) DetectDivergence(ctx context.Context, date time.Time) (*entity.DivergenceDetection, error) {
	url := fmt.Sprintf("%s/divergence/detect?date=%s", c.baseURL, date.Format("2006-01-02"))
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

	var dr divergenceResponse
	if err := json.NewDecoder(resp.Body).Decode(&dr); err != nil {
		return nil, err
	}

	return divergenceResponseToEntity(dr, date), nil
}

func (c *Client) GetDivergenceRange(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error) {
	url := fmt.Sprintf("%s/divergence/range?start=%s&end=%s", c.baseURL, from.Format("2006-01-02"), to.Format("2006-01-02"))
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

	var rangeResp struct {
		Detections []divergenceResponse `json:"detections"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&rangeResp); err != nil {
		return nil, err
	}

	results := make([]entity.DivergenceDetection, len(rangeResp.Detections))
	for i, dr := range rangeResp.Detections {
		results[i] = *divergenceResponseToEntity(dr, from)
	}
	return results, nil
}

type divergenceStatusResponse struct {
	IsReady        bool     `json:"is_ready"`
	ModelVersion   string   `json:"model_version"`
	TrainingPairs  int      `json:"training_pairs"`
	MinPairsNeeded int      `json:"min_pairs_needed"`
	R2Score        *float64 `json:"r2_score"`
	MAE            *float64 `json:"mae"`
	Phase          string   `json:"phase"`
	Message        string   `json:"message"`
}

func (c *Client) GetDivergenceStatus(ctx context.Context) (*entity.DivergenceModelStatus, error) {
	url := fmt.Sprintf("%s/divergence/status", c.baseURL)
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

	var sr divergenceStatusResponse
	if err := json.NewDecoder(resp.Body).Decode(&sr); err != nil {
		return nil, err
	}

	return &entity.DivergenceModelStatus{
		IsReady:        sr.IsReady,
		ModelVersion:   sr.ModelVersion,
		TrainingPairs:  sr.TrainingPairs,
		MinPairsNeeded: sr.MinPairsNeeded,
		R2Score:        sr.R2Score,
		MAE:            sr.MAE,
		Phase:          sr.Phase,
		Message:        sr.Message,
	}, nil
}

type divergenceTrainResponseML struct {
	ModelVersion      string   `json:"model_version"`
	TrainingPairsUsed int      `json:"training_pairs_used"`
	R2Score           *float64 `json:"r2_score"`
	MAE               *float64 `json:"mae"`
	RMSE              *float64 `json:"rmse"`
	Message           string   `json:"message"`
}

func (c *Client) TrainDivergenceModel(ctx context.Context) (*entity.DivergenceTrainResult, error) {
	url := fmt.Sprintf("%s/divergence/train", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.trainClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var tr divergenceTrainResponseML
	if err := json.NewDecoder(resp.Body).Decode(&tr); err != nil {
		return nil, err
	}

	return &entity.DivergenceTrainResult{
		ModelVersion:      tr.ModelVersion,
		TrainingPairsUsed: tr.TrainingPairsUsed,
		R2Score:           tr.R2Score,
		MAE:               tr.MAE,
		RMSE:              tr.RMSE,
		Message:           tr.Message,
	}, nil
}

// --- Daily Advice ---

type adviceResponse struct {
	Date         string `json:"date"`
	AdviceText   string `json:"advice_text"`
	ModelName    string `json:"model_name"`
	GenerationMs *int   `json:"generation_ms"`
	Cached       bool   `json:"cached"`
}

func adviceResponseToEntity(ar adviceResponse, fallbackDate time.Time) *entity.DailyAdvice {
	return &entity.DailyAdvice{
		Date:         fallbackDate,
		AdviceText:   ar.AdviceText,
		ModelName:    ar.ModelName,
		GenerationMs: ar.GenerationMs,
		Cached:       ar.Cached,
		GeneratedAt:  time.Now(),
	}
}

func (c *Client) GetAdvice(ctx context.Context, date time.Time) (*entity.DailyAdvice, error) {
	url := fmt.Sprintf("%s/advice?date=%s", c.baseURL, date.Format("2006-01-02"))
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	// LLM generation can take up to 120s
	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var ar adviceResponse
	if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
		return nil, err
	}

	return adviceResponseToEntity(ar, date), nil
}

func (c *Client) RegenerateAdvice(ctx context.Context, date time.Time) (*entity.DailyAdvice, error) {
	url := fmt.Sprintf("%s/advice/regenerate?date=%s", c.baseURL, date.Format("2006-01-02"))
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return nil, err
	}

	// LLM generation can take up to 120s
	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ml service returned %d", resp.StatusCode)
	}

	var ar adviceResponse
	if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
		return nil, err
	}

	return adviceResponseToEntity(ar, date), nil
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
