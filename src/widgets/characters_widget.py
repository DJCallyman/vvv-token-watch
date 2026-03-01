"""
Characters browsing widget for Venice AI Characters API.

Displays available Venice characters with search, filtering, and detail views.
Uses the preview /characters endpoint.
"""

import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QGroupBox, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont

from src.core.worker_factory import APIWorkerFactory

logger = logging.getLogger(__name__)


class CharactersWidget(QWidget):
    """
    Widget for browsing Venice AI characters.
    
    Features:
    - Search characters by name/description
    - Filter by web-enabled, pro models
    - Display character cards with details
    - Pagination support
    """
    
    character_selected = Signal(str)  # Emits character slug
    
    def __init__(self, theme, parent=None):
        """
        Initialize the characters widget.
        
        Args:
            theme: Theme object with color properties
            parent: Parent widget
        """
        super().__init__(parent)
        self.theme = theme
        self.characters_data: List[Dict] = []
        self.current_offset = 0
        self.page_size = 50
        self._worker: Optional[QThread] = None
        
        self._init_ui()
    
    def _cleanup_worker(self):
        """Clean up worker thread."""
        if self._worker is not None:
            try:
                if self._worker.isRunning():
                    self._worker.quit()
                    if not self._worker.wait(2000):
                        self._worker.terminate()
                        self._worker.wait()
                self._worker.deleteLater()
            except RuntimeError:
                pass
            self._worker = None
    
    def closeEvent(self, event):
        """Handle widget close."""
        self._cleanup_worker()
        super().closeEvent(event)
    
    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Header
        header = QLabel("Venice Characters (Preview API)")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header.setFont(header_font)
        header.setStyleSheet(f"color: {self.theme.text};")
        main_layout.addWidget(header)
        
        note_label = QLabel("Browse characters available for use with the Venice chat completions API.")
        note_label.setStyleSheet(f"color: {self.theme.text}; font-style: italic;")
        note_label.setWordWrap(True)
        main_layout.addWidget(note_label)
        
        # Controls row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search characters...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.theme.accent};
            }}
        """)
        self.search_input.returnPressed.connect(self.fetch_characters)
        controls_layout.addWidget(self.search_input)
        
        # Web-enabled filter
        self.web_filter = QComboBox()
        self.web_filter.addItems(["All", "Web Enabled", "Not Web Enabled"])
        self.web_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        controls_layout.addWidget(self.web_filter)
        
        # Fetch button
        button_style = f"""
            QPushButton {{
                background-color: {self.theme.accent};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: {self.theme.border};
                color: {self.theme.text};
            }}
        """
        
        self.fetch_button = QPushButton("Load Characters")
        self.fetch_button.setStyleSheet(button_style)
        self.fetch_button.clicked.connect(self.fetch_characters)
        controls_layout.addWidget(self.fetch_button)
        
        # Load more button
        self.load_more_button = QPushButton("Load More")
        self.load_more_button.setStyleSheet(button_style)
        self.load_more_button.clicked.connect(self._load_more)
        self.load_more_button.setVisible(False)
        controls_layout.addWidget(self.load_more_button)
        
        controls_layout.addStretch()
        
        # Results count label
        self.results_label = QLabel("")
        self.results_label.setStyleSheet(f"color: {self.theme.text}; font-style: italic;")
        controls_layout.addWidget(self.results_label)
        
        main_layout.addLayout(controls_layout)
        
        # Scroll area for character cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background-color: {self.theme.background}; border: none;")
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.addStretch()
        
        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area)
    
    def fetch_characters(self):
        """Fetch characters from the Venice API."""
        self.current_offset = 0
        self._clear_cards()
        self._do_fetch()
    
    def _load_more(self):
        """Load next page of characters."""
        self.current_offset += self.page_size
        self._do_fetch(append=True)
    
    def _do_fetch(self, append: bool = False):
        """Execute the character fetch request."""
        self._cleanup_worker()
        
        self.fetch_button.setEnabled(False)
        self.load_more_button.setVisible(False)
        
        if not append:
            self.results_label.setText("Loading...")
        
        params = {
            "limit": self.page_size,
            "offset": self.current_offset,
            "isAdult": "false"
        }
        
        search_text = self.search_input.text().strip()
        if search_text:
            params["search"] = search_text
        
        web_filter = self.web_filter.currentText()
        if web_filter == "Web Enabled":
            params["isWebEnabled"] = "true"
        elif web_filter == "Not Web Enabled":
            params["isWebEnabled"] = "false"
        
        self._worker = APIWorkerFactory.create_simple_worker(
            endpoint="/characters",
            params=params,
            use_admin_key=False,
            parent=self
        )
        self._worker.result.connect(
            lambda result, a=append: self._on_fetch_complete(result, a)
        )
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()
    
    def _on_fetch_complete(self, result: Dict, append: bool = False):
        """Handle character fetch results."""
        self.fetch_button.setEnabled(True)
        
        if not result.get('success'):
            self.results_label.setText(f"Error: {result.get('error', 'Unknown')}")
            return
        
        data = result.get('data', {})
        characters = data.get('data', [])
        
        if not append:
            self.characters_data = characters
        else:
            self.characters_data.extend(characters)
        
        # Display character cards
        if not append:
            self._clear_cards()
        
        for char in characters:
            self._add_character_card(char)
        
        total_shown = len(self.characters_data)
        self.results_label.setText(f"Showing {total_shown} characters")
        
        # Show load more if we got a full page
        self.load_more_button.setVisible(len(characters) >= self.page_size)
    
    def _clear_cards(self):
        """Clear all character cards from the display."""
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _add_character_card(self, char: Dict):
        """Add a character card to the display."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.card_background};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 10px;
            }}
            QFrame:hover {{
                border-color: {self.theme.accent};
            }}
        """)
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(12, 8, 12, 8)
        
        # Top row: name + badges
        top_row = QHBoxLayout()
        
        name_label = QLabel(char.get('name', 'Unknown'))
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {self.theme.text}; border: none;")
        top_row.addWidget(name_label)
        
        # Badges
        if char.get('webEnabled'):
            web_badge = QLabel("🌐 Web")
            web_badge.setStyleSheet(f"color: #4CAF50; font-size: 10px; border: none;")
            top_row.addWidget(web_badge)
        
        model_id = char.get('modelId', '')
        if model_id:
            model_badge = QLabel(f"🤖 {model_id}")
            model_badge.setStyleSheet(f"color: {self.theme.accent}; font-size: 10px; border: none;")
            top_row.addWidget(model_badge)
        
        imports = char.get('stats', {}).get('imports', 0)
        if imports > 0:
            pop_badge = QLabel(f"⭐ {imports}")
            pop_badge.setStyleSheet(f"color: #FFC107; font-size: 10px; border: none;")
            top_row.addWidget(pop_badge)
        
        top_row.addStretch()
        card_layout.addLayout(top_row)
        
        # Slug
        slug = char.get('slug', '')
        if slug:
            slug_label = QLabel(f"slug: {slug}")
            slug_label.setStyleSheet(f"color: {self.theme.text}; font-size: 9px; opacity: 0.6; border: none;")
            card_layout.addWidget(slug_label)
        
        # Description
        description = char.get('description', '')
        if description:
            desc_label = QLabel(description[:200] + ('...' if len(description) > 200 else ''))
            desc_label.setStyleSheet(f"color: {self.theme.text}; border: none;")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)
        
        # Tags
        tags = char.get('tags', [])
        if tags:
            tags_text = ", ".join(tags[:8])
            if len(tags) > 8:
                tags_text += f" (+{len(tags) - 8} more)"
            tags_label = QLabel(f"Tags: {tags_text}")
            tags_label.setStyleSheet(f"color: {self.theme.text}; font-size: 9px; opacity: 0.7; border: none;")
            tags_label.setWordWrap(True)
            card_layout.addWidget(tags_label)
        
        # Share URL
        share_url = char.get('shareUrl', '')
        if share_url:
            url_label = QLabel(f"<a href='{share_url}' style='color: {self.theme.accent};'>{share_url}</a>")
            url_label.setOpenExternalLinks(True)
            url_label.setStyleSheet(f"font-size: 9px; border: none;")
            card_layout.addWidget(url_label)
        
        # Insert before the stretch
        insert_pos = max(0, self.cards_layout.count() - 1)
        self.cards_layout.insertWidget(insert_pos, card)
