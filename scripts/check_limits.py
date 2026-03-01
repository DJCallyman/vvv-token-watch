"""
Utility script to check API rate limits.

This is a standalone script for debugging rate limit issues.
Run directly: python scripts/check_limits.py
"""

import os
import sys
import json
import logging

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

RATE_LIMIT_URL = "https://api.venice.ai/api/v1/api_keys/rate_limits/log"
REQUEST_TIMEOUT = 30


def get_api_key() -> str:
    """Get API key from environment with validation."""
    api_key = os.getenv("VENICE_API_KEY") or os.getenv("VENICE_ADMIN_KEY")
    if not api_key:
        logger.error("VENICE_API_KEY or VENICE_ADMIN_KEY not set in environment")
        sys.exit(1)
    return api_key


def check_rate_limits(api_key: str) -> dict:
    """
    Fetch rate limit logs from Venice API.
    
    Args:
        api_key: Venice API key
        
    Returns:
        API response data as dictionary
        
    Raises:
        requests.exceptions.RequestException: On network errors
        ValueError: On invalid response
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            RATE_LIMIT_URL, 
            headers=headers, 
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        
        return data
        
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise


def main():
    """Main entry point."""
    try:
        api_key = get_api_key()
        data = check_rate_limits(api_key)
        
        print("Successfully retrieved rate limit logs:")
        print(json.dumps(data, indent=4))
        
        if data.get("data"):
            print(f"\nFound {len(data['data'])} recent rate limit events.")
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Data error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
