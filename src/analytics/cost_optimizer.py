"""
Cost Optimization Engine for Venice AI Usage

This module analyzes usage patterns and provides intelligent recommendations
for reducing costs while maintaining model capabilities.
"""

from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging

from src.data.model_pricing import ModelPricingDatabase, ModelPricing
from src.utils.model_utils import ModelNameParser


logger = logging.getLogger(__name__)


@dataclass
class ModelUsageStats:
    """Statistics for a specific model's usage"""
    model_id: str
    display_name: str
    request_count: int
    total_tokens: int
    avg_tokens_per_request: float
    total_cost_diem: float
    total_cost_usd: float
    percentage_of_total: float
    api_keys_using: List[str] = None  # Names of API keys using this model


@dataclass
class CostSavingsRecommendation:
    """A recommendation for reducing costs"""
    current_model_id: str
    current_model_name: str
    recommended_model_id: str
    recommended_model_name: str
    current_cost: float
    potential_cost: float
    savings_amount: float
    savings_percent: float
    usage_count: int
    reason: str
    confidence: str  # "high", "medium", "low"
    api_keys_using: List[str] = None  # Names of API keys that should switch models


@dataclass
class CostOptimizationReport:
    """Comprehensive cost optimization report"""
    analysis_period_days: int
    total_cost_diem: float
    total_cost_usd: float
    model_breakdown: List[ModelUsageStats]
    recommendations: List[CostSavingsRecommendation]
    potential_monthly_savings: float
    generated_at: str


