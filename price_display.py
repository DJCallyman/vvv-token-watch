from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from .theme import Theme

class PriceDisplayWidget(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.holding_value = 0.0
        self.init_ui()
        
    def init_ui(self):
        self.price_label = QLabel("0.00")
        self.price_label.setStyleSheet(f"""
            color: {self.theme.text};
            background-color: {self.theme.input_background};
            font-size: 24px;
            padding: 10px;
            border-radius: 4px;
        """)
        self.price_label.setAlignment(Qt.AlignCenter)
        
        self.holding_label = QLabel("Holding: $0.00")
        self.holding_label.setStyleSheet(f"""
            color: {self.theme.text};
            font-size: 16px;
            margin-top: 5px;
        """)
        self.holding_label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.price_label)
        layout.addWidget(self.holding_label)
        self.setLayout(layout)
        
    def set_price(self, price: float):
        self.price_label.setText(f"${price:.2f}")
        
    def set_holding_value(self, value: float):
        self.holding_value = value
        self.holding_label.setText(f"Holding: ${value:,.2f}")
        
    def set_validation_state(self, state: str):
        """Update styling based on validation state"""
        if state == "error":
            color = self.theme.error
        elif state == "warning":
            color = self.theme.warning
        else:
            color = self.theme.text
            
        self.price_label.setStyleSheet(f"""
            color: {color};
            background-color: {self.theme.input_background};
            font-size: 24px;
            padding: 10px;
            border-radius: 4px;
        """)
        self.holding_label.setStyleSheet(f"""
            color: {color};
            font-size: 16px;
            margin-top: 5px;
        """)
