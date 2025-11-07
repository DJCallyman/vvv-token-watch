"""
Base worker classes for API operations.

This module provides base classes for all worker threads to eliminate code duplication
and provide consistent error handling, signal definitions, and execution patterns.
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtCore import QThread, Signal

from src.core.venice_api_client import VeniceAPIClient


logger = logging.getLogger(__name__)


class BaseAPIWorker(QThread):
    """
    Base worker class for all API operations with Venice API.
    
    Provides:
    - Consistent signal definitions
    - Centralized error handling
    - Template method pattern for data fetching
    - Logging integration
    
    Subclasses should override fetch_data() method.
    """
    
    # Standard signals used by all workers
    result = Signal(dict)           # {'success': bool, 'data': Any, 'error': str}
    error_occurred = Signal(str)    # Error message string
    progress_updated = Signal(str)  # Progress/status message
    
    def __init__(self, api_client: VeniceAPIClient, parent=None):
        """
        Initialize base worker.
        
        Args:
            api_client: Configured VeniceAPIClient instance
            parent: Parent QObject
        """
        super().__init__(parent)
        self.api_client = api_client
        self._should_stop = False
    
    def run(self):
        """
        Main execution method. Calls fetch_data() and handles results/errors.
        Template method pattern - subclasses override fetch_data().
        """
        result = {'success': False, 'data': None, 'error': None}
        
        try:
            logger.debug(f"{self.__class__.__name__} starting data fetch")
            data = self.fetch_data()
            
            if self._should_stop:
                logger.debug(f"{self.__class__.__name__} stopped by request")
                return
            
            result['success'] = True
            result['data'] = data
            logger.debug(f"{self.__class__.__name__} fetch completed successfully")
            
        except Exception as e:
            error_msg = self.handle_error(e)
            result['error'] = error_msg
            logger.error(f"{self.__class__.__name__} failed: {error_msg}", exc_info=True)
        
        finally:
            self.result.emit(result)
    
    def fetch_data(self) -> Any:
        """
        Override this method in subclasses to implement specific data fetching logic.
        
        Returns:
            Data to be emitted in result signal
            
        Raises:
            Exception: Any exception will be caught and handled by run()
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement fetch_data()")
    
    def handle_error(self, error: Exception) -> str:
        """
        Handle errors with consistent logging and signal emission.
        Can be overridden for custom error handling.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Formatted error message string
        """
        error_msg = f"{self.__class__.__name__} error: {str(error)}"
        self.error_occurred.emit(error_msg)
        return error_msg
    
    def stop(self):
        """Request the worker to stop (for long-running operations)"""
        self._should_stop = True
    
    def emit_progress(self, message: str):
        """Helper to emit progress updates"""
        logger.debug(f"{self.__class__.__name__}: {message}")
        self.progress_updated.emit(message)


class SimpleAPIWorker(BaseAPIWorker):
    """
    Simple worker for basic GET requests that don't need complex processing.
    Can be used for endpoints that return data in a standard format.
    """
    
    def __init__(self, api_client: VeniceAPIClient, endpoint: str, 
                 params: Optional[Dict] = None, timeout: int = 20, parent=None):
        """
        Initialize simple API worker.
        
        Args:
            api_client: Configured VeniceAPIClient instance
            endpoint: API endpoint path (e.g., "/models")
            params: Optional query parameters
            timeout: Request timeout in seconds
            parent: Parent QObject
        """
        super().__init__(api_client, parent)
        self.endpoint = endpoint
        self.params = params or {}
        self.timeout = timeout
    
    def fetch_data(self) -> Dict[str, Any]:
        """Fetch data from the configured endpoint"""
        self.emit_progress(f"Fetching from {self.endpoint}")
        response = self.api_client.get(self.endpoint, params=self.params, timeout=self.timeout)
        data = response.json()
        
        # Validate response structure
        if not data or 'data' not in data:
            raise ValueError("API response missing 'data' key or is empty")
        
        return data
