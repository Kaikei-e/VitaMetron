-- +goose Up

-- New VAS columns (0-100)
ALTER TABLE condition_logs ADD COLUMN mood_vas SMALLINT CHECK (mood_vas BETWEEN 0 AND 100);
ALTER TABLE condition_logs ADD COLUMN energy_vas SMALLINT CHECK (energy_vas BETWEEN 0 AND 100);
ALTER TABLE condition_logs ADD COLUMN sleep_quality_vas SMALLINT CHECK (sleep_quality_vas BETWEEN 0 AND 100);
ALTER TABLE condition_logs ADD COLUMN stress_vas SMALLINT CHECK (stress_vas BETWEEN 0 AND 100);

-- Backfill existing data (1-5 → VAS approximate: 1→10, 2→30, 3→50, 4→70, 5→90)
UPDATE condition_logs SET overall_vas = (overall - 1) * 20 + 10 WHERE overall_vas IS NULL;
UPDATE condition_logs SET mood_vas = (mental - 1) * 20 + 10 WHERE mental IS NOT NULL;
UPDATE condition_logs SET energy_vas = (energy - 1) * 20 + 10 WHERE energy IS NOT NULL;

-- Make overall_vas NOT NULL (all rows backfilled)
ALTER TABLE condition_logs ALTER COLUMN overall_vas SET NOT NULL;
ALTER TABLE condition_logs ALTER COLUMN overall_vas SET DEFAULT 50;

-- Relax overall NOT NULL constraint (legacy; new records auto-computed)
ALTER TABLE condition_logs ALTER COLUMN overall SET DEFAULT 3;

-- WHO-5 Well-Being Index assessment table
CREATE TABLE IF NOT EXISTS who5_assessments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assessed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    item1        SMALLINT NOT NULL CHECK (item1 BETWEEN 0 AND 5),
    item2        SMALLINT NOT NULL CHECK (item2 BETWEEN 0 AND 5),
    item3        SMALLINT NOT NULL CHECK (item3 BETWEEN 0 AND 5),
    item4        SMALLINT NOT NULL CHECK (item4 BETWEEN 0 AND 5),
    item5        SMALLINT NOT NULL CHECK (item5 BETWEEN 0 AND 5),
    raw_score    SMALLINT GENERATED ALWAYS AS (item1 + item2 + item3 + item4 + item5) STORED,
    percentage   SMALLINT GENERATED ALWAYS AS ((item1 + item2 + item3 + item4 + item5) * 4) STORED,
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_who5_assessed_at ON who5_assessments (assessed_at DESC);

-- +goose Down
DROP TABLE IF EXISTS who5_assessments;
ALTER TABLE condition_logs DROP COLUMN IF EXISTS stress_vas;
ALTER TABLE condition_logs DROP COLUMN IF EXISTS sleep_quality_vas;
ALTER TABLE condition_logs DROP COLUMN IF EXISTS energy_vas;
ALTER TABLE condition_logs DROP COLUMN IF EXISTS mood_vas;
ALTER TABLE condition_logs ALTER COLUMN overall_vas DROP NOT NULL;
ALTER TABLE condition_logs ALTER COLUMN overall_vas DROP DEFAULT;
