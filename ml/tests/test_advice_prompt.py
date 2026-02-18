"""Tests for the structured advice prompt builder."""

from app.services.advice_prompt import (
    _build_activity_section,
    _build_ml_insights_section,
    _build_outlook_section,
    _build_sleep_section,
    _build_subjective_section,
    _build_vitals_section,
    _build_vri_section,
    _sleep_efficiency_pct,
    build_user_prompt,
)


# ── Vitals section ──


def test_vitals_rhr_above_baseline():
    ctx = {
        "biometrics": {"resting_hr": 65},
        "baselines_60d": {"median_resting_hr": 60.0},
    }
    lines = _build_vitals_section(ctx)
    assert any("65 bpm" in ln and "高め" in ln for ln in lines)


def test_vitals_rhr_below_baseline():
    ctx = {
        "biometrics": {"resting_hr": 55},
        "baselines_60d": {"median_resting_hr": 60.0},
    }
    lines = _build_vitals_section(ctx)
    assert any("55 bpm" in ln and "低め" in ln for ln in lines)


def test_vitals_hrv_with_baseline():
    ctx = {
        "biometrics": {"hrv_daily_rmssd": 45.0},
        "baselines_60d": {"median_hrv": 38.0},
    }
    lines = _build_vitals_section(ctx)
    assert any("45.0" in ln and "38.0" in ln and "上回" in ln for ln in lines)


def test_vitals_hrv_deep_higher_than_daily():
    ctx = {
        "biometrics": {"hrv_daily_rmssd": 40.0, "hrv_deep_rmssd": 55.0},
    }
    lines = _build_vitals_section(ctx)
    assert any("副交感神経" in ln for ln in lines)


def test_vitals_spo2_good():
    ctx = {"biometrics": {"spo2_avg": 97.0}}
    lines = _build_vitals_section(ctx)
    assert any("97.0%" in ln and "良好" in ln for ln in lines)


def test_vitals_spo2_low():
    ctx = {"biometrics": {"spo2_avg": 93.0}}
    lines = _build_vitals_section(ctx)
    assert any("93.0%" in ln and "低め" in ln for ln in lines)


def test_vitals_missing_data_skipped():
    ctx = {"biometrics": {}}
    lines = _build_vitals_section(ctx)
    assert lines == []


def test_vitals_no_baselines():
    ctx = {"biometrics": {"resting_hr": 62, "hrv_daily_rmssd": 42.0}}
    lines = _build_vitals_section(ctx)
    assert any("62 bpm" in ln for ln in lines)
    assert any("42.0 ms" in ln for ln in lines)


# ── Sleep section ──


def test_sleep_duration_sufficient():
    ctx = {
        "biometrics": {"sleep_duration_hours": 7.5},
        "baselines_60d": {"median_sleep_hours": 7.2},
    }
    lines = _build_sleep_section(ctx)
    assert any("十分" in ln for ln in lines)


def test_sleep_duration_short():
    ctx = {
        "biometrics": {"sleep_duration_hours": 5.5},
        "baselines_60d": {"median_sleep_hours": 7.2},
    }
    lines = _build_sleep_section(ctx)
    assert any("睡眠不足" in ln for ln in lines)


def test_sleep_deep_excellent():
    ctx = {"biometrics": {"deep_sleep_min": 95}}
    lines = _build_sleep_section(ctx)
    assert any("非常に良好" in ln for ln in lines)


def test_sleep_deep_insufficient():
    ctx = {"biometrics": {"deep_sleep_min": 25}}
    lines = _build_sleep_section(ctx)
    assert any("不足" in ln for ln in lines)


def test_sleep_efficiency_decimal():
    """sleep_efficiency as 0.92 should be normalized to 92%."""
    ctx = {"biometrics": {"sleep_efficiency": 0.92}}
    lines = _build_sleep_section(ctx)
    assert any("92%" in ln and "良好" in ln for ln in lines)


def test_sleep_efficiency_percentage():
    """sleep_efficiency as 92 should stay 92%."""
    ctx = {"biometrics": {"sleep_efficiency": 92}}
    lines = _build_sleep_section(ctx)
    assert any("92%" in ln and "良好" in ln for ln in lines)


