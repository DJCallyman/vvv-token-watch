"""
Tests for the configuration module.
"""

import pytest
import os
from unittest.mock import patch, mock_open
from pathlib import Path


class TestConfig:
    """Test cases for configuration management."""
    
    def test_config_validates_admin_key(self):
        """Test that configuration validation checks for admin key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.config.config.load_dotenv'):
                from src.config.config import Config
                
                # Clear the admin key
                Config.VENICE_ADMIN_KEY = None
                
                is_valid, error_msg = Config.validate()
                
                assert not is_valid
                assert "admin" in error_msg.lower() or "API" in error_msg
    
    def test_config_validates_with_key(self):
        """Test that configuration validation passes with valid key."""
        # Import first to get the class
        from src.config.config import Config
        
        # Temporarily set the key
        original_key = Config.VENICE_ADMIN_KEY
        try:
            Config.VENICE_ADMIN_KEY = 'valid_key'
            is_valid, error_msg = Config.validate()
            
            # Should be valid with admin key
            assert is_valid
        finally:
            Config.VENICE_ADMIN_KEY = original_key


class TestThemeConfig:
    """Test cases for theme configuration."""
    
    def test_theme_default_dark(self):
        """Test that default theme is dark."""
        from src.config.theme import Theme
        
        theme = Theme()
        
        assert theme.mode == "dark"
        assert theme.background == "#1e1e1e"
        assert theme.text == "#ffffff"
    
    def test_theme_light_mode(self):
        """Test light theme configuration."""
        from src.config.theme import Theme
        
        theme = Theme(mode="light")
        
        assert theme.mode == "light"
        assert theme.background == "#ffffff"
        assert theme.text == "#000000"
    
    def test_theme_set_mode(self):
        """Test theme set_mode functionality."""
        from src.config.theme import Theme
        
        theme = Theme(mode="dark")
        assert theme.mode == "dark"
        
        theme.set_mode("light")
        assert theme.mode == "light"
        
        theme.set_mode("dark")
        assert theme.mode == "dark"
    
    def test_theme_colors_accessible(self):
        """Test that theme colors are accessible."""
        from src.config.theme import Theme
        
        theme = Theme()
        colors = theme.theme_colors
        
        assert "background" in colors
        assert "text" in colors
        assert "accent" in colors
        assert "card_background" in colors
