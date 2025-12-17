"""
Model name parsing and manipulation utilities.

This module consolidates model name processing logic to eliminate duplication
across multiple files and provide consistent model name handling.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from src.data.model_pricing import ModelPricingDatabase, ModelPricing


class ModelNameParser:
    """
    Utilities for parsing and cleaning model names from various sources.
    
    Provides consistent model name extraction and cleaning across the application,
    particularly for SKU-based model names from billing/usage APIs.
    """
    
    # Common suffixes to remove from model names
    TECHNICAL_SUFFIXES = [
        '-llm-input-mtoken',
        '-llm-output-mtoken',
        '-llm-input',
        '-llm-output',
        '-mtoken',
        '-input',
        '-output',
        '-tokens',
    ]
    
    # Model type indicators
    MODEL_TYPE_INDICATORS = {
        'llm': ['gpt', 'llama', 'mistral', 'qwen', 'claude', 'gemini'],
        'vision': ['vision', 'vl', 'multimodal'],
        'image': ['flux', 'stable-diffusion', 'sd', 'dall-e'],
        'audio': ['tts', 'whisper', 'speech'],
        'embedding': ['embed', 'embedding'],
    }
    
    @staticmethod
    def clean_sku_name(sku: str) -> str:
        """
        Remove technical suffixes from SKU to get clean model name.
        
        Args:
            sku: Raw SKU string (e.g., "llama-3.3-70b-llm-input-mtoken")
            
        Returns:
            Cleaned model name (e.g., "llama-3.3-70b")
        """
        if not sku:
            return ""
        
        # Split on -llm- first as it's a major separator
        base = sku.split('-llm-')[0] if '-llm-' in sku else sku
        
        # Remove other technical suffixes
        for suffix in ModelNameParser.TECHNICAL_SUFFIXES:
            base = base.replace(suffix, '')
        
        return base.strip('-')
    
    @staticmethod
    def extract_base_model_name(sku: str) -> str:
        """
        Extract the base model name from a SKU, removing version numbers and variants.
        
        Args:
            sku: Raw SKU string (e.g., "llama-3.3-70b-instruct-llm-input")
            
        Returns:
            Base model name (e.g., "llama-3")
        """
        # First clean the SKU
        cleaned = ModelNameParser.clean_sku_name(sku)
        
        # Remove common variant indicators
        cleaned = re.sub(r'-(instruct|turbo|vision|chat|base)$', '', cleaned)
        
        # Extract base model (before version numbers)
        # Pattern: model-name followed by version like 3.3, 70b, etc.
        match = re.match(r'^([a-zA-Z]+-[0-9]+(?:\.[0-9]+)?)', cleaned)
        if match:
            return match.group(1)
        
        # Fallback: return first two components
        parts = cleaned.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        
        return cleaned
    
    @staticmethod
    def format_display_name(sku: str, capitalize: bool = True) -> str:
        """
        Format a SKU into a human-readable display name.
        
        Args:
            sku: Raw SKU string
            capitalize: Whether to capitalize words
            
        Returns:
            Formatted display name
        """
        cleaned = ModelNameParser.clean_sku_name(sku)
        
        if capitalize:
            # Capitalize each part while preserving numbers
            parts = cleaned.split('-')
            formatted_parts = []
            for part in parts:
                if part.replace('.', '').isdigit():
                    formatted_parts.append(part)
                else:
                    formatted_parts.append(part.capitalize())
            return ' '.join(formatted_parts)
        
        return cleaned.replace('-', ' ')
    
    @staticmethod
    def detect_model_type(model_name: str) -> str:
        """
        Detect the type of model based on name patterns.
        
        Args:
            model_name: Model name or SKU
            
        Returns:
            Model type: 'llm', 'vision', 'image', 'audio', 'embedding', or 'unknown'
        """
        model_lower = model_name.lower()
        
        for model_type, indicators in ModelNameParser.MODEL_TYPE_INDICATORS.items():
            for indicator in indicators:
                if indicator in model_lower:
                    return model_type
        
        return 'unknown'
    
    @staticmethod
    def group_by_base_model(skus: List[str]) -> Dict[str, List[str]]:
        """
        Group SKUs by their base model name.
        
        Args:
            skus: List of SKU strings
            
        Returns:
            Dictionary mapping base model names to lists of related SKUs
        """
        groups = {}
        
        for sku in skus:
            base = ModelNameParser.extract_base_model_name(sku)
            if base not in groups:
                groups[base] = []
            groups[base].append(sku)
        
        return groups
    
    @staticmethod
    def is_input_sku(sku: str) -> bool:
        """Check if SKU represents input tokens/usage"""
        return '-input' in sku.lower()
    
    @staticmethod
    def is_output_sku(sku: str) -> bool:
        """Check if SKU represents output tokens/usage"""
        return '-output' in sku.lower()
    
    @staticmethod
    def parse_model_info(sku: str) -> Dict[str, Any]:
        """
        Parse comprehensive information from a SKU.
        
        Args:
            sku: Raw SKU string
            
        Returns:
            Dictionary with parsed information:
            - base_name: Base model name
            - clean_name: Cleaned full name
            - display_name: Human-readable name
            - model_type: Detected model type
            - is_input: Whether it's input-related
            - is_output: Whether it's output-related
        """
        return {
            'original': sku,
            'base_name': ModelNameParser.extract_base_model_name(sku),
            'clean_name': ModelNameParser.clean_sku_name(sku),
            'display_name': ModelNameParser.format_display_name(sku),
            'model_type': ModelNameParser.detect_model_type(sku),
            'is_input': ModelNameParser.is_input_sku(sku),
            'is_output': ModelNameParser.is_output_sku(sku),
        }
    
    @staticmethod
    def get_model_pricing(sku: str) -> Optional[ModelPricing]:
        """
        Get pricing information for a model based on its SKU.
        
        DEPRECATED: Use ModelCacheManager.get_model() instead for current pricing.
        This method is kept for backward compatibility and fallback scenarios.
        
        Args:
            sku: Raw SKU string (e.g., "llama-3.3-70b-llm-input-mtoken")
            
        Returns:
            ModelPricing object or None if not found
        """
        clean_model_id = ModelNameParser.clean_sku_name(sku)
        return ModelPricingDatabase.get_model(clean_model_id)
    
    @staticmethod
    def calculate_sku_cost(sku: str, units: float) -> Optional[float]:
        """
        Calculate cost for a specific SKU based on units consumed.

        DEPRECATED: Use ModelCacheManager.calculate_text_cost() instead for current pricing.
        This method is kept for backward compatibility and fallback scenarios.

        For chat models:
        - Input SKUs: units = tokens, cost = (tokens * input_price) / 1M
        - Output SKUs: units = tokens, cost = (tokens * output_price) / 1M
        
        For image models:
        - units = generations, cost = generations * generation_price
        
        For audio models:
        - units = characters, cost = (characters * character_price) / 1M
        
        Args:
            sku: Raw SKU string
            units: Number of units consumed (tokens, generations, characters)
            
        Returns:
            Cost in USD or None if pricing not found
        """
        pricing = ModelNameParser.get_model_pricing(sku)
        if not pricing:
            return None
        
        # Chat/embedding models (token-based)
        if ModelNameParser.is_input_sku(sku) and pricing.input_price is not None:
            return (units * pricing.input_price) / 1_000_000
        
        if ModelNameParser.is_output_sku(sku) and pricing.output_price is not None:
            return (units * pricing.output_price) / 1_000_000
        
        # Image models (generation-based)
        if pricing.generation_price is not None:
            return units * pricing.generation_price
        
        # Audio models (character-based)
        if pricing.character_price is not None:
            return (units * pricing.character_price) / 1_000_000
        
        return None
    
    @staticmethod
    def find_model_alternatives(current_sku: str, 
                               min_savings_percent: float = 10.0) -> List[Tuple[str, str, float]]:
        """
        Find cheaper alternative models for a given SKU.
        
        DEPRECATED: Use ModelCacheManager._find_cheaper_alternatives_from_cache() instead.
        This method is kept for backward compatibility and fallback scenarios.
        
        Args:
            current_sku: Current SKU being used
            min_savings_percent: Minimum savings percentage to include (default 10%)
            
        Returns:
            List of (model_id, display_name, savings_percent) tuples
        """
        clean_model_id = ModelNameParser.clean_sku_name(current_sku)
        current_pricing = ModelPricingDatabase.get_model(clean_model_id)
        
        if not current_pricing:
            return []
        
        # Get required capabilities from current model
        required_caps = current_pricing.capabilities
        
        # Find alternatives
        alternatives_data = ModelPricingDatabase.find_cheaper_alternatives(
            clean_model_id, 
            required_capabilities=required_caps
        )
        
        # Filter by minimum savings and format results
        results = []
        for alt_id, savings_pct in alternatives_data:
            if savings_pct >= min_savings_percent:
                alt_pricing = ModelPricingDatabase.get_model(alt_id)
                if alt_pricing:
                    results.append((alt_id, alt_pricing.display_name, savings_pct))
        
        return results


class ModelFilter:
    """
    Utilities for filtering and searching models.
    """
    
    @staticmethod
    def filter_by_type(models: List[Dict[str, Any]], model_type: str) -> List[Dict[str, Any]]:
        """
        Filter models by type.
        
        Args:
            models: List of model dictionaries
            model_type: Type to filter by ('text', 'image', 'tts', etc.)
            
        Returns:
            Filtered list of models
        """
        if model_type.lower() == 'all':
            return models
        
        return [m for m in models if m.get('type', '').lower() == model_type.lower()]
    
    @staticmethod
    def filter_by_trait(models: List[Dict[str, Any]], trait: str) -> List[Dict[str, Any]]:
        """
        Filter models by trait.
        
        Args:
            models: List of model dictionaries
            trait: Trait to filter by
            
        Returns:
            Filtered list of models
        """
        if trait.lower() == 'all':
            return models
        
        return [m for m in models if trait in m.get('traits', [])]
    
    @staticmethod
    def search_models(models: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Search models by name or ID.
        
        Args:
            models: List of model dictionaries
            query: Search query string
            
        Returns:
            Filtered list of matching models
        """
        if not query:
            return models
        
        query_lower = query.lower()
        results = []
        
        for model in models:
            model_id = model.get('id', '').lower()
            model_name = model.get('name', '').lower()
            
            if query_lower in model_id or query_lower in model_name:
                results.append(model)
        
        return results
