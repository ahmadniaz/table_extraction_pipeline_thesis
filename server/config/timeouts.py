"""
Centralized Timeout Configuration for Commission Tracker
Manages all timeout settings across WebSocket, API, Process, and Infrastructure layers
"""

from dataclasses import dataclass
import os
from typing import Literal


@dataclass
class TimeoutSettings:
    """Centralized timeout configuration for the entire application"""
    
    # WebSocket timeouts
    websocket_connection: int = 1800  # 30 minutes
    websocket_ping_interval: int = 30  # 30 seconds
    websocket_keepalive: int = 300  # 5 minutes
    
    # API timeouts
    mistral_api: int = 1800  # 30 minutes
    gpt_api: int = 300  # 5 minutes
    
    # Process timeouts
    total_extraction: int = 1800  # 30 minutes
    document_processing: int = 600  # 10 minutes
    table_extraction: int = 1200  # 20 minutes
    metadata_extraction: int = 300  # 5 minutes
    post_processing: int = 300  # 5 minutes
    
    # Server timeouts
    uvicorn_keepalive: int = 1800  # 30 minutes
    uvicorn_graceful_shutdown: int = 60  # 60 seconds
    
    # Document size-based timeouts
    small_document_timeout: int = 300  # 5 minutes for < 10 pages
    medium_document_timeout: int = 600  # 10 minutes for 10-50 pages
    large_document_timeout: int = 1200  # 20 minutes for 50+ pages
    max_timeout: int = 1800  # 30 minutes absolute maximum
    
    @classmethod
    def from_env(cls) -> 'TimeoutSettings':
        """Load timeout settings from environment variables with fallback defaults"""
        return cls(
            websocket_connection=int(os.getenv('WEBSOCKET_TIMEOUT', '1800')),
            websocket_ping_interval=int(os.getenv('WEBSOCKET_PING_INTERVAL', '30')),
            websocket_keepalive=int(os.getenv('WEBSOCKET_KEEPALIVE', '300')),
            mistral_api=int(os.getenv('MISTRAL_TIMEOUT', '1800')),
            gpt_api=int(os.getenv('GPT_TIMEOUT', '300')),
            total_extraction=int(os.getenv('EXTRACTION_TIMEOUT', '1800')),
            document_processing=int(os.getenv('DOCUMENT_PROCESSING_TIMEOUT', '600')),
            table_extraction=int(os.getenv('TABLE_EXTRACTION_TIMEOUT', '1200')),
            metadata_extraction=int(os.getenv('METADATA_EXTRACTION_TIMEOUT', '300')),
            post_processing=int(os.getenv('POST_PROCESSING_TIMEOUT', '300')),
            uvicorn_keepalive=int(os.getenv('UVICORN_TIMEOUT_KEEP_ALIVE', '1800')),
            uvicorn_graceful_shutdown=int(os.getenv('UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN', '60')),
            small_document_timeout=int(os.getenv('SMALL_DOC_TIMEOUT', '300')),
            medium_document_timeout=int(os.getenv('MEDIUM_DOC_TIMEOUT', '600')),
            large_document_timeout=int(os.getenv('LARGE_DOC_TIMEOUT', '1200')),
            max_timeout=int(os.getenv('MAX_TIMEOUT', '1800')),
        )
    
    @classmethod
    def get_adaptive_timeout(cls, document_size: Literal['small', 'medium', 'large', 'xlarge'] = 'large') -> int:
        """Get timeout based on document size classification"""
        settings = cls.from_env()
        timeouts = {
            'small': settings.small_document_timeout,
            'medium': settings.medium_document_timeout,
            'large': settings.large_document_timeout,
            'xlarge': settings.max_timeout
        }
        return timeouts.get(document_size, settings.large_document_timeout)
    
    @staticmethod
    def calculate_document_size_category(page_count: int) -> Literal['small', 'medium', 'large', 'xlarge']:
        """Calculate document size category based on page count"""
        if page_count <= 10:
            return 'small'
        elif page_count <= 50:
            return 'medium'
        elif page_count <= 100:
            return 'large'
        else:
            return 'xlarge'


# Global timeout settings instance
timeout_settings = TimeoutSettings.from_env()

