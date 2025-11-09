import logging
import feedparser
import trafilatura
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent.config import settings
from agent.services.clustering_service import ClusteringService
from agent.rss_config import get_feed_category, get_all_feeds

logger = logging.getLogger(__name__)

class RSSDiscoveryService:
    """
    RSS-based news discovery service that replaces NewsAPI.
    Fetches from RSS feeds and processes through clustering pipeline.
    """
    
    def __init__(self, db_session: Session, debug_llm_responses: bool = False):
        """Initialize the RSS discovery service"""
        self.db = db_session
        self.clustering_service = ClusteringService(db_session, debug_llm_responses=debug_llm_responses)
        self.rss_feeds = get_all_feeds()
        
    def discover_and_process_articles(self, max_articles_per_feed: int = 20, max_workers: int = 10) -> Dict[str, Any]:
        """
        Main method: Discover articles from RSS feeds and process through clustering

        Args:
            max_articles_per_feed: Maximum articles to process per RSS feed
            max_workers: Maximum number of parallel feed processing threads

        Returns:
            Summary of processing results
        """
        logger.info(f"Starting RSS discovery with {max_workers} parallel workers for {len(self.rss_feeds)} feeds (rate-limited to stay under Gemini API limits)...")

        results = {
            'feeds_processed': 0,
            'articles_discovered': 0,
            'articles_processed': 0,
            'new_articles': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'new_clusters': 0,
            'feed_results': []
        }

        # Process feeds in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all feed processing tasks
            future_to_feed = {
                executor.submit(self._process_feed, feed_url, max_articles_per_feed): feed_url
                for feed_url in self.rss_feeds
            }

            # Collect results as they complete
            for future in as_completed(future_to_feed):
                feed_url = future_to_feed[future]
                try:
                    feed_result = future.result()
                    results['feed_results'].append(feed_result)

                    # Aggregate results
                    results['feeds_processed'] += 1
                    results['articles_discovered'] += feed_result['articles_discovered']
                    results['articles_processed'] += feed_result['articles_processed']
                    results['new_articles'] += feed_result['new_articles']
                    results['duplicates_skipped'] += feed_result['duplicates_skipped']
                    results['errors'] += feed_result['errors']

                    if results['feeds_processed'] % 10 == 0:
                        logger.info(f"Progress: {results['feeds_processed']}/{len(self.rss_feeds)} feeds processed")
                except Exception as e:
                    logger.error(f"Error processing feed {feed_url}: {str(e)}")
                    results['errors'] += 1

        logger.info(f"RSS discovery complete: {results['new_articles']} new articles from {results['feeds_processed']} feeds")
        return results
    
    def _process_feed(self, feed_url: str, max_articles: int) -> Dict[str, Any]:
        """Process a single RSS feed"""
        logger.info(f"Processing RSS feed: {feed_url}")
        
        result = {
            'feed_url': feed_url,
            'articles_discovered': 0,
            'articles_processed': 0,
            'new_articles': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'status': 'success'
        }
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                logger.warning(f"RSS feed returned status {feed.status}: {feed_url}")
                result['status'] = f'http_error_{feed.status}'
                return result
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"No entries found in RSS feed: {feed_url}")
                result['status'] = 'no_entries'
                return result
            
            # Get feed source name and category
            source_name = self._extract_source_name(feed, feed_url)
            feed_category = get_feed_category(feed_url)
            
            # Process articles
            articles_to_process = []
            for entry in feed.entries[:max_articles]:
                article_data = self._parse_rss_entry(entry, source_name)
                if article_data:
                    # Add feed category to article data
                    article_data['feed_category'] = feed_category
                    articles_to_process.append(article_data)
                    result['articles_discovered'] += 1
            
            # Process through clustering service
            for article_data in articles_to_process:
                try:
                    article_id = self.clustering_service.process_article(article_data)
                    result['articles_processed'] += 1
                    
                    if article_id:
                        result['new_articles'] += 1
                    else:
                        result['duplicates_skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process article {article_data.get('title', 'Unknown')}: {str(e)}")
                    result['errors'] += 1
            
            logger.info(f"Feed processed: {result['new_articles']} new articles from {feed_url}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process RSS feed {feed_url}: {str(e)}")
            result['status'] = 'error'
            result['errors'] = 1
            return result
    
    def _extract_source_name(self, feed, feed_url: str) -> str:
        """Extract source name from RSS feed"""
        if hasattr(feed, 'feed'):
            if hasattr(feed.feed, 'title') and feed.feed.title:
                return feed.feed.title
            if hasattr(feed.feed, 'link') and feed.feed.link:
                # Extract domain name from link
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(feed.feed.link).netloc
                    return domain.replace('www.', '').title()
                except:
                    pass
        
        # Fallback: extract from feed URL
        try:
            from urllib.parse import urlparse
            domain = urlparse(feed_url).netloc
            return domain.replace('www.', '').replace('feeds.', '').title()
        except:
            return "Unknown Source"
    
    def _parse_rss_entry(self, entry, source_name: str) -> Optional[Dict[str, Any]]:
        """Parse a single RSS entry into article data"""
        try:
            # Required fields
            if not hasattr(entry, 'title') or not entry.title:
                return None
            if not hasattr(entry, 'link') or not entry.link:
                return None
            
            # Parse publication date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:6])
                except:
                    pass

            # If RSS feed doesn't provide a date, use discovery date as fallback
            # This prevents frontend from showing "Jan 1, 1970" (Unix epoch)
            if not published_date:
                published_date = datetime.now()

            # Extract summary/description
            summary = ""
            if hasattr(entry, 'summary') and entry.summary:
                summary = self._clean_html_text(entry.summary)
            elif hasattr(entry, 'description') and entry.description:
                summary = self._clean_html_text(entry.description)
            
            # Skip very old articles (older than 7 days)
            if published_date and published_date < datetime.now() - timedelta(days=7):
                logger.debug(f"Skipping old article: {entry.title}")
                return None
            
            return {
                'title': entry.title.strip(),
                'url': entry.link.strip(),
                'summary': summary,
                'published_date': published_date,
                'source_name': source_name
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse RSS entry: {str(e)}")
            return None
    
    def _clean_html_text(self, html_text: str) -> str:
        """Clean HTML tags from text"""
        if not html_text:
            return ""
        
        try:
            # Use trafilatura for HTML cleaning
            cleaned = trafilatura.extract(html_text, include_formatting=False)
            if cleaned:
                return cleaned.strip()
        except:
            pass
        
        # Fallback: simple HTML tag removal
        import re
        cleaned = re.sub(r'<[^>]+>', '', html_text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def get_recent_clusters(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recently created or updated story clusters
        
        Args:
            hours: Look back this many hours for recent activity
            limit: Maximum number of clusters to return
            
        Returns:
            List of story clusters with article counts
        """
        try:
            from sqlalchemy import text
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            query = text("""
                SELECT 
                    sc.cluster_id,
                    sc.canonical_title,
                    sc.created_at,
                    COUNT(a.article_id) as article_count,
                    MAX(a.created_at) as last_article_added,
                    array_agg(DISTINCT a.category) as categories,
                    array_agg(DISTINCT a.source_name) as sources
                FROM story_clusters sc
                LEFT JOIN articles a ON sc.cluster_id = a.cluster_id
                WHERE sc.created_at >= :cutoff_time OR a.created_at >= :cutoff_time
                GROUP BY sc.cluster_id, sc.canonical_title, sc.created_at
                ORDER BY MAX(a.created_at) DESC, sc.created_at DESC
                LIMIT :limit
            """)
            
            results = self.db.execute(query, {
                "cutoff_time": cutoff_time,
                "limit": limit
            }).fetchall()
            
            clusters = []
            for row in results:
                clusters.append({
                    'cluster_id': row.cluster_id,
                    'canonical_title': row.canonical_title,
                    'created_at': row.created_at,
                    'article_count': row.article_count,
                    'last_article_added': row.last_article_added,
                    'categories': [c for c in row.categories if c],
                    'sources': [s for s in row.sources if s]
                })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to get recent clusters: {str(e)}")
            return []
    
    def get_cluster_articles(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get all articles for a specific cluster"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT 
                    article_id, title, summary, url, source_name,
                    publication_timestamp, category, subcategory, tags,
                    created_at
                FROM articles
                WHERE cluster_id = :cluster_id
                ORDER BY publication_timestamp DESC, created_at DESC
            """)
            
            results = self.db.execute(query, {"cluster_id": cluster_id}).fetchall()
            
            articles = []
            for row in results:
                articles.append({
                    'article_id': row.article_id,
                    'title': row.title,
                    'summary': row.summary,
                    'url': row.url,
                    'source_name': row.source_name,
                    'publication_timestamp': row.publication_timestamp,
                    'category': row.category,
                    'subcategory': row.subcategory,
                    'tags': row.tags,
                    'created_at': row.created_at
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to get cluster articles: {str(e)}")
            return []
