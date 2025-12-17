"""
Centralized error handling utilities.

This module provides consistent error handling, logging, and signal emission
across the entire application to eliminate scattered error handling patterns.
"""

import logging
from typing import Optional
from PySide6.QtCore import Signal


logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling with consistent logging patterns.
    
    Provides static methods for common error handling scenarios to ensure
    consistent error messages, logging levels, and signal emissions throughout
    the application.
    """
    
    @staticmethod
    def log_and_emit(error: Exception, context: str, 
                     signal: Optional[Signal] = None,
                     include_traceback: bool = True) -> str:
        """
        Handle an error with logging and optional signal emission.
        
        Args:
            error: The exception that occurred
            context: Context string describing where/what failed (e.g., "Failed to fetch usage data")
            signal: Optional Signal to emit the error message to
            include_traceback: Whether to log full traceback (default True)
            
        Returns:
            Formatted error message string
        """
        error_msg = f"{context}: {str(error)}"
        
        if include_traceback:
            logger.error(error_msg, exc_info=True)
        else:
            logger.error(error_msg)
        
        if signal:
            signal.emit(error_msg)
        
        return error_msg
    
    @staticmethod
    def log_warning(message: str, context: Optional[str] = None):
        """
        Log a warning message with consistent formatting.
        
        Args:
            message: The warning message
            context: Optional context for where the warning occurred
        """
        if context:
            full_message = f"{context}: {message}"
        else:
            full_message = message
        
        logger.warning(full_message)
    
    @staticmethod
    def log_debug(message: str, context: Optional[str] = None):
        """
        Log a debug message with consistent formatting.
        
        Args:
            message: The debug message
            context: Optional context for where the debug occurred
        """
        if context:
            full_message = f"{context}: {message}"
        else:
            full_message = message
        
        logger.debug(full_message)
    
    @staticmethod
    def log_info(message: str, context: Optional[str] = None):
        """
        Log an info message with consistent formatting.
        
        Args:
            message: The info message
            context: Optional context for the information
        """
        if context:
            full_message = f"{context}: {message}"
        else:
            full_message = message
        
        logger.info(full_message)
    
    @staticmethod
    def handle_api_error(error: Exception, endpoint: str, 
                        signal: Optional[Signal] = None) -> str:
        """
        Handle API-specific errors with appropriate context.
        
        Args:
            error: The exception that occurred
            endpoint: The API endpoint that failed
            signal: Optional Signal to emit the error to
            
        Returns:
            Formatted error message
        """
        context = f"API request to {endpoint} failed"
        return ErrorHandler.log_and_emit(error, context, signal)
    
    @staticmethod
    def handle_worker_error(error: Exception, worker_name: str,
                           signal: Optional[Signal] = None) -> str:
        """
        Handle worker thread errors with appropriate context.
        
        Args:
            error: The exception that occurred
            worker_name: Name of the worker that failed
            signal: Optional Signal to emit the error to
            
        Returns:
            Formatted error message
        """
        context = f"{worker_name} thread error"
        return ErrorHandler.log_and_emit(error, context, signal)
    
    @staticmethod
    def handle_data_error(error: Exception, operation: str,
                         signal: Optional[Signal] = None) -> str:
        """
        Handle data processing/parsing errors.
        
        Args:
            error: The exception that occurred
            operation: Description of the data operation that failed
            signal: Optional Signal to emit the error to
            
        Returns:
            Formatted error message
        """
        context = f"Data processing error during {operation}"
        return ErrorHandler.log_and_emit(error, context, signal)
    
    @staticmethod
    def handle_ui_error(error: Exception, component: str) -> str:
        """
        Handle UI component errors (typically don't need signal emission).
        
        Args:
            error: The exception that occurred
            component: Name of the UI component that failed
            
        Returns:
            Formatted error message
        """
        context = f"UI component error in {component}"
        return ErrorHandler.log_and_emit(error, context, signal=None, include_traceback=False)
    
    @staticmethod
    def safe_execute(func, *args, default=None, error_msg: Optional[str] = None, **kwargs):
        """
        Execute a function with error handling, returning default on failure.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            default: Default value to return on error (default None)
            error_msg: Custom error message prefix
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result or default value on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = error_msg or f"Error executing {func.__name__}"
            ErrorHandler.log_and_emit(e, context, include_traceback=False)
            return default


class ErrorMessages:
    """
    Common error message templates for consistency across the application.
    """
    
    # API errors
    API_CONNECTION_FAILED = "Failed to connect to Venice API"
    API_TIMEOUT = "API request timed out"
    API_INVALID_RESPONSE = "API returned invalid or unexpected response"
    API_UNAUTHORIZED = "API authentication failed - check your API key"
    API_RATE_LIMITED = "API rate limit exceeded"
    
    # Data errors
    DATA_PARSE_FAILED = "Failed to parse API response data"
    DATA_VALIDATION_FAILED = "Data validation failed"
    DATA_MISSING_FIELD = "Required field missing from data"
    
    # Worker errors
    WORKER_INITIALIZATION_FAILED = "Worker thread failed to initialize"
    WORKER_EXECUTION_FAILED = "Worker thread execution failed"
    
    # UI errors
    UI_UPDATE_FAILED = "Failed to update UI component"
    UI_RENDER_FAILED = "Failed to render UI element"
    
    # File errors
    FILE_LOAD_FAILED = "Failed to load file"
    FILE_SAVE_FAILED = "Failed to save file"
    FILE_PARSE_FAILED = "Failed to parse file"
    
    @staticmethod
    def format(template: str, **kwargs) -> str:
        """Format an error message template with variables"""
        return template.format(**kwargs)
