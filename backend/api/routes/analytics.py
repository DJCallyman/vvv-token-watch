"""
Analytics API routes for model usage and performance metrics.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.venice_api_client import VeniceAPIClient
from backend.config import get_settings, Settings
from backend.core.billing_pagination import (
    BillingUsageDeprecated,
    fetch_usage_analytics_optional,
)
from backend.core.cache import TtlCache
from backend.core.billing_sync import sync_billing_entries, load_billing_entries
from backend.database import AsyncSessionLocal
from backend.models.schemas import (
    AnalyticsResponse,
    DailyAnalyticsResponse,
    DailyUsage,
    ModelAnalytics,
    ModelBreakdown,
    ModelRecommendation,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Single-flight lock so concurrent /models and /daily requests share one sync.
# The sync fetches only new entries since the last sync (typically 0–1 pages).
_sync_lock = asyncio.Lock()

# Short-lived cache of the sync result so a rapid burst of requests
# (e.g. /models + /daily fired together) doesn't each hit the DB.
_sync_cache = TtlCache(max_size=4)
_SYNC_CACHE_TTL = 30.0  # seconds


def _analytics_window(days: int) -> tuple[datetime, datetime]:
    """Analytics window for the given number of days."""
    end = datetime.now(timezone.utc)
    return end - timedelta(days=days), end


async def get_billing_entries_from_db(
    client: VeniceAPIClient,
    days: int,
) -> tuple[List[Dict[str, Any]], str]:
    """Sync new billing entries to the DB, then load the window from the DB.

    Returns (entries, source). The sync fetches only entries newer than the
    newest stored timestamp, so after the initial load this is near-instant.
    Both /models and /daily share the same sync via the single-flight lock.
    The sync is global (not per-days) — it always fetches new entries since
    the last sync, regardless of which time window the caller wants.
    """
    # The sync cache is global — once synced, any days window loads from DB
    cache_key = "sync:global"
    cached = _sync_cache.get(cache_key)
    if cached is not None:
        # Sync was done recently, just load from DB
        start, end = _analytics_window(days)
        async with AsyncSessionLocal() as session:
            entries = await load_billing_entries(session, start, end)
        return entries, 'billing-db'

    async with _sync_lock:
        # Re-check after acquiring the lock
        cached = _sync_cache.get(cache_key)
        if cached is not None:
            start, end = _analytics_window(days)
            async with AsyncSessionLocal() as session:
                entries = await load_billing_entries(session, start, end)
            return entries, 'billing-db'

        # Sync new entries from the Venice API to the database
        async with AsyncSessionLocal() as session:
            new_count = await sync_billing_entries(session, client)

        # Mark sync as done so subsequent requests skip the API
        _sync_cache.set(cache_key, True, ttl=_SYNC_CACHE_TTL)

        # Load the requested window from the database
        start, end = _analytics_window(days)
        async with AsyncSessionLocal() as session:
            entries = await load_billing_entries(session, start, end)

        logger.info(
            "Analytics: synced %d new entries, loaded %d from DB for %d-day window",
            new_count, len(entries), days,
        )

        _sync_cache.set(cache_key, entries, ttl=_SYNC_CACHE_TTL)
        return entries, 'billing-db'


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


def detect_model_type(sku: str) -> str:
    """Detect the model type (llm, image, video, music, embedding, other) from SKU."""
    s = sku.lower()

    if s == 'credit-purchase':
        return 'other'

    # Video: e.g. grok-imagine-text-to-video-*, kling-v3-pro-text-to-video-*
    if 'text-to-video' in s:
        return 'video'

    # Music: elevenlabs-music-*, minimax-music-*, stable-audio-*, ace-step-*
    if any(kw in s for kw in ('music', 'stable-audio', 'ace-step')):
        return 'music'

    # Embedding: text-embedding-bge-m3-llm-*-mtoken (check before llm)
    if 'embedding' in s:
        return 'embedding'

    # Image: *-image-unit, *-fixed-*img, *-edit-fixed-*
    if re.search(r'-image-unit|-fixed-.*img|-edit-fixed-', s):
        return 'image'

    # LLM: *-llm-{input|output|cache-*}-mtoken
    if '-llm-' in s:
        return 'llm'

    # Audio (speech/TTS if Venice ever adds them)
    if 'audio' in s or 'speech' in s or 'tts' in s:
        return 'audio'

    return 'other'


def clean_model_name(sku: str) -> str:
    """Extract clean model name from SKU.

    Handles all known Venice billing SKU patterns:
      LLM:       {model}-llm-{extended-}?{cache-write-5m|cache-write|cache-input|input|output}-mtoken
      Image:     {model}-image-unit | {model}-{edit-}?fixed-{1K-}?{websearch-}?1img
      Video:     {model}-text-to-video-duration-{rate|resolution}-*
      Music:     elevenlabs-music-duration-based-*, minimax-music-v2-fixed,
                 ace-step-*-duration-based-*, stable-audio-*-fixed-*
      Embedding: text-embedding-*-llm-{input|output}-mtoken
      Other:     credit-purchase
    """
    s = sku.lower()

    if s == 'credit-purchase':
        return 'credit-purchase'

    # --- Video: {model}-text-to-video-* ---
    m = re.match(r'^(.+?)-text-to-video-', s)
    if m:
        return m.group(1)

    # --- Music (checked before generic -fixed- to avoid false matches) ---
    # elevenlabs-music-duration-based-{60s|120s|240s}
    m = re.match(r'^(elevenlabs-music)-duration-based-', s)
    if m:
        return m.group(1)
    # minimax-music-v2-fixed
    m = re.match(r'^(minimax-music-v2)-fixed', s)
    if m:
        return m.group(1)
    # ace-step-15-duration-based-*
    m = re.match(r'^(ace-step-[\d.]+)-duration-based-', s)
    if m:
        return m.group(1)
    # stable-audio-25-fixed-*
    m = re.match(r'^(stable-audio-[\d.]+)-fixed-', s)
    if m:
        return m.group(1)

    # --- Embedding: text-embedding-{name}-llm-{input|output}-mtoken ---
    m = re.match(r'^(text-embedding-.+?)-llm-(?:input|output)-mtoken', s)
    if m:
        return m.group(1)

    # --- LLM: {model}-llm-{extended-}?{variant}-mtoken ---
    m = re.match(
        r'^(.+?)-llm-(?:extended-)?(?:cache-write(?:-5m)?|cache-input|input|output)-mtoken',
        s,
    )
    if m:
        return m.group(1)

    # --- Image: {model}-image-unit ---
    m = re.match(r'^(.+?)-image-unit', s)
    if m:
        return m.group(1)

    # --- Image edit: {model}-edit-fixed-* ---
    m = re.match(r'^(.+?)-edit-fixed-', s)
    if m:
        return m.group(1)

    # --- Image fixed: {model}-fixed-{1K-}?{websearch-}?{N}img ---
    m = re.match(r'^(.+?)-fixed-(?:\d+[Kk]-)?(?:websearch-)?\d*img', s)
    if m:
        return m.group(1)

    # Fallback: return as-is
    return s


def process_usage_data(usage_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process raw billing usage data into analytics format.

    BUG-05: Track cost_usd and cost_diem separately based on entry['currency'].
    Do NOT mix currencies 1:1. 'cost' is retained (sum of absolute amounts) for
    backward compat but is a mixed unit; prefer the separated fields.
    """
    model_data: Dict[str, Dict] = {}
    request_tracker: Dict[str, set] = {}

    logger.info(f"Processing {len(usage_entries)} usage entries")

    for entry in usage_entries:
        sku = entry.get('sku', 'unknown')
        amount = entry.get('amount', 0)
        currency = (entry.get('currency') or '').upper()
        inference = entry.get('inferenceDetails') or {}

        abs_amount = abs(amount)
        if abs_amount == 0:
            continue

        model_name = clean_model_name(sku)
        model_type = detect_model_type(sku)
        logger.debug(f"SKU: {sku} -> Model: {model_name}, Type: {model_type}, Amount: {abs_amount}, Currency: {currency}")

        if model_name not in model_data:
            model_data[model_name] = {
                'requests': 0,
                'tokens': 0,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'cost': 0.0,          # legacy mixed; prefer cost_usd + cost_diem
                'cost_usd': 0.0,
                'cost_diem': 0.0,
                'cost_bundled_credits': 0.0,
                'response_times': [],
                'model_type': model_type,
            }
            request_tracker[model_name] = set()

        request_id = None
        if isinstance(inference, dict):
            request_id = inference.get('requestId') or None

        is_new_request = request_id and request_id not in request_tracker[model_name]
        if is_new_request:
            request_tracker[model_name].add(request_id)
            model_data[model_name]['requests'] += 1
        elif not request_id:
            model_data[model_name]['requests'] += 1

        if isinstance(inference, dict):
            prompt_tokens = inference.get('promptTokens') or 0
            completion_tokens = inference.get('completionTokens') or 0
            model_data[model_name]['prompt_tokens'] += prompt_tokens
            model_data[model_name]['completion_tokens'] += completion_tokens
            model_data[model_name]['tokens'] += prompt_tokens + completion_tokens

            if is_new_request:
                exec_time = inference.get('inferenceExecutionTime')
                if exec_time:
                    model_data[model_name]['response_times'].append(exec_time)

        # Separate by currency (BUG-05). Use abs for "cost" semantics.
        model_data[model_name]['cost'] += abs_amount
        if currency == 'USD':
            model_data[model_name]['cost_usd'] += abs_amount
        elif currency == 'DIEM':
            model_data[model_name]['cost_diem'] += abs_amount
        elif currency in ('BUNDLED_CREDITS', 'VCU'):
            # Track bundled/legacy credits separately — do not mix into diem.
            model_data[model_name]['cost_bundled_credits'] += abs_amount
        else:
            # Unknown/other currencies contribute to legacy 'cost' only
            pass

    logger.info(f"Found {len(model_data)} models with data")

    for model_name, data in model_data.items():
        times = data['response_times']
        data['avg_response_time_ms'] = sum(times) / len(times) if times else 0.0
        del data['response_times']

    return model_data


