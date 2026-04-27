"""
Centralized styling constants for PySide6/Qt widgets.

This module provides consistent styling values across the application:
- Border radius values
- Spacing/padding values
- Font sizes and weights
- Animation durations

All widgets should reference these constants instead of hardcoding values.
"""

from typing import Final


BORDER_RADIUS_SM: Final = 4
BORDER_RADIUS_MD: Final = 6
BORDER_RADIUS_LG: Final = 8
BORDER_RADIUS_XL: Final = 12


PADDING_SM: Final = 4
PADDING_MD: Final = 8
PADDING_LG: Final = 12
PADDING_XL: Final = 16
PADDING_XXL: Final = 20


MARGIN_SM: Final = 4
MARGIN_MD: Final = 8
MARGIN_LG: Final = 12
MARGIN_XL: Final = 16


SPACING_SM: Final = 4
SPACING_MD: Final = 8
SPACING_LG: Final = 12
SPACING_XL: Final = 16
SPACING_XXL: Final = 20


FONT_SIZE_SM: Final = 9
FONT_SIZE_MD: Final = 10
FONT_SIZE_LG: Final = 12
FONT_SIZE_XL: Final = 14
FONT_SIZE_XXL: Final = 16
FONT_SIZE_HERO: Final = 18


MIN_WIDTH_SM: Final = 60
MIN_WIDTH_MD: Final = 80
MIN_WIDTH_LG: Final = 100
MIN_WIDTH_XL: Final = 120


MIN_HEIGHT_SM: Final = 22
MIN_HEIGHT_MD: Final = 28
MIN_HEIGHT_LG: Final = 32
MIN_HEIGHT_XL: Final = 40


ANIMATION_DURATION_FAST: Final = 100
ANIMATION_DURATION_NORMAL: Final = 200
ANIMATION_DURATION_SLOW: Final = 300
ANIMATION_DURATION_PULSE: Final = 1000


ICON_SIZE_SM: Final = 14
ICON_SIZE_MD: Final = 20
ICON_SIZE_LG: Final = 24
ICON_SIZE_XL: Final = 32


def get_button_style(
    background: str,
    border: str,
    text_color: str,
    hover_background: str = None,
    pressed_background: str = None,
    disabled_background: str = None,
    disabled_text: str = None,
) -> str:
    """
    Generate a consistent button stylesheet.
    
    Args:
        background: Normal background color
        border: Border color
        text_color: Text color
        hover_background: Hover state background (optional)
        pressed_background: Pressed state background (optional)
        disabled_background: Disabled state background (optional)
        disabled_text: Disabled state text color (optional)
    
    Returns:
        Complete button stylesheet string
    """
    hover = hover_background or background
    pressed = pressed_background or background
    disabled_bg = disabled_background or border
    disabled_txt = disabled_text or text_color
    
    return f"""
        QPushButton {{
            background-color: {background};
            color: {text_color};
            border: 1px solid {border};
            border-radius: {BORDER_RADIUS_MD}px;
            padding: {PADDING_SM}px {PADDING_LG}px;
            font-weight: 500;
            min-width: {MIN_WIDTH_MD}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
            border-width: 2px;
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg};
            color: {disabled_txt};
            border: 1px solid {disabled_bg};
        }}
    """


def get_card_style(
    background: str,
    border: str,
    border_radius: int = BORDER_RADIUS_LG,
    padding: int = PADDING_LG,
) -> str:
    """
    Generate a consistent card/widget stylesheet.
    
    Args:
        background: Background color
        border: Border color
        border_radius: Border radius in pixels
        padding: Internal padding in pixels
    
    Returns:
        Complete card stylesheet string
    """
    return f"""
        QFrame, QWidget {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: {border_radius}px;
            padding: {padding}px;
        }}
    """


def get_input_style(
    background: str,
    border: str,
    focus_border: str,
    text_color: str,
    placeholder_color: str = None,
) -> str:
    """
    Generate a consistent input field stylesheet.
    
    Args:
        background: Background color
        border: Normal border color
        focus_border: Focus/hover border color
        text_color: Text color
        placeholder_color: Placeholder text color (optional)
    
    Returns:
        Complete input stylesheet string
    """
    ph_color = placeholder_color or text_color
    return f"""
        QLineEdit, QTextEdit, QSpinBox, QComboBox {{
            background-color: {background};
            border: 2px solid {border};
            border-radius: {BORDER_RADIUS_SM}px;
            color: {text_color};
            padding: {PADDING_SM}px;
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
            border-color: {focus_border};
        }}
        QLineEdit::placeholder {{
            color: {ph_color};
        }}
    """


def get_scrollbar_style(
    background: str,
    handle_color: str,
    handle_width: int = 12,
    border_radius: int = 6,
) -> str:
    """
    Generate a consistent scrollbar stylesheet.
    
    Args:
        background: Scrollbar track background
        handle_color: Scrollbar handle color
        handle_width: Handle width in pixels
        border_radius: Handle border radius
    
    Returns:
        Complete scrollbar stylesheet string
    """
    return f"""
        QScrollBar:vertical {{
            background: {background};
            width: {handle_width}px;
            border-radius: {border_radius}px;
        }}
        QScrollBar::handle:vertical {{
            background: {handle_color};
            border-radius: {border_radius}px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {handle_color};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {background};
            height: {handle_width}px;
            border-radius: {border_radius}px;
        }}
        QScrollBar::handle:horizontal {{
            background: {handle_color};
            border-radius: {border_radius}px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {handle_color};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """


def get_table_style(
    background: str,
    header_background: str,
    header_text: str,
    border: str,
    grid_line: str = None,
    alternate_background: str = None,
) -> str:
    """
    Generate a consistent table stylesheet.
    
    Args:
        background: Table background
        header_background: Header row background
        header_text: Header text color
        border: Table border color
        grid_line: Grid line color (optional)
        alternate_background: Alternate row background (optional)
    
    Returns:
        Complete table stylesheet string
    """
    grid = grid_line or border
    alt = alternate_background or background
    
    style = f"""
        QTableWidget, QTableView {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: {BORDER_RADIUS_SM}px;
            gridline-color: {grid};
        }}
        QTableWidget QHeaderView::section, QTableView QHeaderView::section {{
            background-color: {header_background};
            color: {header_text};
            padding: {PADDING_SM}px;
            border: none;
            border-bottom: 1px solid {border};
        }}
    """
    
    if alternate_background:
        style += f"""
            QTableWidget::item:alternate, QTableView::item:alternate {{
                background-color: {alt};
            }}
        """
    
    return style
