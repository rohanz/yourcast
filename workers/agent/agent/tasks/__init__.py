# Tasks package
import logging
from typing import List
from celery import current_task
from agent.celery_app import app
from agent.pipeline.podcast_generator import PodcastGenerator
from agent.services.episode_service import EpisodeService

# Import RSS tasks
from agent.tasks.rss_tasks import discover_rss_articles, get_recent_clusters, manual_rss_discovery

logger = logging.getLogger(__name__)

@app.task(bind=True)
def generate_podcast(self, episode_id: str, subcategories: List[str], duration_minutes: int):
    """Generate podcast episode task"""
    try:
        logger.info(f"Starting podcast generation for episode {episode_id}")
        
        episode_service = EpisodeService()
        generator = PodcastGenerator(episode_service)
        
        # Update status to processing
        episode_service.set_episode_status(
            episode_id, "processing", stage="started", progress=0
        )
        
        # Execute pipeline
        generator.generate_episode(episode_id, subcategories, duration_minutes)
        
        logger.info(f"Completed podcast generation for episode {episode_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate podcast for episode {episode_id}: {str(e)}")
        episode_service = EpisodeService()
        episode_service.set_episode_status(
            episode_id, "failed", error=str(e)
        )
        raise