def generate_recommendations(model_data: Dict[str, Dict]) -> List[Dict[str, str]]:
    """Generate actionable recommendations based on usage patterns.

    Uses the per-currency cost buckets (``cost_usd`` / ``cost_diem``) so the
    ranking and message text never mix currencies. The legacy mixed ``cost``
    field is still present in payloads (backward compat) but is no longer
    authoritative for these recommendations.
    """
    recommendations: List[Dict[str, str]] = []

    if not model_data:
        return recommendations

    # Prefer USD for ranking and labels when present, otherwise fall back to
    # DIEM (with a '$'→'DIEM' label switch). The currency is described in the
    # message itself so there is no hidden currency conversion.
    def primary_currency(data: Dict[str, Any]) -> str:
        return 'usd' if float(data.get('cost_usd') or 0.0) > 0 else 'diem'

    def cost_per_1k(data: Dict[str, Any]) -> float:
        tokens = data.get('tokens') or 0
        if tokens <= 0:
            return 0.0
        cur = primary_currency(data)
        amount = float(data.get('cost_usd') or 0.0) if cur == 'usd' else float(data.get('cost_diem') or 0.0)
        return amount / (tokens / 1000.0)

    efficiency: Dict[str, tuple[float, str]] = {}
    for model, data in model_data.items():
        if (data.get('tokens') or 0) > 0:
            efficiency[model] = (cost_per_1k(data), primary_currency(data))

    if efficiency:
        sorted_by_efficiency = sorted(
            [(m, c[0], c[1]) for m, c in efficiency.items()],
            key=lambda x: x[1],
        )
        most_efficient, most_cost, most_cur = sorted_by_efficiency[0]
        least_efficient, least_cost, least_cur = sorted_by_efficiency[-1]

        if most_cost < least_cost * 0.5:
            unit = '$' if most_cur == 'usd' else 'DIEM'
            recommendations.append({
                'type': 'efficiency',
                'message': (
                    f"'{most_efficient}' is most cost-efficient "
                    f"({unit}{most_cost:.4f}/1K tokens)"
                ),
                'priority': 'high',
            })

    # Latency recommendations are currency-agnostic.
    for model, data in model_data.items():
        avg_ms = data.get('avg_response_time_ms')
        if avg_ms is not None and avg_ms > 5000:
            recommendations.append({
                'type': 'performance',
                'message': f"'{model}' has high latency ({avg_ms/1000:.1f}s avg)",
                'priority': 'medium',
            })

    # Dominance: pick the dominant model in whichever currency this dataset
    # reports. Show the actual currency instead of mislabeling as DIEM.
    sorted_by_usage = sorted(
        model_data.items(),
        key=lambda x: float(x[1].get('cost_usd') or 0.0) + float(x[1].get('cost_diem') or 0.0),
        reverse=True,
    )
    if len(sorted_by_usage) > 1:
        top_model_name, top_model_data = sorted_by_usage[0]
        top_cost = float(top_model_data.get('cost_usd') or 0.0)
        top_currency = 'usd' if top_cost > 0 else 'diem'
        rest_cost = sum(
            float(d.get('cost_usd') or 0.0) if top_currency == 'usd'
            else float(d.get('cost_diem') or 0.0)
            for _, d in sorted_by_usage[1:]
        )
        if top_cost > 0 and top_cost > rest_cost * 0.5:
            unit = '$' if top_currency == 'usd' else 'DIEM'
            recommendations.append({
                'type': 'cost',
                'message': (
                    f"'{top_model_name}' accounts for {unit}{top_cost:.2f} usage "
                    f"(more than half of total)"
                ),
                'priority': 'high',
            })

    return recommendations[:5]


