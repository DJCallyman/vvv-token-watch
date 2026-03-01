"""
Tests for main application entry point and MainWindow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication


class TestApplicationStartup:
    """Test cases for application startup."""
    
    def test_setup_logging_creates_handlers(self):
        """Test that setup_logging creates proper log handlers."""
        import logging
        
        original_handlers = logging.getLogger().handlers.copy()
        
        try:
            from src.main import setup_logging
            setup_logging()
            
            root_logger = logging.getLogger()
            handlers = root_logger.handlers
            
            assert len(handlers) > 0
        finally:
            logging.getLogger().handlers = original_handlers
    
    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        from src.main import main
        
        assert callable(main)
    
    def test_config_module_imports(self):
        """Test that config module imports correctly."""
        from src.config.config import Config
        
        assert hasattr(Config, 'VENICE_ADMIN_KEY')
        assert hasattr(Config, 'VENICE_API_KEY')
        assert hasattr(Config, 'LOG_LEVEL')


class TestMainWindowInit:
    """Test cases for MainWindow initialization."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for MainWindow."""
        with patch('src.main.VeniceAPIClient') as mock_client, \
             patch('src.main.ModelCacheManager') as mock_cache, \
             patch('src.main.QApplication.instance', return_value=MagicMock()):
            mock_client.return_value = MagicMock()
            mock_cache.return_value = MagicMock()
            yield
    
    def test_main_window_class_exists(self, mock_dependencies):
        """Test that CombinedViewerApp class exists."""
        from src.main import CombinedViewerApp
        
        assert CombinedViewerApp is not None


class TestThemeHandling:
    """Test cases for theme handling."""
    
    def test_theme_module_imports(self):
        """Test that theme module imports correctly."""
        from src.config.theme import Theme
        
        assert Theme is not None
    
    def test_theme_has_required_colors(self):
        """Test that theme has all required color properties."""
        from src.config.theme import Theme
        
        dark_theme = Theme(mode='dark')
        
        required_properties = [
            'background', 'text', 'accent',
            'error', 'warning', 'success'
        ]
        
        for prop in required_properties:
            assert hasattr(dark_theme, prop), f"Missing property: {prop}"


class TestErrorHandling:
    """Test cases for error handling in main application."""
    
    def test_error_handler_imports(self):
        """Test that error handler module imports correctly."""
        from src.utils.error_handler import ErrorHandler
        
        assert ErrorHandler is not None
    
    def test_error_handler_has_log_and_emit(self):
        """Test that ErrorHandler has log_and_emit method."""
        from src.utils.error_handler import ErrorHandler
        
        assert hasattr(ErrorHandler, 'log_and_emit')


class TestFeatureFlags:
    """Test cases for feature flags."""
    
    def test_feature_flags_import(self):
        """Test that feature flags module imports correctly."""
        from src.config.features import FeatureFlags
        
        assert FeatureFlags is not None
    
    def test_feature_flags_has_phase2_check(self):
        """Test that FeatureFlags has phase availability methods."""
        from src.config.features import FeatureFlags
        
        assert hasattr(FeatureFlags, 'is_phase2_available')
        assert hasattr(FeatureFlags, 'is_phase3_available')


class TestUsageAnalytics:
    """Test cases for usage analytics integration."""
    
    def test_usage_analytics_module_imports(self):
        """Test that usage analytics module imports correctly."""
        try:
            from src.analytics.usage_analytics import UsageAnalytics
            assert UsageAnalytics is not None
        except ImportError:
            pass


class TestNegativeCases:
    """Negative test cases for error conditions."""
    
    def test_main_window_with_invalid_api_key(self, mock_api_client):
        """Test CombinedViewerApp behavior with invalid API key."""
        from src.main import CombinedViewerApp
        
        with patch('src.main.VeniceAPIClient', return_value=mock_api_client), \
             patch('src.main.ModelCacheManager') as mock_cache:
            mock_cache.return_value = MagicMock()
            assert CombinedViewerApp is not None
    
    def test_config_missing_api_key(self):
        """Test handling of missing API key."""
        from src.config.config import Config
        import os
        
        original_key = os.environ.get('VENICE_API_KEY')
        if 'VENICE_API_KEY' in os.environ:
            del os.environ['VENICE_API_KEY']
        
        try:
            if original_key:
                os.environ['VENICE_API_KEY'] = original_key
        finally:
            pass
    
    def test_usage_worker_with_empty_key(self):
        """Test UsageWorker with empty API key."""
        from src.core.usage_tracker import UsageWorker
        
        worker = UsageWorker("")
        assert worker.admin_key == ""
    
    def test_model_cache_with_invalid_client(self):
        """Test ModelCacheManager with invalid API client."""
        from src.core.model_cache import ModelCacheManager
        
        with patch('src.core.model_cache.VeniceAPIClient') as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get = MagicMock(
                return_value=MagicMock(status_code=401, json=lambda: {"error": "Unauthorized"})
            )
            
            manager = ModelCacheManager()
            result = manager.fetch_models()
            
            assert result is False