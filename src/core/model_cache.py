"""
Model Cache Manager for Venice AI Models

Fetches and manages model data from the Venice API, providing dynamic model lists
and pricing information. Includes caching and fallback mechanisms for reliability.
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from src.core.venice_api_client import VeniceAPIClient
from src.config.config import Config

logger = logging.getLogger(__name__)


@dataclass
class CachedModel:
    """Simplified model representation for caching"""
    id: str
    name: str
    model_type: str  # 'text', 'image', etc.
    input_price_usd: Optional[float] = None
    output_price_usd: Optional[float] = None
    generation_price_usd: Optional[float] = None
    capabilities: List[str] = None
    is_beta: bool = False
    context_window: Optional[int] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class ModelCacheManager:
    """
    Manages model data fetching from Venice API with local caching.
    
    Provides:
    - Fetches all models from /models endpoint at startup
    - Caches to file for offline access
    - Offers fallback to bundled static models if API unavailable
    - Exposes clean interfaces for getting pricing and model info
    """
    
    CACHE_FILE = Path("data/model_cache.json")
    
    def __init__(self, api_client: Optional[VeniceAPIClient] = None):
        """
        Initialize the model cache manager.
        
        Args:
            api_client: Optional VeniceAPIClient. If None, creates one with regular API key
        """
        self.api_client = api_client or VeniceAPIClient(Config.VENICE_API_KEY)
        self.models: Dict[str, CachedModel] = {}
        self.raw_api_data: Optional[Dict] = None  # Store raw API response for full details
        self.cache_timestamp: Optional[str] = None  # ISO format timestamp
        self._load_cache()
    
    def fetch_models(self, force_refresh: bool = False) -> bool:
        """
        Fetch models from Venice API and update cache.
        
        Args:
            force_refresh: If True, always fetch from API even if cache exists
            
        Returns:
            True if fetch successful, False if failed (may have fallen back to cache)
        """
        try:
            logger.info("Fetching models from Venice API...")
            response = self.api_client.get("/models", params={"type": "all"})
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch models: {response.status_code}")
                return False
            
            data = response.json()
            self.raw_api_data = data  # Store raw data for accessing full model specs
            self._parse_models(data)
            self._save_cache()
            logger.info(f"Successfully fetched and cached {len(self.models)} models")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to fetch models from API: {e}. Using cached data.")
            return False
    
    def _parse_models(self, api_response: Dict) -> None:
        """Parse API response and build model cache."""
        self.models.clear()
        
        if not api_response.get('data'):
            logger.warning("No model data in API response")
            return
        
        for model_data in api_response['data']:
            try:
                model_id = model_data.get('id')
                if not model_id:
                    continue
                
                model_spec = model_data.get('model_spec', {})
                model_type = model_data.get('type', 'unknown')
                
                # Extract pricing based on model type
                pricing = model_spec.get('pricing', {})
                input_price = None
                output_price = None
                generation_price = None
                
                if model_type == 'text':
                    input_price = pricing.get('input', {}).get('usd')
                    output_price = pricing.get('output', {}).get('usd')
                elif model_type in ('image', 'upscale', 'inpaint'):
                    generation_price = pricing.get('generation', {}).get('usd')
                elif model_type == 'tts':
                    input_price = pricing.get('input', {}).get('usd')
                elif model_type == 'embedding':
                    input_price = pricing.get('input', {}).get('usd')
                    output_price = pricing.get('output', {}).get('usd')
                
                # Extract capabilities
                capabilities_spec = model_spec.get('capabilities', {})
                capabilities = []
                
                if isinstance(capabilities_spec, dict):
                    if capabilities_spec.get('supportsVision'):
                        capabilities.append('vision')
                    if capabilities_spec.get('supportsFunctionCalling'):
                        capabilities.append('function_calling')
                    if capabilities_spec.get('supportsReasoning'):
                        capabilities.append('reasoning')
                    if capabilities_spec.get('supportsResponseSchema'):
                        capabilities.append('response_schema')
                    if capabilities_spec.get('optimizedForCode'):
                        capabilities.append('optimized_for_code')
                
                # Get traits
                traits = model_data.get('model_spec', {}).get('traits', [])
                
                cached_model = CachedModel(
                    id=model_id,
                    name=model_spec.get('name', model_id),
                    model_type=model_type,
                    input_price_usd=input_price,
                    output_price_usd=output_price,
                    generation_price_usd=generation_price,
                    capabilities=capabilities,
                    is_beta=model_spec.get('beta', False),
                    context_window=model_spec.get('availableContextTokens')
                )
                
                self.models[model_id] = cached_model
                logger.debug(f"Cached model: {model_id} ({model_type})")
                
            except Exception as e:
                logger.warning(f"Failed to parse model {model_data.get('id', 'unknown')}: {e}")
                continue
    
    def _save_cache(self) -> None:
        """Save models to local cache file."""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            self.cache_timestamp = datetime.now().isoformat()
            
            cache_data = {
                'timestamp': self.cache_timestamp,
                'models': {
                    model_id: {
                        'id': m.id,
                        'name': m.name,
                        'type': m.model_type,
                        'input_price_usd': m.input_price_usd,
                        'output_price_usd': m.output_price_usd,
                        'generation_price_usd': m.generation_price_usd,
                        'capabilities': m.capabilities,
                        'is_beta': m.is_beta,
                        'context_window': m.context_window,
                    }
                    for model_id, m in self.models.items()
                },
                'raw_api_data': self.raw_api_data
            }
            
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Saved model cache to {self.CACHE_FILE} (timestamp: {self.cache_timestamp})")
            
        except Exception as e:
            logger.warning(f"Failed to save model cache: {e}")
    
    def _load_cache(self) -> None:
        """Load models from local cache file if it exists."""
        try:
            if not self.CACHE_FILE.exists():
                logger.debug(f"No cache file found at {self.CACHE_FILE}")
                return
            
            with open(self.CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Load timestamp if present
            self.cache_timestamp = cache_data.get('timestamp')
            
            models_data = cache_data.get('models', {})
            for model_id, model_dict in models_data.items():
                self.models[model_id] = CachedModel(
                    id=model_dict.get('id'),
                    name=model_dict.get('name'),
                    model_type=model_dict.get('type'),
                    input_price_usd=model_dict.get('input_price_usd'),
                    output_price_usd=model_dict.get('output_price_usd'),
                    generation_price_usd=model_dict.get('generation_price_usd'),
                    capabilities=model_dict.get('capabilities', []),
                    is_beta=model_dict.get('is_beta', False),
                    context_window=model_dict.get('context_window')
                )
            
            self.raw_api_data = cache_data.get('raw_api_data')
            timestamp_str = f" (updated: {self.cache_timestamp})" if self.cache_timestamp else ""
            logger.info(f"Loaded {len(self.models)} models from cache{timestamp_str}")
            
        except Exception as e:
            logger.warning(f"Failed to load model cache: {e}")
    
    def get_model(self, model_id: str) -> Optional[CachedModel]:
        """Get a specific model by ID."""
        return self.models.get(model_id)
    
    def get_models_by_type(self, model_type: str) -> List[CachedModel]:
        """Get all models of a specific type."""
        return [m for m in self.models.values() if m.model_type == model_type]
    
    def get_text_models(self) -> List[CachedModel]:
        """Get all text/LLM models."""
        return self.get_models_by_type('text')
    
    def get_image_models(self) -> List[CachedModel]:
        """Get all image models."""
        return self.get_models_by_type('image')
    
    def get_all_models(self) -> Dict[str, CachedModel]:
        """Get all cached models."""
        return self.models.copy()
    
    def get_model_price(self, model_id: str, tokens: int = 1_000_000, 
                       is_output: bool = False) -> Optional[float]:
        """
        Get the price for a model in USD.
        
        Args:
            model_id: The model ID
            tokens: Number of tokens (default 1M for per-token comparison)
            is_output: If True, use output price for text models
            
        Returns:
            Price in USD or None if not found
        """
        model = self.get_model(model_id)
        if not model:
            return None
        
        # For text models, use input or output price
        if model.model_type == 'text':
            price_per_m = model.output_price_usd if is_output else model.input_price_usd
            if price_per_m is not None:
                return (price_per_m * tokens) / 1_000_000
        
        # For image/generation models, use generation price
        if model.generation_price_usd is not None:
            return model.generation_price_usd * tokens  # Usually per generation, not per token
        
        return None
    
    def calculate_text_cost(self, model_id: str, prompt_tokens: int, 
                           completion_tokens: int) -> Optional[float]:
        """
        Calculate cost for a text model request.
        
        Args:
            model_id: The model ID
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Total cost in USD or None if not found
        """
        model = self.get_model(model_id)
        if not model or model.model_type != 'text':
            return None
        
        if model.input_price_usd is None or model.output_price_usd is None:
            return None
        
        input_cost = (prompt_tokens * model.input_price_usd) / 1_000_000
        output_cost = (completion_tokens * model.output_price_usd) / 1_000_000
        
        return input_cost + output_cost
    
    def get_raw_model_data(self, model_id: str) -> Optional[Dict]:
        """
        Get raw API data for a specific model for full details.
        
        Args:
            model_id: The model ID
            
        Returns:
            Raw model data from API or None if not found
        """
        if not self.raw_api_data or not self.raw_api_data.get('data'):
            return None
        
        for model_data in self.raw_api_data['data']:
            if model_data.get('id') == model_id:
                return model_data
        
        return None
    
    def get_cache_timestamp(self) -> Optional[str]:
        """
        Get the timestamp when the cache was last updated.
        
        Returns:
            ISO format timestamp string or None if no timestamp available
        """
        return self.cache_timestamp
    
    def get_cache_timestamp_formatted(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
        """
        Get formatted cache timestamp for display.
        
        Args:
            format_str: Python datetime format string (default: "YYYY-MM-DD HH:MM:SS")
            
        Returns:
            Formatted timestamp string or None if no timestamp available
        """
        if not self.cache_timestamp:
            return None
        
        try:
            dt = datetime.fromisoformat(self.cache_timestamp)
            return dt.strftime(format_str)
        except Exception as e:
            logger.warning(f"Failed to format cache timestamp: {e}")
            return None
