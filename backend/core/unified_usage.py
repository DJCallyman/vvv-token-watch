"""
Unified usage module for combining API key usage and web app usage.

This module provides:
- UnifiedUsageEntry: Data structure representing either API key or web app usage
- UnifiedUsageIntegrator: Logic for merging API keys and web usage data
- Utility functions: SKU formatting and model name extraction
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.core.usage_tracker import APIKeyUsage, UsageMetrics
from src.core.web_usage import WebUsageMetrics


# ============================================================================
# Usage Category Detection
# ============================================================================

class UsageCategory:
    """Constants for usage categories."""
    VIDEO = "video"
    IMAGE = "image"
    LLM = "llm"
    UNKNOWN = "unknown"
    
    # Icons for each category
    ICONS = {
        VIDEO: "🎬",
        IMAGE: "🖼️",
        LLM: "💬",
        UNKNOWN: "📊"
    }
    
    # Display names for category groups
    DISPLAY_NAMES = {
        VIDEO: "Video Generation",
        IMAGE: "Image Generation",
        LLM: "Text (LLM) Models",
        UNKNOWN: "Other Usage"
    }


def detect_usage_category(sku: str, notes: str = "") -> str:
    """
    Detect the usage category from SKU and notes.
    
    Args:
        sku: The SKU identifier
        notes: The notes field from billing (e.g., "Video Inference", "Image Inference")
    
    Returns:
        UsageCategory constant
    """
    sku_lower = sku.lower()
    notes_lower = notes.lower() if notes else ""
    
    # Check notes first (most reliable)
    if "video inference" in notes_lower:
        return UsageCategory.VIDEO
    if "image inference" in notes_lower or "fal image" in notes_lower:
        return UsageCategory.IMAGE
    if "llm inference" in notes_lower:
        return UsageCategory.LLM
    
    # Fall back to SKU pattern matching
    # Video models
    video_patterns = [
        'video', 'veo', 'kling', 'sora', 'wan-', 'ltx', 'longcat', 'ovi-image-to-video'
    ]
    if any(pattern in sku_lower for pattern in video_patterns):
        return UsageCategory.VIDEO
    
    # Image models
    image_patterns = [
        'image-unit', 'img', 'flux', 'nano-banana', 'seedream', 'hidream',
        'stable-diffusion', 'sd35', 'lustify', 'wai-illustrious', 'upscale'
    ]
    if any(pattern in sku_lower for pattern in image_patterns):
        return UsageCategory.IMAGE
    
    # LLM models (text)
    llm_patterns = [
        'llm', 'mtoken', 'gpt', 'llama', 'mistral', 'qwen', 'claude', 'gemma',
        'deepseek', 'glm', 'grok', 'hermes'
    ]
    if any(pattern in sku_lower for pattern in llm_patterns):
        return UsageCategory.LLM
    
    return UsageCategory.UNKNOWN


def get_category_icon(category: str) -> str:
    """Get the icon for a usage category."""
    return UsageCategory.ICONS.get(category, UsageCategory.ICONS[UsageCategory.UNKNOWN])


def get_category_display_name(category: str) -> str:
    """Get the display name for a usage category."""
    return UsageCategory.DISPLAY_NAMES.get(category, UsageCategory.DISPLAY_NAMES[UsageCategory.UNKNOWN])


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class UnifiedUsageEntry:
    """
    Unified entry that can represent either an API key or web app usage.
    Allows seamless integration in the leaderboard.
    """
    # Common fields
    id: str                         # Unique identifier (key ID or "webapp-{sku}")
    name: str                       # Display name
    usage: UsageMetrics             # 7-day usage metrics
    is_active: bool                 # Active status
    entry_type: str                 # "api_key" or "web_app" or "web_group"
    
    # API key specific fields
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    
    # Web app specific fields
    sku: Optional[str] = None       # Model/service SKU for web usage
    request_count: int = 0          # Number of requests (for web usage)
    daily_average: Optional[UsageMetrics] = None  # Pre-calculated daily average
    
    # Hierarchical structure for grouping
    parent_id: Optional[str] = None  # ID of parent entry (for grouped children)
    children: List['UnifiedUsageEntry'] = field(default_factory=list)  # Child entries
    is_expanded: bool = False       # Whether group is expanded (for web_group)
    depth: int = 0                  # Nesting depth (0 = top level, 1 = child, etc.)
    
    # Visual indicators
    icon: str = "🔑"                # Emoji icon (🔑 for keys, 🌐 for web)
    
    @property
    def identifier(self) -> str:
        """Get display identifier (name for UI display)"""
        return self.name
    
    @property
    def is_web_app(self) -> bool:
        """Check if this is a web app entry"""
        return self.entry_type == "web_app"
    
    @property
    def is_api_key(self) -> bool:
        """Check if this is an API key entry"""
        return self.entry_type == "api_key"
    
    @property
    def is_group(self) -> bool:
        """Check if this is a group entry (parent)"""
        return self.entry_type == "web_group"
    
    @property
    def has_children(self) -> bool:
        """Check if this entry has child entries"""
        return len(self.children) > 0
    
    def add_child(self, child: 'UnifiedUsageEntry'):
        """Add a child entry to this group"""
        child.parent_id = self.id
        child.depth = self.depth + 1
        self.children.append(child)
    
    def toggle_expanded(self):
        """Toggle the expanded state of this group"""
        if self.is_group:
            self.is_expanded = not self.is_expanded
    
    @staticmethod
    def from_api_key(key_usage) -> 'UnifiedUsageEntry':
        """Create from APIKeyUsage object"""
        return UnifiedUsageEntry(
            id=key_usage.id,
            name=key_usage.name,
            usage=key_usage.usage,
            is_active=key_usage.is_active,
            entry_type="api_key",
            created_at=key_usage.created_at,
            last_used_at=key_usage.last_used_at,
            icon="🔑"
        )
    
    @staticmethod
    def from_web_sku(sku: str, sku_data: dict, total_days: int = 7) -> 'UnifiedUsageEntry':
        """
        Create from SKU breakdown data.
        
        Args:
            sku: Model/service SKU
            sku_data: Dict with count, amount, currency, units, notes
            total_days: Number of days in the period
        """
        # Extract amounts by currency
        currency = sku_data.get("currency", "DIEM")
        amount = sku_data.get("amount", 0.0)
        notes = sku_data.get("notes", "")
        
        # Distribute amount to appropriate currency
        diem_amount = amount if currency == "DIEM" else 0.0
        usd_amount = amount if currency == "USD" else 0.0
        
        usage = UsageMetrics(diem=diem_amount, usd=usd_amount)
        
        # Calculate daily average
        daily_avg = UsageMetrics(
            diem=diem_amount / total_days,
            usd=usd_amount / total_days
        )
        
        # Create friendly name from SKU
        display_name = format_sku_display_name(sku)
        
        # Detect category and get appropriate icon
        category = detect_usage_category(sku, notes)
        icon = get_category_icon(category)
        
        # Determine entry type based on category
        entry_type = f"web_{category}"  # e.g., web_video, web_image, web_llm
        
        return UnifiedUsageEntry(
            id=f"webapp-{sku}",
            name=display_name,
            usage=usage,
            is_active=True,  # Web usage is always "active"
            entry_type=entry_type,
            sku=sku,
            request_count=sku_data.get("count", 0),
            daily_average=daily_avg,
            icon=icon
        )
    
    @staticmethod
    def create_web_group(web_metrics, total_days: int = 7) -> 'UnifiedUsageEntry':
        """
        Create a group entry for web app usage that can contain children.
        
        Args:
            web_metrics: WebUsageMetrics object
            total_days: Number of days in the period
        """
        usage = UsageMetrics(
            diem=web_metrics.diem,
            usd=web_metrics.usd
        )
        
        daily_avg = UsageMetrics(
            diem=web_metrics.diem / total_days,
            usd=web_metrics.usd / total_days
        )
        
        return UnifiedUsageEntry(
            id="web-group",
            name="Web App Usage",
            usage=usage,
            is_active=True,
            entry_type="web_group",
            sku="all",
            request_count=web_metrics.total_requests,
            daily_average=daily_avg,
            icon="🌐",
            is_expanded=False,
            depth=0
        )


# ============================================================================
# Integration Logic
# ============================================================================

class UnifiedUsageIntegrator:
    """Integrates API key usage and web app usage into unified entries."""
    
    @staticmethod
    def create_unified_entries(
        api_keys: List[APIKeyUsage],
        web_usage: WebUsageMetrics,
        days: int = 7,
        group_web_entries: bool = True
    ) -> Tuple[List[UnifiedUsageEntry], float, float, float, float]:
        """
        Create unified entries from API keys and web usage.
        
        Args:
            api_keys: List of API key usage objects
            web_usage: Web app usage metrics
            days: Number of days for the period (default 7)
            group_web_entries: Whether to group web entries under a parent (default True)
            
        Returns:
            Tuple of (entries, api_keys_diem, api_keys_usd, web_diem, web_usd)
            - entries: List of UnifiedUsageEntry objects
            - api_keys_diem: Total DIEM usage from API keys
            - api_keys_usd: Total USD usage from API keys
            - web_diem: Total DIEM usage from web app
            - web_usd: Total USD usage from web app
        """
        entries = []
        
        # Convert API keys to unified entries
        api_keys_diem = 0.0
        api_keys_usd = 0.0
        
        for api_key in api_keys:
            entry = UnifiedUsageEntry.from_api_key(api_key)
            entries.append(entry)
            api_keys_diem += api_key.usage.diem
            api_keys_usd += api_key.usage.usd
        
        # Convert web usage by SKU to unified entries
        web_diem = web_usage.diem
        web_usd = web_usage.usd
        
        if group_web_entries and web_usage.total_requests > 0:
            # Create parent group entry for all web usage
            web_group = UnifiedUsageEntry.create_web_group(web_usage, days)
            
            # Group SKUs by category first, then by base model name
            # Structure: category -> model_name -> [sku_entries]
            category_groups: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
            category_totals: Dict[str, Dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {'diem': 0.0, 'usd': 0.0, 'count': 0}))
            category_grand_totals: Dict[str, dict] = defaultdict(lambda: {'diem': 0.0, 'usd': 0.0, 'count': 0})
            
            # First pass: categorize and group SKUs
            for sku, sku_data in web_usage.by_sku.items():
                amount = sku_data.get("amount", 0.0)
                if amount > 0:
                    notes = sku_data.get("notes", "")
                    category = detect_usage_category(sku, notes)
                    base_model = extract_base_model_name(sku)
                    
                    child_entry = UnifiedUsageEntry.from_web_sku(
                        sku=sku,
                        sku_data=sku_data,
                        total_days=days
                    )
                    category_groups[category][base_model].append(child_entry)
                    
                    # Accumulate totals per model
                    currency = sku_data.get("currency", "DIEM")
                    if currency == "DIEM":
                        category_totals[category][base_model]['diem'] += amount
                        category_grand_totals[category]['diem'] += amount
                    else:
                        category_totals[category][base_model]['usd'] += amount
                        category_grand_totals[category]['usd'] += amount
                    category_totals[category][base_model]['count'] += sku_data.get("count", 0)
                    category_grand_totals[category]['count'] += sku_data.get("count", 0)
            
            # Second pass: create category groups with model subgroups
            # Order categories: Video first, then Image, then LLM, then Unknown
            category_order = [UsageCategory.VIDEO, UsageCategory.IMAGE, UsageCategory.LLM, UsageCategory.UNKNOWN]
            
            for category in category_order:
                if category not in category_groups:
                    continue
                    
                model_groups = category_groups[category]
                model_totals = category_totals[category]
                grand_totals = category_grand_totals[category]
                
                # Create category-level group (e.g., "Video Generation")
                category_usage = UsageMetrics(diem=grand_totals['diem'], usd=grand_totals['usd'])
                category_daily_avg = UsageMetrics(
                    diem=grand_totals['diem'] / days,
                    usd=grand_totals['usd'] / days
                )
                
                category_icon = get_category_icon(category)
                category_display = get_category_display_name(category)
                
                category_group_entry = UnifiedUsageEntry(
                    id=f"web-category-{category}",
                    name=category_display,
                    usage=category_usage,
                    is_active=True,
                    entry_type="web_group",
                    sku=f"category-{category}",
                    request_count=grand_totals['count'],
                    daily_average=category_daily_avg,
                    icon=category_icon,
                    is_expanded=False,
                    depth=1  # This is a child of web_group
                )
                
                # Create model-level groups within this category
                for base_model, sku_entries in sorted(model_groups.items()):
                    totals = model_totals[base_model]
                    model_usage = UsageMetrics(diem=totals['diem'], usd=totals['usd'])
                    model_daily_avg = UsageMetrics(
                        diem=totals['diem'] / days,
                        usd=totals['usd'] / days
                    )
                    
                    model_group_entry = UnifiedUsageEntry(
                        id=f"web-model-{category}-{base_model.replace(' ', '-').lower()}",
                        name=base_model,
                        usage=model_usage,
                        is_active=True,
                        entry_type="web_group",
                        sku=f"group-{base_model}",
                        request_count=totals['count'],
                        daily_average=model_daily_avg,
                        icon=category_icon,
                        is_expanded=False,
                        depth=2  # This is a grandchild of web_group
                    )
                    
                    # Add individual SKU entries as children of this model group
                    for sku_entry in sku_entries:
                        sku_entry.depth = 3  # Great-grandchildren of top web_group
                        model_group_entry.add_child(sku_entry)
                    
                    # Add the model group to the category group
                    category_group_entry.add_child(model_group_entry)
                
                # Add the category group to the top-level web group
                web_group.add_child(category_group_entry)
            
            # Add the top-level web group (with nested children) to entries
            entries.append(web_group)
        else:
            # Add individual web entries without grouping
            for sku, sku_data in web_usage.by_sku.items():
                amount = sku_data.get("amount", 0.0)
                if amount > 0:
                    entry = UnifiedUsageEntry.from_web_sku(
                        sku=sku,
                        sku_data=sku_data,
                        total_days=days
                    )
                    entries.append(entry)
        
        return entries, api_keys_diem, api_keys_usd, web_diem, web_usd
    
    @staticmethod
    def filter_by_date_range(
        api_keys: List[APIKeyUsage],
        days: int = 7
    ) -> List[APIKeyUsage]:
        """
        Filter API keys to align with the date range.
        
        Note: The /api_keys endpoint returns 7-day trailing usage by default,
        so this is primarily for consistency checks.
        
        Args:
            api_keys: List of API key usage objects
            days: Number of days to include
            
        Returns:
            List of API keys within the date range
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        filtered = []
        for key in api_keys:
            # API keys with usage in the period
            if key.usage.diem > 0:
                filtered.append(key)
            # Or keys with recent last_used_at
            elif key.last_used_at:
                try:
                    last_used = datetime.fromisoformat(
                        key.last_used_at.replace('Z', '+00:00')
                    )
                    if last_used >= cutoff:
                        filtered.append(key)
                except (ValueError, AttributeError):
                    # Include if we can't parse the date
                    filtered.append(key)
            else:
                # Include keys with no usage data
                filtered.append(key)
        
        return filtered
    
    @staticmethod
    def flatten_entries(entries: List[UnifiedUsageEntry]) -> List[UnifiedUsageEntry]:
        """
        Flatten hierarchical entries for display.
        
        Expands groups to show children when is_expanded=True.
        Handles nested groups recursively.
        Returns a flat list suitable for table display.
        
        Args:
            entries: List of unified entries (may include groups with children)
            
        Returns:
            Flat list of entries with children inserted after expanded parents
        """
        def flatten_recursive(entry_list, parent_expanded=True):
            """Recursively flatten entries respecting expanded state."""
            result = []
            for entry in entry_list:
                # Always add the entry itself if parent is expanded
                if parent_expanded:
                    result.append(entry)
                
                # If it's an expanded group, recursively add its children
                if entry.is_group and entry.is_expanded and entry.has_children:
                    result.extend(flatten_recursive(entry.children, parent_expanded=True))
            
            return result
        
        return flatten_recursive(entries)


