"""
Worker Configuration Manager

Provides centralized configuration for the worker service using the shared config system.
"""

import sys
import os
from pathlib import Path
from typing import List

# Add shared config to Python path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from yourcast_config import ConfigManager, get_config


class WorkerConfig:
    """Worker-specific configuration wrapper with convenience methods."""
    
    def __init__(self):
        self.config = get_config()
        
        # Validate required worker configuration keys
        required_keys = [
            "internal.postgres_url",
            "internal.redis_url",
            "tts.deepinfra.voices",
            "llm.podcast.words_per_minute"
        ]
        
        try:
            self.config.validate_required_keys(required_keys)
        except KeyError as e:
            raise RuntimeError(f"Missing required worker configuration: {e}")
    
    # Database and Redis
    @property
    def database_url(self) -> str:
        return self.config.get("internal.postgres_url")
    
    @property
    def redis_url(self) -> str:
        return self.config.get("internal.redis_url")
    
    # TTS Configuration
    @property
    def tts_deepinfra_url(self) -> str:
        return self.config.get("external_services.deepinfra.url")
    
    @property
    def tts_deepinfra_voices(self) -> List[str]:
        return self.config.get("tts.deepinfra.voices")
    
    @property
    def tts_deepinfra_speed(self) -> float:
        return self.config.get("tts.deepinfra.speed", 1.0)
    
    @property
    def tts_deepinfra_sample_rate(self) -> int:
        return self.config.get("tts.deepinfra.sample_rate", 24000)
    
    @property
    def tts_deepinfra_timeout(self) -> int:
        return self.config.get("tts.deepinfra.timeout", 60)
    
    @property
    def tts_google_url(self) -> str:
        return self.config.get("external_services.google_tts.url")
    
    @property
    def tts_google_timeout(self) -> int:
        return self.config.get("tts.google.timeout", 30)
    
    # LLM Configuration
    @property
    def llm_words_per_minute(self) -> int:
        return self.config.get("llm.podcast.words_per_minute", 120)
    
    @property
    def llm_intro_text(self) -> str:
        return self.config.get("llm.podcast.intro_text", "Welcome to Your Cast, your world update, without the noise.")
    
    @property
    def llm_target_style(self) -> str:
        return self.config.get("llm.podcast.target_style", "professional and conversational - like a knowledgeable friend sharing interesting news. Let the facts and details carry the interest naturally. Avoid over-the-top enthusiasm, forced humor, or overusing phrases like 'buckle up', 'you heard that right', etc.")
    
    @property
    def llm_max_sources(self) -> int:
        return self.config.get("llm.podcast.max_sources", 10)
    
    # Embedding Configuration
    @property
    def embedding_max_length(self) -> int:
        return self.config.get("embedding.text_max_length", 8192)
    
    @property
    def embedding_batch_size(self) -> int:
        return self.config.get("embedding.batch_size", 100)
    
    # Algorithm Configuration
    @property
    def min_importance_score(self) -> int:
        return self.config.get("algorithms.clustering.min_importance_score", 40)
    
    @property
    def max_importance_score(self) -> int:
        return self.config.get("algorithms.clustering.max_importance_score", 100)
    
    @property
    def default_importance_score(self) -> int:
        return self.config.get("algorithms.clustering.default_importance_score", 50)
    
    @property
    def min_articles_per_episode(self) -> int:
        return self.config.get("algorithms.article_selection.min_articles_per_episode", 3)
    
    @property
    def max_articles_per_episode(self) -> int:
        return self.config.get("algorithms.article_selection.max_articles_per_episode", 15)
    
    # Worker Limits
    @property
    def redis_queue_timeout(self) -> int:
        return self.config.get("limits.redis.queue_timeout", 5)
    
    @property
    def redis_sleep_interval(self) -> int:
        return self.config.get("limits.redis.sleep_interval", 5)
    
    @property
    def max_concurrent_jobs(self) -> int:
        return self.config.get("limits.worker.max_concurrent_jobs", 3)
    
    @property
    def job_timeout(self) -> int:
        return self.config.get("limits.worker.job_timeout", 600)
    
    @property
    def retry_attempts(self) -> int:
        return self.config.get("limits.worker.retry_attempts", 3)
    
    # Database Query Limits
    @property
    def db_similar_articles_limit(self) -> int:
        return self.config.get("limits.database.query_limits.similar_articles", 5)
    
    @property
    def db_recent_clusters_limit(self) -> int:
        return self.config.get("limits.database.query_limits.recent_clusters", 20)
    
    @property
    def db_default_limit(self) -> int:
        return self.config.get("limits.database.query_limits.default", 10)
    
    # RSS Discovery
    @property
    def rss_recent_hours(self) -> int:
        return self.config.get("algorithms.rss_discovery.recent_hours", 24)
    
    @property
    def rss_max_articles_per_feed(self) -> int:
        return self.config.get("algorithms.rss_discovery.max_articles_per_feed", 50)
    
    @property
    def rss_feed_timeout(self) -> int:
        return self.config.get("algorithms.rss_discovery.feed_timeout", 10)
    
    # Storage settings
    @property
    def storage_dir(self) -> str:
        return os.getenv("STORAGE_DIR", "/app/storage")
    
    @property
    def storage_base_url(self) -> str:
        return self.config.get("api.storage_base_url")
    
    # API Keys (still from environment variables for security)
    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")
    
    @property
    def deepinfra_api_key(self) -> str:
        return os.getenv("DEEPINFRA_API_KEY", "")
    
    @property
    def google_tts_api_key(self) -> str:
        return os.getenv("GOOGLE_TTS_API_KEY", "")
    
    @property
    def news_api_key(self) -> str:
        return os.getenv("NEWS_API_KEY", "")

    @property
    def fal_api_key(self) -> str:
        return os.getenv("FAL_KEY", "")


# Global instance
_worker_config: WorkerConfig = None


def get_worker_config() -> WorkerConfig:
    """Get the global worker configuration instance."""
    global _worker_config
    if _worker_config is None:
        _worker_config = WorkerConfig()
    return _worker_config