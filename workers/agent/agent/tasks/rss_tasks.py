import logging
from celery import shared_task
from datetime import datetime
from sqlalchemy.orm import sessionmaker

from agent.config import settings
from agent.services.rss_discovery_service import RSSDiscoveryService

# TODO: Import database connection - adjust path as needed
# from app.database.connection import engine

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="rss_discovery")
def discover_rss_articles(self, max_articles_per_feed: int = 20):
    """
    Celery task to discover and process RSS articles
    
    This task should run every 3 hours as specified in your requirements
    """
    logger.info("Starting RSS discovery task...")
    
    try:
        # TODO: Replace with actual database session creation
        # SessionLocal = sessionmaker(bind=engine)
        # db = SessionLocal()
        
        # For now, we'll need to create a proper database connection
        # This is a placeholder that needs to be updated with actual DB connection
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Initialize RSS discovery service
            rss_service = RSSDiscoveryService(db)
            
            # Discover and process articles
            results = rss_service.discover_and_process_articles(max_articles_per_feed)
            
            # Log results
            logger.info(f"RSS discovery completed successfully:")
            logger.info(f"  - Feeds processed: {results['feeds_processed']}")
            logger.info(f"  - Articles discovered: {results['articles_discovered']}")
            logger.info(f"  - New articles: {results['new_articles']}")
            logger.info(f"  - Duplicates skipped: {results['duplicates_skipped']}")
            logger.info(f"  - Errors: {results['errors']}")
            
            # Update task state with results
            self.update_state(
                state='SUCCESS',
                meta={
                    'results': results,
                    'completed_at': datetime.now().isoformat()
                }
            )
            
            return results
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"RSS discovery task failed: {str(e)}")
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
        )
        
        raise

@shared_task(bind=True, name="get_recent_clusters")
def get_recent_clusters(self, hours: int = 24, limit: int = 20):
    """
    Get recent story clusters for monitoring/debugging
    """
    logger.info(f"Fetching recent clusters from last {hours} hours...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            rss_service = RSSDiscoveryService(db)
            clusters = rss_service.get_recent_clusters(hours, limit)
            
            logger.info(f"Found {len(clusters)} recent clusters")
            return {
                'clusters': clusters,
                'count': len(clusters),
                'hours': hours,
                'fetched_at': datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to get recent clusters: {str(e)}")
        raise

@shared_task(bind=True, name="manual_rss_discovery")  
def manual_rss_discovery(self, feed_urls: list = None, max_articles: int = 10):
    """
    Manually trigger RSS discovery for specific feeds (useful for testing)
    """
    logger.info("Starting manual RSS discovery...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            rss_service = RSSDiscoveryService(db)
            
            # If specific feeds provided, temporarily override
            if feed_urls:
                original_feeds = rss_service.rss_feeds
                rss_service.rss_feeds = feed_urls
                logger.info(f"Using custom feeds: {feed_urls}")
            
            results = rss_service.discover_and_process_articles(max_articles)
            
            # Restore original feeds if overridden
            if feed_urls:
                rss_service.rss_feeds = original_feeds
            
            logger.info(f"Manual RSS discovery completed: {results['new_articles']} new articles")
            return results
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Manual RSS discovery failed: {str(e)}")
        raise
