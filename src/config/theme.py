from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QObject, Signal
from .config import Config


class Theme(QObject):
    """Centralized theme management with signal-based updates and QPalette support."""
    
    theme_changed = Signal(str)  # Emits new theme mode when changed
    
    def __init__(self, mode=None):
        super().__init__()
        self.mode = mode or Config.THEME_MODE
        
    @property
    def background(self):
        if self.mode == 'dark':
            return '#1e1e1e'
        return '#ffffff'
    
    @property
    def text(self):
        if self.mode == 'dark':
            return '#ffffff'
        return '#000000'
    
    @property
    def accent(self):
        if self.mode == 'dark':
            return '#0078d7'
        return '#005a9e'
    
    @property
    def input_background(self):
        if self.mode == 'dark':
            return '#252526'
        return '#f5f5f5'
    
    @property
    def error(self):
        return '#ff4444' if self.mode == 'dark' else '#cc0000'
    
    @property
    def warning(self):
        return '#ffc107' if self.mode == 'dark' else '#ff9800'
    
    @property
    def success(self):
        return '#00c853' if self.mode == 'dark' else '#4caf50'
    
    @property
    def border(self):
        if self.mode == 'dark':
            return '#333333'
        return '#cccccc'
    
    @property
    def card_background(self):
        if self.mode == 'dark':
            return '#2d2d2d'
        return '#f0f0f0'
    
    @property
    def text_secondary(self):
        if self.mode == 'dark':
            return '#bbbbbb'
        return '#666666'
    
    @property
    def positive(self):
        return '#00cc66' if self.mode == 'dark' else '#00994d'
    
    @property
    def negative(self):
        return '#ff3333' if self.mode == 'dark' else '#cc0000'
    
    @property
    def primary(self):
        return '#0078d7' if self.mode == 'dark' else '#005a9e'
    
    @property
    def hero_gradient_start(self):
        """Start color for hero card gradient background"""
        return '#2d5aa0' if self.mode == 'dark' else '#4a90e2'
    
    @property
    def hero_gradient_end(self):
        """End color for hero card gradient background"""
        return '#1e3a5f' if self.mode == 'dark' else '#357abd'
    
    @property
    def button_background(self):
        """Background color for buttons"""
        return '#404040' if self.mode == 'dark' else '#f0f0f0'
    
    @property
    def button_hover(self):
        """Button hover color"""
        return '#505050' if self.mode == 'dark' else '#e0e0e0'
    
    @property
    def button_pressed(self):
        """Button pressed color"""
        return '#606060' if self.mode == 'dark' else '#d0d0d0'
    
    @property
    def accent_light(self):
        """Lighter accent color for hover states"""
        return '#4da6e8' if self.mode == 'dark' else '#3377bb'
    
    @property
    def accent_dark(self):
        """Darker accent color for pressed states"""
        return '#0055a0' if self.mode == 'dark' else '#003d7a'
    
    @property
    def accent_darker(self):
        """Darkest accent color for active states"""
        return '#003d7a' if self.mode == 'dark' else '#002266'
    
    @property
    def text_muted(self):
        """Muted text color for secondary information"""
        return self.text_secondary
    
    @property
    def widget_bg(self):
        """Widget background (alias for card_background)"""
        return self.card_background
    
    @property
    def success_light(self):
        """Lighter success color for backgrounds"""
        return '#33d977' if self.mode == 'dark' else '#66cc66'
    
    @property
    def success_dark(self):
        """Darker success color for pressed states"""
        return '#00994d' if self.mode == 'dark' else '#388e3c'
    
    @property
    def card_background_light(self):
        """Lighter card background for nested elements"""
        return '#3a3a3a' if self.mode == 'dark' else '#ffffff'
    
    @property
    def chart_colors(self):
        """Theme-adapted colors for data visualization charts.
        
        Returns 6 distinct colors that maintain good contrast in both themes.
        Colors adapt to theme mode while preserving visual distinction.
        """
        if self.mode == 'dark':
            return [
                '#5dade2',  # Bright blue (was #2196F3)
                '#f39c12',  # Bright orange (was #FF9800)
                '#bb8fce',  # Bright purple (was #9C27B0)
                '#48c9b0',  # Bright cyan (was #00BCD4)
                '#ec7063',  # Bright pink/red (was #E91E63)
                '#aab7b8',  # Bright brown/gray (was #795548)
            ]
        else:
            return [
                '#2874a6',  # Deep blue
                '#d68910',  # Deep orange
                '#7d3c98',  # Deep purple
                '#117a65',  # Deep cyan/teal
                '#c0392b',  # Deep red
                '#5d6d7e',  # Deep gray
            ]
    
    @property
    def status_colors(self):
        """Color coding system for immediate status recognition"""
        return {
            'active': self.positive,         # Green for active/online
            'inactive': self.negative,       # Red for inactive/offline
            'warning': self.warning,         # Yellow/orange for warnings
            'neutral': self.text_secondary,  # Gray for neutral states
            'loading': self.primary,         # Blue for loading states
            'price_positive': self.positive, # Use theme's positive color
            'price_negative': self.negative, # Use theme's negative color
        }
    
    @property
    def theme_colors(self):
        """Return a dictionary of all theme colors for easy access."""
        return {
            'background': self.background,
            'text': self.text,
            'accent': self.accent,
            'accent_light': self.accent_light,
            'accent_dark': self.accent_dark,
            'accent_darker': self.accent_darker,
            'input_background': self.input_background,
            'error': self.error,
            'warning': self.warning,
            'success': self.success,
            'success_light': self.success_light,
            'success_dark': self.success_dark,
            'border': self.border,
            'card_background': self.card_background,
            'card_background_light': self.card_background_light,
            'text_secondary': self.text_secondary,
            'text_muted': self.text_muted,
            'widget_bg': self.widget_bg,
            'positive': self.positive,
            'negative': self.negative,
            'primary': self.primary,
            'text_primary': self.text,
            'hero_gradient_start': self.hero_gradient_start,
            'hero_gradient_end': self.hero_gradient_end,
            'button_background': self.button_background,
            'button_hover': self.button_hover,
            'button_pressed': self.button_pressed,
            **self.status_colors
        }
    
    def set_mode(self, mode):
        """Change theme mode and emit signal for all widgets to update.
        
        Args:
            mode: 'dark' or 'light'
        """
        if mode != self.mode:
            self.mode = mode
            self.theme_changed.emit(mode)
    
    def apply_palette(self, app):
        """Apply theme colors to Qt application's global palette.
        
        This ensures native Qt widgets inherit theme colors by default.
        
        Args:
            app: QApplication instance
        """
        palette = QPalette()
        
        # Base colors
        palette.setColor(QPalette.Window, QColor(self.background))
        palette.setColor(QPalette.WindowText, QColor(self.text))
        palette.setColor(QPalette.Base, QColor(self.input_background))
        palette.setColor(QPalette.AlternateBase, QColor(self.card_background))
        palette.setColor(QPalette.Text, QColor(self.text))
        palette.setColor(QPalette.Button, QColor(self.button_background))
        palette.setColor(QPalette.ButtonText, QColor(self.text))
        palette.setColor(QPalette.BrightText, QColor(self.text))
        
        # Highlight colors (selections)
        palette.setColor(QPalette.Highlight, QColor(self.accent))
        palette.setColor(QPalette.HighlightedText, QColor(self.text))
        
        # Disabled state
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(self.text_secondary))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(self.text_secondary))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(self.text_secondary))
        
        # Links
        palette.setColor(QPalette.Link, QColor(self.accent))
        palette.setColor(QPalette.LinkVisited, QColor(self.primary))
        
        app.setPalette(palette)
