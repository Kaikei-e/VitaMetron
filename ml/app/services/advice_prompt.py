"""Structured prompt builder for daily health advice.

Converts the health context dict into Japanese talking points
so the 4B quantized LLM receives pre-interpreted, natural-language input
instead of raw JSON.
"""

from __future__ import annotations

# ── Risk signal translations ──

_RISK_SIGNAL_JA: dict[str, str] = {
    "hrv_significant_drop": "HRVの大幅な低下",
    "resting_hr_elevated": "安静時心拍の上昇",
    "sleep_deficit": "睡眠不足",
    "deep_sleep_deficit": "深い睡眠の不足",
    "spo2_low": "SpO2の低下",
    "activity_drop": "活動量の減少",
    "hrv_declining_trend": "HRVの低下傾向",
    "sleep_efficiency_low": "睡眠効率の低下",
    "high_onset_latency": "入眠困難",
    "rem_deficit": "REM睡眠の不足",
    "condition_decline": "体調の低下傾向",
}


def _pct_diff(current: float, baseline: float) -> str:
    """Return a Japanese description of percentage difference from baseline."""
    diff = current - baseline
    pct = abs(diff / baseline) * 100 if baseline else 0
    if abs(diff) < 0.5 and pct < 2:
        return f"{current:.1f}（ベースライン {baseline:.1f} とほぼ同等）"
    if diff > 0:
        return f"{current:.1f}（ベースライン {baseline:.1f} を {pct:.0f}% 上回っている）"
    return f"{current:.1f}（ベースライン {baseline:.1f} を {pct:.0f}% 下回っている）"


def _fmt_int_diff(current: int, baseline: float) -> str:
    """Return comparison string for integer metrics."""
    diff = current - baseline
    pct = abs(diff / baseline) * 100 if baseline else 0
    if pct < 5:
        return f"{current:,}（ベースライン {baseline:,.0f} とほぼ同等）"
    if diff > 0:
        return f"{current:,}（ベースライン {baseline:,.0f} を {pct:.0f}% 上回っている）"
    return f"{current:,}（ベースライン {baseline:,.0f} を {pct:.0f}% 下回っている）"


def _sleep_efficiency_pct(val: float | None) -> float | None:
    """Normalize sleep efficiency to percentage (handle both 0-1 and 0-100)."""
    if val is None:
        return None
    if val <= 1.0:
        return val * 100
    return val


# ── Section builders ──


def _build_vitals_section(ctx: dict) -> list[str]:
    """Build vitals section: RHR, HRV, HRV Deep, SpO2."""
    bio = ctx.get("biometrics", {})
    baselines = ctx.get("baselines_60d", {})
    lines: list[str] = []

    rhr = bio.get("resting_hr")
    if rhr is not None:
        bl = baselines.get("median_resting_hr")
        if bl is not None:
            diff = rhr - bl
            direction = "高め" if diff > 0 else "低め"
            lines.append(
                f"安静時心拍: {rhr} bpm"
                f"（ベースライン {bl:.0f} bpm より {abs(diff):.0f} bpm {direction}）"
            )
        else:
            lines.append(f"安静時心拍: {rhr} bpm")

    hrv = bio.get("hrv_daily_rmssd")
    if hrv is not None:
        bl = baselines.get("median_hrv")
        if bl is not None:
            lines.append(f"HRV (RMSSD): {_pct_diff(hrv, bl)} ms")
        else:
            lines.append(f"HRV (RMSSD): {hrv:.1f} ms")

    hrv_deep = bio.get("hrv_deep_rmssd")
    if hrv_deep is not None:
        if hrv is not None and hrv_deep > hrv:
            lines.append(
                f"深い睡眠中のHRV: {hrv_deep:.1f} ms"
                f"（日中より高く、副交感神経の回復が良好）"
            )
        else:
            lines.append(f"深い睡眠中のHRV: {hrv_deep:.1f} ms")

    spo2 = bio.get("spo2_avg")
    if spo2 is not None:
        if spo2 >= 95:
            lines.append(f"SpO2: {spo2:.1f}%（良好）")
        else:
            lines.append(f"SpO2: {spo2:.1f}%（やや低め、注意）")

    return lines


