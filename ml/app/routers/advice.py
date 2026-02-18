"""Daily health advice generation via Ollama LLM."""

import datetime
import hashlib
import json
import logging
import re
import time

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.schemas.advice import AdviceResponse
from app.services.advice_prompt import build_user_prompt

logger = logging.getLogger(__name__)

router = APIRouter()

FETCH_CACHED_ADVICE_QUERY = """
SELECT date, advice_text, model_name, generation_ms, generated_at
FROM daily_advice WHERE date = $1::date
"""

UPSERT_ADVICE_QUERY = """
INSERT INTO daily_advice (date, advice_text, prompt_hash, model_name, generation_ms, context_summary)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (date) DO UPDATE SET
    advice_text=$2, prompt_hash=$3, model_name=$4, generation_ms=$5,
    context_summary=$6, generated_at=NOW()
"""

# ── Context collection queries ──

FETCH_DAILY_SUMMARY_QUERY = """
SELECT date, resting_hr, hrv_daily_rmssd, hrv_deep_rmssd, spo2_avg,
       sleep_duration_min,
       sleep_deep_min AS deep_sleep_min,
       sleep_rem_min AS rem_sleep_min,
       sleep_light_min AS light_sleep_min,
       sleep_minutes_asleep,
       sleep_onset_latency AS sleep_onset_latency_min,
       steps,
       active_zone_min AS active_zone_minutes,
       vo2_max AS vo2max
FROM daily_summaries WHERE date = $1::date
"""

FETCH_WEEKLY_SUMMARIES_QUERY = """
SELECT date, resting_hr, hrv_daily_rmssd, hrv_deep_rmssd, spo2_avg,
       sleep_duration_min,
       sleep_deep_min AS deep_sleep_min,
       sleep_rem_min AS rem_sleep_min,
       sleep_light_min AS light_sleep_min,
       sleep_minutes_asleep,
       steps,
       active_zone_min AS active_zone_minutes
FROM daily_summaries
WHERE date BETWEEN $1::date AND $2::date
ORDER BY date ASC
"""

FETCH_ROLLING_BASELINES_QUERY = """
SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resting_hr) AS median_resting_hr,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hrv_daily_rmssd) AS median_hrv,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sleep_duration_min) AS median_sleep_min,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY steps) AS median_steps,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sleep_deep_min) AS median_deep_sleep_min
FROM daily_summaries
WHERE date BETWEEN $1::date AND $2::date
"""

FETCH_VRI_QUERY = """
SELECT date, vri_score, vri_confidence,
       z_ln_rmssd, z_resting_hr, z_sleep_duration, z_deep_sleep
FROM vri_scores WHERE date = $1::date
"""

FETCH_ANOMALY_QUERY = """
SELECT date, anomaly_score, normalized_score, is_anomaly, explanation
FROM anomaly_detections WHERE date = $1::date
"""

FETCH_CONDITION_PREDICTION_QUERY = """
SELECT target_date, predicted_score, confidence, contributing_factors, risk_signals
FROM condition_predictions WHERE target_date = $1::date
ORDER BY predicted_at DESC LIMIT 1
"""

FETCH_CONDITION_LOG_QUERY = """
SELECT overall_vas, tags, note AS notes
FROM condition_logs
WHERE logged_at::date = $1::date
ORDER BY logged_at DESC LIMIT 1
"""

FETCH_DIVERGENCE_QUERY = """
SELECT date, divergence_type, residual, confidence, explanation
FROM divergence_detections WHERE date = $1::date
"""

FETCH_HRV_PREDICTION_QUERY = """
SELECT target_date, predicted_zscore AS predicted_hrv_zscore,
       predicted_direction, confidence
FROM hrv_predictions WHERE date = $1::date
ORDER BY computed_at DESC LIMIT 1
"""


