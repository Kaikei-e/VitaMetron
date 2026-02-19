-- +goose Up
-- Remove HC-imported duplicate sleep stages that share a Fitbit LogID.
-- Uses recursive CTE to trace the main chain per log_id (start -> end_time = next start_time),
-- then deletes all entries NOT in any chain.
WITH RECURSIVE chain AS (
  SELECT s.ctid AS rid, s.log_id, s.time, s.seconds,
         s.time + make_interval(secs => s.seconds) AS end_time
  FROM sleep_stages s
  INNER JOIN (
    SELECT log_id, min(time) AS min_time
    FROM sleep_stages
    GROUP BY log_id
  ) first ON s.log_id = first.log_id AND s.time = first.min_time

  UNION ALL

  SELECT s.ctid, s.log_id, s.time, s.seconds,
         s.time + make_interval(secs => s.seconds)
  FROM sleep_stages s
  JOIN chain c ON s.log_id = c.log_id AND s.time = c.end_time
)
DELETE FROM sleep_stages
WHERE ctid NOT IN (SELECT rid FROM chain);

-- +goose Down
-- Deleted rows cannot be restored.
