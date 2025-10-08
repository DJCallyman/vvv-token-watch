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
            'text_primary': self.text
        }
