-- +goose Up
-- Remove Health Connect sleep stage duplicates where Fitbit data exists
-- for the same time window (within 5 minutes).
DELETE FROM sleep_stages s1
WHERE s1.log_id = 0
  AND EXISTS (
    SELECT 1 FROM sleep_stages s2
    WHERE s2.log_id != 0
      AND s2.time BETWEEN s1.time - INTERVAL '5 minutes' AND s1.time + INTERVAL '5 minutes'
  );

-- +goose Down
-- No rollback: cannot restore deleted rows.
