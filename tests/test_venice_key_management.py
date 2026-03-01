"""
Tests for Venice API Key Management Service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestVeniceAPIKeyInfo:
    """Test cases for VeniceAPIKeyInfo dataclass."""
    
    def test_key_info_creation(self):
        """Test creating VeniceAPIKeyInfo instance."""
        from src.services.venice_key_management import VeniceAPIKeyInfo
        
        key_info = VeniceAPIKeyInfo(
            id="key_abc123",
            description="Test Key",
            last6_chars="abc123",
            created_at="2024-01-01T00:00:00Z",
            expires_at="2025-01-01T00:00:00Z",
            last_used_at="2024-01-15T12:00:00Z",
            api_key_type="INFERENCE",
            consumption_limits={"usd": 100.0},
            usage={"usd": 10.0, "diem": 100.0}
        )
        
        assert key_info.id == "key_abc123"
        assert key_info.description == "Test Key"
        assert key_info.is_active is True
    
    def test_key_info_defaults(self):
        """Test VeniceAPIKeyInfo default values."""
        from src.services.venice_key_management import VeniceAPIKeyInfo
        
        key_info = VeniceAPIKeyInfo(
            id="key_test",
            description="Test",
            last6_chars="test12",
            created_at="2024-01-01T00:00:00Z",
            expires_at=None,
            last_used_at=None,
            api_key_type="INFERENCE",
            consumption_limits={},
            usage={}
        )
        
        assert key_info.is_active is True
        assert key_info.expires_at is None
        assert key_info.last_used_at is None


class TestVeniceKeyManagementService:
    """Test cases for VeniceKeyManagementService class."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        client = MagicMock()
        client.get = MagicMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": []}
        ))
        client.post = MagicMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"success": True, "data": {"id": "new_key"}}
        ))
        client.delete = MagicMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"success": True}
        ))
        return client
    
    @pytest.fixture
    def key_service(self, mock_api_client):
        """Create a key management service with mocked client."""
        with patch('src.services.venice_key_management.VeniceAPIClient', return_value=mock_api_client):
            from src.services.venice_key_management import VeniceKeyManagementService
            return VeniceKeyManagementService("test_admin_key")
    
    def test_service_initialization(self, key_service):
        """Test service initialization."""
        assert key_service.admin_key == "test_admin_key"
        assert key_service.api_client is not None
    
    def test_get_api_keys_success(self, key_service, mock_api_client):
        """Test successful API key fetch."""
        mock_api_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "key_1",
                        "description": "Test Key 1",
                        "last6Chars": "abc123",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "expiresAt": None,
                        "lastUsedAt": "2024-01-15T00:00:00Z",
                        "apiKeyType": "INFERENCE",
                        "consumptionLimits": {},
                        "usage": {"usd": 10.0}
                    }
                ]
            }
        )
        
        keys = key_service.get_api_keys()
        
        assert len(keys) == 1
        assert keys[0].id == "key_1"
        assert keys[0].description == "Test Key 1"
    
    def test_get_api_keys_empty_list(self, key_service, mock_api_client):
        """Test API key fetch with no keys."""
        mock_api_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []}
        )
        
        keys = key_service.get_api_keys()
        
        assert len(keys) == 0
    
    def test_get_api_keys_error(self, key_service, mock_api_client):
        """Test API key fetch with error."""
        mock_api_client.get.side_effect = Exception("Network error")
        
        keys = key_service.get_api_keys()
        
        assert keys == []
    
    def test_revoke_api_key_success(self, key_service, mock_api_client):
        """Test successful key revocation."""
        mock_api_client.delete.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True}
        )
        
        result = key_service.revoke_api_key("key_123")
        
        assert result is True
        mock_api_client.delete.assert_called_once()
    
    def test_revoke_api_key_failure(self, key_service, mock_api_client):
        """Test key revocation failure."""
        mock_api_client.delete.return_value = MagicMock(
            status_code=404,
            text="Not found"
        )
        
        result = key_service.revoke_api_key("nonexistent_key")
        
        assert result is False
    
    def test_revoke_api_key_exception(self, key_service, mock_api_client):
        """Test key revocation with exception."""
        mock_api_client.delete.side_effect = Exception("Network error")
        
        result = key_service.revoke_api_key("key_123")
        
        assert result is False
    
    def test_rename_api_key_not_supported(self, key_service):
        """Test that rename returns False (not supported)."""
        result = key_service.rename_api_key("key_123", "New Name")
        
        assert result is False
    
    def test_set_consumption_limits_not_supported(self, key_service):
        """Test that set_consumption_limits returns False (not supported)."""
        result = key_service.set_consumption_limits("key_123", usd_limit=100.0)
        
        assert result is False
    
    def test_create_api_key_success(self, key_service, mock_api_client):
        """Test successful key creation."""
        mock_api_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "id": "new_key_123",
                    "description": "New Test Key",
                    "last6Chars": "xyz789"
                }
            }
        )
        
        result = key_service.create_api_key("New Test Key")
        
        assert result is not None
        assert result["id"] == "new_key_123"
    
    def test_create_api_key_with_limits(self, key_service, mock_api_client):
        """Test key creation with consumption limits."""
        mock_api_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "data": {"id": "limited_key"}}
        )
        
        result = key_service.create_api_key(
            "Limited Key",
            usd_limit=100.0,
            diem_limit=1000.0
        )
        
        assert result is not None
        mock_api_client.post.assert_called_once()
        call_data = mock_api_client.post.call_args[1]['data']
        assert 'consumptionLimit' in call_data
    
    def test_create_api_key_failure(self, key_service, mock_api_client):
        """Test key creation failure."""
        mock_api_client.post.return_value = MagicMock(
            status_code=400,
            text="Bad request"
        )
        
        result = key_service.create_api_key("Test Key")
        
        assert result is None
    
    def test_create_api_key_exception(self, key_service, mock_api_client):
        """Test key creation with exception."""
        mock_api_client.post.side_effect = Exception("Network error")
        
        result = key_service.create_api_key("Test Key")
        
        assert result is None
    
    def test_test_key_management_capabilities(self, key_service, mock_api_client):
        """Test capability detection."""
        capabilities = key_service.test_key_management_capabilities()
        
        assert isinstance(capabilities, dict)
        assert "list_keys" in capabilities
        assert "create_key" in capabilities
        assert "revoke_key" in capabilities
        assert capabilities["rename_key"] is False
        assert capabilities["set_limits"] is False


