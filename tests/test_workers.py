"""
Tests for worker threads.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import QThread


class TestUsageWorker:
    """Test cases for usage tracking worker."""
    
    def test_worker_initialization(self):
        """Test usage worker initialization."""
        from src.core.usage_tracker import UsageWorker
        
        worker = UsageWorker("test_admin_key")
        
        assert worker.admin_key == "test_admin_key"
        assert not worker.isRunning()
    
    def test_worker_has_required_attributes(self):
        """Test that worker has required attributes."""
        from src.core.usage_tracker import UsageWorker
        
        worker = UsageWorker("test_admin_key")
        
        # Check for required signals/attributes (UsageWorker has specific signals, not 'result')
        assert hasattr(worker, 'usage_data_updated')
        assert hasattr(worker, 'balance_data_updated')
        assert hasattr(worker, 'error_occurred')
        assert hasattr(worker, 'api_client')


class TestPriceWorker:
    """Test cases for price tracking worker."""
    
    def test_worker_initialization(self):
        """Test price worker initialization."""
        from src.core.price_worker import PriceWorker
        
        worker = PriceWorker("venice-token", ["usd", "aud"])
        
        assert worker.token_id == "venice-token"
        assert worker.currencies == ["usd", "aud"]
    
    def test_worker_has_required_attributes(self):
        """Test that worker has required attributes."""
        from src.core.price_worker import PriceWorker
        
        worker = PriceWorker("venice-token", ["usd"])
        
        # Check for required signals/attributes (PriceWorker has specific signals)
        assert hasattr(worker, 'price_updated')
        assert hasattr(worker, 'error_occurred')


class TestWorkerFactory:
    """Test cases for worker factory."""
    
    def test_factory_creates_traits_worker(self):
        """Test factory creates traits worker."""
        from src.core.worker_factory import APIWorkerFactory
        
        worker = APIWorkerFactory.create_traits_worker()
        
        assert worker is not None
        assert hasattr(worker, 'result')
    
    def test_factory_creates_usage_worker(self):
        """Test factory creates usage worker."""
        from src.core.worker_factory import APIWorkerFactory
        
        worker = APIWorkerFactory.create_usage_worker("test_key")
        
        assert worker is not None
        assert worker.admin_key == "test_key"
    
    def test_factory_creates_models_worker(self):
        """Test factory creates models worker."""
        from src.core.worker_factory import APIWorkerFactory
        
        worker = APIWorkerFactory.create_models_worker()
        
        assert worker is not None


class TestBaseWorker:
    """Test cases for base worker class."""
    
    def test_base_worker_stops_cleanly(self):
        """Test that base worker stops cleanly."""
        from src.core.base_worker import BaseAPIWorker
        from src.core.venice_api_client import VeniceAPIClient
        
        client = VeniceAPIClient("test_key")
        worker = BaseAPIWorker(client)
        
        # Should have _stop_event attribute (thread-safe)
        assert hasattr(worker, '_stop_event')
        assert not worker._stop_event.is_set()
        
        # Stop should set event
        worker.stop()
        assert worker._stop_event.is_set()
    
    def test_base_worker_has_stop_method(self):
        """Test that base worker has stop method."""
        from src.core.base_worker import BaseAPIWorker
        from src.core.venice_api_client import VeniceAPIClient
        
        client = VeniceAPIClient("test_key")
        worker = BaseAPIWorker(client)
        
        # Verify stop method exists
        assert hasattr(worker, 'stop')
        assert callable(getattr(worker, 'stop'))
    
    def test_base_worker_has_is_stopped_method(self):
        """Test that base worker has is_stopped method for thread-safe check."""
        from src.core.base_worker import BaseAPIWorker
        from src.core.venice_api_client import VeniceAPIClient
        
        client = VeniceAPIClient("test_key")
        worker = BaseAPIWorker(client)
        
        assert hasattr(worker, 'is_stopped')
        assert not worker.is_stopped()
        worker.stop()
        assert worker.is_stopped()
    
    def test_base_worker_has_fetch_data(self):
        """Test that base worker requires fetch_data implementation."""
        from src.core.base_worker import BaseAPIWorker
        from src.core.venice_api_client import VeniceAPIClient
        
        client = VeniceAPIClient("test_key")
        worker = BaseAPIWorker(client)
        
        # fetch_data should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            worker.fetch_data()
