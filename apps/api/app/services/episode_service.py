import redis
from typing import List, Optional
from app.config import settings
from app.schemas import EpisodeStatusEvent
import json

class EpisodeService:
    def __init__(self):
        self.redis_client = None
    
    def _get_redis_client(self):
        """Lazy initialization of Redis client"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(settings.redis_url)
                # Test connection
                self.redis_client.ping()
            except Exception as e:
                print(f"WARNING: Could not connect to Redis: {e}")
                self.redis_client = None
        return self.redis_client
    
    def queue_episode_generation(self, episode_id: str, subcategories: List[str], duration_minutes: int):
        """Queue episode generation job"""
        redis_client = self._get_redis_client()
        if not redis_client:
            print("WARNING: Redis not available, skipping queue operation")
            return
            
        job_data = {
            "episode_id": episode_id,
            "subcategories": subcategories,
            "duration_minutes": duration_minutes
        }
        
        try:
            # Add to Redis queue (will be consumed by worker)
            redis_client.lpush("episode_queue", json.dumps(job_data))
            
            # Set initial status
            self.set_episode_status(episode_id, "processing", stage="queued")
        except Exception as e:
            print(f"WARNING: Failed to queue episode generation: {e}")
    
    def set_episode_status(self, episode_id: str, status: str, stage: Optional[str] = None, progress: Optional[int] = None, error: Optional[str] = None):
        """Update episode status in Redis and publish to SSE subscribers"""
        redis_client = self._get_redis_client()
        if not redis_client:
            print("WARNING: Redis not available, skipping status update")
            return
            
        from datetime import datetime
        
        status_data = {
            "episode_id": episode_id,
            "status": status,
            "stage": stage,
            "progress": progress,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Store status in Redis with expiration
            key = f"episode_status:{episode_id}"
            redis_client.setex(key, 3600, json.dumps(status_data))  # Expire in 1 hour
            
            # Publish to pub/sub channel for real-time SSE updates
            channel = f"episode_status:{episode_id}"
            redis_client.publish(channel, json.dumps(status_data))
        except Exception as e:
            print(f"WARNING: Failed to set episode status: {e}")
    
    def get_episode_status_event(self, episode_id: str) -> Optional[EpisodeStatusEvent]:
        """Get current episode status"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return None
            
        try:
            key = f"episode_status:{episode_id}"
            status_data = redis_client.get(key)
            
            if status_data:
                data = json.loads(status_data)
                return EpisodeStatusEvent(**data)
        except Exception as e:
            print(f"WARNING: Failed to get episode status: {e}")
        
        return None