# ---------------------------------------------------------------------------
# Billing pagination (cursor + legacy) lives in backend.core.billing_pagination.
# The legacy walker raises BillingUsageDeprecated (with HTTP 410) which the
# route handlers below let propagate to the frontend as the documented
# migration signal — previously a blanket `except Exception` swallowed it.
# ---------------------------------------------------------------------------


def build_analytics_model_response(
    analytics: Dict[str, Any],
    days: int,
) -> AnalyticsResponse:
    model_usage: Dict[str, ModelAnalytics] = {}
    total_tokens = 0
    total_cost = 0.0

    for model in analytics.get('byModel', []):
        name = model.get('modelName', 'unknown')
        cost_usd = float(model.get('totalUsd', 0))
        cost_diem = float(model.get('totalDiem', 0))
        cost = cost_usd + cost_diem
        units = int(model.get('totalUnits', 0))
        breakdown = [
            ModelBreakdown(
                type=b.get('type', 'unknown'),
                usd=float(b.get('usd', 0)),
                diem=float(b.get('diem', 0)),
                units=int(b.get('units', 0)),
            )
            for b in model.get('breakdown', [])
        ]
        model_usage[name] = ModelAnalytics(
            requests=None,
            tokens=units,
            prompt_tokens=sum(b.units for b in breakdown if (b.type or '').lower() == 'input'),
            completion_tokens=sum(b.units for b in breakdown if (b.type or '').lower() == 'output'),
            cost=cost,
            cost_usd=cost_usd,
            cost_diem=cost_diem,
            avg_response_time_ms=None,
            model_type=(model.get('modelType') or 'other').lower(),
            breakdown=breakdown,
        )
        total_tokens += units
        total_cost += cost

    recommendations = generate_recommendations({
        name: {
            'tokens': model.tokens,
            'cost': model.cost,
            'avg_response_time_ms': model.avg_response_time_ms,
            'model_type': model.model_type,
        }
        for name, model in model_usage.items()
    })

    return AnalyticsResponse(
        model_usage=model_usage,
        total_requests=0,
        total_tokens=total_tokens,
        total_cost=total_cost,
        period_days=days,
        recommendations=[ModelRecommendation(**r) for r in recommendations],
        source='billing/usage-analytics',
    )


