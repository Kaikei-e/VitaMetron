-- +goose Up

-- VAS column on condition_logs (0-100 continuous scale)
ALTER TABLE condition_logs ADD COLUMN overall_vas SMALLINT;

CREATE TABLE divergence_detections (
    date                DATE PRIMARY KEY,
    condition_log_id    BIGINT,
    actual_score        REAL NOT NULL,
    predicted_score     REAL NOT NULL,
    residual            REAL NOT NULL,
    cusum_positive      REAL NOT NULL DEFAULT 0,
    cusum_negative      REAL NOT NULL DEFAULT 0,
    cusum_alert         BOOLEAN NOT NULL DEFAULT FALSE,
    divergence_type     TEXT NOT NULL DEFAULT 'aligned',
    confidence          REAL NOT NULL DEFAULT 0,
    top_drivers         JSONB,
    explanation         TEXT,
    model_version       TEXT,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE divergence_model_metadata (
    model_version    TEXT PRIMARY KEY,
    trained_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_pairs   INTEGER NOT NULL,
    r2_score         REAL,
    mae              REAL,
    rmse             REAL,
    residual_mean    REAL,
    residual_std     REAL,
    feature_names    TEXT[],
    config           JSONB
);

-- +goose Down
ALTER TABLE condition_logs DROP COLUMN IF EXISTS overall_vas;
DROP TABLE IF EXISTS divergence_model_metadata;
DROP TABLE IF EXISTS divergence_detections;