class CostOptimizer:
    """
    Analyzes usage patterns and generates cost optimization recommendations.
    
    This class processes billing/usage data to identify opportunities for
    cost savings through model substitution and usage pattern optimization.
    """
    
    # Thresholds for recommendations
    MIN_SAVINGS_PERCENT = 15.0  # Minimum savings % to recommend
    MIN_REQUEST_COUNT = 10  # Minimum requests to analyze
    SMALL_REQUEST_TOKEN_THRESHOLD = 1000  # Tokens threshold for "small" requests
    
    def __init__(self):
        """Initialize the cost optimizer"""
        self.model_usage: Dict[str, Dict] = {}
        self.total_cost_diem = 0.0
        self.total_cost_usd = 0.0
        self.api_key_usage: Dict[str, Dict] = {}  # Store API key usage data
    
    def set_api_key_usage(self, api_key_data: List[Dict]) -> None:
        """
        Store API key usage data for cross-referencing with model usage.
        
        Args:
            api_key_data: List of API key dicts from /api_keys endpoint
                Each should have: id, description, usage.trailingSevenDays
        """
        self.api_key_usage.clear()
        
        for key_data in api_key_data:
            key_id = key_data.get('id', '')
            key_name = key_data.get('description', f"Key {key_data.get('last6Chars', 'unknown')}")
            usage = key_data.get('usage', {}).get('trailingSevenDays', {})
            
            diem_usage = float(usage.get('diem', 0))
            usd_usage = float(usage.get('usd', 0))
            
            # Only store keys with actual usage
            if diem_usage > 0 or usd_usage > 0:
                self.api_key_usage[key_name] = {
                    'id': key_id,
                    'diem': diem_usage,
                    'usd': usd_usage,
                    'total': diem_usage + usd_usage
                }
                logger.debug(f"Stored API key: '{key_name}' with {diem_usage:.4f} DIEM")
        
        logger.info(f"Loaded {len(self.api_key_usage)} API keys with usage: {list(self.api_key_usage.keys())}")
    
    def analyze_billing_data(self, billing_entries: List[Dict]) -> None:
        """
        Analyze billing/usage entries to build usage statistics.
        
        Args:
            billing_entries: List of billing entry dicts from /billing/usage API
                Each entry should have: sku, units, amount, currency, inferenceDetails
        """
        self.model_usage.clear()
        self.total_cost_diem = 0.0
        self.total_cost_usd = 0.0
        
        for entry in billing_entries:
            sku = entry.get('sku', '')
            entry.get('units', 0)
            amount = abs(entry.get('amount', 0))  # Cost is negative in API
            currency = entry.get('currency', 'DIEM')
            inference_details = entry.get('inferenceDetails') or {}
            
            # Extract model ID
            model_id = ModelNameParser.clean_sku_name(sku)
            
            if model_id not in self.model_usage:
                pricing = ModelPricingDatabase.get_model(model_id)
                display_name = pricing.display_name if pricing else model_id
                
                self.model_usage[model_id] = {
                    'display_name': display_name,
                    'request_count': 0,
                    'total_tokens': 0,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'cost_diem': 0.0,
                    'cost_usd': 0.0,
                    'token_samples': [],  # For calculating averages
                }
            
            # Update statistics
            model_data = self.model_usage[model_id]
            
            # Count requests (each SKU with inferenceDetails is a request)
            if inference_details:
                model_data['request_count'] += 1
                
                prompt_tokens = inference_details.get('promptTokens', 0) or 0
                completion_tokens = inference_details.get('completionTokens', 0) or 0
                total_tokens = prompt_tokens + completion_tokens
                
                model_data['prompt_tokens'] += prompt_tokens
                model_data['completion_tokens'] += completion_tokens
                model_data['total_tokens'] += total_tokens
                
                if total_tokens > 0:
                    model_data['token_samples'].append(total_tokens)
            
            # Accumulate costs
            if currency == 'DIEM':
                model_data['cost_diem'] += amount
                self.total_cost_diem += amount
            elif currency == 'USD':
                model_data['cost_usd'] += amount
                self.total_cost_usd += amount
    
    def generate_model_breakdown(self) -> List[ModelUsageStats]:
        """
        Generate usage breakdown by model.
        
        Returns:
            List of ModelUsageStats sorted by cost (highest first)
        """
        breakdown = []
        
        for model_id, data in self.model_usage.items():
            if data['request_count'] == 0:
                continue
            
            avg_tokens = (
                sum(data['token_samples']) / len(data['token_samples'])
                if data['token_samples'] else 0
            )
            
            total_cost = data['cost_diem'] + data['cost_usd']
            percentage = (total_cost / (self.total_cost_diem + self.total_cost_usd) * 100
                         if (self.total_cost_diem + self.total_cost_usd) > 0 else 0)
            
            # Determine which API keys are likely using this model
            # We'll map keys based on their usage proportion
            api_keys_using = self._map_api_keys_to_model(model_id, total_cost)
            
            stats = ModelUsageStats(
                model_id=model_id,
                display_name=data['display_name'],
                request_count=data['request_count'],
                total_tokens=data['total_tokens'],
                avg_tokens_per_request=avg_tokens,
                total_cost_diem=data['cost_diem'],
                total_cost_usd=data['cost_usd'],
                percentage_of_total=percentage,
                api_keys_using=api_keys_using
            )
            breakdown.append(stats)
        
        # Sort by total cost (DIEM + USD)
        breakdown.sort(key=lambda x: x.total_cost_diem + x.total_cost_usd, reverse=True)
        return breakdown
    
    def generate_recommendations(self) -> List[CostSavingsRecommendation]:
        """
        Generate cost optimization recommendations based on usage patterns.
        
        Returns:
            List of CostSavingsRecommendation objects
        """
        recommendations = []
        
        for model_id, data in self.model_usage.items():
            # Skip if insufficient data
            if data['request_count'] < self.MIN_REQUEST_COUNT:
                continue
            
            current_pricing = ModelPricingDatabase.get_model(model_id)
            if not current_pricing or not current_pricing.input_price:
                continue
            
            # Calculate average request size
            avg_tokens = (
                sum(data['token_samples']) / len(data['token_samples'])
                if data['token_samples'] else 0
            )
            
            # Determine if this is a "small request" use case
            is_small_request = avg_tokens < self.SMALL_REQUEST_TOKEN_THRESHOLD
            
            # Get required capabilities
            required_caps = current_pricing.capabilities if not is_small_request else []
            
            # Find cheaper alternatives
            alternatives = ModelPricingDatabase.find_cheaper_alternatives(
                model_id,
                required_capabilities=required_caps
            )
            
            for alt_id, savings_pct in alternatives:
                if savings_pct < self.MIN_SAVINGS_PERCENT:
                    continue
                
                alt_pricing = ModelPricingDatabase.get_model(alt_id)
                if not alt_pricing:
                    continue
                
                # Calculate actual savings based on usage
                current_cost = data['cost_diem'] + data['cost_usd']
                potential_cost = current_cost * (1 - savings_pct / 100)
                savings_amount = current_cost - potential_cost
                
                # Map API keys to this model
                api_keys_using = self._map_api_keys_to_model(model_id, current_cost)
                
                # Determine confidence level
                confidence = self._determine_confidence(
                    current_pricing, alt_pricing, avg_tokens, is_small_request
                )
                
                # Generate reason
                reason = self._generate_recommendation_reason(
                    current_pricing, alt_pricing, avg_tokens, is_small_request
                )
                
                recommendation = CostSavingsRecommendation(
                    current_model_id=model_id,
                    current_model_name=current_pricing.display_name,
                    recommended_model_id=alt_id,
                    recommended_model_name=alt_pricing.display_name,
                    current_cost=current_cost,
                    potential_cost=potential_cost,
                    savings_amount=savings_amount,
                    savings_percent=savings_pct,
                    usage_count=data['request_count'],
                    reason=reason,
                    confidence=confidence,
                    api_keys_using=api_keys_using
                )
                recommendations.append(recommendation)
                
                # Only recommend the best alternative per model
                break
        
        # Sort by savings amount (highest first)
        recommendations.sort(key=lambda x: x.savings_amount, reverse=True)
        return recommendations
    
    def _map_api_keys_to_model(self, model_id: str, model_cost: float) -> List[str]:
        """
        Map API keys to a specific model based on usage proportions.
        
        Since Venice API doesn't provide per-key model breakdown, we estimate
        which keys are using each model based on their total usage relative to
        the model's cost.
        
        Args:
            model_id: The model to map keys to
            model_cost: Total cost for this model
            
        Returns:
            List of API key names with confidence prefix (e.g., "Likely: KeyName" or "Possibly: KeyName")
        """
        if not self.api_key_usage:
            return []
        
        # Sort keys by usage
        sorted_keys = sorted(
            self.api_key_usage.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )
        
        logger.debug(f"_map_api_keys_to_model for '{model_id}': sorted_keys = {[(k, v['total']) for k, v in sorted_keys]}")
        
        if not sorted_keys:
            return []
        
        # If there's only one active key, it must be using all models
        if len(self.api_key_usage) == 1:
            return [f"Confirmed: {sorted_keys[0][0]}"]
        
        # Calculate model's percentage of total usage
        total_usage = self.total_cost_diem + self.total_cost_usd
        if total_usage == 0:
            # No usage data - show all keys as possible
            return [f"Possibly: {key_name}" for key_name, _ in sorted_keys]
        
        model_pct = (model_cost / total_usage) * 100
        
        # Debug logging
        logger.debug(f"Model '{model_id}': cost={model_cost:.4f}, total={total_usage:.4f}, model_pct={model_pct:.1f}%")
        if sorted_keys:
            top_key_pct = (sorted_keys[0][1]['total'] / total_usage) * 100
            logger.debug(f"  Top key '{sorted_keys[0][0]}': usage={sorted_keys[0][1]['total']:.4f}, pct={top_key_pct:.1f}%")
        
        # High confidence: Model dominates usage (>80%)
        if model_pct > 80 and sorted_keys:
            top_key_pct = (sorted_keys[0][1]['total'] / total_usage) * 100
            if top_key_pct > 70:
                # Top key also dominates - very likely it's using this model
                return [f"Likely: {sorted_keys[0][0]}"]
            else:
                # Usage spread across keys - show top 2
                return [f"Likely: {key_name}" for key_name, _ in sorted_keys[:2]]
        
        # Medium confidence: Model is significant (>30%)
        if model_pct > 30:
            # Show top 2 keys as likely users
            result = [f"Likely: {sorted_keys[0][0]}"]
            if len(sorted_keys) > 1:
                result.append(f"Possibly: {sorted_keys[1][0]}")
            return result
        
        # Low confidence: Model is minor part of usage
        # Show all keys with >1% usage as possible
        threshold = total_usage * 0.01
        possible_keys = [f"Possibly: {key_name}" for key_name, key_data in sorted_keys if key_data['total'] >= threshold]
        return possible_keys if possible_keys else [f"Possibly: {key_name}" for key_name, _ in sorted_keys[:3]]
    
    def _determine_confidence(self, current: ModelPricing, alternative: ModelPricing,
                             avg_tokens: float, is_small_request: bool) -> str:
        """Determine confidence level for a recommendation"""
        # High confidence: small requests, cheaper model
        if is_small_request and avg_tokens < 500:
            return "high"
        
        # Medium confidence: moderate requests, similar capabilities
        if set(alternative.capabilities).issuperset(set(current.capabilities)):
            return "medium"
        
        # Low confidence: might lose some capabilities
        return "low"
    
    def _generate_recommendation_reason(self, current: ModelPricing, alternative: ModelPricing,
                                       avg_tokens: float, is_small_request: bool) -> str:
        """Generate human-readable reason for recommendation"""
        if is_small_request:
            return (f"Your requests average {avg_tokens:.0f} tokens - "
                   f"{alternative.display_name} is optimized for smaller requests")
        
        if set(alternative.capabilities) == set(current.capabilities):
            return f"{alternative.display_name} offers identical capabilities at lower cost"
        
        return f"{alternative.display_name} can handle most of your use cases at lower cost"
    
    def generate_report(self, analysis_days: int = 7) -> CostOptimizationReport:
        """
        Generate comprehensive cost optimization report.
        
        Args:
            analysis_days: Number of days analyzed
            
        Returns:
            CostOptimizationReport object
        """
        model_breakdown = self.generate_model_breakdown()
        recommendations = self.generate_recommendations()
        
        # Calculate potential monthly savings
        total_savings = sum(rec.savings_amount for rec in recommendations)
        days_multiplier = 30.0 / analysis_days if analysis_days > 0 else 1.0
        potential_monthly_savings = total_savings * days_multiplier
        
        return CostOptimizationReport(
            analysis_period_days=analysis_days,
            total_cost_diem=self.total_cost_diem,
            total_cost_usd=self.total_cost_usd,
            model_breakdown=model_breakdown,
            recommendations=recommendations,
            potential_monthly_savings=potential_monthly_savings,
            generated_at=datetime.now().isoformat()
        )
    
    def get_model_comparison(self, model_id_1: str, model_id_2: str,
                            avg_prompt_tokens: int = 500,
                            avg_completion_tokens: int = 500) -> Dict:
        """
        Compare two models for a typical usage scenario.
        
        Args:
            model_id_1: First model ID
            model_id_2: Second model ID
            avg_prompt_tokens: Average prompt size
            avg_completion_tokens: Average completion size
            
        Returns:
            Dictionary with comparison data
        """
        model1 = ModelPricingDatabase.get_model(model_id_1)
        model2 = ModelPricingDatabase.get_model(model_id_2)
        
        if not model1 or not model2:
            return {}
        
        cost1 = ModelPricingDatabase.calculate_chat_cost(
            model_id_1, avg_prompt_tokens, avg_completion_tokens
        )
        cost2 = ModelPricingDatabase.calculate_chat_cost(
            model_id_2, avg_prompt_tokens, avg_completion_tokens
        )
        
        if cost1 is None or cost2 is None:
            return {}
        
        savings = cost1 - cost2
        savings_pct = (savings / cost1 * 100) if cost1 > 0 else 0
        
        return {
            'model1': {
                'id': model_id_1,
                'name': model1.display_name,
                'cost': cost1,
                'capabilities': [cap.value for cap in model1.capabilities],
            },
            'model2': {
                'id': model_id_2,
                'name': model2.display_name,
                'cost': cost2,
                'capabilities': [cap.value for cap in model2.capabilities],
            },
            'comparison': {
                'cheaper_model': model_id_1 if cost1 < cost2 else model_id_2,
                'savings_usd': abs(savings),
                'savings_percent': abs(savings_pct),
                'cost_per_1k_requests_diff': abs(savings) * 1000,
            }
        }
