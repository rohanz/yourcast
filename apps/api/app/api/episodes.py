import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database.connection import get_db
from app.models import Episode, EpisodeSegment, Source
from app.schemas import (
    CreateEpisodeRequest,
    CreateEpisodeResponse,
    EpisodeSchema,
    EpisodeSegmentSchema,
    SourceSchema,
    EpisodeStatusEvent,
)
from app.services.episode_service_cloudtasks import EpisodeService
from app.middleware.auth import get_current_user
import json
import asyncio
import sys
import os

# No need to import agent services - API queries database directly

router = APIRouter()

@router.get("/tags/search")
def search_tags(query: str, db: Session = Depends(get_db)):
    """
    Search for tags matching user query.
    Returns tags sorted by popularity (most articles first) but doesn't show counts.
    """
    from sqlalchemy import text

    if not query or len(query) < 2:
        return {"tags": []}

    # Extract all unique tags from JSON arrays, sorted by article count
    # Normalize tags by grouping on lowercase to combine "NVIDIA", "Nvidia", "nvidia"
    # Use MAX(tag) to pick one consistent capitalization for display
    query_result = text("""
        SELECT MAX(tag) as tag, COUNT(*) as tag_count
        FROM articles
        CROSS JOIN LATERAL jsonb_array_elements_text(tags::jsonb) as tag
        WHERE tags IS NOT NULL
          AND tag ILIKE :query
        GROUP BY LOWER(tag)
        ORDER BY tag_count DESC
        LIMIT 20
    """)

    results = db.execute(query_result, {"query": f"%{query}%"}).fetchall()

    return {
        "tags": [row.tag for row in results]
    }

