from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CreateEpisodeRequest(BaseModel):
    subcategories: List[str]
    duration_minutes: int

class CreateEpisodeResponse(BaseModel):
    episode_id: str
    status: str

class EpisodeSegmentSchema(BaseModel):
    id: str
    episode_id: str
    start_time: int
    end_time: int
    text: str
    source_id: Optional[str]
    order_index: int
    
    class Config:
        from_attributes = True

class EpisodeSchema(BaseModel):
    id: str
    user_id: Optional[str]
    title: str
    description: Optional[str]
    duration_seconds: int
    subcategories: List[str]
    status: str
    audio_url: Optional[str]
    transcript_url: Optional[str]
    vtt_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    played_at: Optional[datetime]
    play_progress: int

    class Config:
        from_attributes = True

class MarkPlayedRequest(BaseModel):
    current_position: int  # Current playback position in seconds

class EpisodeStatusEvent(BaseModel):
    episode_id: str
    status: str
    stage: Optional[str]
    progress: Optional[int]
    error: Optional[str]