# ============================================================================
# SKU Parsing Helpers (Private)
# ============================================================================

def _extract_version(parts: list) -> str:
    """Extract version number from parts list."""
    return next((p for p in parts if p.replace('.', '').isdigit()), '')


def _extract_duration(parts: list) -> str:
    """Extract duration (e.g., '8s') from parts list."""
    return next((p for p in parts if p.endswith('s') and p[:-1].isdigit()), '')


def _extract_resolution(parts: list) -> str:
    """Extract resolution (e.g., '720p') from parts list."""
    return next((p for p in parts if 'p' in p and p.replace('p', '').isdigit()), '')


def _format_video_details(duration: str, resolution: str) -> str:
    """Format duration and resolution into details string."""
    details = ', '.join(filter(None, [duration, resolution]))
    return f" ({details})" if details else ""


def _parse_veo_version(parts: list) -> str:
    """Extract Veo version from combined or separate forms."""
    veo_part = next((p for p in parts if p.startswith('veo')), None)
    if not veo_part:
        return ''
    
    if len(veo_part) > 3:
        num_part = veo_part[3:]
        if num_part.replace('.', '').isdigit():
            if '.' not in num_part and len(num_part) == 2:
                return f"{num_part[0]}.{num_part[1]}"
            return num_part
    elif veo_part == 'veo':
        idx = parts.index(veo_part)
        if idx + 1 < len(parts) and parts[idx + 1].replace('.', '').isdigit():
            return parts[idx + 1]
    return ''


