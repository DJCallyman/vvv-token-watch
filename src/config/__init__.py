"""Configuration modules for application settings."""

from .config import Config
from .theme import Theme
from .features import FeatureFlags, FeatureGuard, requires_phase2, requires_phase3
from .style_constants import (
    BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG, BORDER_RADIUS_XL,
    PADDING_SM, PADDING_MD, PADDING_LG, PADDING_XL, PADDING_XXL,
    MARGIN_SM, MARGIN_MD, MARGIN_LG, MARGIN_XL,
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL,
    FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL, FONT_SIZE_HERO,
    MIN_WIDTH_SM, MIN_WIDTH_MD, MIN_WIDTH_LG, MIN_WIDTH_XL,
    MIN_HEIGHT_SM, MIN_HEIGHT_MD, MIN_HEIGHT_LG, MIN_HEIGHT_XL,
    ANIMATION_DURATION_FAST, ANIMATION_DURATION_NORMAL, ANIMATION_DURATION_SLOW, ANIMATION_DURATION_PULSE,
    ICON_SIZE_SM, ICON_SIZE_MD, ICON_SIZE_LG, ICON_SIZE_XL,
    get_button_style, get_card_style, get_input_style, get_scrollbar_style, get_table_style,
)

__all__ = [
    'Config',
    'Theme',
    'FeatureFlags',
    'FeatureGuard',
    'requires_phase2',
    'requires_phase3',
    'BORDER_RADIUS_SM', 'BORDER_RADIUS_MD', 'BORDER_RADIUS_LG', 'BORDER_RADIUS_XL',
    'PADDING_SM', 'PADDING_MD', 'PADDING_LG', 'PADDING_XL', 'PADDING_XXL',
    'MARGIN_SM', 'MARGIN_MD', 'MARGIN_LG', 'MARGIN_XL',
    'SPACING_SM', 'SPACING_MD', 'SPACING_LG', 'SPACING_XL', 'SPACING_XXL',
    'FONT_SIZE_SM', 'FONT_SIZE_MD', 'FONT_SIZE_LG', 'FONT_SIZE_XL', 'FONT_SIZE_XXL', 'FONT_SIZE_HERO',
    'MIN_WIDTH_SM', 'MIN_WIDTH_MD', 'MIN_WIDTH_LG', 'MIN_WIDTH_XL',
    'MIN_HEIGHT_SM', 'MIN_HEIGHT_MD', 'MIN_HEIGHT_LG', 'MIN_HEIGHT_XL',
    'ANIMATION_DURATION_FAST', 'ANIMATION_DURATION_NORMAL', 'ANIMATION_DURATION_SLOW', 'ANIMATION_DURATION_PULSE',
    'ICON_SIZE_SM', 'ICON_SIZE_MD', 'ICON_SIZE_LG', 'ICON_SIZE_XL',
    'get_button_style', 'get_card_style', 'get_input_style', 'get_scrollbar_style', 'get_table_style',
]
