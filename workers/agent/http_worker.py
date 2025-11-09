#!/usr/bin/env python3
"""
HTTP Worker - Receives podcast generation jobs from Cloud Tasks via HTTP POST
"""

import logging
import json
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
from agent.pipeline.podcast_generator import PodcastGenerator
from agent.services.episode_service import EpisodeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="YourCast Worker")


class GenerateEpisodeRequest(BaseModel):
    """Request model for episode generation"""
    episode_id: str
    subcategories: List[str]
    duration_minutes: int
    custom_tags: List[str] = []


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "service": "yourcast-worker"}


@app.post("/generate")
async def generate_episode(request: GenerateEpisodeRequest):
    """
    Generate podcast episode - called by Cloud Tasks

    This endpoint receives HTTP POST requests from Cloud Tasks queue
    and processes them to generate podcast episodes.
    """
    episode_id = request.episode_id
    subcategories = request.subcategories
    duration_minutes = request.duration_minutes
    custom_tags = request.custom_tags

    logger.info(f"📥 Received job for episode {episode_id}")
    logger.info(f"   Subcategories: {subcategories}")
    logger.info(f"   Duration: {duration_minutes} minutes")
    logger.info(f"   Custom tags: {custom_tags}")

    try:
        # Initialize services
        episode_service = EpisodeService()
        generator = PodcastGenerator(episode_service)

        # Update status to processing
        logger.info(f"🔄 Starting generation for episode {episode_id}")
        episode_service.set_episode_status(
            episode_id, "processing", stage="started", progress=0
        )

        # Execute podcast generation pipeline
        await generator.generate_episode(episode_id, subcategories, duration_minutes, custom_tags)

        logger.info(f"✅ Completed podcast generation for episode {episode_id}")

        return {
            "status": "success",
            "episode_id": episode_id,
            "message": "Podcast generated successfully"
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to generate podcast for episode {episode_id}: {error_msg}")

        # Update episode status to failed
        try:
            episode_service = EpisodeService()
            episode_service.set_episode_status(
                episode_id, "failed", error=error_msg
            )
        except Exception as update_error:
            logger.error(f"Failed to update episode status: {update_error}")

        # Return error response
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "episode_id": episode_id,
                "error": error_msg
            }
        )


@app.post("/discover")
async def discover_articles():
    """
    Run RSS discovery to populate database with articles

    This endpoint triggers the full RSS discovery process which:
    - Fetches articles from all configured RSS feeds
    - Clusters similar articles into stories
    - Stores them in the database for podcast generation

    With concurrency=3, this uses 1 slot while 2 podcast generations can run simultaneously.
    """
    logger.info("📡 Starting RSS discovery...")

    try:
        from agent.services.rss_discovery_service import RSSDiscoveryService
        from agent.config import settings
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Create database connection
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Initialize service
        service = RSSDiscoveryService(db, debug_llm_responses=False)

        # Run discovery with no limits
        results = service.discover_and_process_articles(max_articles_per_feed=1000)

        logger.info(f"✅ Discovery completed: {results}")

        # Close database session
        db.close()

        return {
            "status": "success",
            "message": "RSS discovery completed",
            "results": results
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Discovery failed: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "error": error_msg
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "yourcast-worker",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "generate": "/generate (POST)",
            "discover": "/discover (POST)"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run the worker server
    # Cloud Run will set PORT environment variable
    import os
    port = int(os.environ.get("PORT", 8001))

    logger.info(f"🚀 Starting HTTP Worker on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
