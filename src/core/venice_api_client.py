"""
Venice API Client helper for shared API request functionality.

This module provides a reusable base class for making requests to the Venice API,
eliminating code duplication across worker threads and service classes.
"""

from typing import Dict, Optional
import requests


class VeniceAPIClient:
    """
    Base client for Venice API requests with shared configuration.
    
    Provides common setup for API URL, headers, and authentication that is
    reused across multiple worker threads and service classes.
    """
    
    BASE_URL = "https://api.venice.ai/api/v1"
    
    def __init__(self, api_key: str):
        """
        Initialize the Venice API client.
        
        Args:
            api_key: Venice API key (regular or admin key depending on endpoints needed)
        """
        self.api_key = api_key
        self.base_url = self.BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get(self, endpoint: str, params: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """
        Make a GET request to the Venice API.
        
        Args:
            endpoint: API endpoint path (e.g., "/billing/usage")
            params: Optional query parameters
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=timeout)
        response.raise_for_status()
        return response
    
    def post(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """
        Make a POST request to the Venice API.
        
        Args:
            endpoint: API endpoint path (e.g., "/api_keys")
            data: Optional JSON payload
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
        response.raise_for_status()
        return response
    
    def put(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """
        Make a PUT request to the Venice API.
        
        Args:
            endpoint: API endpoint path
            data: Optional JSON payload
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.put(url, headers=self.headers, json=data, timeout=timeout)
        response.raise_for_status()
        return response
    
    def delete(self, endpoint: str, timeout: int = 30) -> requests.Response:
        """
        Make a DELETE request to the Venice API.
        
        Args:
            endpoint: API endpoint path
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self.headers, timeout=timeout)
        response.raise_for_status()
        return response
