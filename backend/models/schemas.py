"""Shared Pydantic response/request schemas for the web API."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ModelBreakdown(BaseModel):
    type: str
    usd: float
    diem: float
    units: int


class ModelAnalytics(BaseModel):
    requests: int
    tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost: float
    avg_response_time_ms: float
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
    requests: int
    tokens: int
    cost: float


class DailyAnalyticsResponse(BaseModel):
    daily_usage: List[DailyUsage]
    period_days: int
    source: str = "billing/usage"


class BenchmarkStartParams(BaseModel):
    models: Optional[List[str]] = None  # None = all qualifying models
    tests: Optional[List[str]] = None   # None = all tests
    iterations: int = 10
    workers: int = 4
    privacy: str = "both"               # "both" | "private" | "anonymized"
