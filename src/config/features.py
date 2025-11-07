"""
Feature flags for phase-based functionality.

This module provides centralized feature availability checking to eliminate
scattered try/except import patterns throughout the codebase.
"""

import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Centralized feature flag management for phase-based development.
    
    Provides lazy loading and caching of feature availability to reduce
    redundant import attempts and provide consistent feature checking.
    """
    
    # Cache for feature availability
    _phase2_available: Optional[bool] = None
    _phase3_available: Optional[bool] = None
    _feature_modules: Dict[str, Any] = {}
    
    @classmethod
    def is_phase2_available(cls) -> bool:
        """
        Check if Phase 2 features (analytics, exchange rates) are available.
        
        Returns:
            True if Phase 2 modules can be imported
        """
        if cls._phase2_available is None:
            try:
                from src.analytics.usage_analytics import UsageAnalytics
                from src.services.exchange_rate_service import ExchangeRateService
                
                # Cache the modules for later use
                cls._feature_modules['UsageAnalytics'] = UsageAnalytics
                cls._feature_modules['ExchangeRateService'] = ExchangeRateService
                
                cls._phase2_available = True
                logger.info("Phase 2 features are available")
                
            except ImportError as e:
                cls._phase2_available = False
                logger.warning(f"Phase 2 features not available: {e}")
        
        return cls._phase2_available
    
    @classmethod
    def is_phase3_available(cls) -> bool:
        """
        Check if Phase 3 features (key management, reports) are available.
        
        Returns:
            True if Phase 3 modules can be imported
        """
        if cls._phase3_available is None:
            try:
                from src.widgets.key_management_widget import APIKeyManagementWidget
                from src.analytics.usage_reports import UsageReportGenerator
                from src.services.venice_key_management import get_key_management_service
                
                # Cache the modules for later use
                cls._feature_modules['APIKeyManagementWidget'] = APIKeyManagementWidget
                cls._feature_modules['UsageReportGenerator'] = UsageReportGenerator
                cls._feature_modules['get_key_management_service'] = get_key_management_service
                
                cls._phase3_available = True
                logger.info("Phase 3 features are available")
                
            except ImportError as e:
                cls._phase3_available = False
                logger.warning(f"Phase 3 features not available: {e}")
        
        return cls._phase3_available
    
    @classmethod
    def get_feature_module(cls, module_name: str) -> Optional[Any]:
        """
        Get a cached feature module if available.
        
        Args:
            module_name: Name of the module to retrieve
            
        Returns:
            The module/class or None if not available
        """
        return cls._feature_modules.get(module_name)
    
    @classmethod
    def reset(cls):
        """Reset all cached feature flags (useful for testing)"""
        cls._phase2_available = None
        cls._phase3_available = None
        cls._feature_modules.clear()
    
    @classmethod
    def get_available_features(cls) -> Dict[str, bool]:
        """
        Get a summary of all feature availability.
        
        Returns:
            Dictionary mapping feature names to availability status
        """
        return {
            'phase2': cls.is_phase2_available(),
            'phase3': cls.is_phase3_available(),
        }
    
    @classmethod
    def log_feature_status(cls):
        """Log the current status of all features"""
        features = cls.get_available_features()
        logger.info("Feature availability summary:")
        for feature, available in features.items():
            status = "✓ Available" if available else "✗ Not Available"
            logger.info(f"  {feature}: {status}")


class FeatureGuard:
    """
    Context manager and decorator for feature-gated code execution.
    """
    
    def __init__(self, feature_check, fallback=None, error_msg: str = "Feature not available"):
        """
        Initialize feature guard.
        
        Args:
            feature_check: Callable that returns True if feature is available
            fallback: Optional fallback value to return if feature unavailable
            error_msg: Error message to log if feature unavailable
        """
        self.feature_check = feature_check
        self.fallback = fallback
        self.error_msg = error_msg
    
    def __enter__(self):
        if not self.feature_check():
            raise ImportError(self.error_msg)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def __call__(self, func):
        """Use as decorator"""
        def wrapper(*args, **kwargs):
            if self.feature_check():
                return func(*args, **kwargs)
            else:
                logger.warning(f"{self.error_msg} - using fallback")
                return self.fallback
        return wrapper


# Convenience decorators for common feature gates
def requires_phase2(fallback=None):
    """Decorator that requires Phase 2 features"""
    return FeatureGuard(
        FeatureFlags.is_phase2_available,
        fallback=fallback,
        error_msg="Phase 2 features required but not available"
    )


def requires_phase3(fallback=None):
    """Decorator that requires Phase 3 features"""
    return FeatureGuard(
        FeatureFlags.is_phase3_available,
        fallback=fallback,
        error_msg="Phase 3 features required but not available"
    )
