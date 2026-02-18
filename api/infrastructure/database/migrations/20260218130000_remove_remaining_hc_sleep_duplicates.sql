-- +goose Up
-- Remove remaining Health Connect sleep stages (log_id=0) on any day
-- where Fitbit data (log_id!=0) also exists. The previous migration
-- used a 5-minute proximity window which missed offset entries.
DELETE FROM sleep_stages s1
WHERE s1.log_id = 0
  AND EXISTS (
    SELECT 1 FROM sleep_stages s2
    WHERE s2.log_id != 0
      AND date_trunc('day', s2.time) = date_trunc('day', s1.time)
  );

-- +goose Down
-- No rollback: cannot restore deleted rows.
