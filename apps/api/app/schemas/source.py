from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class SourceSchema(BaseModel):
    id: str
    episode_id: str
    title: str
    url: str
    published_date: Optional[datetime]
    excerpt: Optional[str]
    summary: Optional[str]
    
    class Config:
        from_attributes = True