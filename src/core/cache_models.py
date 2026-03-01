"""
Cache tracking data structures for Venice AI prompt caching metrics.

This module provides dataclasses for tracking prompt cache usage,
including cache hits, misses, costs, and savings calculations.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime


@dataclass
class CacheMetrics:
    """
    Cache metrics for a single request or aggregated period.
    """
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    regular_prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_cost_usd: float = 0.0
    cache_write_cost_usd: float = 0.0
    regular_input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    cost_without_cache_usd: float = 0.0
    savings_usd: float = 0.0
    savings_percent: float = 0.0

    @property
    def total_prompt_tokens(self) -> int:
        """Total prompt tokens (cached + uncached)"""
        return self.cached_tokens + self.regular_prompt_tokens

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of prompt tokens served from cache"""
        if self.total_prompt_tokens == 0:
            return 0.0
        return (self.cached_tokens / self.total_prompt_tokens) * 100

    @property
    def is_cache_hit(self) -> bool:
        """Whether this request had any cache hits"""
        return self.cached_tokens > 0

    @property
    def is_cache_write(self) -> bool:
        """Whether this request wrote to cache"""
        return self.cache_creation_tokens > 0


@dataclass
class ModelCacheStats:
    """
    Aggregated cache statistics for a specific model.
    """
    model_id: str
    model_name: str = ""
    total_requests: int = 0
    cache_hit_requests: int = 0
    cache_miss_requests: int = 0
    total_prompt_tokens: int = 0
    total_cached_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_regular_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cache_read_cost_usd: float = 0.0
    total_cache_write_cost_usd: float = 0.0
    total_regular_input_cost_usd: float = 0.0
    total_output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    total_cost_without_cache_usd: float = 0.0
    total_savings_usd: float = 0.0

    def __post_init__(self):
        if not self.model_name:
            self.model_name = self.model_id

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of requests with cache hits"""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hit_requests / self.total_requests) * 100

    @property
    def token_cache_hit_rate(self) -> float:
        """Percentage of tokens served from cache"""
        if self.total_prompt_tokens == 0:
            return 0.0
        return (self.total_cached_tokens / self.total_prompt_tokens) * 100

    @property
    def average_savings_per_request(self) -> float:
        """Average cost savings per request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_savings_usd / self.total_requests

    @property
    def savings_percent(self) -> float:
        """Overall savings percentage"""
        if self.total_cost_without_cache_usd == 0:
            return 0.0
        return (self.total_savings_usd / self.total_cost_without_cache_usd) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary for display/serialization"""
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'total_requests': self.total_requests,
            'cache_hit_requests': self.cache_hit_requests,
            'cache_hit_rate': f"{self.cache_hit_rate:.1f}%",
            'total_prompt_tokens': self.total_prompt_tokens,
            'total_cached_tokens': self.total_cached_tokens,
            'token_cache_hit_rate': f"{self.token_cache_hit_rate:.1f}%",
            'total_cache_creation_tokens': self.total_cache_creation_tokens,
            'total_savings_usd': f"${self.total_savings_usd:.4f}",
            'savings_percent': f"{self.savings_percent:.1f}%",
            'total_cost_usd': f"${self.total_cost_usd:.4f}",
        }


@dataclass
class DailyCacheStats:
    """
    Daily cache statistics for tracking trends over time.
    """
    date: str  # YYYY-MM-DD format
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_cached_tokens: int = 0
    total_savings_usd: float = 0.0
    cache_hit_rate: float = 0.0
    models_used: List[str] = field(default_factory=list)


@dataclass
class CachePerformanceReport:
    """
    Comprehensive cache performance report for a time period.
    """
    start_date: str
    end_date: str
    total_requests: int = 0
    total_savings_usd: float = 0.0
    overall_cache_hit_rate: float = 0.0
    overall_savings_percent: float = 0.0
    model_stats: Dict[str, ModelCacheStats] = field(default_factory=dict)
    daily_stats: List[DailyCacheStats] = field(default_factory=list)
    top_saving_models: List[tuple] = field(default_factory=list)
    lowest_hit_rate_models: List[tuple] = field(default_factory=list)
    generated_at: str = ""
    period_days: int = 1

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()

    def get_summary(self) -> Dict:
        """Get a summary of the report"""
        return {
            'period': f"{self.start_date} to {self.end_date}",
            'total_requests': self.total_requests,
            'total_savings_usd': f"${self.total_savings_usd:.4f}",
            'overall_cache_hit_rate': f"{self.overall_cache_hit_rate:.1f}%",
            'overall_savings_percent': f"{self.overall_savings_percent:.1f}%",
            'models_with_cache': len(self.model_stats),
            'top_saving_model': self.top_saving_models[0] if self.top_saving_models else None,
        }


@dataclass
class CacheOptimizationRecommendation:
    """
    A recommendation for improving cache performance.
    """
    recommendation_id: str
    model_id: str
    model_name: str
    category: str  # 'prompt_structure', 'cache_key', 'threshold', 'model_selection'
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    current_value: str
    recommended_value: str
    potential_savings_usd: float = 0.0
    action_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'priority': self.priority,
            'title': self.title,
            'description': self.description,
            'model': self.model_name,
            'current': self.current_value,
            'recommended': self.recommended_value,
            'potential_savings': f"${self.potential_savings_usd:.4f}" if self.potential_savings_usd > 0 else "N/A",
        }
