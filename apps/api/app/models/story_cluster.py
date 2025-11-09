from sqlalchemy import Column, String, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class StoryCluster(Base):
    __tablename__ = "story_clusters"

    cluster_id = Column(String, primary_key=True)
    canonical_title = Column(Text, nullable=False)
    importance_score = Column(Float, default=50.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    articles = relationship("Article", back_populates="story_cluster")