"""
Model Pricing Database for Venice AI Models

This module contains comprehensive pricing information for all Venice AI models,
extracted from the official Venice API documentation. Prices are in USD per 1M tokens
(for LLMs) or per generation/character (for image/audio models).

Source: https://docs.venice.ai/overview/pricing
Last Updated: 2025-11-29
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ModelType(Enum):
    """Model category types"""
    CHAT = "chat"
    IMAGE = "image"
    AUDIO = "audio"
    EMBEDDING = "embedding"
    VIDEO = "video"


class ModelCapability(Enum):
    """Model capabilities"""
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    REASONING = "reasoning"
    UNCENSORED = "uncensored"


class ModelTrait(Enum):
    """Model traits from /models/traits endpoint"""
    FASTEST = "fastest"
    MOST_UNCENSORED = "most_uncensored"
    DEFAULT = "default"
    FUNCTION_CALLING_DEFAULT = "function_calling_default"
    DEFAULT_VISION = "default_vision"
    ELIZA_DEFAULT = "eliza-default"
    SPECIALIZED_EDITING = "specialized_editing"
    DEFAULT_CODE = "default_code"


@dataclass
class ModelPricing:
    """Pricing information for a specific model"""
    model_id: str
    display_name: str
    model_type: ModelType
    
    # For chat/embedding models (USD per 1M tokens)
    input_price: Optional[float] = None
    output_price: Optional[float] = None
    
    # For image models (USD per generation)
    generation_price: Optional[float] = None
    
    # For audio models (USD per 1M characters)
    character_price: Optional[float] = None
    
    # Additional metadata
    capabilities: List[ModelCapability] = None
    traits: List[ModelTrait] = None
    context_window: Optional[int] = None
    is_beta: bool = False
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.traits is None:
            self.traits = []


class ModelPricingDatabase:
    """
    Centralized database of Venice AI model pricing and metadata.
    
    This class provides easy lookup of pricing information for cost calculations
    and optimization recommendations.
    """
    
    # Chat Models (Stable) - Updated 2025-11-29
    CHAT_MODELS = {
        "qwen3-4b": ModelPricing(
            model_id="qwen3-4b",
            display_name="Venice Small",
            model_type=ModelType.CHAT,
            input_price=0.05,
            output_price=0.15,
            capabilities=[ModelCapability.FUNCTION_CALLING, ModelCapability.REASONING],
            context_window=32768,
        ),
        "qwen3-235b-a22b-instruct-2507": ModelPricing(
            model_id="qwen3-235b-a22b-instruct-2507",
            display_name="Qwen 3 235B A22B Instruct 2507",
            model_type=ModelType.CHAT,
            input_price=0.15,
            output_price=0.75,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            context_window=131072,
        ),
        "llama-3.2-3b": ModelPricing(
            model_id="llama-3.2-3b",
            display_name="Llama 3.2 3B",
            model_type=ModelType.CHAT,
            input_price=0.15,
            output_price=0.60,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            traits=[ModelTrait.FASTEST],
            context_window=131072,
        ),
        "venice-uncensored": ModelPricing(
            model_id="venice-uncensored",
            display_name="Venice Uncensored 1.1",
            model_type=ModelType.CHAT,
            input_price=0.20,
            output_price=0.90,
            capabilities=[ModelCapability.UNCENSORED],
            traits=[ModelTrait.MOST_UNCENSORED],
            context_window=32768,
        ),
        "qwen3-235b-a22b-thinking-2507": ModelPricing(
            model_id="qwen3-235b-a22b-thinking-2507",
            display_name="Qwen 3 235B A22B Thinking 2507",
            model_type=ModelType.CHAT,
            input_price=0.45,
            output_price=3.50,
            capabilities=[ModelCapability.FUNCTION_CALLING, ModelCapability.REASONING],
            context_window=131072,
        ),
        "qwen3-235b": ModelPricing(
            model_id="qwen3-235b",
            display_name="Venice Large (D)",
            model_type=ModelType.CHAT,
            input_price=0.45,
            output_price=3.50,
            capabilities=[ModelCapability.FUNCTION_CALLING, ModelCapability.REASONING],
            context_window=131072,
        ),
        "mistral-31-24b": ModelPricing(
            model_id="mistral-31-24b",
            display_name="Venice Medium (3.1)",
            model_type=ModelType.CHAT,
            input_price=0.50,
            output_price=2.00,
            capabilities=[ModelCapability.FUNCTION_CALLING, ModelCapability.VISION],
            traits=[ModelTrait.DEFAULT_VISION],
            context_window=131072,
        ),
        "llama-3.3-70b": ModelPricing(
            model_id="llama-3.3-70b",
            display_name="Llama 3.3 70B",
            model_type=ModelType.CHAT,
            input_price=0.70,
            output_price=2.80,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            traits=[ModelTrait.DEFAULT, ModelTrait.FUNCTION_CALLING_DEFAULT],
            context_window=131072,
        ),
        "qwen3-coder-480b-a35b-instruct": ModelPricing(
            model_id="qwen3-coder-480b-a35b-instruct",
            display_name="Qwen 3 Coder 480B",
            model_type=ModelType.CHAT,
            input_price=0.75,
            output_price=3.00,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            traits=[ModelTrait.DEFAULT_CODE],
            context_window=262144,
        ),
        "zai-org-glm-4.6": ModelPricing(
            model_id="zai-org-glm-4.6",
            display_name="GLM 4.6",
            model_type=ModelType.CHAT,
            input_price=0.85,
            output_price=2.75,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            context_window=202752,
        ),
    }
    
    # Chat Models (Beta) - Updated 2025-11-29
    BETA_CHAT_MODELS = {
        "openai-gpt-oss-120b": ModelPricing(
            model_id="openai-gpt-oss-120b",
            display_name="OpenAI GPT OSS 120B",
            model_type=ModelType.CHAT,
            input_price=0.07,
            output_price=0.30,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            context_window=131072,
            is_beta=True,
        ),
        "google-gemma-3-27b-it": ModelPricing(
            model_id="google-gemma-3-27b-it",
            display_name="Google Gemma 3 27B",
            model_type=ModelType.CHAT,
            input_price=0.12,
            output_price=0.20,
            capabilities=[ModelCapability.FUNCTION_CALLING, ModelCapability.VISION],
            context_window=202752,
            is_beta=True,
        ),
        "qwen3-next-80b": ModelPricing(
            model_id="qwen3-next-80b",
            display_name="Qwen 3 Next 80B",
            model_type=ModelType.CHAT,
            input_price=0.35,
            output_price=1.90,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            context_window=262144,
            is_beta=True,
        ),
        "deepseek-ai-DeepSeek-R1": ModelPricing(
            model_id="deepseek-ai-DeepSeek-R1",
            display_name="DeepSeek R1",
            model_type=ModelType.CHAT,
            input_price=0.85,
            output_price=2.75,
            capabilities=[ModelCapability.FUNCTION_CALLING],
            context_window=131072,
            is_beta=True,
        ),
        "hermes-3-llama-3.1-405b": ModelPricing(
            model_id="hermes-3-llama-3.1-405b",
            display_name="Hermes 3 Llama 3.1 405B",
            model_type=ModelType.CHAT,
            input_price=1.10,
            output_price=3.00,
            capabilities=[],
            context_window=131072,
            is_beta=True,
        ),
    }
    
    # Image Models - Updated 2025-11-29
    IMAGE_MODELS = {
        "nano-banana-pro": ModelPricing(
            model_id="nano-banana-pro",
            display_name="Nano Banana Pro",
            model_type=ModelType.IMAGE,
            generation_price=0.18,
        ),
        "venice-sd35": ModelPricing(
            model_id="venice-sd35",
            display_name="Venice SD35",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
            traits=[ModelTrait.DEFAULT, ModelTrait.ELIZA_DEFAULT],
        ),
        "hidream": ModelPricing(
            model_id="hidream",
            display_name="HiDream",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
        ),
        "qwen-image": ModelPricing(
            model_id="qwen-image",
            display_name="Qwen Image",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
            traits=[ModelTrait.SPECIALIZED_EDITING],
        ),
        "lustify-sdxl": ModelPricing(
            model_id="lustify-sdxl",
            display_name="Lustify SDXL",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
        ),
        "lustify-v7": ModelPricing(
            model_id="lustify-v7",
            display_name="Lustify v7",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
        ),
        "wai-Illustrious": ModelPricing(
            model_id="wai-Illustrious",
            display_name="Anime (WAI)",
            model_type=ModelType.IMAGE,
            generation_price=0.01,
        ),
    }
    
    # Image Processing Operations
    IMAGE_OPERATIONS = {
        "upscale-2x": ModelPricing(
            model_id="upscale-2x",
            display_name="Image Upscale 2x",
            model_type=ModelType.IMAGE,
            generation_price=0.02,
        ),
        "upscale-4x": ModelPricing(
            model_id="upscale-4x",
            display_name="Image Upscale 4x",
            model_type=ModelType.IMAGE,
            generation_price=0.08,
        ),
        "image-edit": ModelPricing(
            model_id="image-edit",
            display_name="Image Edit (Inpaint)",
            model_type=ModelType.IMAGE,
            generation_price=0.04,
        ),
    }
    
    # Audio Models
    AUDIO_MODELS = {
        "tts-kokoro": ModelPricing(
            model_id="tts-kokoro",
            display_name="Kokoro TTS",
            model_type=ModelType.AUDIO,
            character_price=3.50,  # Per 1M characters
        ),
    }
    
    # Embedding Models
    EMBEDDING_MODELS = {
        "text-embedding-bge-m3": ModelPricing(
            model_id="text-embedding-bge-m3",
            display_name="BGE-M3",
            model_type=ModelType.EMBEDDING,
            input_price=0.15,
            output_price=0.60,
        ),
    }
    
    # Web Search/Scraping Pricing (per 1K calls)
    WEB_FEATURES = {
        "web-search-venice": ModelPricing(
            model_id="web-search-venice",
            display_name="Web Search (Venice Models)",
            model_type=ModelType.CHAT,
            generation_price=10.00,  # Per 1K calls
        ),
        "web-search-other": ModelPricing(
            model_id="web-search-other",
            display_name="Web Search (Other Models)",
            model_type=ModelType.CHAT,
            generation_price=25.00,  # Per 1K calls
        ),
        "web-scraping-venice": ModelPricing(
            model_id="web-scraping-venice",
            display_name="Web Scraping (Venice Models)",
            model_type=ModelType.CHAT,
            generation_price=10.00,  # Per 1K calls
        ),
        "web-scraping-other": ModelPricing(
            model_id="web-scraping-other",
            display_name="Web Scraping (Other Models)",
            model_type=ModelType.CHAT,
            generation_price=25.00,  # Per 1K calls
        ),
    }
    
    # Venice models eligible for cheaper web features
    VENICE_MODELS = ["venice-uncensored", "qwen3-4b", "mistral-31-24b", "qwen3-235b"]
    
    @classmethod
    def get_all_models(cls) -> Dict[str, ModelPricing]:
        """Get all models combined"""
        all_models = {}
        all_models.update(cls.CHAT_MODELS)
        all_models.update(cls.BETA_CHAT_MODELS)
        all_models.update(cls.IMAGE_MODELS)
        all_models.update(cls.IMAGE_OPERATIONS)
        all_models.update(cls.AUDIO_MODELS)
        all_models.update(cls.EMBEDDING_MODELS)
        all_models.update(cls.WEB_FEATURES)
        return all_models
    
    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelPricing]:
        """
        Get pricing information for a specific model.
        
        Args:
            model_id: The model identifier
            
        Returns:
            ModelPricing object or None if not found
        """
        all_models = cls.get_all_models()
        return all_models.get(model_id)
    
    @classmethod
    def get_chat_models(cls, include_beta: bool = False) -> Dict[str, ModelPricing]:
        """
        Get all chat models.
        
        Args:
            include_beta: Whether to include beta models
            
        Returns:
            Dictionary of chat models
        """
        models = dict(cls.CHAT_MODELS)
        if include_beta:
            models.update(cls.BETA_CHAT_MODELS)
        return models
    
    @classmethod
    def calculate_chat_cost(cls, model_id: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        """
        Calculate cost for a chat completion request.
        
        Args:
            model_id: The model identifier
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Cost in USD or None if model not found
        """
        model = cls.get_model(model_id)
        if not model or model.input_price is None or model.output_price is None:
            return None
        
        # Prices are per 1M tokens, so divide by 1,000,000
        input_cost = (prompt_tokens * model.input_price) / 1_000_000
        output_cost = (completion_tokens * model.output_price) / 1_000_000
        
        return input_cost + output_cost
    
    @classmethod
    def find_cheaper_alternatives(cls, current_model_id: str, 
                                  required_capabilities: List[ModelCapability] = None) -> List[Tuple[str, float]]:
        """
        Find cheaper alternative models with similar capabilities.
        
        Args:
            current_model_id: The current model being used
            required_capabilities: List of required capabilities to maintain
            
        Returns:
            List of (model_id, cost_savings_percent) tuples, sorted by savings
        """
        current = cls.get_model(current_model_id)
        if not current or current.model_type != ModelType.CHAT:
            return []
        
        required_capabilities = required_capabilities or []
        alternatives = []
        
        # Get all chat models
        chat_models = cls.get_chat_models(include_beta=False)
        
        for alt_id, alt_model in chat_models.items():
            if alt_id == current_model_id:
                continue
            
            # Skip if missing required capabilities
            if not all(cap in alt_model.capabilities for cap in required_capabilities):
                continue
            
            # Calculate average cost (assuming 1:3 input:output ratio)
            current_avg_cost = (current.input_price + 3 * current.output_price) / 4
            alt_avg_cost = (alt_model.input_price + 3 * alt_model.output_price) / 4
            
            if alt_avg_cost < current_avg_cost:
                savings_percent = ((current_avg_cost - alt_avg_cost) / current_avg_cost) * 100
                alternatives.append((alt_id, savings_percent))
        
        # Sort by savings (highest first)
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return alternatives
    
    @classmethod
    def get_models_by_trait(cls, trait: ModelTrait) -> List[str]:
        """
        Get all model IDs with a specific trait.
        
        Args:
            trait: The trait to filter by
            
        Returns:
            List of model IDs
        """
        matching_models = []
        for model_id, model in cls.get_all_models().items():
            if trait in model.traits:
                matching_models.append(model_id)
        return matching_models
    
    @classmethod
    def get_models_by_capability(cls, capability: ModelCapability) -> List[str]:
        """
        Get all model IDs with a specific capability.
        
        Args:
            capability: The capability to filter by
            
        Returns:
            List of model IDs
        """
        matching_models = []
        for model_id, model in cls.get_all_models().items():
            if capability in model.capabilities:
                matching_models.append(model_id)
        return matching_models
