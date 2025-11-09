"""
Configuration Management System

Provides centralized configuration loading with environment-specific overrides.
"""

import os
import yaml
import logging
import re
from typing import Any, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Thread-safe configuration manager with environment override support."""
    
    def __init__(self, config_dir: Optional[Path] = None, environment: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Path to config directory (defaults to project root/config)
            environment: Environment name (defaults to ENVIRONMENT env var or 'development')
        """
        # Determine config directory
        if config_dir is None:
            # Find project root (directory containing this file's parent's parent)
            current_file = Path(__file__).resolve()
            
            # In Docker, check if config exists at /app/config first
            if Path("/app/config").exists():
                config_dir = Path("/app/config")
            else:
                # Fallback to standard path resolution
                project_root = current_file.parent.parent.parent
                config_dir = project_root / "config"
        
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._config_cache: Dict[str, Any] = {}
        
        # Load all configurations
        self._load_config()
    
    def _load_config(self) -> None:
        """Load base configuration files and apply environment overrides."""
        logger.info(f"Loading configuration from {self.config_dir} for environment '{self.environment}'")
        
        # Base config files to load
        config_files = [
            "endpoints.yaml",
            "services.yaml", 
            "limits.yaml",
            "algorithms.yaml",
            "ui.yaml",
            "infrastructure.yaml"
        ]
        
        # Load base configurations
        for config_file in config_files:
            file_path = self.config_dir / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = yaml.safe_load(f)
                        if content:
                            self._config_cache.update(content)
                            logger.debug(f"Loaded config from {config_file}")
                except Exception as e:
                    logger.error(f"Error loading {config_file}: {e}")
                    raise
            else:
                logger.warning(f"Config file not found: {file_path}")
        
        # Load environment-specific overrides
        env_config_path = self.config_dir / "environments" / f"{self.environment}.yaml"
        if env_config_path.exists():
            try:
                with open(env_config_path, 'r') as f:
                    env_config = yaml.safe_load(f)
                    if env_config:
                        self._merge_config(self._config_cache, env_config)
                        logger.info(f"Applied {self.environment} environment overrides")
            except Exception as e:
                logger.error(f"Error loading environment config: {e}")
                raise
        else:
            logger.info(f"No environment config found for '{self.environment}'")
        
        # Expand environment variables
        self._expand_env_vars()
        
        logger.info(f"Configuration loaded successfully for environment '{self.environment}'")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _expand_env_vars(self) -> None:
        """Expand environment variables in config values."""
        self._config_cache = self._expand_dict(self._config_cache)
    
    def _expand_dict(self, obj: Any) -> Any:
        """Recursively expand environment variables in dictionary values."""
        if isinstance(obj, dict):
            return {key: self._expand_dict(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_dict(item) for item in obj]
        elif isinstance(obj, str):
            return os.path.expandvars(obj)
        else:
            return obj
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path like 'api.base_url' or 'tts.deepinfra.timeout'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            >>> config.get('api.base_url')
            'http://localhost:8000'
            >>> config.get('tts.deepinfra.voices')
            ['af_nicole', 'af_bella', 'af_aoede']
        """
        keys = key_path.split('.')
        value = self._config_cache
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise KeyError(f"Configuration key '{key_path}' not found")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Top-level section name like 'api', 'tts', etc.
            
        Returns:
            Dictionary containing the entire section
        """
        return self.get(section, {})
    
    def has(self, key_path: str) -> bool:
        """Check if configuration key exists."""
        try:
            self.get(key_path)
            return True
        except KeyError:
            return False
    
    def reload(self) -> None:
        """Reload configuration from files."""
        self._config_cache.clear()
        self._load_config()
        logger.info("Configuration reloaded")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as dictionary (for debugging)."""
        return self._config_cache.copy()
    
    def validate_required_keys(self, required_keys: list) -> None:
        """
        Validate that required configuration keys exist.
        
        Args:
            required_keys: List of required key paths
            
        Raises:
            KeyError: If any required key is missing
        """
        missing_keys = []
        for key in required_keys:
            if not self.has(key):
                missing_keys.append(key)
        
        if missing_keys:
            raise KeyError(f"Missing required configuration keys: {missing_keys}")


# Global configuration instance
_config_instance: Optional[ConfigManager] = None


def get_config(config_dir: Optional[Path] = None, environment: Optional[str] = None) -> ConfigManager:
    """
    Get global configuration instance (singleton pattern).
    
    Args:
        config_dir: Config directory (only used on first call)
        environment: Environment name (only used on first call)
        
    Returns:
        ConfigManager instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigManager(config_dir, environment)
    
    return _config_instance


def reset_config() -> None:
    """Reset global configuration instance (mainly for testing)."""
    global _config_instance
    _config_instance = None