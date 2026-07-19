"""
Analytics API routes for model usage and performance metrics.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.venice_api_client import VeniceAPIClient
from backend.config import get_settings, Settings
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
    """Generate actionable recommendations based on usage patterns."""
    recommendations = []
    
    if not model_data:
        return recommendations
    
    efficiency = {}
    for model, data in model_data.items():
        if data['tokens'] > 0:
            efficiency[model] = data['cost'] / (data['tokens'] / 1000)
    
    if efficiency:
        sorted_by_efficiency = sorted(efficiency.items(), key=lambda x: x[1])
        most_efficient = sorted_by_efficiency[0]
        least_efficient = sorted_by_efficiency[-1]
        
        if most_efficient[1] < least_efficient[1] * 0.5:
            recommendations.append({
                'type': 'efficiency',
                'message': f"'{most_efficient[0]}' is most cost-efficient (${most_efficient[1]:.4f}/1K tokens)",
                'priority': 'high'
            })
    
    for model, data in model_data.items():
        if data['avg_response_time_ms'] > 5000:
            recommendations.append({
                'type': 'performance',
                'message': f"'{model}' has high latency ({data['avg_response_time_ms']/1000:.1f}s avg)",
                'priority': 'medium'
            })
    
    sorted_by_usage = sorted(model_data.items(), key=lambda x: x[1]['cost'], reverse=True)
    if len(sorted_by_usage) > 1:
        top_model = sorted_by_usage[0]
        if top_model[1]['cost'] > sum(d['cost'] for _, d in sorted_by_usage[1:]) * 0.5:
            recommendations.append({
                'type': 'cost',
                'message': f"'{top_model[0]}' accounts for {top_model[1]['cost']:.2f} DIEM usage",
                'priority': 'high'
            })
    
    return recommendations[:5]


async def _fetch_usage_analytics(
    client: VeniceAPIClient,
    start_date: datetime,
    end_date: datetime,
) -> Optional[Dict[str, Any]]:
    """Try the Beta usage-analytics endpoint; return None if unavailable."""
    try:
        params = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
        }
        response = await client.get('/billing/usage-analytics', params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as exc:
        logger.debug("usage-analytics endpoint unavailable: %s", exc)
    return None


@router.get("/models", response_model=AnalyticsResponse)
async def get_model_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings)
):
    """
    Get model usage analytics including requests, tokens, costs, and performance.
    Uses /billing/usage-analytics when available, falling back to manual pagination
    of /billing/usage.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        analytics = await _fetch_usage_analytics(client, start_date, end_date)
        if analytics:
            logger.info("Analytics /models using /billing/usage-analytics")
            model_usage: Dict[str, ModelAnalytics] = {}
            total_requests = 0
            total_tokens = 0
            total_cost = 0.0

            for model in analytics.get('byModel', []):
                name = model.get('modelName', 'unknown')
                cost_usd = float(model.get('totalUsd', 0))
                cost_diem = float(model.get('totalDiem', 0))
                # BUG-05: do not mix; keep separate. Legacy 'cost' is the sum for compat only.
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
                    requests=None,  # BUG-08: usage-analytics does not expose request counts
                    tokens=units,
                    prompt_tokens=sum(b.units for b in breakdown if (b.type or '').lower() == 'input'),
                    completion_tokens=sum(b.units for b in breakdown if (b.type or '').lower() == 'output'),
                    cost=cost,
                    cost_usd=cost_usd,
                    cost_diem=cost_diem,
                    avg_response_time_ms=None,  # BUG-08: not provided by this source
                    model_type=(model.get('modelType') or 'other').lower(),
                    breakdown=breakdown,
                )
                total_tokens += units
                total_cost += cost  # legacy mixed total (documented)

            recommendations = generate_recommendations({
                name: {
                    'tokens': m.tokens,
                    'cost': m.cost,
                    'avg_response_time_ms': m.avg_response_time_ms,
                    'model_type': m.model_type,
                }
                for name, m in model_usage.items()
            })

            return AnalyticsResponse(
                model_usage=model_usage,
                total_requests=total_requests,
                total_tokens=total_tokens,
                total_cost=total_cost,
                period_days=days,
                recommendations=[ModelRecommendation(**r) for r in recommendations],
                source='billing/usage-analytics',
            )

        usage_entries = []
        page = 1
        max_pages = settings.API_MAX_PAGES
        while page <= max_pages:
            params = {
                'startDate': start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'endDate': end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'limit': settings.API_PAGE_SIZE,
                'sortOrder': 'desc',
                'page': page,
            }
            response = await client.get('/billing/usage', params=params)
            if response.status_code >= 400:
                response.raise_for_status()
            data = response.json()
            page_entries = data.get('data', [])
            usage_entries.extend(page_entries)
            pagination = data.get('pagination', {})
            total_pages = int(pagination.get('totalPages', response.headers.get('x-pagination-total-pages', 1)))
            if page >= total_pages:
                break
            page += 1
        logger.info(f"Analytics /models fetched {len(usage_entries)} billing entries across {page} page(s) for last {days} day(s)")
        
        model_data = process_usage_data(usage_entries)
        
        if not model_data:
            return AnalyticsResponse(
                model_usage={},
                total_requests=0,
                total_tokens=0,
                total_cost=0.0,
                period_days=days,
                recommendations=[]
            )
        
        model_analytics = {}
        for model_name, mdata in model_data.items():
            model_analytics[model_name] = ModelAnalytics(
                requests=mdata['requests'],
                tokens=mdata['tokens'],
                prompt_tokens=mdata['prompt_tokens'],
                completion_tokens=mdata['completion_tokens'],
                cost=mdata['cost'],
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
            source='billing/usage',
        )

    except Exception as e:
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
    Uses /billing/usage-analytics when available, falling back to manual pagination
    of /billing/usage.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        analytics = await _fetch_usage_analytics(client, start_date, end_date)
        if analytics:
            logger.info("Analytics /daily using /billing/usage-analytics")
            daily_usage = []
            for entry in analytics.get('byDate', []):
                # BUG-08 + BUG-05: do not sum every numeric; prefer explicit usd/diem.
                # If the payload provides them, use them; otherwise leave at 0 and let
                # the UI know via source that request/latency/cost details are limited.
                usd = entry.get('usd') or entry.get('totalUsd') or 0
                diem = entry.get('diem') or entry.get('totalDiem') or 0
                try:
                    usd_f = float(usd)
                except Exception:
                    usd_f = 0.0
                try:
                    diem_f = float(diem)
                except Exception:
                    diem_f = 0.0
                daily_usage.append(
                    DailyUsage(
                        date=entry.get('date', ''),
                        requests=0,   # not provided by this source
                        tokens=0,     # not provided by this source
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

        usage_entries = []
        page = 1
        max_pages = settings.API_MAX_PAGES
        while page <= max_pages:
            params = {
                'startDate': start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'endDate': end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'limit': settings.API_PAGE_SIZE,
                'sortOrder': 'asc',
                'page': page,
            }
            response = await client.get('/billing/usage', params=params)
            if response.status_code >= 400:
                response.raise_for_status()
            data = response.json()
            page_entries = data.get('data', [])
            usage_entries.extend(page_entries)
            pagination = data.get('pagination', {})
            total_pages = int(pagination.get('totalPages', response.headers.get('x-pagination-total-pages', 1)))
            if page >= total_pages:
                break
            page += 1
        logger.info(f"Analytics /daily fetched {len(usage_entries)} billing entries across {page} page(s)")
        
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
        
        daily_usage = [
            DailyUsage(
                date=date,
                requests=data['requests'],
                tokens=data['tokens'],
                cost=data['cost'],
                cost_usd=data.get('cost_usd', 0.0),
                cost_diem=data.get('cost_diem', 0.0),
            )
            for date, data in sorted(daily_data.items())
        ]
        
        return DailyAnalyticsResponse(
            daily_usage=daily_usage,
            period_days=days,
            source='billing/usage',
        )

    except Exception as e:
        logger.exception("Failed to fetch daily analytics")
        raise HTTPException(status_code=500, detail="Failed to fetch daily analytics")