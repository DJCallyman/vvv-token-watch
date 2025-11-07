"""
Factory for creating worker instances with consistent configuration.

This module eliminates duplication in worker initialization by providing
factory methods that handle API client creation and configuration.
"""

from typing import Optional
from src.core.venice_api_client import VeniceAPIClient
from src.core.base_worker import SimpleAPIWorker
from src.config.config import Config


class APIWorkerFactory:
    """
    Factory for creating worker instances with shared configuration.
    
    Provides centralized worker creation with consistent API client setup,
    reducing initialization boilerplate throughout the application.
    """
    
    @staticmethod
    def _get_api_client(api_key: Optional[str] = None, use_admin_key: bool = False) -> VeniceAPIClient:
        """
        Get a configured API client.
        
        Args:
            api_key: Optional explicit API key. If None, uses config defaults
            use_admin_key: If True, uses admin key from config
            
        Returns:
            Configured VeniceAPIClient instance
        """
        if api_key:
            return VeniceAPIClient(api_key)
        elif use_admin_key:
            return VeniceAPIClient(Config.VENICE_ADMIN_KEY)
        else:
            return VeniceAPIClient(Config.VENICE_API_KEY)
    
    @staticmethod
    def create_usage_worker(api_key: Optional[str] = None, parent=None):
        """
        Create a UsageWorker with admin API client.
        
        Args:
            api_key: Optional admin API key. If None, uses Config.VENICE_ADMIN_KEY
            parent: Parent QObject
            
        Returns:
            Configured UsageWorker instance
        """
        from src.core.usage_tracker import UsageWorker
        
        key = api_key or Config.VENICE_ADMIN_KEY
        return UsageWorker(key, parent)
    
    @staticmethod
    def create_web_usage_worker(api_key: Optional[str] = None, days: int = 7, parent=None):
        """
        Create a WebUsageWorker with admin API client.
        
        Args:
            api_key: Optional admin API key. If None, uses Config.VENICE_ADMIN_KEY
            days: Number of days to fetch (default 7)
            parent: Parent QObject
            
        Returns:
            Configured WebUsageWorker instance
        """
        from src.core.web_usage import WebUsageWorker
        
        key = api_key or Config.VENICE_ADMIN_KEY
        return WebUsageWorker(key, days, parent)
    
    @staticmethod
    def create_model_analytics_worker(api_key: Optional[str] = None, parent=None):
        """
        Create a ModelAnalyticsWorker with admin API client.
        
        Args:
            api_key: Optional admin API key. If None, uses Config.VENICE_ADMIN_KEY
            parent: Parent QObject
            
        Returns:
            Configured ModelAnalyticsWorker instance
        """
        from src.analytics.model_comparison import ModelAnalyticsWorker
        
        key = api_key or Config.VENICE_ADMIN_KEY
        return ModelAnalyticsWorker(key)
    
    @staticmethod
    def create_exchange_rate_worker(parent=None):
        """
        Create an ExchangeRateWorker.
        
        Args:
            parent: Parent QObject
            
        Returns:
            Configured ExchangeRateWorker instance
        """
        from src.services.exchange_rate_service import ExchangeRateWorker
        
        return ExchangeRateWorker(parent)
    
    @staticmethod
    def create_simple_worker(endpoint: str, params: Optional[dict] = None,
                            use_admin_key: bool = False, timeout: int = 20,
                            api_key: Optional[str] = None, parent=None) -> SimpleAPIWorker:
        """
        Create a SimpleAPIWorker for basic GET requests.
        
        Args:
            endpoint: API endpoint path (e.g., "/models")
            params: Optional query parameters
            use_admin_key: Whether to use admin API key
            timeout: Request timeout in seconds
            api_key: Optional explicit API key
            parent: Parent QObject
            
        Returns:
            Configured SimpleAPIWorker instance
        """
        api_client = APIWorkerFactory._get_api_client(api_key, use_admin_key)
        return SimpleAPIWorker(api_client, endpoint, params, timeout, parent)
    
    @staticmethod
    def create_models_worker(model_type: str = "all", parent=None) -> SimpleAPIWorker:
        """
        Create a worker for fetching model list.
        
        Args:
            model_type: Model type to filter by (default "all")
            parent: Parent QObject
            
        Returns:
            Configured SimpleAPIWorker for /models endpoint
        """
        return APIWorkerFactory.create_simple_worker(
            endpoint="/models",
            params={"type": model_type},
            use_admin_key=False,
            parent=parent
        )
    
    @staticmethod
    def create_traits_worker(parent=None) -> SimpleAPIWorker:
        """
        Create a worker for fetching model traits.
        
        Args:
            parent: Parent QObject
            
        Returns:
            Configured SimpleAPIWorker for /models/traits endpoint
        """
        return APIWorkerFactory.create_simple_worker(
            endpoint="/models/traits",
            use_admin_key=False,
            parent=parent
        )
    
    @staticmethod
    def create_style_presets_worker(parent=None) -> SimpleAPIWorker:
        """
        Create a worker for fetching image style presets.
        
        Args:
            parent: Parent QObject
            
        Returns:
            Configured SimpleAPIWorker for /image/styles endpoint
        """
        return APIWorkerFactory.create_simple_worker(
            endpoint="/image/styles",
            use_admin_key=False,
            parent=parent
        )


class WorkerPool:
    """
    Simple worker pool for managing multiple worker instances.
    Helps track and clean up workers when needed.
    """
    
    def __init__(self):
        self._workers = []
    
    def add_worker(self, worker):
        """Add a worker to the pool"""
        self._workers.append(worker)
        return worker
    
    def create_and_add(self, factory_method, *args, **kwargs):
        """Create a worker using factory and add to pool"""
        worker = factory_method(*args, **kwargs)
        self.add_worker(worker)
        return worker
    
    def stop_all(self):
        """Stop all workers in the pool"""
        for worker in self._workers:
            if hasattr(worker, 'stop'):
                worker.stop()
    
    def wait_all(self, timeout: int = 5000):
        """Wait for all workers to finish"""
        for worker in self._workers:
            if worker.isRunning():
                worker.wait(timeout)
    
    def cleanup(self):
        """Clean up all workers"""
        self.stop_all()
        self.wait_all()
        self._workers.clear()
