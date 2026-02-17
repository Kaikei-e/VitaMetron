-- +goose Up
ALTER TABLE hrv_model_metadata
ADD COLUMN IF NOT EXISTS lstm_config JSONB,
ADD COLUMN IF NOT EXISTS ensemble_config JSONB;

-- +goose Down
ALTER TABLE hrv_model_metadata
DROP COLUMN IF EXISTS ensemble_config,
DROP COLUMN IF EXISTS lstm_config;
