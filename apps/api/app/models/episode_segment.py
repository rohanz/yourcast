from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class EpisodeSegment(Base):
    __tablename__ = "episode_segments"
    
    id = Column(String, primary_key=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    start_time = Column(Integer, nullable=False)  # seconds
    end_time = Column(Integer, nullable=False)    # seconds
    text = Column(Text, nullable=False)
    source_id = Column(String, ForeignKey("sources.id"))
    order_index = Column(Integer, nullable=False)
    
    # Relationships
    episode = relationship("Episode", back_populates="segments")
    source = relationship("Source", back_populates="segments")