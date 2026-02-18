-- +goose Up
CREATE TABLE IF NOT EXISTS daily_advice (
    date            DATE PRIMARY KEY,
    advice_text     TEXT NOT NULL,
    prompt_hash     TEXT,
    model_name      TEXT NOT NULL DEFAULT 'gemma3:4b-it-qat',
    generation_ms   INTEGER,
    context_summary JSONB,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- +goose Down
DROP TABLE IF EXISTS daily_advice;
