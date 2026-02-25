package entity

import "time"

type TrainabilityCheck struct {
	Model             string `json:"model"`
	Trainable         bool   `json:"trainable"`
	Reason            string `json:"reason"`
	AvailableCount    int    `json:"available_count"`
	NewSinceLastTrain int    `json:"new_since_last_train"`
	RecentQualityOK   bool   `json:"recent_quality_ok"`
}

type RetrainCheckResult struct {
	Anomaly    TrainabilityCheck `json:"anomaly"`
	HRV        TrainabilityCheck `json:"hrv"`
	Divergence TrainabilityCheck `json:"divergence"`
}

type RetrainModelResult struct {
	Status        string   `json:"status"`
	Message       *string  `json:"message,omitempty"`
	ModelVersion  *string  `json:"model_version,omitempty"`
	TrainingDays  *int     `json:"training_days,omitempty"`
	TrainingPairs *int     `json:"training_pairs,omitempty"`
	OptunaTrial   *int     `json:"optuna_trials,omitempty"`
	CVMAE         *float64 `json:"cv_mae,omitempty"`
	R2            *float64 `json:"r2,omitempty"`
}

type RetrainResult struct {
	Trigger         string             `json:"trigger"`
	Mode            string             `json:"mode"`
	Anomaly         RetrainModelResult `json:"anomaly"`
	HRV             RetrainModelResult `json:"hrv"`
	Divergence      RetrainModelResult `json:"divergence"`
	DurationSeconds *float64           `json:"duration_seconds,omitempty"`
	LogID           *int64             `json:"log_id,omitempty"`
}

type RetrainLogEntry struct {
	ID                     int64      `json:"id"`
	StartedAt              time.Time  `json:"started_at"`
	CompletedAt            *time.Time `json:"completed_at,omitempty"`
	Trigger                string     `json:"trigger"`
	RetrainMode            string     `json:"retrain_mode"`
	AnomalyStatus          string     `json:"anomaly_status"`
	AnomalyMessage         *string    `json:"anomaly_message,omitempty"`
	AnomalyModelVersion    *string    `json:"anomaly_model_version,omitempty"`
	AnomalyTrainingDays    *int       `json:"anomaly_training_days,omitempty"`
	HRVStatus              string     `json:"hrv_status"`
	HRVMessage             *string    `json:"hrv_message,omitempty"`
	HRVModelVersion        *string    `json:"hrv_model_version,omitempty"`
	HRVTrainingDays        *int       `json:"hrv_training_days,omitempty"`
	HRVOptunaTrial         *int       `json:"hrv_optuna_trials,omitempty"`
	HRVCVMAE               *float64   `json:"hrv_cv_mae,omitempty"`
	DivergenceStatus       string     `json:"divergence_status"`
	DivergenceMessage      *string    `json:"divergence_message,omitempty"`
	DivergenceModelVersion *string    `json:"divergence_model_version,omitempty"`
	DivergenceTrainingPrs  *int       `json:"divergence_training_pairs,omitempty"`
	DivergenceR2           *float64   `json:"divergence_r2,omitempty"`
	DurationSeconds        *float64   `json:"duration_seconds,omitempty"`
}

type RetrainLogsResult struct {
	Logs  []RetrainLogEntry `json:"logs"`
	Total int               `json:"total"`
}
