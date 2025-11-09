"""
API Configuration using centralized configuration system.
"""

import os
from .config_manager import get_api_config


class Settings:
    """Settings class using centralized configuration."""
    
    def __init__(self):
        # Initialize centralized config
        self._api_config = get_api_config()
    
    @property
    def database_url(self) -> str:
        return self._api_config.database_url
    
    @property
    def redis_url(self) -> str:
        return self._api_config.redis_url
    
    @property
    def storage_dir(self) -> str:
        return self._api_config.storage_dir
    
    # API Keys still from environment for security
    @property
    def news_api_key(self) -> str:
        return os.getenv("NEWS_API_KEY", "")
    
    @property 
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")
    
    @property
    def google_tts_api_key(self) -> str:
        return os.getenv("GOOGLE_TTS_API_KEY", "")


# Global settings instance
settings = Settings()

# Direct access to configuration manager
config = get_api_config()