-- +goose Up
-- Fix condition_logs where logged_at was stored as UTC noon (12:00 UTC)
-- instead of JST noon (12:00 JST = 03:00 UTC).
-- Shift these records back by 9 hours to correct the timezone offset.
UPDATE condition_logs
SET logged_at = logged_at - INTERVAL '9 hours'
WHERE EXTRACT(HOUR FROM logged_at) = 12
  AND EXTRACT(MINUTE FROM logged_at) = 0;

-- +goose Down
-- Reverse the correction: shift back to UTC noon
UPDATE condition_logs
SET logged_at = logged_at + INTERVAL '9 hours'
WHERE EXTRACT(HOUR FROM logged_at) = 3
  AND EXTRACT(MINUTE FROM logged_at) = 0;
