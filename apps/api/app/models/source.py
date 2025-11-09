from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    article_id = Column(String, nullable=True)  # Reference to original article from RSS system
    cluster_id = Column(String, ForeignKey("story_clusters.cluster_id"), nullable=True)  # Track which cluster this article came from
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    published_date = Column(DateTime(timezone=True), nullable=False)
    excerpt = Column(Text)
    summary = Column(Text)

    # Relationships
    episode = relationship("Episode", back_populates="sources")
    segments = relationship("EpisodeSegment", back_populates="source")