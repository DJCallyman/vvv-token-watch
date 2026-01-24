"""
Video Quote Worker for fetching base prices for video models.

Queries the Venice Video Quote API with minimal parameters to get base pricing
for comparison purposes in the model comparison table.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from PySide6.QtCore import Signal

from src.core.base_worker import BaseAPIWorker
from src.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)


@dataclass
class VideoBasePrice:
    """Base price information for a video model."""
    model_id: str
    base_usd: float
    base_diem: float
    min_duration: float
    min_resolution: str


class VideoQuoteWorker(BaseAPIWorker):
    """
    Worker to fetch base prices for video models using the Video Quote API.
    
    For each video model, determines minimal parameters (shortest duration,
    lowest resolution, no audio) and queries the quote API for base pricing.
    """
    
    # Signal emitted when quotes are fetched
    video_base_prices_updated = Signal(list)  # List[VideoBasePrice]
    
    def __init__(self, api_client: VeniceAPIClient, video_models: List[Dict[str, Any]], parent=None):
        """
        Initialize video quote worker.
        
        Args:
            api_client: Configured VeniceAPIClient instance
            video_models: List of video model dictionaries from API
            parent: Parent QObject
        """
        super().__init__(api_client, parent)
        self.video_models = video_models
    
    def fetch_data(self) -> List[VideoBasePrice]:
        """Fetch base prices for all video models."""
        base_prices = []
        
        for model in self.video_models:
            try:
                model_id = model.get('id')
                if not model_id:
                    continue
                
                # Extract minimal parameters from model constraints
                constraints = model.get('model_spec', {}).get('constraints', {})
                
                # Get minimum duration
                durations = constraints.get('durations', [])
                if durations:
                    # Parse duration strings like "5s", "8s" to find the minimum numeric value
                    def parse_duration(dur_str):
                        try:
                            # Remove 's' suffix and convert to float
                            return float(dur_str.rstrip('s'))
                        except (ValueError, AttributeError):
                            return 999  # Invalid durations at end
                    
                    min_duration = min(durations, key=parse_duration)
                    min_duration_value = parse_duration(min_duration)
                else:
                    min_duration = "5s"  # Default
                    min_duration_value = 5.0
                
                # Get aspect ratio (use first available)
                aspect_ratios = constraints.get('aspect_ratios', [])
                aspect_ratio = aspect_ratios[0] if aspect_ratios else "16:9"  # Default
                
                # Get lowest resolution (sort by numeric value)
                resolutions = constraints.get('resolutions', [])
                if resolutions:
                    # Extract numeric part and sort (e.g., "720p" -> 720)
                    def res_to_num(res):
                        try:
                            return int(res.rstrip('p'))
                        except ValueError:
                            return 999  # Put invalid resolutions at end
                    
                    min_resolution = min(resolutions, key=res_to_num)
                else:
                    min_resolution = "720p"  # Default
                
                # Prepare quote request
                quote_params = {
                    "model": model_id,
                    "duration": min_duration,  # String format like "5s"
                    "resolution": min_resolution,
                    "aspect_ratio": aspect_ratio,
                    "audio": False
                }
                
                self.emit_progress(f"Getting quote for {model_id}")
                
                # Call quote API
                logger.info(f"Sending quote request for {model_id}: {quote_params}")
                response = self.api_client.post("/video/quote", data=quote_params, timeout=30)
                
                if response.status_code == 200:
                    quote_data = response.json()
                    logger.info(f"Quote response for {model_id}: {quote_data}")
                    base_price = VideoBasePrice(
                        model_id=model_id,
                        base_usd=quote_data.get('quote', 0.0),  # The key is 'quote', not 'usd'
                        base_diem=quote_data.get('diem', 0.0),
                        min_duration=min_duration_value,
                        min_resolution=min_resolution
                    )
                    base_prices.append(base_price)
                else:
                    logger.warning(f"Quote API failed for {model_id}: {response.status_code}")
                    logger.warning(f"Response content: {response.text}")
                    logger.warning(f"Request params: {quote_params}")
                    
            except Exception as e:
                logger.warning(f"Failed to get quote for {model_id}: {e}")
                continue
        
        return base_prices
    
    def run(self):
        """Override run to emit custom signal."""
        result = {'success': False, 'data': None, 'error': None}
        
        try:
            data = self.fetch_data()
            
            if self._should_stop:
                return
            
            result['success'] = True
            result['data'] = data
            
        except Exception as e:
            error_msg = self.handle_error(e)
            result['error'] = error_msg
        
        finally:
            # Emit both standard result and custom signal
            self.result.emit(result)
            if result['success'] and result['data']:
                self.video_base_prices_updated.emit(result['data'])