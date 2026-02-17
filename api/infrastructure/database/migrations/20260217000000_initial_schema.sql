-- +goose Up

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- OAuth tokens (single-user, one row per provider)
CREATE TABLE IF NOT EXISTS oauth_tokens (
    provider       TEXT PRIMARY KEY,
    access_token   BYTEA NOT NULL,
    refresh_token  BYTEA NOT NULL,
    token_type     TEXT NOT NULL DEFAULT 'Bearer',
    expires_at     TIMESTAMPTZ NOT NULL,
    scopes         TEXT[],
    extra          JSONB,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Condition logs (5-point scale)
CREATE TABLE IF NOT EXISTS condition_logs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    overall     SMALLINT NOT NULL CHECK (overall BETWEEN 1 AND 5),
    mental      SMALLINT CHECK (mental BETWEEN 1 AND 5),
    physical    SMALLINT CHECK (physical BETWEEN 1 AND 5),
    energy      SMALLINT CHECK (energy BETWEEN 1 AND 5),
    note        TEXT,
    tags        TEXT[] DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_condition_logged_at ON condition_logs (logged_at DESC);

-- Daily biometrics summary
CREATE TABLE IF NOT EXISTS daily_summaries (
    date                DATE PRIMARY KEY,
    provider            TEXT NOT NULL DEFAULT 'fitbit',
    resting_hr          SMALLINT,
    avg_hr              REAL,
    max_hr              SMALLINT,
    hrv_daily_rmssd     REAL,
    hrv_deep_rmssd      REAL,
    spo2_avg            REAL,
    spo2_min            REAL,
    spo2_max            REAL,
    br_full_sleep       REAL,
    br_deep_sleep       REAL,
    br_light_sleep      REAL,
    br_rem_sleep        REAL,
    skin_temp_variation REAL,
    sleep_start         TIMESTAMPTZ,
    sleep_end           TIMESTAMPTZ,
    sleep_duration_min  INTEGER,
    sleep_minutes_asleep INTEGER,
    sleep_minutes_awake INTEGER,
    sleep_onset_latency INTEGER,
    sleep_type          TEXT,
    sleep_deep_min      INTEGER,
    sleep_light_min     INTEGER,
    sleep_rem_min       INTEGER,
    sleep_wake_min      INTEGER,
    sleep_is_main       BOOLEAN DEFAULT TRUE,
    steps               INTEGER,
    distance_km         REAL,
    floors              INTEGER,
    calories_total      INTEGER,
    calories_active     INTEGER,
    calories_bmr        INTEGER,
    active_zone_min     INTEGER,
    minutes_sedentary   INTEGER,
    minutes_lightly     INTEGER,
    minutes_fairly      INTEGER,
    minutes_very        INTEGER,
    vo2_max             REAL,
    hr_zone_out_min     INTEGER,
    hr_zone_fat_min     INTEGER,
    hr_zone_cardio_min  INTEGER,
    hr_zone_peak_min    INTEGER,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('daily_summaries', by_range('date'), if_not_exists => TRUE);

-- Heart rate intraday
CREATE TABLE IF NOT EXISTS heart_rate_intraday (
    time       TIMESTAMPTZ NOT NULL,
    bpm        SMALLINT NOT NULL,
    confidence SMALLINT DEFAULT 0,
    PRIMARY KEY (time)
);
SELECT create_hypertable('heart_rate_intraday', by_range('time'), if_not_exists => TRUE);

-- Sleep stages
CREATE TABLE IF NOT EXISTS sleep_stages (
    time     TIMESTAMPTZ NOT NULL,
    stage    TEXT NOT NULL,
    seconds  INTEGER NOT NULL,
    log_id   BIGINT,
    PRIMARY KEY (time)
);
SELECT create_hypertable('sleep_stages', by_range('time'), if_not_exists => TRUE);

-- Exercise logs
CREATE TABLE IF NOT EXISTS exercise_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id     TEXT UNIQUE,
    activity_name   TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    duration_ms     BIGINT NOT NULL,
    calories        INTEGER,
    avg_hr          SMALLINT,
    distance_km     REAL,
    zone_minutes    JSONB,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ML prediction results
CREATE TABLE IF NOT EXISTS condition_predictions (
    target_date         DATE PRIMARY KEY,
    predicted_score     REAL NOT NULL,
    confidence          REAL NOT NULL,
    contributing_factors JSONB,
    risk_signals        TEXT[],
    predicted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TimescaleDB continuous aggregate (7-day moving average)
-- +goose StatementBegin
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.continuous_aggregates
        WHERE view_name = 'daily_7d_avg'
    ) THEN
        EXECUTE '
            CREATE MATERIALIZED VIEW daily_7d_avg
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket(''1 day'', date) AS bucket,
                avg(resting_hr)         AS rhr_7d,
                avg(hrv_daily_rmssd)    AS hrv_7d,
                avg(sleep_duration_min) AS sleep_7d,
                avg(steps)              AS steps_7d,
                avg(spo2_avg)           AS spo2_7d
            FROM daily_summaries
            GROUP BY time_bucket(''1 day'', date)
            WITH NO DATA';
    END IF;
END $$;
-- +goose StatementEnd

SELECT add_continuous_aggregate_policy('daily_7d_avg',
    start_offset  => INTERVAL '14 days',
    end_offset    => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily data quality
CREATE TABLE IF NOT EXISTS daily_data_quality (
    date                DATE PRIMARY KEY,
    wear_time_hours     REAL,
    hr_sample_count     INTEGER,
    completeness_pct    REAL,
    metrics_present     TEXT[],
    metrics_missing     TEXT[],
    plausibility_flags  JSONB,
    plausibility_pass   BOOLEAN,
    is_valid_day        BOOLEAN,
    baseline_days       INTEGER,
    baseline_maturity   TEXT,
    confidence_score    REAL,
    confidence_level    TEXT,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- VRI scores
CREATE TABLE IF NOT EXISTS vri_scores (
    date                DATE PRIMARY KEY,
    vri_score           REAL NOT NULL,
    vri_confidence      REAL NOT NULL,
    z_ln_rmssd          REAL,
    z_resting_hr        REAL,
    z_sleep_duration    REAL,
    z_sri               REAL,
    z_spo2              REAL,
    z_deep_sleep        REAL,
    z_br                REAL,
    sri_value           REAL,
    sri_days_used       INTEGER,
    baseline_window_days INTEGER,
    metrics_included    TEXT[],
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Rolling baselines (60-day median/MAD)
CREATE TABLE IF NOT EXISTS rolling_baselines (
    date                DATE PRIMARY KEY,
    ln_rmssd_median     REAL, ln_rmssd_mad REAL, ln_rmssd_count INTEGER,
    rhr_median          REAL, rhr_mad REAL, rhr_count INTEGER,
    sleep_dur_median    REAL, sleep_dur_mad REAL, sleep_dur_count INTEGER,
    sri_median          REAL, sri_mad REAL, sri_count INTEGER,
    spo2_median         REAL, spo2_mad REAL, spo2_count INTEGER,
    deep_sleep_median   REAL, deep_sleep_mad REAL, deep_sleep_count INTEGER,
    br_median           REAL, br_mad REAL, br_count INTEGER,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Anomaly detection results
CREATE TABLE IF NOT EXISTS anomaly_detections (
    date                  DATE PRIMARY KEY,
    anomaly_score         REAL NOT NULL,
    normalized_score      REAL NOT NULL,
    is_anomaly            BOOLEAN NOT NULL,
    quality_gate          TEXT NOT NULL,
    quality_confidence    REAL NOT NULL,
    quality_adjusted_score REAL NOT NULL,
    top_drivers           JSONB,
    explanation           TEXT,
    model_version         TEXT,
    computed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Anomaly model metadata
CREATE TABLE IF NOT EXISTS anomaly_model_metadata (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_version    TEXT NOT NULL UNIQUE,
    trained_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_days    INTEGER NOT NULL,
    contamination    REAL NOT NULL,
    pot_threshold    REAL NOT NULL,
    feature_names    TEXT[] NOT NULL,
    config           JSONB
);

-- Retention policies (auto-delete old intraday data)
SELECT add_retention_policy('heart_rate_intraday', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('sleep_stages', INTERVAL '90 days', if_not_exists => TRUE);

-- +goose Down

SELECT remove_retention_policy('sleep_stages', if_exists => TRUE);
SELECT remove_retention_policy('heart_rate_intraday', if_exists => TRUE);

DROP TABLE IF EXISTS anomaly_model_metadata;
DROP TABLE IF EXISTS anomaly_detections;
DROP TABLE IF EXISTS rolling_baselines;
DROP TABLE IF EXISTS vri_scores;
DROP TABLE IF EXISTS daily_data_quality;

SELECT remove_continuous_aggregate_policy('daily_7d_avg', if_not_exists => TRUE);
DROP MATERIALIZED VIEW IF EXISTS daily_7d_avg;

DROP TABLE IF EXISTS condition_predictions;
DROP TABLE IF EXISTS exercise_logs;
DROP TABLE IF EXISTS sleep_stages;
DROP TABLE IF EXISTS heart_rate_intraday;
DROP TABLE IF EXISTS daily_summaries;
DROP TABLE IF EXISTS condition_logs;
DROP TABLE IF EXISTS oauth_tokens;
