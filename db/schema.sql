-- db/schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─── プロバイダー OAuth トークン ───
-- 個人ユースのためユーザーテーブルは不要。
-- プロバイダーごとに1レコードのみ (e.g., "fitbit")。
CREATE TABLE oauth_tokens (
    provider       TEXT PRIMARY KEY,          -- "fitbit" | "apple_health" | "garmin"
    access_token   BYTEA NOT NULL,            -- AES-256-GCM 暗号化済み
    refresh_token  BYTEA NOT NULL,            -- AES-256-GCM 暗号化済み
    token_type     TEXT NOT NULL DEFAULT 'Bearer',
    expires_at     TIMESTAMPTZ NOT NULL,
    scopes         TEXT[],
    extra          JSONB,                     -- プロバイダー固有の追加情報
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── 5段階コンディション記録 ───
CREATE TABLE condition_logs (
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
CREATE INDEX idx_condition_logged_at ON condition_logs (logged_at DESC);

-- ─── 日次バイオメトリクスサマリー ───
CREATE TABLE daily_summaries (
    date                DATE PRIMARY KEY,
    provider            TEXT NOT NULL DEFAULT 'fitbit',

    -- 心拍
    resting_hr          SMALLINT,
    avg_hr              REAL,
    max_hr              SMALLINT,

    -- HRV
    hrv_daily_rmssd     REAL,
    hrv_deep_rmssd      REAL,

    -- SpO2
    spo2_avg            REAL,
    spo2_min            REAL,
    spo2_max            REAL,

    -- 呼吸数
    br_full_sleep       REAL,
    br_deep_sleep       REAL,
    br_light_sleep      REAL,
    br_rem_sleep        REAL,

    -- 皮膚温度
    skin_temp_variation REAL,

    -- 睡眠
    sleep_start         TIMESTAMPTZ,
    sleep_end           TIMESTAMPTZ,
    sleep_duration_min  INTEGER,
    sleep_minutes_asleep INTEGER,
    sleep_minutes_awake INTEGER,
    sleep_onset_latency INTEGER,
    sleep_type          TEXT,       -- 'stages' | 'classic'
    sleep_deep_min      INTEGER,
    sleep_light_min     INTEGER,
    sleep_rem_min       INTEGER,
    sleep_wake_min      INTEGER,
    sleep_is_main       BOOLEAN DEFAULT TRUE,

    -- アクティビティ
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

    -- VO2 Max
    vo2_max             REAL,

    -- 心拍ゾーン
    hr_zone_out_min     INTEGER,
    hr_zone_fat_min     INTEGER,
    hr_zone_cardio_min  INTEGER,
    hr_zone_peak_min    INTEGER,

    synced_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('daily_summaries', by_range('date'));

-- ─── 心拍 Intraday ───
CREATE TABLE heart_rate_intraday (
    time       TIMESTAMPTZ NOT NULL,
    bpm        SMALLINT NOT NULL,
    confidence SMALLINT DEFAULT 0,
    PRIMARY KEY (time)
);
SELECT create_hypertable('heart_rate_intraday', by_range('time'));

-- ─── 睡眠ステージ詳細 ───
CREATE TABLE sleep_stages (
    time     TIMESTAMPTZ NOT NULL,
    stage    TEXT NOT NULL,          -- 'deep' | 'light' | 'rem' | 'wake'
    seconds  INTEGER NOT NULL,
    log_id   BIGINT,
    PRIMARY KEY (time)
);
SELECT create_hypertable('sleep_stages', by_range('time'));

-- ─── エクササイズログ ───
CREATE TABLE exercise_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id     TEXT UNIQUE,        -- Fitbit の logId 等
    activity_name   TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    duration_ms     BIGINT NOT NULL,
    calories        INTEGER,
    avg_hr          SMALLINT,
    distance_km     REAL,
    zone_minutes    JSONB,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── ML 予測結果 ───
CREATE TABLE condition_predictions (
    target_date         DATE PRIMARY KEY,
    predicted_score     REAL NOT NULL,
    confidence          REAL NOT NULL,
    contributing_factors JSONB,
    risk_signals        TEXT[],
    predicted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TimescaleDB 連続集約 (7日移動平均) ───
CREATE MATERIALIZED VIEW daily_7d_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', date) AS bucket,
    avg(resting_hr)         AS rhr_7d,
    avg(hrv_daily_rmssd)    AS hrv_7d,
    avg(sleep_duration_min) AS sleep_7d,
    avg(steps)              AS steps_7d,
    avg(spo2_avg)           AS spo2_7d
FROM daily_summaries
GROUP BY time_bucket('1 day', date)
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_7d_avg',
    start_offset  => INTERVAL '14 days',
    end_offset    => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour'
);

-- ─── データ保持ポリシー ───
-- 心拍 Intraday は 90 日で自動削除 (ストレージ節約)
SELECT add_retention_policy('heart_rate_intraday', INTERVAL '90 days');
-- 睡眠ステージ詳細も 90 日
SELECT add_retention_policy('sleep_stages', INTERVAL '90 days');
