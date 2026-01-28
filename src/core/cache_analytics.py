"""
Cache Analytics module for Venice AI prompt caching metrics.

This module provides the CacheAnalytics class for analyzing prompt cache usage,
calculating savings, and generating performance reports from billing data.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from itertools import groupby

from src.core.model_cache import ModelCacheManager, CachedModel
from src.core.cache_models import (
    CacheMetrics, ModelCacheStats, DailyCacheStats,
    CachePerformanceReport, CacheOptimizationRecommendation
)
from src.core.venice_api_client import VeniceAPIClient
from src.config.config import Config

logger = logging.getLogger(__name__)


class CacheAnalytics:
    """
    Analyzes Venice AI billing data to calculate prompt cache metrics,
    savings, and performance statistics.
    """

    def __init__(self, model_cache_manager: Optional[ModelCacheManager] = None,
                 api_client: Optional[VeniceAPIClient] = None):
        """
        Initialize the cache analytics engine.

        Args:
            model_cache_manager: Optional ModelCacheManager instance for pricing data
            api_client: Optional VeniceAPIClient for fetching billing data
        """
        self.model_cache = model_cache_manager or ModelCacheManager()
        self.api_client = api_client or VeniceAPIClient(Config.VENICE_ADMIN_KEY)

        self._default_pricing_cache: Dict[str, CachedModel] = {}

    def calculate_request_cache_metrics(
        self,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
        cache_creation_tokens: int = 0
    ) -> CacheMetrics:
        """
        Calculate cache metrics for a single request.

        Args:
            model_id: The model ID used
            prompt_tokens: Total prompt tokens
            completion_tokens: Completion tokens
            cached_tokens: Tokens served from cache
            cache_creation_tokens: Tokens written to cache

        Returns:
            CacheMetrics with calculated values
        """
        model = self.model_cache.get_model(model_id)

        if not model:
            model = self._get_default_model_pricing(model_id)

        regular_prompt_tokens = max(0, prompt_tokens - cached_tokens)
        cache_read_cost = self._calculate_cache_read_cost(model, cached_tokens)
        cache_write_cost = self._calculate_cache_write_cost(model, cache_creation_tokens)
        regular_input_cost = self._calculate_regular_input_cost(model, regular_prompt_tokens)
        output_cost = self._calculate_output_cost(model, completion_tokens)

        total_cost = cache_read_cost + cache_write_cost + regular_input_cost + output_cost

        cost_without_cache = regular_input_cost + output_cost + self._calculate_cache_read_cost(model, prompt_tokens)

        savings = cost_without_cache - total_cost
        savings_percent = (savings / cost_without_cache * 100) if cost_without_cache > 0 else 0

        return CacheMetrics(
            cached_tokens=cached_tokens,
            cache_creation_tokens=cache_creation_tokens,
            regular_prompt_tokens=regular_prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_cost_usd=cache_read_cost,
            cache_write_cost_usd=cache_write_cost,
            regular_input_cost_usd=regular_input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            cost_without_cache_usd=cost_without_cache,
            savings_usd=savings,
            savings_percent=savings_percent
        )

    def _calculate_cache_read_cost(self, model: CachedModel, cached_tokens: int) -> float:
        """Calculate cost for cache reads (discounted rate)"""
        if model.cache_input_price_usd is None:
            return 0.0
        return (cached_tokens * model.cache_input_price_usd) / 1_000_000

    def _calculate_cache_write_cost(self, model: CachedModel, creation_tokens: int) -> float:
        """Calculate cost for cache writes (may have premium)"""
        if model.cache_write_price_usd is None:
            return 0.0
        return (creation_tokens * model.cache_write_price_usd) / 1_000_000

    def _calculate_regular_input_cost(self, model: CachedModel, tokens: int) -> float:
        """Calculate cost for regular (non-cached) input"""
        if model.input_price_usd is None:
            return 0.0
        return (tokens * model.input_price_usd) / 1_000_000

    def _calculate_output_cost(self, model: CachedModel, tokens: int) -> float:
        """Calculate cost for output tokens"""
        if model.output_price_usd is None:
            return 0.0
        return (tokens * model.output_price_usd) / 1_000_000

    def _get_default_model_pricing(self, model_id: str) -> CachedModel:
        """Get default pricing for unknown models"""
        if model_id not in self._default_pricing_cache:
            self._default_pricing_cache[model_id] = CachedModel(
                id=model_id,
                name=model_id,
                model_type='text',
                input_price_usd=0.60,
                output_price_usd=6.00,
                cache_input_price_usd=0.06,
                cache_write_price_usd=0.75,
                supports_cache=True
            )
        return self._default_pricing_cache[model_id]

    def _extract_model_id_from_sku(self, sku: str) -> Optional[str]:
        """Extract model ID from SKU string"""
        if not sku:
            return None

        sku_lower = sku.lower()

        model_patterns = [
            ('grok', 'grok'),
            ('glm', 'glm'),
            ('qwen', 'qwen'),
            ('llama', 'llama'),
            ('mistral', 'mistral'),
            ('deepseek', 'deepseek'),
            ('claude', 'claude'),
            ('minimax', 'minimax'),
            ('kimi', 'kimi'),
            ('gemini', 'gemini'),
            ('gpt', 'gpt'),
            ('hermes', 'hermes'),
        ]

        for pattern, model_id in model_patterns:
            if pattern in sku_lower:
                return model_id

        return None

    def _is_llm_sku(self, sku: str) -> bool:
        """Check if SKU is for LLM inference"""
        if not sku:
            return False

        sku_lower = sku.lower()

        non_llm_indicators = ['video', 'image', 'veo', 'sora', 'kling', 'flux', 'sd35', 'upscale', 'embed']
        if any(ind in sku_lower for ind in non_llm_indicators):
            return False

        llm_indicators = ['llm', 'mtoken', 'input', 'output', 'prompt', 'completion', 'cache']
        return any(ind in sku_lower for ind in llm_indicators)

    def _get_model_display_name(self, model_id: str) -> str:
        """Get display name for model"""
        display_names = {
            'grok': 'Grok',
            'glm': 'GLM',
            'qwen': 'Qwen',
            'llama': 'Llama',
            'mistral': 'Mistral',
            'deepseek': 'DeepSeek',
            'claude': 'Claude',
            'minimax': 'MiniMax',
            'kimi': 'Kimi',
            'gemini': 'Gemini',
            'gpt': 'GPT',
            'hermes': 'Hermes',
        }
        return display_names.get(model_id, model_id.title())

    def analyze_billing_records(
        self,
        billing_records: List[Dict],
        days: int = 7
    ) -> Tuple[CachePerformanceReport, Dict[str, ModelCacheStats]]:
        """
        Analyze billing records to generate cache performance report.

        Venice billing uses separate SKUs for cache and regular usage:
        - {model}-llm-input-mtoken: Regular prompt input
        - {model}-llm-cache-input-mtoken: Cached prompt input (discounted)
        - {model}-llm-output-mtoken: Completion output

        We group records by requestId and calculate cache metrics from SKU costs.

        Args:
            billing_records: List of billing records from /billing/usage
            days: Number of days in the analysis period

        Returns:
            Tuple of (CachePerformanceReport, dict of model_stats)
        """
        model_stats: Dict[str, ModelCacheStats] = defaultdict(lambda: ModelCacheStats(model_id=""))
        daily_stats: Dict[str, DailyCacheStats] = defaultdict(lambda: DailyCacheStats(date=""))

        total_requests = 0
        total_savings_usd = 0.0
        total_prompt_tokens = 0
        total_cached_tokens = 0
        total_cost_without_cache = 0.0

        requests_by_id: Dict[str, List[Dict]] = defaultdict(list)

        for record in billing_records:
            sku = record.get('sku', '')
            model_id = self._extract_model_id_from_sku(sku)

            if not model_id or not self._is_llm_sku(sku):
                continue

            inference_details = record.get('inferenceDetails') or {}
            request_id = inference_details.get('requestId', '')

            if request_id:
                requests_by_id[request_id].append(record)

        for request_id, records in requests_by_id.items():
            total_requests += 1

            prompt_tokens = 0
            completion_tokens = 0
            cache_input_cost = 0.0
            regular_input_cost = 0.0
            output_cost = 0.0
            cache_write_cost = 0.0
            timestamp = ""
            date_str = ""
            model_id = ""

            cache_input_units = 0
            regular_input_units = 0
            output_units = 0

            for record in records:
                sku = record.get('sku', '')
                amount = abs(float(record.get('amount', 0)))
                currency = record.get('currency', 'DIEM')
                price_per_unit = float(record.get('pricePerUnitUsd', 0))
                units = float(record.get('units', 0))
                timestamp = record.get('timestamp', timestamp)
                date_str = timestamp[:10] if timestamp else date_str

                if not model_id:
                    model_id = self._extract_model_id_from_sku(sku) or "unknown"

                inference_details = record.get('inferenceDetails', {})
                record_prompt_tokens = inference_details.get('promptTokens', 0)
                record_completion_tokens = inference_details.get('completionTokens', 0)

                prompt_tokens = max(prompt_tokens, record_prompt_tokens)
                completion_tokens = max(completion_tokens, record_completion_tokens)

                sku_lower = sku.lower()

                if 'cache' in sku_lower and 'input' in sku_lower:
                    cache_input_cost += amount
                    cache_input_units = units
                elif 'output' in sku_lower:
                    output_cost += amount
                    output_units = units
                elif 'input' in sku_lower:
                    regular_input_cost += amount
                    regular_input_units = units
                elif 'cache' in sku_lower and 'write' in sku_lower:
                    cache_write_cost += amount

            if model_id == "unknown" or model_id not in model_stats:
                model_id = model_id

            if model_stats[model_id].model_name == "":
                model_stats[model_id].model_id = model_id
                model_stats[model_id].model_name = self._get_model_display_name(model_id)

            model = self.model_cache.get_model(model_id)

            total_actual_cost = cache_input_cost + regular_input_cost + output_cost + cache_write_cost

            if regular_input_units > 0 and cache_input_units > 0:
                total_prompt_tokens_est = int(regular_input_units * 1_000_000)
                cached_tokens_est = int(cache_input_units * 1_000_000)
                regular_tokens_est = total_prompt_tokens_est - cached_tokens_est
            else:
                cached_tokens_est = int(cache_input_units * 1_000_000) if cache_input_units > 0 else 0
                regular_tokens_est = prompt_tokens - cached_tokens_est
                if regular_tokens_est < 0:
                    regular_tokens_est = prompt_tokens
                    cached_tokens_est = 0

            if model and model.input_price_usd and model.cache_input_price_usd:
                regular_cost_at_full = (regular_tokens_est * model.input_price_usd) / 1_000_000
                cached_cost_at_discounted = (cached_tokens_est * model.cache_input_price_usd) / 1_000_000
                cost_without_cache_usd = regular_cost_at_full + cached_cost_at_discounted + output_cost
            else:
                cost_without_cache_usd = 0

            is_cache_hit = cache_input_cost > 0
            
            savings = 0
            if is_cache_hit and regular_input_cost > 0:
                savings = regular_input_cost - cache_input_cost

            model_stats[model_id].total_requests += 1
            if is_cache_hit:
                model_stats[model_id].cache_hit_requests += 1
            else:
                model_stats[model_id].cache_miss_requests += 1

            model_stats[model_id].total_prompt_tokens += prompt_tokens
            model_stats[model_id].total_cached_tokens += cached_tokens_est
            model_stats[model_id].total_regular_prompt_tokens += regular_tokens_est
            model_stats[model_id].total_completion_tokens += completion_tokens
            model_stats[model_id].total_cache_read_cost_usd += cache_input_cost
            model_stats[model_id].total_cache_write_cost_usd += cache_write_cost
            model_stats[model_id].total_regular_input_cost_usd += regular_input_cost
            model_stats[model_id].total_output_cost_usd += output_cost
            model_stats[model_id].total_cost_usd += total_actual_cost + cache_write_cost
            model_stats[model_id].total_cost_without_cache_usd += cost_without_cache_usd
            model_stats[model_id].total_savings_usd += savings

            total_savings_usd += savings
            total_prompt_tokens += prompt_tokens
            total_cached_tokens += cached_tokens_est
            total_cost_without_cache += cost_without_cache_usd

            if date_str not in daily_stats:
                daily_stats[date_str] = DailyCacheStats(date=date_str)
            daily_stats[date_str].total_requests += 1
            daily_stats[date_str].total_prompt_tokens += prompt_tokens
            daily_stats[date_str].total_cached_tokens += cached_tokens_est
            daily_stats[date_str].total_savings_usd += max(0, savings)
            if model_id not in daily_stats[date_str].models_used:
                daily_stats[date_str].models_used.append(model_id)

        overall_hit_rate = (total_cached_tokens / total_prompt_tokens * 100) if total_prompt_tokens > 0 else 0
        overall_savings_percent = (total_savings_usd / total_cost_without_cache * 100) if total_cost_without_cache > 0 else 0

        sorted_daily_stats = sorted(daily_stats.values(), key=lambda x: x.date)

        for ds in sorted_daily_stats:
            ds.cache_hit_rate = (ds.total_cached_tokens / ds.total_prompt_tokens * 100) if ds.total_prompt_tokens > 0 else 0

        top_saving_models = sorted(
            [(mid, stats.total_savings_usd, stats.cache_hit_rate) for mid, stats in model_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        lowest_hit_rate_models = sorted(
            [(mid, stats.cache_hit_rate, stats.total_requests) for mid, stats in model_stats.items() if stats.total_requests >= 5],
            key=lambda x: (x[1], -x[2])
        )[:5]

        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')

        report = CachePerformanceReport(
            start_date=start_date,
            end_date=end_date,
            total_requests=total_requests,
            total_savings_usd=total_savings_usd,
            overall_cache_hit_rate=overall_hit_rate,
            overall_savings_percent=overall_savings_percent,
            model_stats=dict(model_stats),
            daily_stats=sorted_daily_stats,
            top_saving_models=top_saving_models,
            lowest_hit_rate_models=lowest_hit_rate_models,
            period_days=days
        )

        return report, dict(model_stats)

    def generate_optimization_recommendations(
        self,
        model_stats: Dict[str, ModelCacheStats]
    ) -> List[CacheOptimizationRecommendation]:
        """
        Generate cache optimization recommendations based on model statistics.

        Args:
            model_stats: Dictionary of model statistics

        Returns:
            List of CacheOptimizationRecommendation objects
        """
        recommendations = []

        for model_id, stats in model_stats.items():
            if stats.total_requests < 5:
                continue

            if stats.cache_hit_rate < 20:
                recommendations.append(CacheOptimizationRecommendation(
                    recommendation_id=f"rec-{model_id}-hit-rate",
                    model_id=model_id,
                    model_name=stats.model_name,
                    category="prompt_structure",
                    priority="high" if stats.cache_hit_rate < 10 else "medium",
                    title=f"Low cache hit rate for {stats.model_name}",
                    description=f"The model has only {stats.cache_hit_rate:.1f}% cache hit rate. This may indicate prompt structure issues.",
                    current_value=f"{stats.cache_hit_rate:.1f}% hit rate",
                    recommended_value="70%+ for optimal caching",
                    potential_savings_usd=stats.total_savings_usd * 0.5,
                    action_items=[
                        "Ensure static content is at the beginning of prompts",
                        "Use consistent prompt_cache_key for multi-turn conversations",
                        "Avoid dynamic content (timestamps, random values) in prompt prefix"
                    ]
                ))

            if stats.token_cache_hit_rate < stats.cache_hit_rate * 0.8:
                recommendations.append(CacheOptimizationRecommendation(
                    recommendation_id=f"rec-{model_id}-token-efficiency",
                    model_id=model_id,
                    model_name=stats.model_name,
                    category="prompt_structure",
                    priority="medium",
                    title=f"Low token cache efficiency for {stats.model_name}",
                    description="Request cache hit rate is higher than token cache hit rate, suggesting small cache payloads.",
                    current_value=f"Request: {stats.cache_hit_rate:.1f}%, Token: {stats.token_cache_hit_rate:.1f}%",
                    recommended_value="Token rate should be close to request rate",
                    action_items=[
                        "Increase prompt prefix size to meet minimum cache threshold (~1024 tokens)",
                        "Bundle more static content before dynamic content"
                    ]
                ))

            model = self.model_cache.get_model(model_id)
            if model and model.cache_input_price_usd and model.cache_write_price_usd:
                write_to_read_ratio = model.cache_write_price_usd / model.cache_input_price_usd
                if write_to_read_ratio > 1.0 and stats.total_cache_creation_tokens > stats.total_cached_tokens * 0.5:
                    recommendations.append(CacheOptimizationRecommendation(
                        recommendation_id=f"rec-{model_id}-write-cost",
                        model_id=model_id,
                        model_name=stats.model_name,
                        category="threshold",
                        priority="medium",
                        title=f"High cache write costs for {stats.model_name}",
                        description="Cache write operations are costly relative to reads. Verify cache reuse justifies writes.",
                        current_value=f"Write/Read ratio: {write_to_read_ratio:.1f}x",
                        recommended_value="Ensure 2+ reuses per cache write",
                        potential_savings_usd=stats.total_cache_write_cost_usd * 0.3,
                        action_items=[
                            "Ensure prompts are reused at least 2-3 times to justify cache write costs",
                            "Use longer prompts with more static content to amortize write cost"
                        ]
                    ))

        recommendations.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x.priority],
            -x.potential_savings_usd
        ))

        return recommendations

    def estimate_potential_savings(
        self,
        model_stats: Dict[str, ModelCacheStats],
        target_hit_rate: float = 70.0
    ) -> Dict[str, float]:
        """
        Estimate potential savings if cache hit rates were improved.

        Args:
            model_stats: Dictionary of model statistics
            target_hit_rate: Target cache hit rate percentage

        Returns:
            Dictionary with savings estimates
        """
        total_current_savings = 0.0
        total_potential_savings = 0.0
        models_needing_improvement = 0

        for model_id, stats in model_stats.items():
            if stats.total_requests < 5:
                continue

            current_hit_rate = stats.cache_hit_rate
            if current_hit_rate < target_hit_rate:
                models_needing_improvement += 1
                improvement_factor = (target_hit_rate - current_hit_rate) / 100

                additional_tokens = stats.total_prompt_tokens * improvement_factor
                model = self.model_cache.get_model(model_id)

                if model and model.cache_input_price_usd:
                    additional_savings = (additional_tokens * model.cache_input_price_usd) / 1_000_000 * 0.9
                    total_potential_savings += additional_savings

            total_current_savings += stats.total_savings_usd

        return {
            'current_savings': total_current_savings,
            'potential_additional_savings': total_potential_savings,
            'models_needing_improvement': models_needing_improvement,
            'target_hit_rate': target_hit_rate,
            'total_potential_savings': total_current_savings + total_potential_savings
        }
