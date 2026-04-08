package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"vitametron/api/domain/entity"
)

type CircadianRepo struct {
	pool *pgxpool.Pool
}

func NewCircadianRepo(pool *pgxpool.Pool) *CircadianRepo {
	return &CircadianRepo{pool: pool}
}

func (r *CircadianRepo) GetByDate(ctx context.Context, date time.Time) (*entity.CircadianScore, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT date, chs_score, chs_confidence,
			cosinor_mesor, cosinor_amplitude, cosinor_acrophase_hour,
			npar_is, npar_iv, npar_ra, npar_m10, npar_m10_start, npar_l5, npar_l5_start,
			sleep_midpoint_hour, sleep_midpoint_var_min, social_jetlag_min,
			nocturnal_dip_pct, daytime_mean_hr, nighttime_mean_hr,
			z_rhythm_strength, z_rhythm_stability, z_rhythm_fragmentation,
			z_sleep_regularity, z_phase_alignment,
			sri_value, baseline_window_days, metrics_included, computed_at
		 FROM circadian_scores WHERE date = $1`, date)

	var s entity.CircadianScore
	err := row.Scan(
		&s.Date, &s.CHSScore, &s.CHSConfidence,
		&s.CosinorMesor, &s.CosinorAmplitude, &s.CosinorAcrophaseHour,
		&s.NPARIS, &s.NPARIV, &s.NPARRA, &s.NPARM10, &s.NPARM10Start, &s.NPARL5, &s.NPARL5Start,
		&s.SleepMidpointHour, &s.SleepMidpointVarMin, &s.SocialJetlagMin,
		&s.NocturnalDipPct, &s.DaytimeMeanHR, &s.NighttimeMeanHR,
		&s.ZRhythmStrength, &s.ZRhythmStability, &s.ZRhythmFragmentation,
		&s.ZSleepRegularity, &s.ZPhaseAlignment,
		&s.SRIValue, &s.BaselineWindowDays, &s.MetricsIncluded, &s.ComputedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *CircadianRepo) ListRange(ctx context.Context, from, to time.Time) ([]entity.CircadianScore, error) {
	rows, err := r.pool.Query(ctx,
		`SELECT date, chs_score, chs_confidence,
			cosinor_mesor, cosinor_amplitude, cosinor_acrophase_hour,
			npar_is, npar_iv, npar_ra, npar_m10, npar_m10_start, npar_l5, npar_l5_start,
			sleep_midpoint_hour, sleep_midpoint_var_min, social_jetlag_min,
			nocturnal_dip_pct, daytime_mean_hr, nighttime_mean_hr,
			z_rhythm_strength, z_rhythm_stability, z_rhythm_fragmentation,
			z_sleep_regularity, z_phase_alignment,
			sri_value, baseline_window_days, metrics_included, computed_at
		 FROM circadian_scores WHERE date BETWEEN $1 AND $2 ORDER BY date ASC`, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var scores []entity.CircadianScore
	for rows.Next() {
		var s entity.CircadianScore
		if err := rows.Scan(
			&s.Date, &s.CHSScore, &s.CHSConfidence,
			&s.CosinorMesor, &s.CosinorAmplitude, &s.CosinorAcrophaseHour,
			&s.NPARIS, &s.NPARIV, &s.NPARRA, &s.NPARM10, &s.NPARM10Start, &s.NPARL5, &s.NPARL5Start,
			&s.SleepMidpointHour, &s.SleepMidpointVarMin, &s.SocialJetlagMin,
			&s.NocturnalDipPct, &s.DaytimeMeanHR, &s.NighttimeMeanHR,
			&s.ZRhythmStrength, &s.ZRhythmStability, &s.ZRhythmFragmentation,
			&s.ZSleepRegularity, &s.ZPhaseAlignment,
			&s.SRIValue, &s.BaselineWindowDays, &s.MetricsIncluded, &s.ComputedAt); err != nil {
			return nil, err
		}
		scores = append(scores, s)
	}
	return scores, rows.Err()
}
