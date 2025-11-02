from .config import Config


class Theme:
    def __init__(self, mode=None):
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
    def status_colors(self):
        """Color coding system for immediate status recognition"""
        return {
            'active': self.positive,         # Green for active/online
            'inactive': self.negative,       # Red for inactive/offline
            'warning': self.warning,         # Yellow/orange for warnings
            'neutral': self.text_secondary,  # Gray for neutral states
            'loading': self.primary,         # Blue for loading states
            'price_positive': '#00cc66',     # Green for positive price change
            'price_negative': '#ff3333',     # Red for negative price change
        }
    
    @property
    def theme_colors(self):
        """Return a dictionary of all theme colors for easy access."""
        return {
            'background': self.background,
            'text': self.text,
            'accent': self.accent,
            'input_background': self.input_background,
            'error': self.error,
            'warning': self.warning,
            'success': self.success,
            'border': self.border,
            'card_background': self.card_background,
            'text_secondary': self.text_secondary,
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