def _format_veo_sku(parts: list) -> str:
    """Format Veo SKU into display name."""
    version = _parse_veo_version(parts)
    quality = 'Full' if 'full' in parts else 'Fast' if 'fast' in parts else ''
    mode = 'I2V' if 'image' in parts else 'T2V' if 'text' in parts else ''
    duration = _extract_duration(parts)
    resolution = _extract_resolution(parts)
    
    name_parts = [p for p in ["Veo", version, quality, mode] if p]
    return ' '.join(name_parts) + _format_video_details(duration, resolution)


def _format_sora_sku(parts: list) -> str:
    """Format Sora SKU into display name."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    duration = _extract_duration(parts)
    resolution = _extract_resolution(parts)
    
    name_parts = [p for p in ["Sora", version, tier] if p]
    return ' '.join(name_parts) + _format_video_details(duration, resolution)


def _format_wan_sku(parts: list) -> str:
    """Format Wan SKU into display name."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    duration = _extract_duration(parts)
    resolution = _extract_resolution(parts)
    
    name_parts = [p for p in ["Wan", version, tier] if p]
    return ' '.join(name_parts) + _format_video_details(duration, resolution)


def _format_kling_sku(parts: list) -> str:
    """Format Kling SKU into display name."""
    version = _extract_version(parts)
    tier = 'Turbo Pro' if 'turbo' in parts and 'pro' in parts else 'Turbo' if 'turbo' in parts else ''
    duration = _extract_duration(parts)
    mode = 'Image-to-Video' if 'image' in parts else 'Text-to-Video' if 'text' in parts else ''
    
    name_parts = [p for p in ["Kling", version, tier] if p]
    details = ', '.join(filter(None, [mode, duration]))
    return ' '.join(name_parts) + (f" ({details})" if details else "")


