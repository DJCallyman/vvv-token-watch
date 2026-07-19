"""Shared Pydantic response/request schemas for the web API."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ModelBreakdown(BaseModel):
    type: str
    usd: float
    diem: float
    units: int


class ModelAnalytics(BaseModel):
    requests: Optional[int] = None  # None when source='billing/usage-analytics' (not provided)
    tokens: int
    prompt_tokens: int
    completion_tokens: int
    # BUG-05: separate per-currency costs. 'cost' kept for backward compat but
    # is now the sum in a mixed unit (not recommended). Prefer cost_usd + cost_diem.
    cost: float = 0.0
    cost_usd: float = 0.0
    cost_diem: float = 0.0
    avg_response_time_ms: Optional[float] = None  # None when source='billing/usage-analytics'
    # success_rate removed: Venice billing usage does not expose per-request
    # success/failure status, so any computed rate would always be 100%.
    model_type: str = "other"
    breakdown: List[ModelBreakdown] = []


class ModelRecommendation(BaseModel):
    type: str
    message: str
    priority: str


class AnalyticsResponse(BaseModel):
    model_usage: Dict[str, ModelAnalytics]
    total_requests: int
    total_tokens: int
    total_cost: float
    period_days: int
    recommendations: List[ModelRecommendation]
    source: str = "billing/usage"


class DailyUsage(BaseModel):
    date: str
    # BUG-08: requests/tokens not provided by billing/usage-analytics source
    requests: Optional[int] = None
    tokens: Optional[int] = None
    cost: float = 0.0
    # BUG-05: separate per-currency daily costs
    cost_usd: float = 0.0
    cost_diem: float = 0.0


class DailyAnalyticsResponse(BaseModel):
    daily_usage: List[DailyUsage]
    period_days: int
    source: str = "billing/usage"


_ALL_BENCHMARK_TESTS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")
_MAX_MODELS_PER_BENCHMARK_RUN = 50


class BenchmarkStartParams(BaseModel):
    models: Optional[List[str]] = Field(default=None, max_length=_MAX_MODELS_PER_BENCHMARK_RUN)
    tests: Optional[List[str]] = Field(default=None, max_length=len(_ALL_BENCHMARK_TESTS))
    iterations: int = Field(default=10, ge=1, le=100)
    workers: int = Field(default=4, ge=1, le=16)
    privacy: Literal["both", "private", "anonymized"] = "both"

    @field_validator("tests")
    @classmethod
    def _validate_tests(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        cleaned = [str(t).strip().upper() for t in value if str(t).strip()]
        unknown = [t for t in cleaned if t not in _ALL_BENCHMARK_TESTS]
        if unknown:
            raise ValueError(f"Unknown tests: {unknown}. Valid: {list(_ALL_BENCHMARK_TESTS)}")
        if not cleaned:
            raise ValueError("At least one test is required when 'tests' is provided")
        return cleaned

    @field_validator("models")
    @classmethod
    def _validate_models(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        cleaned = [str(m).strip() for m in value if str(m).strip()]
        for m in cleaned:
            if len(m) > 200:
                raise ValueError(f"Model id too long: {m[:50]}...")
        if not cleaned:
            raise ValueError("At least one model id is required when 'models' is provided")
        return cleaned


class BenchmarkEstimateParams(BenchmarkStartParams):
    """Same shape/validation as start params; used for dry-run cost estimation."""


class BenchmarkEstimateResponse(BaseModel):
    model_count: int
    model_ids: List[str]
    tests: List[str]
    iterations: int
    workers: int
    privacy: str
    estimated_calls: int
    estimated_usd: float
    skipped_tests_note: Optional[str] = None
    note: str = "Estimate uses rough token counts; actual cost may vary."
