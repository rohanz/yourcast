#!/usr/bin/env python3
"""
Redis Queue Worker - Processes jobs from Redis queue directly
"""

import logging
import json
import redis
import time
from agent.config import settings
from agent.pipeline.podcast_generator import PodcastGenerator
from agent.services.episode_service import EpisodeService

logger = logging.getLogger(__name__)

def start_worker():
    """Direct Redis queue worker - executes tasks without Celery"""
    
    redis_client = redis.from_url(settings.redis_url)
    logger.info("Starting Redis queue worker (direct execution)...")
    
    while True:
        try:
            # Block until job available
            job_data = redis_client.brpop("episode_queue", timeout=5)
            
            if job_data:
                _, job_json = job_data
                job = json.loads(job_json)
                
                episode_id = job["episode_id"]
                # Handle both old (topics) and new (subcategories) format
                subcategories = job.get("subcategories") or job.get("topics", [])
                duration_minutes = job["duration_minutes"]
                
                logger.info(f"Processing job for episode {episode_id}")
                
                # Execute task directly
                try:
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
                
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    start_worker()