def _format_ltx_sku(parts: list) -> str:
    """Format LTX/Longcat SKU into display name."""
    model_name = 'LTX' if 'ltx' in parts else 'Longcat'
    version = _extract_version(parts)
    quality = 'Fast' if 'fast' in parts else 'Full' if 'full' in parts else ''
    duration = _extract_duration(parts)
    resolution = _extract_resolution(parts)
    mode = 'I2V' if 'image' in parts else 'T2V' if 'text' in parts else ''
    
    name_parts = [p for p in [model_name, version, quality, mode] if p]
    return ' '.join(name_parts) + _format_video_details(duration, resolution)


def _format_grok_sku(parts: list) -> str:
    """Format Grok SKU into display name."""
    version = _extract_version(parts)
    tier = 'Fast' if 'fast' in parts else ''
    io_type = 'Input' if 'input' in parts else 'Output' if 'output' in parts else ''
    
    name_parts = [p for p in ["Grok", version, tier] if p]
    return ' '.join(name_parts) + (f" ({io_type})" if io_type else "")


def _format_glm_sku(parts: list, sku: str) -> str:
    """Format GLM SKU into display name."""
    version = ''
    for part in parts:
        if 'glm' in part:
            idx = parts.index(part)
            if idx + 1 < len(parts) and parts[idx + 1].replace('.', '').isdigit():
                version = parts[idx + 1]
            break
        if part.replace('.', '').isdigit():
            version = part
    
    io_type = 'Input' if 'input' in parts else 'Output' if 'output' in parts else ''
    return f"GLM {version}" + (f" ({io_type})" if io_type else "")


