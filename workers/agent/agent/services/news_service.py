import logging
import uuid
import requests
import feedparser
import trafilatura
from datetime import datetime, timedelta
from typing import List, Dict, Any
from agent.config import settings

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.news_api_key = settings.news_api_key
        self.rss_feeds = settings.rss_feeds
    
    def discover_articles(self, topics: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Discover recent articles for given topics"""
        articles = []
        
        # Try NewsAPI first
        if self.news_api_key:
            try:
                newsapi_articles = self._fetch_from_newsapi(topics, limit)
                articles.extend(newsapi_articles)
                logger.info(f"Found {len(newsapi_articles)} articles from NewsAPI")
            except Exception as e:
                logger.warning(f"NewsAPI failed: {str(e)}")
        
        # If we need more articles or NewsAPI failed, use RSS feeds
        if len(articles) < limit:
            try:
                rss_articles = self._fetch_from_rss(topics, limit - len(articles))
                articles.extend(rss_articles)
                logger.info(f"Found {len(rss_articles)} additional articles from RSS")
            except Exception as e:
                logger.warning(f"RSS feeds failed: {str(e)}")
        
        return articles[:limit]
    
    def _fetch_from_newsapi(self, topics: List[str], limit: int) -> List[Dict[str, Any]]:
        """Fetch articles from NewsAPI"""
        query = " OR ".join(topics)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": yesterday,
            "sortBy": "popularity",
            "language": "en",
            "pageSize": limit,
            "apiKey": self.news_api_key,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        for article in data.get("articles", []):
            if article.get("title") and article.get("url"):
                articles.append({
                    "title": article["title"],
                    "url": article["url"],
                    "published_date": article.get("publishedAt", ""),
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                })
        
        return articles
    
    def _fetch_from_rss(self, topics: List[str], limit: int) -> List[Dict[str, Any]]:
        """Fetch articles from RSS feeds"""
        articles = []
        topic_keywords = [topic.lower() for topic in topics]
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    if len(articles) >= limit:
                        break
                    
                    # Basic topic filtering
                    title = entry.get("title", "").lower()
                    summary = entry.get("summary", "").lower()
                    
                    if any(keyword in title or keyword in summary for keyword in topic_keywords):
                        published = entry.get("published_parsed")
                        published_date = ""
                        if published:
                            published_date = datetime(*published[:6]).isoformat()
                        
                        articles.append({
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "published_date": published_date,
                            "description": entry.get("summary", ""),
                            "source": feed.feed.get("title", "RSS Feed"),
                        })
                
            except Exception as e:
                logger.warning(f"Failed to parse RSS feed {feed_url}: {str(e)}")
                continue
        
        return articles
    
    def extract_article_content(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract full text content from articles using Trafilatura"""
        sources = []
        
        for article in articles:
            try:
                # Download article content
                downloaded = trafilatura.fetch_url(article["url"])
                if not downloaded:
                    continue
                
                # Extract text content
                text = trafilatura.extract(downloaded)
                if not text or len(text) < 100:  # Skip very short articles
                    continue
                
                # Generate excerpt from first paragraph
                excerpt = text.split("\n")[0][:200] + "..." if len(text) > 200 else text
                
                sources.append({
                    "id": str(uuid.uuid4()),
                    "title": article["title"],
                    "url": article["url"],
                    "published_date": article["published_date"],
                    "excerpt": excerpt,
                    "full_text": text,
                    "source_name": article["source"],
                })
                
                logger.info(f"Extracted content from: {article['title']}")
                
            except Exception as e:
                logger.warning(f"Failed to extract content from {article['url']}: {str(e)}")
                continue
        
        return sources