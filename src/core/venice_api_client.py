"""
Venice API Client helper for shared API request functionality.

This module provides a reusable base class for making requests to the Venice API,
eliminating code duplication across worker threads and service classes.
"""

from typing import Dict, Optional
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.config import Config

logger = logging.getLogger(__name__)


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
        Make a GET request to the Venice API with automatic retry on transient failures.
        
        Args:
            endpoint: API endpoint path (e.g., "/billing/usage")
            params: Optional query parameters
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure after retries
        """
        return self._get_with_retry(endpoint, params, timeout)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, 
                                       requests.exceptions.Timeout,
                                       requests.exceptions.HTTPError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Venice API request failed, retrying in {retry_state.next_action.sleep}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        ),
        reraise=True
    )
    def _get_with_retry(self, endpoint: str, params: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """Internal GET method with retry logic."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=timeout)
        # Only retry on 5xx errors, not 4xx client errors
        if response.status_code >= 500:
            response.raise_for_status()
        return response
    
    def post(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """
        Make a POST request to the Venice API with automatic retry on transient failures.
        
        Args:
            endpoint: API endpoint path (e.g., "/api_keys")
            data: Optional JSON payload
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Response object from requests library
            
        Raises:
            requests.exceptions.RequestException: On API request failure after retries
        """
        return self._post_with_retry(endpoint, data, timeout)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, 
                                       requests.exceptions.Timeout,
                                       requests.exceptions.HTTPError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Venice API POST request failed, retrying in {retry_state.next_action.sleep}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        ),
        reraise=True
    )
    def _post_with_retry(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """Internal POST method with retry logic."""
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
        if response.status_code >= 500:
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
