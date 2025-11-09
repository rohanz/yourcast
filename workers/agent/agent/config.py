"""
Legacy worker settings module - kept for backward compatibility.
New code should use config_manager.get_worker_config() instead.
"""

import os
from dotenv import load_dotenv
from .config_manager import get_worker_config

load_dotenv()

class Settings:
    """Legacy settings class - migrating to centralized configuration."""
    
    def __init__(self):
        # Initialize centralized config
        self._worker_config = get_worker_config()
    
    @property
    def redis_url(self) -> str:
        return self._worker_config.redis_url
    
    @property
    def database_url(self) -> str:
        return self._worker_config.database_url
    
    @property
    def storage_dir(self) -> str:
        return self._worker_config.storage_dir
    
    # API Keys - still from environment for security
    @property 
    def gemini_api_key(self) -> str:
        return self._worker_config.gemini_api_key
    
    @property
    def deepinfra_api_key(self) -> str:
        return self._worker_config.deepinfra_api_key
    
    @property
    def google_tts_api_key(self) -> str:
        return self._worker_config.google_tts_api_key
    
    @property
    def news_api_key(self) -> str:
        return self._worker_config.news_api_key

    @property
    def fal_api_key(self) -> str:
        return self._worker_config.fal_api_key

    # Legacy properties for backward compatibility
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    tts_provider = os.getenv("TTS_PROVIDER", "deepinfra")
    
    # RSS feeds for fallback - now using categorized feeds
    @property
    def rss_feeds(self):
        from agent.rss_config import get_all_feeds
        return get_all_feeds()


# Legacy instance
settings = Settings()

# New recommended way
config = get_worker_config()