def _format_llm_sku(parts: list, sku: str) -> str:
    """Format generic LLM SKU into display name."""
    model_name = parts[0].title() if parts else "LLM"
    version = next((p for p in parts if p.replace('.', '').replace('b', '').isdigit()), '')
    io_type = 'Input' if 'input' in parts else 'Output' if 'output' in parts else ''
    
    name_parts = [p for p in [model_name, version] if p]
    return ' '.join(name_parts) + (f" ({io_type})" if io_type else "")


def _format_flux_sku(parts: list) -> str:
    """Format Flux SKU into display name."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    name_parts = [p for p in ["Flux", version, tier] if p]
    return ' '.join(name_parts) if name_parts else "Flux"


def _format_seedream_sku(parts: list) -> str:
    """Format Seedream SKU into display name."""
    version = next((p for p in parts if p.replace('v', '').isdigit()), '')
    return f"Seedream {version}" if version else "Seedream"


def _format_stable_diffusion_sku(parts: list) -> str:
    """Format Stable Diffusion SKU into display name."""
    version = _extract_version(parts)
    return f"Stable Diffusion {version}" if version else "Stable Diffusion"


def _format_upscale_sku(sku: str) -> str:
    """Format Upscale SKU into display name."""
    scale = '4x' if '4x' in sku else '2x' if '2x' in sku else ''
    return f"Upscaler {scale}" if scale else "Upscaler"


# ============================================================================
# SKU Display Name Formatting (Public API)
# ============================================================================

_SKU_FORMATTERS = {
    'veo': _format_veo_sku,
    'sora': _format_sora_sku,
    'wan': _format_wan_sku,
    'kling': _format_kling_sku,
    'ovi': lambda parts: "Ovi Image-to-Video",
    'ltx': _format_ltx_sku,
    'longcat': _format_ltx_sku,
    'grok': _format_grok_sku,
    'flux': _format_flux_sku,
    'seedream': _format_seedream_sku,
    'hidream': lambda parts: "HiDream",
}


def format_sku_display_name(sku: str) -> str:
    """
    Format SKU into human-readable display name.
    
    Examples:
        veo31-full-text-to-video-duration-rate-8s-720p-audio -> Veo 3.1 (8s, 720p)
        sora-2-pro-image-to-video-duration-resolution-rate-8s-720p-audio -> Sora 2 Pro (8s, 720p)
    """
    if not sku:
        return "Unknown Service"
    
    parts = sku.lower().split('-')
    
    # Video models
    if any(p.startswith('veo') for p in parts) or 'veo' in parts:
        return _format_veo_sku(parts)
    
    # Check for registered formatters
    for key, formatter in _SKU_FORMATTERS.items():
        if key in parts:
            return formatter(parts)
    
    # GLM models
    if 'glm' in sku.lower() or 'zai' in parts:
        return _format_glm_sku(parts, sku)
    
    # Generic LLM token usage
    if 'llm' in parts or 'mtoken' in sku.lower():
        return _format_llm_sku(parts, sku)
    
    # Image models
    if 'nano' in parts and 'banana' in parts:
        return "Nano Banana Pro"
    
    if 'stable' in parts or 'sd' in parts:
        return _format_stable_diffusion_sku(parts)
    
    if 'upscale' in sku.lower():
        return _format_upscale_sku(sku)
    
    # Fallback: capitalize and clean up
    clean_name = sku.replace('-', ' ').replace('_', ' ').title()
    return clean_name[:40]


# ============================================================================
# Base Model Name Extraction Helpers
# ============================================================================

def _extract_veo_base(parts: list) -> str:
    """Extract base name for Veo models."""
    version = _parse_veo_version(parts)
    return f"Veo {version}" if version else "Veo"


def _extract_sora_base(parts: list) -> str:
    """Extract base name for Sora models."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    name_parts = [p for p in ["Sora", version, tier] if p]
    return ' '.join(name_parts) if name_parts else "Sora"


