-- +goose Up

-- Circadian Health Score (CHS) — persisted daily circadian rhythm metrics
CREATE TABLE IF NOT EXISTS circadian_scores (
    date                      DATE PRIMARY KEY,
    chs_score                 REAL NOT NULL,
    chs_confidence            REAL NOT NULL,
    -- Cosinor analysis (HR 24h fit)
    cosinor_mesor             REAL,
    cosinor_amplitude         REAL,
    cosinor_acrophase_hour    REAL,
    -- Non-parametric rest-activity rhythm
    npar_is                   REAL,
    npar_iv                   REAL,
    npar_ra                   REAL,
    npar_m10                  REAL,
    npar_m10_start            REAL,
    npar_l5                   REAL,
    npar_l5_start             REAL,
    -- Sleep timing
    sleep_midpoint_hour       REAL,
    sleep_midpoint_var_min    REAL,
    social_jetlag_min         REAL,
    -- Nocturnal HR dip
    nocturnal_dip_pct         REAL,
    daytime_mean_hr           REAL,
    nighttime_mean_hr         REAL,
    -- Z-scores per dimension
    z_rhythm_strength         REAL,
    z_rhythm_stability        REAL,
    z_rhythm_fragmentation    REAL,
    z_sleep_regularity        REAL,
    z_phase_alignment         REAL,
    -- Additional
    sri_value                 REAL,
    baseline_window_days      INTEGER,
    metrics_included          TEXT[],
    computed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Rolling baseline for circadian metrics (60-day median/MAD)
CREATE TABLE IF NOT EXISTS circadian_baselines (
    date                      DATE PRIMARY KEY,
    amplitude_median          REAL,
    amplitude_mad             REAL,
    amplitude_count           INTEGER,
    is_median                 REAL,
    is_mad                    REAL,
    is_count                  INTEGER,
    iv_median                 REAL,
    iv_mad                    REAL,
    iv_count                  INTEGER,
    midpoint_var_median       REAL,
    midpoint_var_mad          REAL,
    midpoint_var_count        INTEGER,
    dip_pct_median            REAL,
    dip_pct_mad               REAL,
    dip_pct_count             INTEGER,
    computed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- +goose Down
DROP TABLE IF EXISTS circadian_baselines;
DROP TABLE IF EXISTS circadian_scores;
