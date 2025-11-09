"""
Episode Service using Cloud Tasks (no Redis dependency)
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Episode
from app.services.cloud_tasks_service import CloudTasksService


class EpisodeService:
    def __init__(self, db: Session = None):
        self.db = db
        self.cloud_tasks = CloudTasksService()

    def queue_episode_generation(
        self,
        episode_id: str,
        subcategories: List[str],
        duration_minutes: int,
        custom_tags: Optional[List[str]] = None
    ):
        """Queue episode generation job using Cloud Tasks"""
        try:
            # Queue task with Cloud Tasks
            task_name = self.cloud_tasks.queue_episode_generation(
                episode_id=episode_id,
                subcategories=subcategories,
                duration_minutes=duration_minutes,
                custom_tags=custom_tags or []
            )

            # Update episode status in database
            if self.db:
                episode = self.db.query(Episode).filter(Episode.id == episode_id).first()
                if episode:
                    episode.status = "queued"
                    self.db.commit()

            print(f"✅ Episode {episode_id} queued: {task_name}")

        except Exception as e:
            print(f"❌ Failed to queue episode generation: {e}")
            # Update episode status to failed
            if self.db:
                episode = self.db.query(Episode).filter(Episode.id == episode_id).first()
                if episode:
                    episode.status = "failed"
                    self.db.commit()
            raise

    def update_episode_status(
        self,
        episode_id: str,
        status: str,
        db: Session = None
    ):
        """Update episode status in database"""
        session = db or self.db
        if not session:
            print("WARNING: No database session available")
            return

        try:
            episode = session.query(Episode).filter(Episode.id == episode_id).first()
            if episode:
                episode.status = status
                session.commit()
                print(f"✅ Updated episode {episode_id} status: {status}")
        except Exception as e:
            print(f"❌ Failed to update episode status: {e}")

    def get_episode_status(self, episode_id: str, db: Session = None) -> Optional[str]:
        """Get episode status from database"""
        session = db or self.db
        if not session:
            return None

        try:
            episode = session.query(Episode).filter(Episode.id == episode_id).first()
            return episode.status if episode else None
        except Exception as e:
            print(f"❌ Failed to get episode status: {e}")
            return None