def test_sleep_efficiency_low():
    ctx = {"biometrics": {"sleep_efficiency": 0.75}}
    lines = _build_sleep_section(ctx)
    assert any("改善" in ln for ln in lines)


def test_sleep_onset_good():
    ctx = {"biometrics": {"sleep_onset_latency_min": 8}}
    lines = _build_sleep_section(ctx)
    assert any("良好" in ln for ln in lines)


def test_sleep_onset_slow():
    ctx = {"biometrics": {"sleep_onset_latency_min": 45}}
    lines = _build_sleep_section(ctx)
    assert any("時間がかかっている" in ln for ln in lines)


# ── Activity section ──


def test_activity_steps_with_baseline():
    ctx = {
        "biometrics": {"steps": 10000},
        "baselines_60d": {"median_steps": 7500.0},
    }
    lines = _build_activity_section(ctx)
    assert any("10,000" in ln and "上回" in ln for ln in lines)


def test_activity_azm_met():
    ctx = {"biometrics": {"active_zone_minutes": 30}}
    lines = _build_activity_section(ctx)
    assert any("達成" in ln for ln in lines)


def test_activity_azm_not_met():
    ctx = {"biometrics": {"active_zone_minutes": 10}}
    lines = _build_activity_section(ctx)
    assert any("未達" in ln for ln in lines)


def test_activity_vo2max():
    ctx = {"biometrics": {"vo2max": 42.0}}
    lines = _build_activity_section(ctx)
    assert any("42.0" in ln for ln in lines)


# ── VRI section ──


def test_vri_good():
    ctx = {
        "vri": {
            "score": 75,
            "z_ln_rmssd": 1.2,
            "z_resting_hr": -0.3,
            "z_sleep_duration": 0.5,
            "z_deep_sleep": 0.8,
        }
    }
    lines = _build_vri_section(ctx)
    assert any("75/100" in ln and "良好" in ln for ln in lines)
    # HRV should be the dominant driver (z=1.2)
    assert any("HRV" in ln and "+1.2" in ln for ln in lines)


def test_vri_rest_recommended():
    ctx = {"vri": {"score": 40}}
    lines = _build_vri_section(ctx)
    assert any("休息推奨" in ln for ln in lines)


def test_vri_none_returns_empty():
    ctx = {}
    assert _build_vri_section(ctx) == []


# ── ML insights section ──


def test_ml_insights_no_anomaly():
    ctx = {"anomaly": {"is_anomaly": False}}
    lines = _build_ml_insights_section(ctx)
    assert any("異常なパターンは検出されていません" in ln for ln in lines)


def test_ml_insights_anomaly_detected():
    ctx = {"anomaly": {"is_anomaly": True, "explanation": "HRVが急落"}}
    lines = _build_ml_insights_section(ctx)
    assert any("異常パターンを検出" in ln and "HRVが急落" in ln for ln in lines)


def test_ml_insights_risk_signals_translated():
    ctx = {
        "condition_prediction": {
            "predicted_score": 65,
            "risk_signals": ["hrv_significant_drop", "sleep_deficit"],
        }
    }
    lines = _build_ml_insights_section(ctx)
    assert any("HRVの大幅な低下" in ln for ln in lines)
    assert any("睡眠不足" in ln for ln in lines)


def test_ml_insights_unknown_risk_signal_passthrough():
    ctx = {
        "condition_prediction": {
            "predicted_score": 60,
            "risk_signals": ["unknown_signal"],
        }
    }
    lines = _build_ml_insights_section(ctx)
    assert any("unknown_signal" in ln for ln in lines)


def test_ml_insights_divergence():
    ctx = {"divergence": {"explanation": "主観的体調が身体データより低い"}}
    lines = _build_ml_insights_section(ctx)
    assert any("主観的体調が身体データより低い" in ln for ln in lines)


# ── Subjective section ──


def test_subjective_with_tags():
    ctx = {
        "subjective_condition": {
            "overall_vas": 72,
            "tags": ["快眠", "運動不足"],
            "notes": None,
        }
    }
    lines = _build_subjective_section(ctx)
    assert any("72/100" in ln for ln in lines)
    assert any("快眠" in ln and "運動不足" in ln for ln in lines)


def test_subjective_none_returns_empty():
    assert _build_subjective_section({}) == []


