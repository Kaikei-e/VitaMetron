-- +goose Up
-- Scale divergence_detections from 0-5 to 0-100 (VAS alignment)
UPDATE divergence_detections
SET actual_score = actual_score * 20,
    predicted_score = predicted_score * 20,
    residual = residual * 20;

-- +goose Down
UPDATE divergence_detections
SET actual_score = actual_score / 20.0,
    predicted_score = predicted_score / 20.0,
    residual = residual / 20.0;
