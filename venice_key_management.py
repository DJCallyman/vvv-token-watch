"""
Venice API Key Management Service for Phase 3 enhancements.
Handles actual API calls to Venice.ai for key management operations.
"""

import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

try:
    from .config import Config
except ImportError:
    from config import Config


@dataclass
class VeniceAPIKeyInfo:
    """Complete API key information from Venice API"""
    id: str
    description: str
    last6_chars: str
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    api_key_type: str
    consumption_limits: Dict[str, Any]
    usage: Dict[str, Any]
    is_active: bool = True


class VeniceKeyManagementService:
    """Service for managing Venice API keys through the Venice API"""
    
    def __init__(self, admin_key: str):
        """
        Initialize with admin API key.
        
        Args:
            admin_key: Venice ADMIN API key with full permissions
        """
        self.admin_key = admin_key
        self.base_url = "https://api.venice.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.admin_key}",
            "Content-Type": "application/json"
        }
    
    def get_api_keys(self) -> List[VeniceAPIKeyInfo]:
        """
        Fetch all API keys from Venice.
        
        Returns:
            List of VeniceAPIKeyInfo objects
        """
        try:
            response = requests.get(f"{self.base_url}/api_keys", headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            keys = []
            
            for key_data in data.get("data", []):
                key_info = VeniceAPIKeyInfo(
                    id=key_data.get("id"),
                    description=key_data.get("description", ""),
                    last6_chars=key_data.get("last6Chars", ""),
                    created_at=key_data.get("createdAt", ""),
                    expires_at=key_data.get("expiresAt"),
                    last_used_at=key_data.get("lastUsedAt"),
                    api_key_type=key_data.get("apiKeyType", ""),
                    consumption_limits=key_data.get("consumptionLimits", {}),
                    usage=key_data.get("usage", {}),
                    is_active=True  # If it's returned, it's active
                )
                keys.append(key_info)
            
            return keys
            
        except Exception as e:
            print(f"ERROR: Failed to fetch API keys: {e}")
            return []
    
    def rename_api_key(self, key_id: str, new_description: str) -> bool:
        """
        Attempt to rename an API key by updating its description.
        
        NOTE: Based on Venice API specification, this operation is NOT SUPPORTED.
        Venice API does not provide PATCH/PUT endpoints for existing keys.
        
        Args:
            key_id: The API key ID
            new_description: New description/name for the key
            
        Returns:
            False - This operation is not supported by Venice API
        """
        print(f"WARNING: Venice API does not support renaming existing keys")
        print(f"The Venice API specification only provides GET, POST, and DELETE operations for API keys")
        print(f"To change a key's description, you would need to:")
        print(f"  1. Create a new key with the desired description")
        print(f"  2. Update your applications to use the new key")
        print(f"  3. Delete the old key")
        return False
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke (delete) an API key.
        
        Args:
            key_id: The API key ID to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{self.base_url}/api_keys",
                headers=self.headers,
                params={"id": key_id},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"SUCCESS: Key {key_id} revoked successfully")
                    return True
                else:
                    print(f"ERROR: Revocation failed - API returned success=false")
                    return False
            else:
                print(f"ERROR: Revocation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Exception during revocation: {e}")
            return False
    
    def set_consumption_limits(self, key_id: str, usd_limit: Optional[float] = None, 
                             diem_limit: Optional[float] = None) -> bool:
        """
        Attempt to set consumption limits for an API key.
        
        NOTE: Based on Venice API specification, this operation is NOT SUPPORTED.
        Venice API does not provide PATCH/PUT endpoints for existing keys.
        
        Args:
            key_id: The API key ID
            usd_limit: USD spending limit
            diem_limit: DIEM spending limit
            
        Returns:
            False - This operation is not supported by Venice API
        """
        print(f"WARNING: Venice API does not support setting consumption limits on existing keys")
        print(f"The Venice API specification only provides GET, POST, and DELETE operations for API keys")
        print(f"Consumption limits can only be set during key creation (POST /api_keys)")
        print(f"To set limits on an existing key, you would need to:")
        print(f"  1. Create a new key with the desired consumption limits")
        print(f"  2. Update your applications to use the new key")
        print(f"  3. Delete the old key")
        return False
    
    def create_api_key(self, description: str, api_key_type: str = "INFERENCE",
                      usd_limit: Optional[float] = None, 
                      diem_limit: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new API key.
        
        Args:
            description: Description/name for the key
            api_key_type: "ADMIN" or "INFERENCE"
            usd_limit: Optional USD spending limit
            diem_limit: Optional DIEM spending limit
            
        Returns:
            Dict with key info if successful, None otherwise
        """
        try:
            create_data = {
                "description": description,
                "apiKeyType": api_key_type
            }
            
            # Add consumption limits if specified
            if usd_limit is not None or diem_limit is not None:
                consumption_limit = {}
                if usd_limit is not None:
                    consumption_limit["usd"] = usd_limit
                if diem_limit is not None:
                    consumption_limit["diem"] = diem_limit
                # VCU is required in the schema, set to null if not specified
                if "vcu" not in consumption_limit:
                    consumption_limit["vcu"] = None
                    
                create_data["consumptionLimit"] = consumption_limit
            
            response = requests.post(
                f"{self.base_url}/api_keys",
                headers=self.headers,
                json=create_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"SUCCESS: Created new API key '{description}'")
                    return result.get("data")
                else:
                    print(f"ERROR: Creation failed - API returned success=false")
                    return None
            else:
                print(f"ERROR: Creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"ERROR: Exception during key creation: {e}")
            return None
    
    def test_key_management_capabilities(self) -> Dict[str, bool]:
        """
        Test what key management operations are supported by the Venice API.
        Based on API specification analysis.
        
        Returns:
            Dict mapping operation names to whether they're supported
        """
        # Based on Venice API specification (swagger.yaml), these are the actual capabilities:
        capabilities = {
            "list_keys": True,        # GET /api_keys - ✅ Supported
            "get_key_details": True,  # GET /api_keys/{id} - ✅ Supported  
            "create_key": True,       # POST /api_keys - ✅ Supported
            "revoke_key": True,       # DELETE /api_keys?id={id} - ✅ Supported
            "rename_key": False,      # ❌ No PATCH/PUT endpoints available
            "set_limits": False,      # ❌ No PATCH/PUT endpoints available
        }
        
        # We can still test if the basic endpoints are reachable
        try:
            # Test list keys (should work)
            response = requests.get(f"{self.base_url}/api_keys", headers=self.headers, timeout=10)
            capabilities["list_keys"] = (response.status_code == 200)
            
        except Exception as e:
            print(f"WARNING: Exception during capability testing: {e}")
            # Fall back to API spec-based capabilities
        
        return capabilities


# Global service instance
_key_management_service = None

def get_key_management_service() -> Optional[VeniceKeyManagementService]:
    """Get the global key management service instance"""
    global _key_management_service
    
    if _key_management_service is None:
        admin_key = Config.VENICE_ADMIN_KEY
        if admin_key:
            _key_management_service = VeniceKeyManagementService(admin_key)
        else:
            print("WARNING: No VENICE_ADMIN_KEY configured - key management unavailable")
    
    return _key_management_service