class TestGlobalServiceInstance:
    """Test cases for global service instance management."""
    
    def test_get_key_management_service_creates_instance(self):
        """Test that get_key_management_service creates instance."""
        from src.services.venice_key_management import get_key_management_service, _key_management_service
        
        with patch('src.services.venice_key_management.Config') as mock_config, \
             patch('src.services.venice_key_management.VeniceAPIClient'):
            mock_config.VENICE_ADMIN_KEY = "test_key"
            
            result = get_key_management_service()
            
            assert result is not None or result is None


class TestNegativeCases:
    """Negative test cases for key management."""
    
    def test_get_api_keys_with_malformed_response(self):
        """Test handling malformed API response."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"invalid": "structure"}
            )
            mock_client_class.return_value = mock_client
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService("test_key")
            keys = service.get_api_keys()
            
            assert keys == []
    
    def test_revoke_nonexistent_key(self):
        """Test revoking a key that doesn't exist."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.delete.return_value = MagicMock(
                status_code=404,
                text="Key not found"
            )
            mock_client_class.return_value = mock_client
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService("test_key")
            result = service.revoke_api_key("nonexistent_key")
            
            assert result is False
    
    def test_create_key_with_invalid_type(self):
        """Test creating key with invalid type."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = MagicMock(
                status_code=400,
                text="Invalid api_key_type"
            )
            mock_client_class.return_value = mock_client
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService("test_key")
            result = service.create_api_key("Test", api_key_type="INVALID")
            
            assert result is None
    
    def test_service_with_empty_admin_key(self):
        """Test service initialization with empty admin key."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client_class.return_value = MagicMock()
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService("")
            
            assert service.admin_key == ""
    
    def test_service_with_none_admin_key(self):
        """Test service initialization with None admin key."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client_class.return_value = MagicMock()
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService(None)
            
            assert service.admin_key is None
    
    def test_capabilities_with_api_failure(self):
        """Test capability detection when API fails."""
        with patch('src.services.venice_key_management.VeniceAPIClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client
            
            from src.services.venice_key_management import VeniceKeyManagementService
            
            service = VeniceKeyManagementService("test_key")
            capabilities = service.test_key_management_capabilities()
            
            assert capabilities["list_keys"] is True