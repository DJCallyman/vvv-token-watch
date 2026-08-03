"""Tests for SKU parsing in backend.api.routes.analytics.

The SKU strings are the source of truth for "which model generated this
charge" — every Venice charge in /billing/usage-history has one. The
helpers below used to be the most regex-heavy code in the repo with zero
test coverage; even one character drift breaks the dashboard.
"""

from __future__ import annotations

import pytest

from backend.api.routes.analytics import clean_model_name, detect_model_type


@pytest.mark.parametrize(
    "sku, expected_model",
    [
        # credit-purchase sentinel
        ("credit-purchase", "credit-purchase"),
        # LLM
        ("qwen3-235b-llm-output-mtoken", "qwen3-235b"),
        ("claude-opus-4-5-llm-cache-write-5m-mtoken", "claude-opus-4-5"),
        ("grok-4-5-llm-extended-input-mtoken", "grok-4-5"),
        ("venice-uncensored-llm-input-mtoken", "venice-uncensored"),
        # Image
        ("flux-2-pro-image-unit", "flux-2-pro"),
        ("nano-banana-edit-fixed-1img", "nano-banana"),
        ("qwen-image-fixed-1K-1img", "qwen-image"),
        ("grok-imagine-fixed-websearch-1img", "grok-imagine"),
        # Video
        ("kling-v3-pro-text-to-video-duration-rate-1080p", "kling-v3-pro"),
        ("grok-imagine-text-to-video-resolution-720p", "grok-imagine"),
        # Music
        ("elevenlabs-music-duration-based-60s", "elevenlabs-music"),
        ("minimax-music-v2-fixed", "minimax-music-v2"),
        ("ace-step-15-duration-based-30s", "ace-step-15"),
        ("stable-audio-25-fixed-1min", "stable-audio-25"),
        # Embedding
        ("text-embedding-bge-m3-llm-input-mtoken", "text-embedding-bge-m3"),
    ],
)
def test_clean_model_name(sku: str, expected_model: str) -> None:
    assert clean_model_name(sku) == expected_model


@pytest.mark.parametrize(
    "sku, expected_type",
    [
        ("credit-purchase", "other"),
        ("qwen3-235b-llm-output-mtoken", "llm"),
        ("flux-2-pro-image-unit", "image"),
        ("nano-banana-edit-fixed-1img", "image"),
        ("grok-imagine-text-to-video-720p", "video"),
        ("elevenlabs-music-duration-based-60s", "music"),
        ("minimax-music-v2-fixed", "music"),
        ("ace-step-15-duration-based-30s", "music"),
        ("stable-audio-25-fixed-1min", "music"),
        ("text-embedding-bge-m3-llm-output-mtoken", "embedding"),
    ],
)
def test_detect_model_type(sku: str, expected_type: str) -> None:
    assert detect_model_type(sku) == expected_type


def test_detect_model_type_embedding_before_llm() -> None:
    """Embedding SKUs contain '-llm-' but should classify as embedding."""
    sku = "text-embedding-bge-m3-llm-output-mtoken"
    assert detect_model_type(sku) == "embedding"


def test_detect_model_type_video_priority() -> None:
    sku = "kling-v3-pro-text-to-video-duration-rate-anything"
    assert detect_model_type(sku) == "video"