def build_analytics_daily_response(
    analytics: Dict[str, Any],
    days: int,
) -> DailyAnalyticsResponse:
    daily_usage = []
    for entry in analytics.get('byDate', []):
        usd = entry.get('USD', entry.get('usd', entry.get('totalUsd', 0)))
        diem = entry.get('DIEM', entry.get('diem', entry.get('totalDiem', 0)))
        try:
            usd_f = float(usd or 0)
        except (TypeError, ValueError):
            usd_f = 0.0
        try:
            diem_f = float(diem or 0)
        except (TypeError, ValueError):
            diem_f = 0.0
        daily_usage.append(
            DailyUsage(
                date=entry.get('date', ''),
                requests=None,
                tokens=None,
                cost=usd_f + diem_f,
                cost_usd=usd_f,
                cost_diem=diem_f,
            )
        )
    return DailyAnalyticsResponse(
        daily_usage=daily_usage,
        period_days=days,
        source='billing/usage-analytics',
    )


@router.get("/models", response_model=AnalyticsResponse)
async def get_model_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings)
):
    """
    Get model usage analytics including requests, tokens, costs, and performance.
    Uses per-request billing history when available, falling back to aggregated
    analytics and then legacy billing pagination.
    """
    try:
        try:
            usage_entries, billing_source = await get_billing_entries_from_db(client, days)
        except BillingUsageDeprecated:
            start_date, end_date = _analytics_window(days)
            analytics = await fetch_usage_analytics_optional(client, start_date, end_date)
            if analytics:
                logger.info("Analytics /models using /billing/usage-analytics fallback")
                return build_analytics_model_response(analytics, days)
            raise
        logger.info(f"Analytics /models loaded {len(usage_entries)} billing entries for last {days} day(s) via {billing_source}")
        
        model_data = process_usage_data(usage_entries)
        
        if not model_data:
            return AnalyticsResponse(
                model_usage={},
                total_requests=0,
                total_tokens=0,
                total_cost=0.0,
                period_days=days,
                recommendations=[],
                source=billing_source,
            )

        model_analytics = {}
        for model_name, mdata in model_data.items():
            model_analytics[model_name] = ModelAnalytics(
                requests=mdata['requests'],
                tokens=mdata['tokens'],
                prompt_tokens=mdata['prompt_tokens'],
                completion_tokens=mdata['completion_tokens'],
                cost=mdata['cost'],
                cost_usd=mdata.get('cost_usd', 0.0),
                cost_diem=mdata.get('cost_diem', 0.0),
                cost_bundled_credits=mdata.get('cost_bundled_credits', 0.0),
                avg_response_time_ms=mdata['avg_response_time_ms'],
                model_type=mdata.get('model_type', 'other'),
            )

        total_requests = sum(d['requests'] for d in model_data.values())
        total_tokens = sum(d['tokens'] for d in model_data.values())
        total_cost = sum(d['cost'] for d in model_data.values())

        recommendations = generate_recommendations(model_data)

        return AnalyticsResponse(
            model_usage=model_analytics,
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_cost=total_cost,
            period_days=days,
            recommendations=[ModelRecommendation(**r) for r in recommendations],
            source=billing_source,
        )

    except HTTPException:
        raise
    except BillingUsageDeprecated as exc:
        logger.info("Legacy /billing/usage 410 in model analytics: %s", exc)
        raise HTTPException(
            status_code=410,
            detail=(
                "/billing/usage is no longer available for this account. "
                "Use /billing/usage-history."
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = str(exc)
        if exc.response is not None:
            body = (exc.response.text or "")[:200]
            detail = f"Venice API returned {exc.response.status_code}: {body}".strip()
        logger.warning("Upstream Venice API error in model analytics: %s", detail)
        raise HTTPException(status_code=502, detail=f"Venice API error: {detail}") from exc
    except Exception:
        logger.exception("Failed to fetch model analytics")
        raise HTTPException(status_code=500, detail="Failed to fetch model analytics")


@router.get("/daily", response_model=DailyAnalyticsResponse)
async def get_daily_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings)
):
    """
    Get daily usage trends.

    Returns aggregated usage metrics per day for trend analysis.
    Uses per-request billing history when available, falling back to aggregated
    analytics and then legacy billing pagination.
    """
    try:
        try:
            usage_entries, billing_source = await get_billing_entries_from_db(client, days)
        except BillingUsageDeprecated:
            start_date, end_date = _analytics_window(days)
            analytics = await fetch_usage_analytics_optional(client, start_date, end_date)
            if analytics:
                logger.info("Analytics /daily using /billing/usage-analytics fallback")
                return build_analytics_daily_response(analytics, days)
            raise
        logger.info(f"Analytics /daily loaded {len(usage_entries)} billing entries via {billing_source}")
        
        daily_data: Dict[str, Dict] = {}
        request_tracker: Dict[str, set] = {}
        
        for entry in usage_entries:
            timestamp = entry.get('timestamp', '')
            if not timestamp:
                continue
            
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_key = dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
            
            amount = abs(entry.get('amount', 0))
            currency = (entry.get('currency') or '').upper()
            inference = entry.get('inferenceDetails') or {}
            
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'requests': 0,
                    'tokens': 0,
                    'cost': 0.0,
                    'cost_usd': 0.0,
                    'cost_diem': 0.0,
                    'cost_bundled_credits': 0.0,
                }
                request_tracker[date_key] = set()

            request_id = None
            if isinstance(inference, dict):
                request_id = inference.get('requestId')

            date_request_key = f"{date_key}-{request_id}" if request_id else None
            if date_request_key and date_request_key not in request_tracker[date_key]:
                request_tracker[date_key].add(date_request_key)
                daily_data[date_key]['requests'] += 1
            elif not request_id:
                daily_data[date_key]['requests'] += 1

            if isinstance(inference, dict):
                prompt_tokens = inference.get('promptTokens') or 0
                completion_tokens = inference.get('completionTokens') or 0
                daily_data[date_key]['tokens'] += prompt_tokens + completion_tokens

            # BUG-05: separate by currency; do not sum every numeric field.
            daily_data[date_key]['cost'] += amount
            if currency == 'USD':
                daily_data[date_key]['cost_usd'] += amount
            elif currency == 'DIEM':
                daily_data[date_key]['cost_diem'] += amount
            elif currency in ('BUNDLED_CREDITS', 'VCU'):
                daily_data[date_key]['cost_bundled_credits'] += amount

        daily_usage = [
            DailyUsage(
                date=date,
                requests=data['requests'],
                tokens=data['tokens'],
                cost=data['cost'],
                cost_usd=data.get('cost_usd', 0.0),
                cost_diem=data.get('cost_diem', 0.0),
                cost_bundled_credits=data.get('cost_bundled_credits', 0.0),
            )
            for date, data in sorted(daily_data.items())
        ]

        return DailyAnalyticsResponse(
            daily_usage=daily_usage,
            period_days=days,
            source=billing_source,
        )

    except HTTPException:
        raise
    except BillingUsageDeprecated as exc:
        logger.info("Legacy /billing/usage 410 in daily analytics: %s", exc)
        raise HTTPException(
            status_code=410,
            detail=(
                "/billing/usage is no longer available for this account. "
                "Use /billing/usage-history."
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = str(exc)
        if exc.response is not None:
            body = (exc.response.text or "")[:200]
            detail = f"Venice API returned {exc.response.status_code}: {body}".strip()
        logger.warning("Upstream Venice API error in daily analytics: %s", detail)
        raise HTTPException(status_code=502, detail=f"Venice API error: {detail}") from exc
    except Exception:
        logger.exception("Failed to fetch daily analytics")
        raise HTTPException(status_code=500, detail="Failed to fetch daily analytics")