def _extract_wan_base(parts: list) -> str:
    """Extract base name for Wan models."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    preview = 'Preview' if 'preview' in parts else ''
    name_parts = [p for p in ["Wan", version, tier, preview] if p]
    return ' '.join(name_parts) if name_parts else "Wan"


def _extract_kling_base(parts: list) -> str:
    """Extract base name for Kling models."""
    version = _extract_version(parts)
    tier = 'Turbo Pro' if 'turbo' in parts and 'pro' in parts else 'Turbo' if 'turbo' in parts else ''
    name_parts = [p for p in ["Kling", version, tier] if p]
    return ' '.join(name_parts) if name_parts else "Kling"


def _extract_ltx_base(parts: list) -> str:
    """Extract base name for LTX models."""
    version = _extract_version(parts)
    quality = 'Fast' if 'fast' in parts else 'Full' if 'full' in parts else ''
    name_parts = [p for p in ["LTX", version, quality] if p]
    return ' '.join(name_parts) if name_parts else "LTX"


def _extract_grok_base(parts: list) -> str:
    """Extract base name for Grok models."""
    version = _extract_version(parts)
    tier = 'Fast' if 'fast' in parts else ''
    name_parts = [p for p in ["Grok", version, tier] if p]
    return ' '.join(name_parts) if name_parts else "Grok"


def _extract_glm_base(parts: list, sku: str) -> str:
    """Extract base name for GLM models."""
    version = ''
    for part in parts:
        if 'glm' in part:
            idx = parts.index(part)
            if idx + 1 < len(parts) and parts[idx + 1].replace('.', '').isdigit():
                version = parts[idx + 1]
            break
        if part.replace('.', '').isdigit():
            version = part
    return f"GLM {version}" if version else "GLM"


def _extract_flux_base(parts: list) -> str:
    """Extract base name for Flux models."""
    version = _extract_version(parts)
    tier = 'Pro' if 'pro' in parts else ''
    name_parts = [p for p in ["Flux", version, tier] if p]
    return ' '.join(name_parts) if name_parts else "Flux"


def _extract_seedream_base(parts: list) -> str:
    """Extract base name for Seedream models."""
    version = next((p for p in parts if p.replace('v', '').isdigit()), '')
    return f"Seedream {version}" if version else "Seedream"


# Map of model keywords to their base extractors
_BASE_EXTRACTORS = {
    'sora': _extract_sora_base,
    'wan': _extract_wan_base,
    'kling': _extract_kling_base,
    'ovi': lambda parts: "Ovi",
    'ltx': _extract_ltx_base,
    'longcat': lambda parts: "Longcat",
    'grok': _extract_grok_base,
    'flux': _extract_flux_base,
    'seedream': _extract_seedream_base,
    'hidream': lambda parts: "HiDream",
    'stable': lambda parts: "Stable Diffusion",
    'sd': lambda parts: "Stable Diffusion",
}


def extract_base_model_name(sku: str) -> str:
    """
    Extract base model name without duration/resolution details.
    Used for grouping SKUs by model type.
    
    Examples:
        veo31-full-text-to-video-duration-rate-8s-720p-audio -> Veo 3.1
        wan-2.5-preview-text-to-video-duration-resolution-rate-10s-720p-audio -> Wan 2.5
        sora-2-pro-image-to-video-duration-resolution-rate-8s-720p-audio -> Sora 2 Pro
        grok-4-fast-llm-input-mtoken -> Grok 4 Fast
        nano-banana-pro-fixed-1img -> Nano Banana Pro
    """
    if not sku:
        return "Unknown Model"
    
    parts = sku.lower().split('-')
    
    # Veo models (handle combined form like 'veo31')
    if any(p.startswith('veo') for p in parts):
        return _extract_veo_base(parts)
    
    # Check for registered extractors
    for key, extractor in _BASE_EXTRACTORS.items():
        if key in parts:
            return extractor(parts)
    
    # GLM models
    if 'glm' in sku.lower() or 'zai' in parts:
        return _extract_glm_base(parts, sku)
    
    # Other LLM models
    if any(llm in parts for llm in ['mistral', 'llama', 'qwen', 'deepseek']):
        model_name = next((p for p in parts if p in ['mistral', 'llama', 'qwen', 'deepseek']), parts[0])
        version = next((p for p in parts if p.replace('.', '').replace('b', '').isdigit()), '')
        return f"{model_name.title()} {version}" if version else model_name.title()
    
    # Image models
    if 'nano' in parts and 'banana' in parts:
        return "Nano Banana Pro"
    
    if 'upscale' in sku.lower():
        return "Upscaler"
    
    # Fallback
    return sku.split('-')[0].title()
