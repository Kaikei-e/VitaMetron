-- +goose Up

-- HRV prediction results
CREATE TABLE IF NOT EXISTS hrv_predictions (
    date                DATE PRIMARY KEY,
    target_date         DATE NOT NULL,
    predicted_zscore    REAL NOT NULL,
    predicted_direction TEXT NOT NULL,
    actual_zscore       REAL,
    confidence          REAL NOT NULL,
    top_drivers         JSONB,
    model_version       TEXT,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HRV model training metadata
CREATE TABLE IF NOT EXISTS hrv_model_metadata (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_version    TEXT NOT NULL UNIQUE,
    trained_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_days    INTEGER NOT NULL,
    cv_mae           REAL NOT NULL,
    cv_rmse          REAL NOT NULL,
    cv_r2            REAL NOT NULL,
    cv_directional_accuracy REAL NOT NULL,
    best_params      JSONB NOT NULL,
    stable_features  TEXT[] NOT NULL,
    feature_names    TEXT[] NOT NULL,
    config           JSONB
);

-- +goose Down
DROP TABLE IF EXISTS hrv_model_metadata;
DROP TABLE IF EXISTS hrv_predictions;
