-- +goose Up
-- Remove HealthConnect sleep_stages data with fake-UTC timestamps (log_id = 0).
-- Correct data will be re-imported with proper JST timezone on next HC import.
DELETE FROM sleep_stages WHERE log_id = 0;

-- +goose Down
-- Deleted rows cannot be restored.