@router.get("/categories")
def get_available_categories(db: Session = Depends(get_db)):
    """Get available categories and subcategories with article counts and importance stats"""
    try:
        from sqlalchemy import text
        
        # Import RSS config to get all possible categories and subcategories
        # We'll add the agent path temporarily to import the config
        import sys
        import os
        
        # Add agent path to get RSS config
        agent_path = "/app/../../../../workers/agent"
        if agent_path not in sys.path:
            sys.path.insert(0, agent_path)
        
        try:
            from agent.rss_config import RSS_FEEDS_CONFIG, CATEGORY_ORDER
        except ImportError:
            # Fallback to hardcoded structure if import fails
            CATEGORY_ORDER = ["World News", "Politics & Government", "Business", "Technology", "Science & Environment", "Sports", "Arts & Culture", "Health", "Lifestyle"]
            RSS_FEEDS_CONFIG = {
                "World News": {"subcategories": ["Africa", "Asia", "Europe", "Middle East", "North America", "South America", "Oceania"]},
                "Politics & Government": {"subcategories": ["US Politics", "International Politics", "Elections", "Policy & Legislation", "Government Affairs"]},
                "Business": {"subcategories": ["Markets", "Corporations & Earnings", "Startups & Entrepreneurship", "Economy and Policy"]},
                "Technology": {"subcategories": ["AI & Machine Learning", "Gadgets & Consumer Tech", "Software & Apps", "Cybersecurity", "Hardware & Infrastructure"]},
                "Science & Environment": {"subcategories": ["Space & Astronomy", "Biology", "Physics & Chemistry", "Research & Academia", "Climate & Weather", "Sustainability", "Conservation & Wildlife"]},
                "Sports": {"subcategories": ["Football (Soccer)", "American Football", "Basketball", "Baseball", "Cricket", "Tennis", "F1", "Boxing", "MMA", "Golf", "Ice hockey", "Rugby", "Volleyball", "Table Tennis (Ping Pong)", "Athletics"]},
                "Arts & Culture": {"subcategories": ["Celebrity News", "Gaming", "Film & TV", "Music", "Literature", "Art & Design", "Fashion"]},
                "Health": {"subcategories": ["Public Health", "Medicine & Healthcare", "Fitness & Wellness", "Mental Health"]},
                "Lifestyle": {"subcategories": ["Travel", "Food & Dining", "Home & Garden", "Relationships & Family", "Hobbies"]}
            }
        
        # Query database for actual article stats
        query = text("""
            SELECT 
                a.category,
                a.subcategory,
                COUNT(DISTINCT a.article_id) as article_count,
                ROUND(AVG(sc.importance_score)::numeric, 1) as avg_importance,
                MAX(sc.importance_score) as max_importance,
                MAX(a.publication_timestamp) as latest_article
            FROM articles a
            LEFT JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
            WHERE a.category IS NOT NULL AND a.subcategory IS NOT NULL
            GROUP BY a.category, a.subcategory
        """)
        
        results = db.execute(query).fetchall()
        
        # Build database stats lookup
        db_stats = {}
        for row in results:
            if row.category not in db_stats:
                db_stats[row.category] = {}
            db_stats[row.category][row.subcategory] = {
                "article_count": row.article_count,
                "avg_importance": float(row.avg_importance) if row.avg_importance else 50.0,
                "max_importance": row.max_importance if row.max_importance else 50,
                "latest_article": row.latest_article.isoformat() if row.latest_article else None
            }
        
        # Build categories from RSS config with database stats
        categories_list = []
        for category_name in CATEGORY_ORDER:
            if category_name not in RSS_FEEDS_CONFIG:
                continue
                
            category_data = RSS_FEEDS_CONFIG[category_name]
            category_info = {
                "category": category_name,
                "subcategories": [],
                "total_articles": 0,
                "avg_importance": 50.0,
                "max_importance": 50
            }
            
            # Add subcategories from RSS config with database stats
            total_weighted_importance = 0
            total_articles = 0
            max_importance = 50
            
            for subcategory_name in category_data["subcategories"]:
                # Get database stats for this subcategory if available
                subcat_stats = db_stats.get(category_name, {}).get(subcategory_name, {
                    "article_count": 0,
                    "avg_importance": 50.0,
                    "max_importance": 50,
                    "latest_article": None
                })
                
                category_info["subcategories"].append({
                    "subcategory": subcategory_name,
                    "article_count": subcat_stats["article_count"],
                    "avg_importance": subcat_stats["avg_importance"],
                    "max_importance": subcat_stats["max_importance"],
                    "latest_article": subcat_stats["latest_article"]
                })
                
                # Accumulate for category totals
                article_count = subcat_stats["article_count"]
                total_articles += article_count
                if article_count > 0:
                    total_weighted_importance += subcat_stats["avg_importance"] * article_count
                    max_importance = max(max_importance, subcat_stats["max_importance"])
            
            # Calculate category-level stats
            category_info["total_articles"] = total_articles
            category_info["max_importance"] = max_importance
            if total_articles > 0:
                category_info["avg_importance"] = round(total_weighted_importance / total_articles, 1)
            
            categories_list.append(category_info)
        
        return {
            "categories": categories_list,
            "total_categories": len(categories_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@router.post("", response_model=CreateEpisodeResponse)
def create_episode(
    request: CreateEpisodeRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Get user ID from authenticated user
    user_id = user.get("uid")

    # Fetch user preferences to get custom_tags
    from app.models.user import User
    db_user = db.query(User).filter(User.id == user_id).first()
    custom_tags = []
    if db_user and db_user.preferences:
        custom_tags = db_user.preferences.get("custom_tags", [])

    # Create episode record associated with user
    episode_id = str(uuid.uuid4())
    episode = Episode(
        id=episode_id,
        user_id=user_id,
        title="Generating...",
        description="Your micro-podcast is being generated",
        subcategories=request.subcategories,
        status="pending"
    )

    db.add(episode)
    db.commit()

    # Queue episode generation job with Cloud Tasks
    episode_service = EpisodeService(db=db)
    episode_service.queue_episode_generation(
        episode_id,
        request.subcategories,
        request.duration_minutes,
        custom_tags=custom_tags
    )

    return CreateEpisodeResponse(episode_id=episode_id, status="pending")

@router.get("/list")
def list_user_episodes(
    limit: int = 5,
    search: str = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get list of user's past episodes with optional search"""
    from sqlalchemy import or_, func

    user_id = user.get("uid")

    # Base query: user's completed episodes only
    query = db.query(Episode).filter(
        and_(
            Episode.user_id == user_id,
            Episode.status == "completed"
        )
    )

    # Add search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Episode.title.ilike(search_term),
                Episode.description.ilike(search_term)
            )
        )

    # Get episodes ordered by creation date (newest first)
    episodes = query.order_by(Episode.created_at.desc()).limit(limit).all()

    # Format response
    result = []
    for episode in episodes:
        result.append({
            "id": str(episode.id),
            "title": episode.title,
            "description": episode.description,
            "created_at": episode.created_at.isoformat() if episode.created_at else None,
            "duration_seconds": episode.duration_seconds,
            "audio_url": episode.audio_url
        })

    return {"episodes": result, "count": len(result)}

@router.get("/{episode_id}", response_model=EpisodeSchema)
def get_episode(episode_id: str, db: Session = Depends(get_db)):
    # Force fresh query by expiring the session
    db.expire_all()
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Check Redis for updated status or populate missing URLs for completed episodes
    if episode.status == "pending":
        episode_service = EpisodeService()
        status_event = episode_service.get_episode_status_event(episode_id)
        if status_event and status_event.status in ["completed", "failed"]:
            # Update database with latest status from Redis
            episode.status = status_event.status
            if status_event.status == "completed":
                # Update other fields if available
                episode.title = "Generated Podcast"  # Could be improved
                episode.description = "Your micro-podcast has been generated"
                # Set file URLs pointing to Python API server
                episode.audio_url = f"{config.storage_base_url}/audio/{episode_id}.mp3"
                episode.transcript_url = f"{config.storage_base_url}/transcripts/{episode_id}.json"
                episode.vtt_url = f"{config.storage_base_url}/vtt/{episode_id}.vtt"
                episode.duration_seconds = 120  # Placeholder - could be improved
            db.commit()
    elif episode.status == "completed" and not episode.audio_url:
        # Fix completed episodes that are missing file URLs
        episode.audio_url = f"{config.storage_base_url}/audio/{episode_id}.mp3"
        episode.transcript_url = f"{config.storage_base_url}/transcripts/{episode_id}.json"
        episode.vtt_url = f"{config.storage_base_url}/vtt/{episode_id}.vtt"
        if episode.duration_seconds == 0:
            episode.duration_seconds = 120  # Placeholder - could be improved
        db.commit()
    
    # Fix for Docker environment: Convert UUID objects to strings for Pydantic
    # (Local development works fine, but Docker containers return UUID objects)
    episode_data = {
        'id': str(episode.id),
        'user_id': str(episode.user_id) if episode.user_id else None,
        'title': episode.title,
        'description': episode.description,
        'duration_seconds': episode.duration_seconds,
        'subcategories': episode.subcategories,
        'status': episode.status,
        'audio_url': episode.audio_url,
        'transcript_url': episode.transcript_url,
        'vtt_url': episode.vtt_url,
        'created_at': episode.created_at,
        'updated_at': episode.updated_at,
        'played_at': episode.played_at,
        'play_progress': episode.play_progress if episode.play_progress is not None else 0
    }
    return EpisodeSchema(**episode_data)

@router.get("/{episode_id}/segments", response_model=List[EpisodeSegmentSchema])
def get_episode_segments(episode_id: str, db: Session = Depends(get_db)):
    segments = (
        db.query(EpisodeSegment)
        .filter(EpisodeSegment.episode_id == episode_id)
        .order_by(EpisodeSegment.order_index)
        .all()
    )
    
    # Fix for Docker environment: Convert UUID objects to strings for Pydantic
    result = []
    for segment in segments:
        segment_data = {
            'id': str(segment.id),
            'episode_id': str(segment.episode_id),
            'start_time': segment.start_time,
            'end_time': segment.end_time,
            'text': segment.text,
            'source_id': str(segment.source_id) if segment.source_id else None,
            'order_index': segment.order_index
        }
        result.append(EpisodeSegmentSchema(**segment_data))
    
    return result

@router.get("/{episode_id}/sources", response_model=List[SourceSchema])
def get_episode_sources(episode_id: str, db: Session = Depends(get_db)):
    sources = db.query(Source).filter(Source.episode_id == episode_id).all()
    
    # Fix for Docker environment: Convert UUID objects to strings for Pydantic
    result = []
    for source in sources:
        source_data = {
            'id': str(source.id),
            'episode_id': str(source.episode_id),
            'title': source.title,
            'url': source.url,
            'published_date': source.published_date,
            'excerpt': source.excerpt,
            'summary': source.summary
        }
        result.append(SourceSchema(**source_data))
    
    return result

@router.get("/{episode_id}/events")
async def get_episode_events(episode_id: str, db: Session = Depends(get_db)):
    """Server-Sent Events endpoint for episode status updates using database polling (Cloud Run compatible)"""
    import asyncio

    async def event_generator():
        try:
            last_status = None

            # Poll database every 2 seconds for status changes
            while True:
                # Expire all cached data and query fresh from database
                db.expire_all()
                episode = db.query(Episode).filter(Episode.id == episode_id).first()

                if not episode:
                    error_event = EpisodeStatusEvent(
                        episode_id=episode_id,
                        status="error",
                        error="Episode not found"
                    )
                    yield f"data: {json.dumps(error_event.dict())}\n\n"
                    return

                # Check if status has changed (just compare status, not timestamp)
                if episode.status != last_status:
                    # Send status update
                    event = EpisodeStatusEvent(
                        episode_id=episode_id,
                        status=episode.status,
                        stage=episode.status,  # Use status as stage for simplicity
                        progress=None,
                        error=None,
                        timestamp=episode.updated_at.isoformat() if episode.updated_at else None
                    )
                    yield f"data: {json.dumps(event.dict())}\n\n"

                    last_status = episode.status

                    # Stop streaming if episode is completed or failed
                    if episode.status in ["completed", "failed"]:
                        return

                # Wait 2 seconds before next poll
                await asyncio.sleep(2)

        except Exception as e:
            error_event = EpisodeStatusEvent(
                episode_id=episode_id,
                status="error",
                error=str(e)
            )
            yield f"data: {json.dumps(error_event.dict())}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/today/check")
def check_todays_episode(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Check if user has an episode created today"""
    from datetime import datetime, timedelta
    from sqlalchemy import and_, func

    user_id = user.get("uid")

    # Get start of today (UTC)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Query for episodes created today
    episode = db.query(Episode).filter(
        and_(
            Episode.user_id == user_id,
            Episode.created_at >= today_start,
            Episode.status.in_(["completed", "pending", "discovering_articles", "extracting_content",
                               "generating_script", "generating_audio", "generating_timestamps",
                               "uploading_files", "finalizing"])
        )
    ).order_by(Episode.created_at.desc()).first()

    if episode:
        return {
            "has_episode": True,
            "episode_id": str(episode.id),
            "status": episode.status
        }
    else:
        return {
            "has_episode": False,
            "episode_id": None,
            "status": None
        }

@router.post("/{episode_id}/played")
def mark_episode_played(
    episode_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Mark episode as played when user has listened for 30+ seconds.
    Called once by frontend when playback hits 30s threshold.
    """
    from datetime import datetime

    user_id = user.get("uid")

    episode = db.query(Episode).filter(
        Episode.id == episode_id,
        Episode.user_id == user_id
    ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Mark as played (only set once, don't update if already played)
    if not episode.played_at:
        episode.played_at = datetime.utcnow()
        db.commit()
        return {"success": True, "played": True, "first_time": True}

    return {"success": True, "played": True, "first_time": False}

@router.post("/auto-generate")
def auto_generate_daily_episodes(db: Session = Depends(get_db)):
    """
    Auto-generate daily podcasts for users who listened to yesterday's episode.
    Called by Cloud Scheduler at 12am daily.

    Logic:
    1. Find users who listened to yesterday's podcast (played_at IS NOT NULL)
    2. Check they have preferences set
    3. Ensure they don't already have today's podcast
    4. Queue episode generation for qualifying users
    """
    from datetime import datetime, timedelta
    from sqlalchemy import text

    # Get yesterday's date range
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Query to find users eligible for auto-generation
    query = text("""
        WITH yesterday_episodes AS (
            SELECT DISTINCT e.user_id
            FROM episodes e
            WHERE e.created_at >= :yesterday_start
              AND e.created_at < :today_start
              AND e.status = 'completed'
              AND e.played_at IS NOT NULL  -- User listened for 30+ seconds
        ),
        today_episodes AS (
            SELECT DISTINCT user_id
            FROM episodes
            WHERE created_at >= :today_start
              AND status != 'failed'  -- Don't count failed episodes
        ),
        users_with_prefs AS (
            SELECT id, preferences
            FROM users
            WHERE preferences IS NOT NULL
              AND preferences::jsonb ? 'subcategories'
              AND jsonb_array_length(preferences::jsonb->'subcategories') > 0
        )
        SELECT u.id, u.preferences
        FROM users_with_prefs u
        INNER JOIN yesterday_episodes ye ON ye.user_id = u.id
        LEFT JOIN today_episodes te ON te.user_id = u.id
        WHERE te.user_id IS NULL  -- No episode today yet
    """)

    results = db.execute(query, {
        "yesterday_start": yesterday_start,
        "today_start": today_start
    }).fetchall()

    generated_count = 0
    episode_service = EpisodeService(db=db)

    for row in results:
        user_id = row.id
        subcategories = row.preferences.get("subcategories", [])
        custom_tags = row.preferences.get("custom_tags", [])

        if not subcategories:
            continue

        try:
            # Create episode
            episode_id = str(uuid.uuid4())
            episode = Episode(
                id=episode_id,
                user_id=user_id,
                title="Generating...",
                description="Your daily podcast",
                subcategories=subcategories,
                status="pending"
            )
            db.add(episode)
            db.commit()

            # Queue generation with default 5 minutes duration
            episode_service.queue_episode_generation(
                episode_id,
                subcategories,
                duration_minutes=5,
                custom_tags=custom_tags
            )
            generated_count += 1

        except Exception as e:
            print(f"Failed to queue episode for user {user_id}: {str(e)}")
            db.rollback()
            continue

    return {
        "success": True,
        "episodes_queued": generated_count,
        "timestamp": datetime.utcnow().isoformat()
    }