def _build_sleep_section(ctx: dict) -> list[str]:
    """Build sleep section: duration, deep, REM, efficiency, onset latency."""
    bio = ctx.get("biometrics", {})
    baselines = ctx.get("baselines_60d", {})
    lines: list[str] = []

    duration = bio.get("sleep_duration_hours")
    if duration is not None:
        bl = baselines.get("median_sleep_hours")
        if bl is not None:
            diff = abs(duration - bl)
            if diff < 0.3:
                label = f"{duration:.1f} 時間（ベースライン {bl:.1f} 時間とほぼ同等）"
            elif duration > bl:
                label = f"{duration:.1f} 時間（ベースライン {bl:.1f} 時間を上回る）"
            else:
                label = f"{duration:.1f} 時間（ベースライン {bl:.1f} 時間を下回る）"
            if duration >= 7:
                label += " → 十分な睡眠時間"
            elif duration >= 6:
                label += " → やや短め"
            else:
                label += " → 睡眠不足"
            lines.append(f"睡眠時間: {label}")
        else:
            lines.append(f"睡眠時間: {duration:.1f} 時間")

    deep = bio.get("deep_sleep_min")
    if deep is not None:
        if deep >= 90:
            lines.append(f"深い睡眠: {deep} 分（非常に良好な深い睡眠）")
        elif deep >= 60:
            lines.append(f"深い睡眠: {deep} 分（十分）")
        elif deep >= 30:
            lines.append(f"深い睡眠: {deep} 分（やや少なめ）")
        else:
            lines.append(f"深い睡眠: {deep} 分（不足気味）")

    rem = bio.get("rem_sleep_min")
    if rem is not None:
        if rem >= 60:
            lines.append(f"REM睡眠: {rem} 分（十分）")
        elif rem >= 30:
            lines.append(f"REM睡眠: {rem} 分（やや少なめ）")
        else:
            lines.append(f"REM睡眠: {rem} 分（不足気味）")

    eff = _sleep_efficiency_pct(bio.get("sleep_efficiency"))
    if eff is not None:
        if eff >= 85:
            lines.append(f"睡眠効率: {eff:.0f}%（良好）")
        elif eff >= 80:
            lines.append(f"睡眠効率: {eff:.0f}%（普通）")
        else:
            lines.append(f"睡眠効率: {eff:.0f}%（改善の余地あり）")

    latency = bio.get("sleep_onset_latency_min")
    if latency is not None:
        if latency <= 15:
            lines.append(f"入眠潜時: {latency} 分（良好）")
        elif latency <= 30:
            lines.append(f"入眠潜時: {latency} 分（普通）")
        else:
            lines.append(f"入眠潜時: {latency} 分（入眠に時間がかかっている）")

    return lines


def _build_activity_section(ctx: dict) -> list[str]:
    """Build activity section: steps, AZM, VO2Max."""
    bio = ctx.get("biometrics", {})
    baselines = ctx.get("baselines_60d", {})
    lines: list[str] = []

    steps = bio.get("steps")
    if steps is not None:
        bl = baselines.get("median_steps")
        if bl is not None:
            lines.append(f"歩数: {_fmt_int_diff(steps, bl)} 歩")
        else:
            lines.append(f"歩数: {steps:,} 歩")

    azm = bio.get("active_zone_minutes")
    if azm is not None:
        if azm >= 22:
            lines.append(
                f"アクティブゾーン分: {azm} 分（WHO推奨の日あたり目安を達成）"
            )
        else:
            lines.append(
                f"アクティブゾーン分: {azm} 分（WHO推奨の日あたり目安に未達）"
            )

    vo2max = bio.get("vo2max")
    if vo2max is not None:
        lines.append(f"VO2Max: {vo2max:.1f} ml/kg/min")

    return lines


def _build_vri_section(ctx: dict) -> list[str]:
    """Build VRI section: score + z-score drivers."""
    vri = ctx.get("vri")
    if vri is None:
        return []

    lines: list[str] = []
    score = vri.get("score")
    if score is None:
        return []

    if score >= 70:
        level = "良好"
    elif score >= 50:
        level = "普通"
    else:
        level = "休息推奨"
    lines.append(f"VRIスコア: {score}/100（{level}）")

    # Find the dominant z-score driver
    z_keys = {
        "z_ln_rmssd": "HRV",
        "z_resting_hr": "安静時心拍",
        "z_sleep_duration": "睡眠時間",
        "z_deep_sleep": "深い睡眠",
    }
    best_key, best_abs = None, 0.0
    for key, _label in z_keys.items():
        val = vri.get(key)
        if val is not None and abs(val) > best_abs:
            best_key = key
            best_abs = abs(val)

    if best_key is not None:
        val = vri[best_key]
        label = z_keys[best_key]
        direction = "プラス" if val > 0 else "マイナス"
        lines.append(
            f"スコアの主要因: {label}が{direction}方向に影響 (z={val:+.1f})"
        )

    return lines