async def _collect_health_context(pool, date: datetime.date) -> dict | None:
    """Collect all health context for the given date."""
    async with pool.acquire() as conn:
        summary = await conn.fetchrow(FETCH_DAILY_SUMMARY_QUERY, date)

    if summary is None:
        return None

    week_start = date - datetime.timedelta(days=6)
    baseline_start = date - datetime.timedelta(days=60)

    async with pool.acquire() as conn:
        weekly = await conn.fetch(FETCH_WEEKLY_SUMMARIES_QUERY, week_start, date)
        baselines = await conn.fetchrow(FETCH_ROLLING_BASELINES_QUERY, baseline_start, date)
        vri = await conn.fetchrow(FETCH_VRI_QUERY, date)
        anomaly = await conn.fetchrow(FETCH_ANOMALY_QUERY, date)
        prediction = await conn.fetchrow(FETCH_CONDITION_PREDICTION_QUERY, date)
        condition = await conn.fetchrow(FETCH_CONDITION_LOG_QUERY, date)
        divergence = await conn.fetchrow(FETCH_DIVERGENCE_QUERY, date)
        hrv_pred = await conn.fetchrow(FETCH_HRV_PREDICTION_QUERY, date)

    ctx: dict = {"date": str(date)}

    # Today's biometrics
    sleep_dur = summary["sleep_duration_min"]
    sleep_asleep = summary["sleep_minutes_asleep"]
    sleep_efficiency = (
        round(sleep_asleep / sleep_dur, 4)
        if sleep_dur and sleep_asleep
        else None
    )

    ctx["biometrics"] = {
        "resting_hr": summary["resting_hr"],
        "hrv_daily_rmssd": summary["hrv_daily_rmssd"],
        "hrv_deep_rmssd": summary["hrv_deep_rmssd"],
        "spo2_avg": summary["spo2_avg"],
        "sleep_duration_hours": round(sleep_dur / 60, 1)
        if sleep_dur
        else None,
        "deep_sleep_min": summary["deep_sleep_min"],
        "rem_sleep_min": summary["rem_sleep_min"],
        "light_sleep_min": summary["light_sleep_min"],
        "sleep_efficiency": sleep_efficiency,
        "sleep_onset_latency_min": summary["sleep_onset_latency_min"],
        "steps": summary["steps"],
        "active_zone_minutes": summary["active_zone_minutes"],
        "vo2max": summary["vo2max"],
    }

    # Baselines (60-day median)
    if baselines:
        ctx["baselines_60d"] = {
            "median_resting_hr": _to_float(baselines["median_resting_hr"]),
            "median_hrv": _to_float(baselines["median_hrv"]),
            "median_sleep_hours": round(baselines["median_sleep_min"] / 60, 1)
            if baselines["median_sleep_min"]
            else None,
            "median_steps": _to_float(baselines["median_steps"]),
            "median_deep_sleep_min": _to_float(baselines["median_deep_sleep_min"]),
        }

    # Weekly trend
    if weekly:
        ctx["weekly_trend"] = {
            "days": len(weekly),
            "avg_resting_hr": _avg([r["resting_hr"] for r in weekly]),
            "avg_hrv": _avg([r["hrv_daily_rmssd"] for r in weekly]),
            "avg_sleep_hours": _avg(
                [r["sleep_duration_min"] / 60 for r in weekly if r["sleep_duration_min"]]
            ),
            "avg_steps": _avg([r["steps"] for r in weekly]),
            "avg_deep_sleep_min": _avg([r["deep_sleep_min"] for r in weekly]),
        }

    # VRI
    if vri:
        ctx["vri"] = {
            "score": vri["vri_score"],
            "confidence": vri["vri_confidence"],
            "z_ln_rmssd": vri["z_ln_rmssd"],
            "z_resting_hr": vri["z_resting_hr"],
            "z_sleep_duration": vri["z_sleep_duration"],
            "z_deep_sleep": vri["z_deep_sleep"],
        }

    # Anomaly
    if anomaly:
        ctx["anomaly"] = {
            "is_anomaly": anomaly["is_anomaly"],
            "normalized_score": anomaly["normalized_score"],
            "explanation": anomaly["explanation"],
        }

    # Condition prediction
    if prediction:
        factors = prediction["contributing_factors"]
        if isinstance(factors, str):
            factors = json.loads(factors)
        risk_signals = prediction["risk_signals"]
        if isinstance(risk_signals, str):
            risk_signals = json.loads(risk_signals)
        ctx["condition_prediction"] = {
            "predicted_score": prediction["predicted_score"],
            "confidence": prediction["confidence"],
            "contributing_factors": factors,
            "risk_signals": risk_signals,
        }

    # Subjective condition
    if condition:
        tags = condition["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        ctx["subjective_condition"] = {
            "overall_vas": condition["overall_vas"],
            "tags": tags,
            "notes": condition["notes"],
        }

    # Divergence
    if divergence:
        ctx["divergence"] = {
            "type": divergence["divergence_type"],
            "residual": divergence["residual"],
            "confidence": divergence["confidence"],
            "explanation": divergence["explanation"],
        }

    # HRV prediction
    if hrv_pred:
        ctx["hrv_prediction"] = {
            "target_date": str(hrv_pred["target_date"]),
            "predicted_zscore": hrv_pred["predicted_hrv_zscore"],
            "direction": hrv_pred["predicted_direction"],
            "confidence": hrv_pred["confidence"],
        }

    return ctx


