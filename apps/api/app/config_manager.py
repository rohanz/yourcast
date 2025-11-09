"""
API Configuration Manager

Provides centralized configuration for the API service using the shared config system.
"""

import sys
import os
from pathlib import Path

# Add shared config to Python path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from yourcast_config import ConfigManager, get_config


class APIConfig:
    """API-specific configuration wrapper with convenience methods."""
    
    def __init__(self):
        self.config = get_config()
        
        # Validate required API configuration keys
        required_keys = [
            "api.base_url",
            "cors.allowed_origins",
            "internal.postgres_url",
            "internal.redis_url"
        ]
        
        try:
            self.config.validate_required_keys(required_keys)
        except KeyError as e:
            raise RuntimeError(f"Missing required API configuration: {e}")
    
    # API Settings
    @property
    def base_url(self) -> str:
        return self.config.get("api.base_url")
    
    @property
    def storage_base_url(self) -> str:
        return self.config.get("api.storage_base_url")
    
    @property 
    def cors_origins(self) -> list:
        return self.config.get("cors.allowed_origins")
    
    # Database and Redis
    @property
    def database_url(self) -> str:
        return self.config.get("internal.postgres_url")
    
    @property
    def redis_url(self) -> str:
        return self.config.get("internal.redis_url")
    
    # Timeouts and Limits
    @property
    def api_timeout(self) -> int:
        return self.config.get("limits.api.timeouts.request", 30)
    
    @property
    def health_check_timeout(self) -> int:
        return self.config.get("limits.api.timeouts.health_check", 10)
    
    @property
    def episodes_per_minute_limit(self) -> int:
        return self.config.get("limits.api.rate_limits.episodes_per_minute", 5)
    
    # Database query limits
    @property
    def default_query_limit(self) -> int:
        return self.config.get("limits.database.query_limits.default", 10)
    
    @property
    def max_query_results(self) -> int:
        return self.config.get("limits.database.query_limits.max_results", 100)
    
    # Storage settings
    @property
    def storage_dir(self) -> str:
        return os.getenv("STORAGE_DIR", "/app/storage")


# Global instance
_api_config: APIConfig = None


def get_api_config() -> APIConfig:
    """Get the global API configuration instance."""
    global _api_config
    if _api_config is None:
        _api_config = APIConfig()
    return _api_config