def _build_ml_insights_section(ctx: dict) -> list[str]:
    """Build ML insights section: anomaly, condition prediction, risk signals, divergence."""
    lines: list[str] = []

    # Anomaly
    anomaly = ctx.get("anomaly")
    if anomaly is not None:
        if anomaly.get("is_anomaly"):
            explanation = anomaly.get("explanation", "")
            lines.append(f"異常検知: 異常パターンを検出（{explanation}）")
        else:
            lines.append("異常検知: 特に異常なパターンは検出されていません")

    # Condition prediction
    pred = ctx.get("condition_prediction")
    if pred is not None:
        score = pred.get("predicted_score")
        if score is not None:
            if score >= 70:
                level = "良好"
            elif score >= 50:
                level = "普通"
            else:
                level = "注意"
            lines.append(f"コンディション予測: {score}/100（{level}）")

        # Risk signals
        risk_signals = pred.get("risk_signals")
        if risk_signals:
            ja_signals = [
                _RISK_SIGNAL_JA.get(s, s) for s in risk_signals
            ]
            lines.append(f"リスクシグナル: {', '.join(ja_signals)}")

    # Divergence
    div = ctx.get("divergence")
    if div is not None:
        explanation = div.get("explanation", "")
        if explanation:
            lines.append(f"体調乖離: {explanation}")
        else:
            lines.append("体調乖離: 主観的体調と身体データが一致しています")

    return lines


def _build_subjective_section(ctx: dict) -> list[str]:
    """Build subjective condition section: VAS, tags, notes."""
    subj = ctx.get("subjective_condition")
    if subj is None:
        return []

    lines: list[str] = []

    vas = subj.get("overall_vas")
    if vas is not None:
        if vas >= 70:
            level = "良好"
        elif vas >= 50:
            level = "普通"
        else:
            level = "不調"
        lines.append(f"自己評価スコア: {vas}/100（{level}）")

    tags = subj.get("tags")
    if tags:
        lines.append(f"自覚症状タグ: {', '.join(tags)}")

    notes = subj.get("notes")
    if notes:
        lines.append(f"メモ: {notes}")

    return lines


def _build_outlook_section(ctx: dict) -> list[str]:
    """Build outlook section: HRV prediction."""
    hrv_pred = ctx.get("hrv_prediction")
    if hrv_pred is None:
        return []

    lines: list[str] = []
    zscore = hrv_pred.get("predicted_zscore")
    direction = hrv_pred.get("direction")
    confidence = hrv_pred.get("confidence")

    if zscore is not None and direction is not None:
        if direction == "above_baseline":
            dir_ja = "ベースラインを上回る見込み"
            outlook = "良好な回復が期待できます"
        elif direction == "below_baseline":
            dir_ja = "ベースラインを下回る見込み"
            outlook = "休息を意識すると良いかもしれません"
        else:
            dir_ja = "ベースライン付近の見込み"
            outlook = "安定した状態が続きそうです"

        conf_str = f"信頼度{confidence:.0f}%" if confidence is not None else ""
        parts = [f"z={zscore:+.1f}"]
        if conf_str:
            parts.append(conf_str)
        lines.append(
            f"明日のHRV予測: {dir_ja}（{'、'.join(parts)}）→ {outlook}"
        )

    return lines


# ── Main entry point ──


def build_user_prompt(ctx: dict) -> str:
    """Build the full user prompt from the health context dict.

    Each section is conditionally included only when data is available.
    """
    parts: list[str] = []

    date_str = ctx.get("date", "")
    parts.append(f"日付: {date_str}")

    sections: list[tuple[str, list[str]]] = [
        ("本日のバイタルサイン", _build_vitals_section(ctx)),
        ("睡眠分析", _build_sleep_section(ctx)),
        ("活動量", _build_activity_section(ctx)),
        ("回復指数 (VRI)", _build_vri_section(ctx)),
        ("MLモデルの分析結果", _build_ml_insights_section(ctx)),
        ("主観的な体調", _build_subjective_section(ctx)),
        ("明日の見通し", _build_outlook_section(ctx)),
    ]

    for title, lines in sections:
        if lines:
            section = f"\n## {title}\n" + "\n".join(f"- {ln}" for ln in lines)
            parts.append(section)

    parts.append(
        "\n以上のトーキングポイントに基づいて、「今日の一言」アドバイスを生成してください。"
    )

    return "\n".join(parts)
