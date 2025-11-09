import logging
import uuid
import json
import redis
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agent.config import settings
from agent.utils.uuid_utils import generate_uuidv7

logger = logging.getLogger(__name__)

# Define database models to match API exactly
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Episode(Base):
    __tablename__ = "episodes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Optional for MVP
    title = Column(String, nullable=False)
    description = Column(Text)
    duration_seconds = Column(Integer, default=0)
    subcategories = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    audio_url = Column(String)
    transcript_url = Column(String)
    vtt_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EpisodeSegment(Base):
    __tablename__ = "episode_segments"
    
    id = Column(String, primary_key=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    source_id = Column(String, ForeignKey("sources.id"), nullable=True)
    order_index = Column(Integer, nullable=False)

class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    article_id = Column(String)  # Reference to original article from RSS system
    cluster_id = Column(String)  # Track which cluster this article came from
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    published_date = Column(DateTime)
    excerpt = Column(Text)
    summary = Column(Text)

logger.info("Using standalone database models for worker")

# SHARED DATABASE ENGINE - Created once when module loads
# This prevents connection pool exhaustion by reusing the same pool across all EpisodeService instances
# With --min-instances=1, the worker stays alive, so we MUST share the engine to avoid accumulating connections
_engine = create_engine(
    settings.database_url,
    pool_size=5,          # Number of persistent connections
    max_overflow=10,      # Additional connections if pool exhausted
    pool_pre_ping=True,   # Verify connections before using (prevents stale connections)
    pool_recycle=3600     # Recycle connections every hour (prevents "gone away" errors)
)
Base.metadata.create_all(_engine, checkfirst=True)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
logger.info(f"✅ Shared database engine created: pool_size=5, max_overflow=10 (max 15 connections total)")

class EpisodeService:
    def __init__(self):
        # Make Redis optional for Cloud Run deployments
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            logger.info("Redis connection established for status updates")
        except (ValueError, redis.RedisError) as e:
            logger.warning(f"Redis not available: {e}. Status updates will use database only.")
            self.redis_client = None

        # Use the SHARED database engine and session maker
        # All EpisodeService instances share the same 15-connection pool
        self.engine = _engine
        self.db_session = _SessionLocal

    def set_episode_status(self, episode_id: str, status: str, stage: Optional[str] = None,
                          progress: Optional[int] = None, error: Optional[str] = None):
        """Update episode status in Redis (if available) and database"""
        status_data = {
            "episode_id": episode_id,
            "status": status,
            "stage": stage,
            "progress": progress,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

        # Update status in database
        db = self.db_session()
        try:
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if episode:
                episode.status = status
                episode.updated_at = datetime.now()
                db.commit()
                logger.info(f"Episode {episode_id} status updated in database: {status} - {stage}")
        except Exception as e:
            logger.error(f"Failed to update episode status in database: {e}")
            db.rollback()
        finally:
            db.close()

        # Optionally store status in Redis with expiration (for real-time updates)
        if self.redis_client:
            try:
                key = f"episode_status:{episode_id}"
                self.redis_client.setex(key, 3600, json.dumps(status_data))  # Expire in 1 hour

                # Publish to pub/sub channel for real-time SSE updates
                channel = f"episode_status:{episode_id}"
                self.redis_client.publish(channel, json.dumps(status_data))
                logger.info(f"Episode {episode_id} status published to Redis SSE")
            except Exception as e:
                logger.warning(f"Failed to publish status update to Redis: {e}")

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get episode from database by ID"""
        db = self.db_session()
        try:
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            return episode
        except Exception as e:
            logger.error(f"Failed to get episode {episode_id}: {e}")
            return None
        finally:
            db.close()

    def store_sources(self, episode_id: str, sources_data: List[Dict[str, Any]]):
        """Store article sources in database with UUIDv7 IDs and return mapping"""
        db = self.db_session()
        article_to_source_map = {}  # Map from article_id to source_id (UUIDv7)
        
        try:
            for source_data in sources_data:
                # Generate new UUIDv7 for this source record
                source_id = generate_uuidv7()
                article_id = source_data["id"]
                
                # Store the mapping for use in segments
                article_to_source_map[article_id] = source_id
                
                source = Source(
                    id=source_id,  # New UUIDv7 for this source record
                    episode_id=episode_id,
                    article_id=article_id,  # Original article ID from RSS system
                    cluster_id=source_data.get("cluster_id"),  # Track cluster to avoid repetition
                    title=source_data["title"],
                    url=source_data["url"],
                    published_date=datetime.fromisoformat(source_data["published_date"].replace('Z', '+00:00')) if source_data["published_date"] else None,
                    excerpt=source_data["excerpt"],
                    summary=source_data.get("summary", "")
                )
                db.add(source)
                
                logger.debug(f"Added source {source_id} for article {article_id} in episode {episode_id}")
            
            db.commit()
            logger.info(f"Stored {len(sources_data)} sources for episode {episode_id}")
            return article_to_source_map
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store sources: {str(e)}")
            raise
        finally:
            db.close()
    
    def update_episode(self, episode_id: str, **updates):
        """Update episode record in database"""
        db = self.db_session()
        try:
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                logger.error(f"Episode {episode_id} not found in database. Available episodes: {[ep.id for ep in db.query(Episode).all()]}")
                # Try to create a basic episode record if it doesn't exist
                episode = Episode(
                    id=episode_id,
                    title="Generated Podcast",
                    description="Podcast generated by worker",
                    subcategories=[],
                    status="processing"
                )
                db.add(episode)
                db.flush()  # Make sure the episode is available for updates
            
            for key, value in updates.items():
                if hasattr(episode, key):
                    setattr(episode, key, value)
            
            db.commit()
            logger.info(f"Updated episode {episode_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update episode: {str(e)}")
            raise
        finally:
            db.close()
    
    def store_episode_segments(self, episode_id: str, transcript_data: List[Dict[str, Any]], article_to_source_map: Dict[str, str]):
        """Store episode segments for chapter navigation with proper source ID mapping"""
        db = self.db_session()
        try:
            # Clear existing segments
            db.query(EpisodeSegment).filter(EpisodeSegment.episode_id == episode_id).delete()
            
            for i, segment_data in enumerate(transcript_data):
                # Only create segments for longer sections (for chapter navigation)
                if segment_data["end"] - segment_data["start"] > 10:  # 10+ seconds
                    # Map article ID to source ID (UUIDv7)
                    source_id = None
                    if segment_data["source_ids"]:
                        article_id = segment_data["source_ids"][0]
                        source_id = article_to_source_map.get(article_id)
                        if not source_id:
                            logger.warning(f"No source mapping found for article {article_id}")
                    
                    # Use topic name for chapter label (cleaner than script text)
                    chapter_text = segment_data.get("topic", segment_data["text"][:100])

                    segment = EpisodeSegment(
                        id=generate_uuidv7(),
                        episode_id=episode_id,
                        start_time=int(segment_data["start"]),
                        end_time=int(segment_data["end"]),
                        text=chapter_text,
                        source_id=source_id,  # Use mapped UUIDv7 source ID
                        order_index=i
                    )
                    db.add(segment)
            
            db.commit()
            logger.info(f"Stored episode segments for {episode_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store segments: {str(e)}")
            raise
        finally:
            db.close()