def test_subjective_with_notes():
    ctx = {
        "subjective_condition": {
            "overall_vas": 50,
            "tags": [],
            "notes": "頭が重い",
        }
    }
    lines = _build_subjective_section(ctx)
    assert any("頭が重い" in ln for ln in lines)


# ── Outlook section ──


def test_outlook_above_baseline():
    ctx = {
        "hrv_prediction": {
            "predicted_zscore": 0.8,
            "direction": "above_baseline",
            "confidence": 72,
        }
    }
    lines = _build_outlook_section(ctx)
    assert any("上回る見込み" in ln for ln in lines)
    assert any("+0.8" in ln for ln in lines)


def test_outlook_below_baseline():
    ctx = {
        "hrv_prediction": {
            "predicted_zscore": -0.5,
            "direction": "below_baseline",
            "confidence": 65,
        }
    }
    lines = _build_outlook_section(ctx)
    assert any("下回る見込み" in ln for ln in lines)
    assert any("休息" in ln for ln in lines)


def test_outlook_none_returns_empty():
    assert _build_outlook_section({}) == []


# ── sleep_efficiency_pct helper ──


def test_sleep_efficiency_pct_decimal():
    assert _sleep_efficiency_pct(0.92) == 92.0


def test_sleep_efficiency_pct_percentage():
    assert _sleep_efficiency_pct(92.0) == 92.0


def test_sleep_efficiency_pct_none():
    assert _sleep_efficiency_pct(None) is None


# ── Full prompt builder ──


def test_build_user_prompt_full_context():
    ctx = {
        "date": "2026-02-18",
        "biometrics": {
            "resting_hr": 62,
            "hrv_daily_rmssd": 45.0,
            "hrv_deep_rmssd": 55.0,
            "spo2_avg": 97.0,
            "sleep_duration_hours": 7.0,
            "deep_sleep_min": 90,
            "rem_sleep_min": 80,
            "sleep_efficiency": 0.92,
            "sleep_onset_latency_min": 10,
            "steps": 8000,
            "active_zone_minutes": 30,
            "vo2max": 42.0,
        },
        "baselines_60d": {
            "median_resting_hr": 60.0,
            "median_hrv": 38.0,
            "median_sleep_hours": 7.2,
            "median_steps": 7500.0,
            "median_deep_sleep_min": 85.0,
        },
        "vri": {
            "score": 72,
            "z_ln_rmssd": 1.2,
            "z_resting_hr": -0.3,
            "z_sleep_duration": 0.5,
            "z_deep_sleep": 0.8,
        },
        "anomaly": {"is_anomaly": False},
        "subjective_condition": {
            "overall_vas": 72,
            "tags": ["快眠", "運動不足"],
            "notes": None,
        },
        "hrv_prediction": {
            "predicted_zscore": 0.8,
            "direction": "above_baseline",
            "confidence": 72,
        },
    }

    prompt = build_user_prompt(ctx)

    # Verify date
    assert "2026-02-18" in prompt

    # Verify all 7 sections appear
    assert "## 本日のバイタルサイン" in prompt
    assert "## 睡眠分析" in prompt
    assert "## 活動量" in prompt
    assert "## 回復指数 (VRI)" in prompt
    assert "## MLモデルの分析結果" in prompt
    assert "## 主観的な体調" in prompt
    assert "## 明日の見通し" in prompt

    # Verify footer
    assert "トーキングポイント" in prompt


def test_build_user_prompt_empty_context():
    """Empty biometrics should still produce a valid prompt with date."""
    ctx = {"date": "2026-02-18", "biometrics": {}}
    prompt = build_user_prompt(ctx)
    assert "2026-02-18" in prompt
    assert "トーキングポイント" in prompt
    # No sections should appear for empty data
    assert "## 本日のバイタルサイン" not in prompt


def test_build_user_prompt_partial_context():
    """Only sections with data should appear."""
    ctx = {
        "date": "2026-02-18",
        "biometrics": {"resting_hr": 62},
    }
    prompt = build_user_prompt(ctx)
    assert "## 本日のバイタルサイン" in prompt
    assert "## 睡眠分析" not in prompt
    assert "## 活動量" not in prompt
    assert "## 回復指数 (VRI)" not in prompt
