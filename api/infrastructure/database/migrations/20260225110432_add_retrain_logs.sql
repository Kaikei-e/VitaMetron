-- +goose Up
CREATE TABLE IF NOT EXISTS retrain_logs (
    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at              TIMESTAMPTZ,
    trigger                   TEXT NOT NULL DEFAULT 'scheduled',
    retrain_mode              TEXT NOT NULL DEFAULT 'daily',
    anomaly_status            TEXT NOT NULL DEFAULT 'pending',
    anomaly_message           TEXT,
    anomaly_model_version     TEXT,
    anomaly_training_days     INTEGER,
    hrv_status                TEXT NOT NULL DEFAULT 'pending',
    hrv_message               TEXT,
    hrv_model_version         TEXT,
    hrv_training_days         INTEGER,
    hrv_optuna_trials         INTEGER,
    hrv_cv_mae                REAL,
    divergence_status         TEXT NOT NULL DEFAULT 'pending',
    divergence_message        TEXT,
    divergence_model_version  TEXT,
    divergence_training_pairs INTEGER,
    divergence_r2             REAL,
    duration_seconds          REAL
);
CREATE INDEX idx_retrain_logs_started_at ON retrain_logs (started_at DESC);

-- +goose Down
DROP TABLE IF EXISTS retrain_logs;