def _to_float(val) -> float | None:
    if val is None:
        return None
    return round(float(val), 2)


def _avg(values: list) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


SYSTEM_PROMPT = """\
あなたは「VitaMetron」のパーソナルヘルスアドバイザーです。
ユーザーのバイオメトリクスデータとMLモデルの分析結果をもとに、日本語で「今日の一言」ヘルスアドバイスを生成してください。

## 出力フォーマット
1. 挨拶（おはようございます/お疲れさまです など）
2. 【本日のハイライト】数値を引用して、最も顕著な1〜2点を述べる
3. 【詳細分析】ポジティブな面と注意点をバランスよく述べる（それぞれ1〜2項目）
4. 【今日のアクション】具体的で実行可能な提案を1〜2個
5. 締めの一言（前向きなメッセージ）

## 文字数
500〜1000文字（改行含む）。この範囲に収めてください。

## 必須ルール
- 具体的な数値データを引用すること（例: 「HRVは42msでベースライン38msを上回っています」）
- ベースラインや週間平均との比較を行うこと
- ポジティブな面を先に述べ、改善点は建設的に述べる
- 医学的な診断・病名は絶対に述べない（例: ×「不整脈の疑い」→ ○「心拍の変動が普段より大きめです」）
- 断定を避け、「〜のようです」「〜かもしれません」などの柔らかい表現を使う
- 絵文字は使わない
- 改行を適度に入れて読みやすくする
- 見出しの記号（【】）を使って構造化する

## 指標の解釈ガイド
- VRIスコア: 70以上=回復良好, 50〜70=普通, 50未満=休息推奨
- HRV (RMSSD): ベースラインより高い=自律神経バランス良好, 低い=疲労/ストレス
- 安静時心拍: ベースラインより低い=良好な回復, 高い=ストレス/疲労の可能性
- 睡眠時間: 7〜9時間が理想的
- 深い睡眠: 60分以上が理想的（身体の回復に重要）
- REM睡眠: 認知機能と感情処理に重要
- 睡眠効率: 85%以上=良好, 80%未満=課題あり
- 入眠潜時: 30分以上=入眠困難の可能性
- SpO2: 95〜100%が正常

## 注意
提供されていないデータについては言及しないでください。
ユーザーから提供された「トーキングポイント」に沿って助言を構成してください。\
"""

# ── Postprocessing ──

_EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\U00002600-\U000026ff"
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0000200d"  # ZWJ
    "]+",
    flags=re.UNICODE,
)

_MEDICAL_REPLACEMENTS: list[tuple[str, str]] = [
    ("受診してください", "専門家にご相談ください"),
    ("受診をお勧め", "専門家への相談をお勧め"),
    ("病院に行", "専門家にご相談"),
    ("医師に相談", "専門家にご相談"),
]

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")


