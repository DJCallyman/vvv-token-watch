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
