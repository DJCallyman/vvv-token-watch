"""
Dynamic column configuration for the model comparison table.
Defines column sets per model type plus defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional


class ModelType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    TTS = "tts"
    ASR = "asr"
    EMBEDDING = "embedding"
    UPSCALE = "upscale"
    INPAINT = "inpaint"


WIDTH_RESIZE = "resize_to_contents"
WIDTH_STRETCH = "stretch"


@dataclass(frozen=True)
class ColumnDefinition:
    """Defines a single column in the comparison table."""

    key: str
    header: str
    width_mode: str
    min_width: int = 60
    tooltip: Optional[str] = None
    sortable: bool = True
    formatter: Optional[Callable[..., object]] = None


TEXT_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("context", "Context", WIDTH_RESIZE, 100),
    ColumnDefinition("quantization", "Quant", WIDTH_RESIZE, 70),
    ColumnDefinition("date_added", "Added", WIDTH_RESIZE, 90),
    ColumnDefinition("vision", "Vision", WIDTH_RESIZE, 70),
    ColumnDefinition("functions", "Functions", WIDTH_RESIZE, 85),
    ColumnDefinition("web_search", "Web Search", WIDTH_RESIZE, 90),
    ColumnDefinition("reasoning", "Reasoning", WIDTH_RESIZE, 85),
    ColumnDefinition("logprobs", "LogProbs", WIDTH_RESIZE, 80),
    ColumnDefinition("response_schema", "JSON", WIDTH_RESIZE, 55),
    ColumnDefinition("optimized_for_code", "Code Opt", WIDTH_RESIZE, 70),
    ColumnDefinition("audio_input", "Audio In", WIDTH_RESIZE, 75),
    ColumnDefinition("video_input", "Video In", WIDTH_RESIZE, 75),
    ColumnDefinition("input_price", "Input $/1M", WIDTH_RESIZE, 110),
    ColumnDefinition("output_price", "Output $/1M", WIDTH_STRETCH, 120),
    ColumnDefinition("cache_input", "Cache Read $/1M", WIDTH_RESIZE, 110),
    ColumnDefinition("cache_write", "Cache Write $/1M", WIDTH_RESIZE, 110),
    ColumnDefinition("privacy", "Privacy", WIDTH_RESIZE, 90),
]

IMAGE_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("resolutions", "Resolutions", WIDTH_RESIZE, 150),
    ColumnDefinition("steps", "Steps", WIDTH_RESIZE, 80),
    ColumnDefinition("prompt_limit", "Prompt Limit", WIDTH_RESIZE, 110),
    ColumnDefinition("generation_price", "Price/Image", WIDTH_STRETCH, 110),
    ColumnDefinition("resolution_pricing", "Res Pricing", WIDTH_RESIZE, 110),
    ColumnDefinition("privacy", "Privacy", WIDTH_RESIZE, 90),
]

VIDEO_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("video_type", "Video Type", WIDTH_RESIZE, 110),
    ColumnDefinition("durations", "Durations", WIDTH_RESIZE, 110),
    ColumnDefinition("resolutions", "Resolutions", WIDTH_RESIZE, 150),
    ColumnDefinition("aspect_ratios", "Aspect Ratios", WIDTH_RESIZE, 120),
    ColumnDefinition("audio", "Audio", WIDTH_RESIZE, 70),
    ColumnDefinition("audio_configurable", "Audio Config", WIDTH_RESIZE, 110),
    ColumnDefinition("base_price", "Base Price", WIDTH_RESIZE, 100),
    ColumnDefinition("audio_price", "Audio Price", WIDTH_RESIZE, 100),
    ColumnDefinition("privacy", "Privacy", WIDTH_RESIZE, 90),
]

TTS_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("voices", "Voices", WIDTH_RESIZE, 110),
    ColumnDefinition("input_price", "Price/1M Chars", WIDTH_STRETCH, 130),
]

ASR_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("input_price", "Price/Min", WIDTH_STRETCH, 110),
]

EMBEDDING_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("dimensions", "Dimensions", WIDTH_RESIZE, 110),
    ColumnDefinition("input_price", "Input $/1M", WIDTH_STRETCH, 110),
]

UPSCALE_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("upscale_factors", "Factors", WIDTH_RESIZE, 90),
    ColumnDefinition("upscale_price", "Price/Upscale", WIDTH_STRETCH, 120),
]

INPAINT_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("resolutions", "Resolutions", WIDTH_RESIZE, 150),
    ColumnDefinition("steps", "Steps", WIDTH_RESIZE, 80),
    ColumnDefinition("inpaint_price", "Price/Inpaint", WIDTH_STRETCH, 120),
]

DEFAULT_COLUMNS: List[ColumnDefinition] = [
    ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
    ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
    ColumnDefinition("specs", "Specs", WIDTH_RESIZE, 150),
    ColumnDefinition("price", "Price", WIDTH_STRETCH, 110),
]

COLUMN_CONFIGS: Dict[ModelType, List[ColumnDefinition]] = {
    ModelType.TEXT: TEXT_COLUMNS,
    ModelType.IMAGE: IMAGE_COLUMNS,
    ModelType.VIDEO: VIDEO_COLUMNS,
    ModelType.TTS: TTS_COLUMNS,
    ModelType.ASR: ASR_COLUMNS,
    ModelType.EMBEDDING: EMBEDDING_COLUMNS,
    ModelType.UPSCALE: UPSCALE_COLUMNS,
    ModelType.INPAINT: INPAINT_COLUMNS,
}


def get_columns_for_type(model_type: Optional[str]) -> List[ColumnDefinition]:
    """Return column definitions for a given model type string."""
    if not model_type or model_type.lower() == "all":
        # For "all" or None, return common columns that work across all model types
        return [
            ColumnDefinition("model", "Model", WIDTH_RESIZE, 160),
            ColumnDefinition("type", "Type", WIDTH_RESIZE, 80),
            ColumnDefinition("specs", "Specs", WIDTH_RESIZE, 200),
            ColumnDefinition("price", "Price", WIDTH_STRETCH, 110),
        ]
    try:
        enum_type = ModelType(model_type.lower())
    except ValueError:
        return DEFAULT_COLUMNS
    return COLUMN_CONFIGS.get(enum_type, DEFAULT_COLUMNS)
