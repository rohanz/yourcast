from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

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
    played_at = Column(DateTime(timezone=True), nullable=True)  # When user listened to episode
    play_progress = Column(Integer, default=0)  # Playback progress 0-100

    # Relationships
    segments = relationship("EpisodeSegment", back_populates="episode")
    sources = relationship("Source", back_populates="episode")