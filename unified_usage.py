"""
Unified usage module for combining API key usage and web app usage.

This module provides:
- UnifiedUsageEntry: Data structure representing either API key or web app usage
- UnifiedUsageIntegrator: Logic for merging API keys and web usage data
- Utility functions: SKU formatting and model name extraction
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from usage_tracker import APIKeyUsage, UsageMetrics
from web_usage import WebUsageMetrics


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
            sku_data: Dict with count, amount, currency, units
            total_days: Number of days in the period
        """
        # Extract amounts by currency
        currency = sku_data.get("currency", "DIEM")
        amount = sku_data.get("amount", 0.0)
        
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
        
        return UnifiedUsageEntry(
            id=f"webapp-{sku}",
            name=display_name,
            usage=usage,
            is_active=True,  # Web usage is always "active"
            entry_type="web_app",
            sku=sku,
            request_count=sku_data.get("count", 0),
            daily_average=daily_avg,
            icon="🎬"
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
            
            # Group SKUs by base model name
            model_groups = defaultdict(list)
            model_totals = defaultdict(lambda: {'diem': 0.0, 'usd': 0.0, 'count': 0})
            
            # First pass: group SKUs and calculate totals per model
            for sku, sku_data in web_usage.by_sku.items():
                amount = sku_data.get("amount", 0.0)
                if amount > 0:
                    base_model = extract_base_model_name(sku)
                    child_entry = UnifiedUsageEntry.from_web_sku(
                        sku=sku,
                        sku_data=sku_data,
                        total_days=days
                    )
                    model_groups[base_model].append(child_entry)
                    
                    # Accumulate totals
                    currency = sku_data.get("currency", "DIEM")
                    if currency == "DIEM":
                        model_totals[base_model]['diem'] += amount
                    else:
                        model_totals[base_model]['usd'] += amount
                    model_totals[base_model]['count'] += sku_data.get("count", 0)
            
            # Second pass: create model group entries and add children
            for base_model, sku_entries in sorted(model_groups.items()):
                # Create a model-level group
                totals = model_totals[base_model]
                model_usage = UsageMetrics(diem=totals['diem'], usd=totals['usd'])
                model_daily_avg = UsageMetrics(
                    diem=totals['diem'] / days,
                    usd=totals['usd'] / days
                )
                
                model_group_entry = UnifiedUsageEntry(
                    id=f"web-model-{base_model.replace(' ', '-').lower()}",
                    name=base_model,
                    usage=model_usage,
                    is_active=True,
                    entry_type="web_group",
                    sku=f"group-{base_model}",
                    request_count=totals['count'],
                    daily_average=model_daily_avg,
                    icon="🎬",
                    is_expanded=False,
                    depth=1  # This is a child of web_group
                )
                
                # Add individual SKU entries as children of this model group
                for sku_entry in sku_entries:
                    sku_entry.depth = 2  # Grandchildren of top web_group
                    model_group_entry.add_child(sku_entry)
                
                # Add the model group to the top-level web group
                web_group.add_child(model_group_entry)
            
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
# Utility Functions
# ============================================================================

def format_sku_display_name(sku: str) -> str:
    """
    Format SKU into human-readable display name.
    
    Examples:
        veo31-full-text-to-video-duration-rate-8s-720p-audio -> Veo 3.1 (8s, 720p)
        sora-2-pro-image-to-video-duration-resolution-rate-8s-720p-audio -> Sora 2 Pro (8s, 720p)
    """
    if not sku:
        return "Unknown Service"
    
    # Extract model name
    parts = sku.lower().split('-')
    
    # Common patterns
    if 'veo' in parts:
        # Find version - handle veo31 -> 3.1, veo2 -> 2, etc.
        version = ''
        for part in parts:
            if part.startswith('veo') and len(part) > 3:
                # Extract numbers after 'veo'
                num_part = part[3:]
                if num_part.replace('.', '').isdigit():
                    # Insert decimal if needed (31 -> 3.1, 20 -> 2.0)
                    if '.' not in num_part and len(num_part) == 2:
                        version = f"{num_part[0]}.{num_part[1]}"
                    else:
                        version = num_part
                    break
            elif part.replace('.', '').isdigit() and 'veo' in parts:
                version = part
                break
        
        duration = next((p for p in parts if p.endswith('s') and p[:-1].isdigit()), '')
        resolution = next((p for p in parts if 'p' in p and p.replace('p', '').isdigit()), '')
        return f"Veo {version} ({duration}, {resolution})" if duration and resolution else f"Veo {version}"
    
    elif 'sora' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Pro' if 'pro' in parts else ''
        duration = next((p for p in parts if p.endswith('s') and p[:-1].isdigit()), '')
        resolution = next((p for p in parts if 'p' in p and p.replace('p', '').isdigit()), '')
        name_parts = [p for p in ["Sora", version, tier] if p]
        details = ', '.join(filter(None, [duration, resolution]))
        return ' '.join(name_parts) + (f" ({details})" if details else "")
    
    elif 'wan' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Pro' if 'pro' in parts else ''
        duration = next((p for p in parts if p.endswith('s') and p[:-1].isdigit()), '')
        resolution = next((p for p in parts if 'p' in p and p.replace('p', '').isdigit()), '')
        name_parts = [p for p in ["Wan", version, tier] if p]
        details = ', '.join(filter(None, [duration, resolution]))
        return ' '.join(name_parts) + (f" ({details})" if details else "")
    
    elif 'kling' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Turbo Pro' if 'turbo' in parts and 'pro' in parts else 'Turbo' if 'turbo' in parts else ''
        duration = next((p for p in parts if p.endswith('s') and p[:-1].isdigit()), '')
        mode = 'Image-to-Video' if 'image' in parts else 'Text-to-Video' if 'text' in parts else ''
        name_parts = [p for p in ["Kling", version, tier] if p]
        details = ', '.join(filter(None, [mode, duration]))
        return ' '.join(name_parts) + (f" ({details})" if details else "")
    
    elif 'ovi' in parts:
        return "Ovi Image-to-Video"
    
    elif 'mistral' in sku or 'llm' in sku:
        return f"{sku.split('-')[0].title()} LLM"
    
    elif 'image' in sku or 'sd' in sku or 'stable' in sku:
        return "Image Generation"
    
    # Fallback: capitalize and clean up
    clean_name = sku.replace('-', ' ').replace('_', ' ').title()
    return clean_name[:40]  # Truncate long names


def extract_base_model_name(sku: str) -> str:
    """
    Extract base model name without duration/resolution details.
    Used for grouping SKUs by model type.
    
    Examples:
        veo31-full-text-to-video-duration-rate-8s-720p-audio -> Veo 3.1
        wan-2.5-preview-text-to-video-duration-resolution-rate-10s-720p-audio -> Wan 2.5
        sora-2-pro-image-to-video-duration-resolution-rate-8s-720p-audio -> Sora 2 Pro
    """
    if not sku:
        return "Unknown Model"
    
    parts = sku.lower().split('-')
    
    if 'veo' in parts:
        version = ''
        for part in parts:
            if part.startswith('veo') and len(part) > 3:
                num_part = part[3:]
                if num_part.replace('.', '').isdigit():
                    if '.' not in num_part and len(num_part) == 2:
                        version = f"{num_part[0]}.{num_part[1]}"
                    else:
                        version = num_part
                    break
            elif part.replace('.', '').isdigit() and 'veo' in parts:
                version = part
                break
        return f"Veo {version}" if version else "Veo"
    
    elif 'sora' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Pro' if 'pro' in parts else ''
        name_parts = [p for p in ["Sora", version, tier] if p]
        return ' '.join(name_parts) if name_parts else "Sora"
    
    elif 'wan' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Pro' if 'pro' in parts else ''
        preview = 'Preview' if 'preview' in parts else ''
        name_parts = [p for p in ["Wan", version, tier, preview] if p]
        return ' '.join(name_parts) if name_parts else "Wan"
    
    elif 'kling' in parts:
        version = next((p for p in parts if p.replace('.', '').isdigit()), '')
        tier = 'Turbo Pro' if 'turbo' in parts and 'pro' in parts else 'Turbo' if 'turbo' in parts else ''
        name_parts = [p for p in ["Kling", version, tier] if p]
        return ' '.join(name_parts) if name_parts else "Kling"
    
    elif 'ovi' in parts:
        return "Ovi"
    
    # Fallback
    return sku.split('-')[0].title()
