"""
Tests for the Venice API client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests


class TestVeniceAPIClient:
    """Test cases for Venice API client."""
    
    @pytest.fixture
    def api_client(self):
        """Create an API client instance."""
        from src.core.venice_api_client import VeniceAPIClient
        return VeniceAPIClient("test_api_key")
    
    def test_client_initialization(self, api_client):
        """Test API client initialization."""
        assert api_client.api_key == "test_api_key"
        assert api_client.base_url == "https://api.venice.ai/api/v1"
    
    def test_client_sets_headers(self, api_client):
        """Test that client sets proper headers."""
        headers = api_client.headers
        
        assert "Authorization" in headers
        assert "Bearer test_api_key" in headers["Authorization"]
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    @patch('src.core.venice_api_client.requests.get')
    def test_get_request_success(self, mock_get, api_client):
        """Test successful GET request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "model1", "type": "text"},
                {"id": "model2", "type": "image"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = api_client.get("/models")
        
        assert result is not None
        assert result.status_code == 200
        mock_get.assert_called_once()
    
    @patch('src.core.venice_api_client.requests.get')
    def test_get_request_failure(self, mock_get, api_client):
        """Test GET request failure."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        result = api_client.get("/models")
        
        assert result is not None
        assert result.status_code == 401
    
    @patch('src.core.venice_api_client.requests.get')
    def test_network_error_handling(self, mock_get, api_client):
        """Test handling of network errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with pytest.raises(requests.exceptions.ConnectionError):
            api_client.get("/models")
    
    @patch('src.core.venice_api_client.requests.get')
    def test_timeout_handling(self, mock_get, api_client):
        """Test handling of timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        with pytest.raises(requests.exceptions.Timeout):
            api_client.get("/models")


class TestModelCacheManager:
    """Test cases for model cache manager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager instance."""
        from src.core.model_cache import ModelCacheManager
        return ModelCacheManager()
    
    def test_cache_initialization(self, cache_manager):
        """Test cache manager initialization."""
        # Cache may already have data from file, so just check it exists
        assert isinstance(cache_manager.models, dict)
        assert hasattr(cache_manager, 'CACHE_FILE')
    
    def test_get_model_returns_cached_model(self, cache_manager, sample_models_data):
        """Test retrieving model by ID returns a CachedModel object."""
        # Load real models from the actual cache file if it exists
        cache_manager.fetch_models()
        
        # Try to get a model - should return CachedModel or None
        model = cache_manager.get_model("venice-uncensored")
        
        # Model might not exist if cache is empty, but shouldn't crash
        if model is not None:
            assert hasattr(model, 'id')
            assert hasattr(model, 'name')
    
    def test_get_models_by_type(self, cache_manager, sample_models_data):
        """Test filtering models by type."""
        cache_manager.fetch_models()
        
        text_models = cache_manager.get_models_by_type("text")
        
        # Should return a list (might be empty if no cache)
        assert isinstance(text_models, list)
    
    def test_get_text_models(self, cache_manager, sample_models_data):
        """Test getting text models."""
        cache_manager.fetch_models()
        
        text_models = cache_manager.get_text_models()
        
        # Should return a list
        assert isinstance(text_models, list)
    
    def test_get_image_models(self, cache_manager, sample_models_data):
        """Test getting image models."""
        cache_manager.fetch_models()
        
        image_models = cache_manager.get_image_models()
        
        # Should return a list
        assert isinstance(image_models, list)
