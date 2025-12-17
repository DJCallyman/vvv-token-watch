from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from src.config.theme import Theme

class ModelViewerWidget(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.init_ui()
        
    def init_ui(self):
        self.viewer_label = QLabel("3D Model Viewer")
        self.viewer_label.setStyleSheet(f"""
            color: {self.theme.text};
            background-color: {self.theme.background};
            font-size: 18px;
            padding: 15px;
            border: 1px solid {self.theme.accent};
            border-radius: 4px;
        """)
        self.viewer_label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer_label)
        self.setLayout(layout)
        
    def update_model(self, model_data):
        """Placeholder for actual model update logic - will be implemented with 3D rendering"""
