"""
Tests for cache analytics module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestCacheMetrics:
    """Test cases for CacheMetrics dataclass."""
    
    def test_cache_metrics_creation(self):
        """Test creating CacheMetrics instance."""
        from src.core.cache_models import CacheMetrics
        
        metrics = CacheMetrics(
            cached_tokens=1000,
            cache_creation_tokens=500,
            regular_prompt_tokens=200,
            completion_tokens=300,
            cache_read_cost_usd=0.001,
            cache_write_cost_usd=0.0005,
            regular_input_cost_usd=0.002,
            output_cost_usd=0.003,
            total_cost_usd=0.0065,
            cost_without_cache_usd=0.008,
            savings_usd=0.0015,
            savings_percent=18.75
        )
        
        assert metrics.cached_tokens == 1000
        assert metrics.savings_percent == 18.75
    
    def test_cache_metrics_defaults(self):
        """Test CacheMetrics with default values."""
        from src.core.cache_models import CacheMetrics
        
        metrics = CacheMetrics(
            cached_tokens=500,
            cache_creation_tokens=0,
            regular_prompt_tokens=500,
            completion_tokens=100
        )
        
        assert metrics.cache_read_cost_usd == 0.0
        assert metrics.savings_usd == 0.0


class TestModelCacheStats:
    """Test cases for ModelCacheStats dataclass."""
    
    def test_model_cache_stats_creation(self):
        """Test creating ModelCacheStats instance."""
        from src.core.cache_models import ModelCacheStats
        
        stats = ModelCacheStats(model_id="llama-3", model_name="Llama 3")
        
        assert stats.model_id == "llama-3"
        assert stats.model_name == "Llama 3"
        assert stats.total_requests == 0
        assert stats.total_savings_usd == 0.0
    
    def test_model_cache_stats_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        from src.core.cache_models import ModelCacheStats
        
        stats = ModelCacheStats(
            model_id="test-model",
            model_name="Test Model",
            total_requests=100,
            cache_hit_requests=80,
            cache_miss_requests=20
        )
        
        assert stats.cache_hit_rate == 80.0
    
    def test_model_cache_stats_zero_requests(self):
        """Test cache hit rate with zero requests."""
        from src.core.cache_models import ModelCacheStats
        
        stats = ModelCacheStats(model_id="test-model")
        
        assert stats.cache_hit_rate == 0.0


class TestCacheAnalytics:
    """Test cases for CacheAnalytics class."""
    
    @pytest.fixture
    def cache_analytics(self):
        """Create a CacheAnalytics instance for testing."""
        with patch('src.core.cache_analytics.VeniceAPIClient'), \
             patch('src.core.cache_analytics.ModelCacheManager'):
            from src.core.cache_analytics import CacheAnalytics
            return CacheAnalytics()
    
    def test_initialization(self, cache_analytics):
        """Test CacheAnalytics initialization."""
        assert cache_analytics is not None
        assert hasattr(cache_analytics, 'model_cache')
        assert hasattr(cache_analytics, 'api_client')
    
    def test_calculate_request_cache_metrics(self, cache_analytics, mock_cached_model):
        """Test calculating cache metrics for a request."""
        with patch.object(cache_analytics.model_cache, 'get_model', return_value=mock_cached_model):
            metrics = cache_analytics.calculate_request_cache_metrics(
                model_id="test-model",
                prompt_tokens=1000,
                completion_tokens=500,
                cached_tokens=200,
                cache_creation_tokens=100
            )
            
            assert metrics.cached_tokens == 200
            assert metrics.completion_tokens == 500
            assert metrics.regular_prompt_tokens == 800
    
    def test_calculate_request_cache_metrics_unknown_model(self, cache_analytics):
        """Test calculating metrics for unknown model uses defaults."""
        with patch.object(cache_analytics.model_cache, 'get_model', return_value=None):
            metrics = cache_analytics.calculate_request_cache_metrics(
                model_id="unknown-model",
                prompt_tokens=1000,
                completion_tokens=500,
                cached_tokens=200
            )
            
            assert metrics is not None
            assert metrics.cached_tokens == 200
    
    def test_extract_model_id_from_sku(self, cache_analytics):
        """Test extracting model ID from SKU strings."""
        test_cases = [
            ("llama-3.3-70b-llm-input-mtoken", "llama"),
            ("deepseek-v3-llm-output-mtoken", "deepseek"),
            ("claude-3-llm-cache-input-mtoken", "claude"),
            ("gpt-4-llm-input-mtoken", "gpt"),
            ("qwen-2.5-llm-output-mtoken", "qwen"),
            ("gemini-pro-llm-input-mtoken", "gemini"),
            ("grok-2-llm-output-mtoken", "grok"),
            ("video-generation-credits", None),
            ("image-generation-credits", None),
        ]
        
        for sku, expected in test_cases:
            result = cache_analytics._extract_model_id_from_sku(sku)
            assert result == expected, f"Failed for SKU: {sku}"
    
    def test_is_llm_sku(self, cache_analytics):
        """Test identifying LLM SKUs."""
        llm_skus = [
            "llama-llm-input-mtoken",
            "deepseek-llm-output-mtoken",
            "claude-llm-cache-input-mtoken",
        ]
        
        non_llm_skus = [
            "video-generation-credits",
            "image-generation-credits",
            "stable-diffusion-generation",
            "embedding-input",
        ]
        
        for sku in llm_skus:
            assert cache_analytics._is_llm_sku(sku) is True, f"Should be LLM: {sku}"
        
        for sku in non_llm_skus:
            assert cache_analytics._is_llm_sku(sku) is False, f"Should not be LLM: {sku}"
    
    def test_analyze_billing_records(self, cache_analytics, sample_billing_records, mock_cached_model):
        """Test analyzing billing records."""
        with patch.object(cache_analytics.model_cache, 'get_model', return_value=mock_cached_model):
            report, model_stats = cache_analytics.analyze_billing_records(
                sample_billing_records,
                days=7
            )
            
            assert report is not None
            assert report.total_requests > 0
            assert report.period_days == 7
            assert isinstance(model_stats, dict)
    
    def test_analyze_empty_billing_records(self, cache_analytics):
        """Test analyzing empty billing records."""
        report, model_stats = cache_analytics.analyze_billing_records([], days=7)
        
        assert report.total_requests == 0
        assert len(model_stats) == 0
    
    def test_generate_optimization_recommendations(self, cache_analytics, mock_cached_model):
        """Test generating optimization recommendations."""
        from src.core.cache_models import ModelCacheStats
        
        model_stats = {
            "low-cache-model": ModelCacheStats(
                model_id="low-cache-model",
                model_name="Low Cache Model",
                total_requests=10,
                cache_hit_requests=1,
                cache_miss_requests=9,
                total_savings_usd=0.01,
                total_prompt_tokens=10000,
                total_cached_tokens=1000,
                total_cache_creation_tokens=0
            ),
            "good-cache-model": ModelCacheStats(
                model_id="good-cache-model",
                model_name="Good Cache Model",
                total_requests=10,
                cache_hit_requests=8,
                cache_miss_requests=2,
                total_savings_usd=0.50,
                total_prompt_tokens=10000,
                total_cached_tokens=8000,
                total_cache_creation_tokens=0
            )
        }
        
        with patch.object(cache_analytics.model_cache, 'get_model', return_value=mock_cached_model):
            recommendations = cache_analytics.generate_optimization_recommendations(model_stats)
        
        assert isinstance(recommendations, list)
        low_cache_rec = [r for r in recommendations if "low-cache-model" in r.model_id]
        assert len(low_cache_rec) > 0
    
    def test_estimate_potential_savings(self, cache_analytics, mock_cached_model):
        """Test estimating potential savings."""
        from src.core.cache_models import ModelCacheStats
        
        model_stats = {
            "test-model": ModelCacheStats(
                model_id="test-model",
                total_requests=100,
                total_prompt_tokens=1_000_000
            )
        }
        
        with patch.object(cache_analytics.model_cache, 'get_model', return_value=mock_cached_model):
            result = cache_analytics.estimate_potential_savings(
                model_stats,
                target_hit_rate=70.0
            )
            
            assert 'current_savings' in result
            assert 'potential_additional_savings' in result
            assert 'target_hit_rate' in result


class TestDailyCacheStats:
    """Test cases for DailyCacheStats dataclass."""
    
    def test_daily_stats_creation(self):
        """Test creating DailyCacheStats instance."""
        from src.core.cache_models import DailyCacheStats
        
        stats = DailyCacheStats(date="2024-01-15")
        
        assert stats.date == "2024-01-15"
        assert stats.total_requests == 0
        assert stats.total_savings_usd == 0.0
    
    def test_daily_stats_with_values(self):
        """Test DailyCacheStats with values."""
        from src.core.cache_models import DailyCacheStats
        
        stats = DailyCacheStats(
            date="2024-01-15",
            total_requests=100,
            total_prompt_tokens=50000,
            total_cached_tokens=25000,
            total_savings_usd=15.50,
            models_used=["llama", "deepseek"],
            cache_hit_rate=50.0
        )
        
        assert stats.cache_hit_rate == 50.0


class TestCachePerformanceReport:
    """Test cases for CachePerformanceReport dataclass."""
    
    def test_report_creation(self):
        """Test creating CachePerformanceReport."""
        from src.core.cache_models import CachePerformanceReport
        
        report = CachePerformanceReport(
            start_date="2024-01-01",
            end_date="2024-01-07",
            total_requests=100,
            total_savings_usd=50.0,
            overall_cache_hit_rate=45.0,
            overall_savings_percent=30.0,
            model_stats={},
            daily_stats=[],
            top_saving_models=[],
            lowest_hit_rate_models=[]
        )
        
        assert report.total_requests == 100
        assert report.overall_cache_hit_rate == 45.0


class TestNegativeCases:
    """Negative test cases for cache analytics."""
    
    def test_analyze_billing_with_malformed_records(self):
        """Test analyzing billing records with malformed data."""
        with patch('src.core.cache_analytics.VeniceAPIClient'), \
             patch('src.core.cache_analytics.ModelCacheManager'):
            from src.core.cache_analytics import CacheAnalytics
            
            analytics = CacheAnalytics()
            
            malformed_records = [
                {"sku": None, "amount": "invalid"},
                {"sku": "", "amount": None},
                {},
                {"sku": "test-sku", "amount": -0.001, "inferenceDetails": None}
            ]
            
            report, model_stats = analytics.analyze_billing_records(malformed_records)
            
            assert report is not None
    
    def test_calculate_metrics_with_zero_tokens(self):
        """Test calculating metrics with zero tokens."""
        with patch('src.core.cache_analytics.VeniceAPIClient'), \
             patch('src.core.cache_analytics.ModelCacheManager'):
            from src.core.cache_analytics import CacheAnalytics
            
            analytics = CacheAnalytics()
            
            with patch.object(analytics.model_cache, 'get_model', return_value=None):
                metrics = analytics.calculate_request_cache_metrics(
                    model_id="test",
                    prompt_tokens=0,
                    completion_tokens=0,
                    cached_tokens=0
                )
                
                assert metrics.total_cost_usd == 0.0
    
    def test_extract_model_id_from_none_sku(self):
        """Test extracting model ID from None SKU."""
        with patch('src.core.cache_analytics.VeniceAPIClient'), \
             patch('src.core.cache_analytics.ModelCacheManager'):
            from src.core.cache_analytics import CacheAnalytics
            
            analytics = CacheAnalytics()
            
            result = analytics._extract_model_id_from_sku(None)
            assert result is None
            
            result = analytics._extract_model_id_from_sku("")
            assert result is None
    
    def test_generate_recommendations_with_no_data(self):
        """Test generating recommendations with insufficient data."""
        with patch('src.core.cache_analytics.VeniceAPIClient'), \
             patch('src.core.cache_analytics.ModelCacheManager'):
            from src.core.cache_analytics import CacheAnalytics
            from src.core.cache_models import ModelCacheStats
            
            analytics = CacheAnalytics()
            
            model_stats = {
                "low-volume": ModelCacheStats(
                    model_id="low-volume",
                    total_requests=2
                )
            }
            
            recommendations = analytics.generate_optimization_recommendations(model_stats)
            
            assert len(recommendations) == 0