def _postprocess_advice(text: str) -> tuple[str, list[str]]:
    """Clean up LLM output: remove fences, emoji, medical terms; check length."""
    warnings: list[str] = []

    # Remove code fences
    text = _CODE_FENCE_RE.sub("", text)

    # Remove emoji
    text = _EMOJI_RE.sub("", text)

    # Medical term replacements
    for old, new in _MEDICAL_REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
            warnings.append(f"medical_term_replaced: {old}")

    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # Length check
    length = len(text)
    if length > 1200:
        # Truncate at last sentence boundary within limit
        truncated = text[:1200]
        last_period = truncated.rfind("。")
        if last_period > 400:
            text = truncated[: last_period + 1]
        else:
            text = truncated
        warnings.append(f"truncated: {length} -> {len(text)}")
    elif length < 400:
        warnings.append(f"short_output: {length} chars")

    # Greeting check (log only)
    first_line = text.split("\n")[0] if text else ""
    greetings = ("おはよう", "お疲れ", "こんにちは", "こんばんは")
    if not any(g in first_line for g in greetings):
        warnings.append("missing_greeting")

    return text, warnings


def _build_prompt(context: dict) -> tuple[str, str]:
    """Build system + user prompts from health context."""
    user_content = build_user_prompt(context)
    return SYSTEM_PROMPT, user_content


async def _call_ollama(
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> tuple[str, int]:
    """Call Ollama /api/chat and return (response_text, generation_ms)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 1024,
        },
    }

    start = time.monotonic()
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        resp = await client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    data = resp.json()
    return data.get("message", {}).get("content", "").strip(), elapsed_ms


async def _generate_advice(
    pool, settings, date: datetime.date
) -> AdviceResponse:
    """Generate advice for a date: collect context → build prompt → call LLM → persist."""
    context = await _collect_health_context(pool, date)
    if context is None:
        return AdviceResponse(
            date=str(date),
            advice_text="本日のデータがまだ不十分です。データが揃い次第アドバイスを生成します。",
            model_name=settings.ollama_model,
        )

    system_prompt, user_prompt = _build_prompt(context)
    prompt_hash = hashlib.sha256(
        (system_prompt + user_prompt).encode()
    ).hexdigest()[:16]

    advice_text, generation_ms = await _call_ollama(
        settings.ollama_base_url,
        settings.ollama_model,
        system_prompt,
        user_prompt,
        settings.ollama_timeout,
    )

    advice_text, pp_warnings = _postprocess_advice(advice_text)
    if pp_warnings:
        logger.warning(
            "Advice post-processing warnings for %s: %s", date, pp_warnings
        )

    # Persist to DB
    async with pool.acquire() as conn:
        await conn.execute(
            UPSERT_ADVICE_QUERY,
            date,
            advice_text,
            prompt_hash,
            settings.ollama_model,
            generation_ms,
            json.dumps(context, ensure_ascii=False),
        )

    return AdviceResponse(
        date=str(date),
        advice_text=advice_text,
        model_name=settings.ollama_model,
        generation_ms=generation_ms,
        cached=False,
    )


@router.get("/advice", response_model=AdviceResponse)
async def get_advice(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    settings = request.app.state.settings

    # Check cache first
    async with pool.acquire() as conn:
        row = await conn.fetchrow(FETCH_CACHED_ADVICE_QUERY, date)

    if row is not None:
        return AdviceResponse(
            date=str(row["date"]),
            advice_text=row["advice_text"],
            model_name=row["model_name"],
            generation_ms=row["generation_ms"],
            cached=True,
        )

    # Generate fresh
    try:
        return await _generate_advice(pool, settings, date)
    except httpx.HTTPError as e:
        logger.error("Ollama API error: %s", e)
        return JSONResponse(
            status_code=503,
            content={"detail": "LLM service unavailable. Please try again later."},
        )


@router.post("/advice/regenerate", response_model=AdviceResponse)
async def regenerate_advice(
    request: Request,
    date: datetime.date = Query(..., description="Target date (YYYY-MM-DD)"),
):
    pool = request.app.state.db_pool
    settings = request.app.state.settings

    try:
        return await _generate_advice(pool, settings, date)
    except httpx.HTTPError as e:
        logger.error("Ollama API error: %s", e)
        return JSONResponse(
            status_code=503,
            content={"detail": "LLM service unavailable. Please try again later."},
        )
