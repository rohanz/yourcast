import logging
import psycopg2
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from agent.config import settings
from agent.rss_config import RSS_FEEDS_CONFIG, CATEGORY_ORDER

logger = logging.getLogger(__name__)

class SmartArticleService:
    # Coverage boost multiplier: higher values give more weight to article count
    # Formula: combined_score = importance_score + (COVERAGE_BOOST * log(article_count))
    COVERAGE_BOOST_MULTIPLIER = 17

    # Article freshness: only include articles from the last N days
    ARTICLE_FRESHNESS_DAYS = 5

    # Time decay rates per category (decay per hour)
    # Formula: score * exp(-age_hours * decay_rate)
    # Higher rate = faster decay (shorter shelf life)
    TIME_DECAY_RATES = {
        "World News": 0.05,           # Half-life ~14h - breaking news gets stale fast!
        "Politics & Government": 0.02, # Half-life ~35h - political developments unfold over days
        "Business": 0.025,            # Half-life ~28h - markets/earnings stay relevant
        "Technology": 0.01,           # Half-life ~69h - product launches/tech news durable
        "Science & Environment": 0.005, # Half-life ~139h - research/studies evergreen
        "Sports": 0.03,               # Half-life ~23h - sports news moderately durable
        "Arts & Culture": 0.005,      # Half-life ~139h - reviews/releases evergreen
        "Health": 0.008,              # Half-life ~87h - health news very durable
        "Lifestyle": 0.005,           # Half-life ~139h - lifestyle content evergreen
        "default": 0.02               # Half-life ~35h - gentle decay for unlisted categories
    }

    def __init__(self):
        """Initialize smart article service with database connection"""
        self.db_config = self._parse_database_url(settings.database_url)
    
    def _parse_database_url(self, database_url: str) -> dict:
        """Parse PostgreSQL database URL into connection components"""
        # Format: postgresql://user:password@host:port/database
        # Or Cloud SQL: postgresql://user:password@/database?host=/cloudsql/instance
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Check if host is in query params (Cloud SQL format)
        if 'host' in query_params:
            host = query_params['host'][0]
        else:
            host = parsed.hostname

        config = {
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path[1:]  # Remove leading /
        }

        # Only add host and port if they exist
        if host:
            config['host'] = host
        if parsed.port:
            config['port'] = parsed.port

        return config
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_articles_for_podcast(
        self,
        selected_categories: List[str],
        selected_subcategories: Optional[List[str]] = None,
        total_articles: int = 15,
        min_importance_score: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Smart article selection for podcast generation based on user preferences
        
        Args:
            selected_categories: List of category names user selected
            selected_subcategories: Optional list of subcategory names to include
            total_articles: Total number of articles to return
            min_importance_score: Minimum importance score to include (1-100)
        
        Returns:
            List of article dictionaries optimally distributed across categories
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Calculate articles per category
            num_categories = len(selected_categories)
            if num_categories == 0:
                logger.warning("No categories selected")
                return []
            
            articles_per_category = max(1, total_articles // num_categories)
            remainder = total_articles % num_categories
            
            logger.info(f"Distributing {total_articles} articles across {num_categories} categories:")
            logger.info(f"Base: {articles_per_category} per category, +{remainder} extra")
            
            all_articles = []
            
            for i, category in enumerate(selected_categories):
                # Calculate how many articles for this category
                category_limit = articles_per_category
                if i < remainder:  # Distribute remainder to first categories
                    category_limit += 1
                
                logger.info(f"Getting {category_limit} articles for {category}")
                
                # Build category-specific query
                query_conditions = [
                    "a.category = %s", 
                    "sc.importance_score >= %s"
                ]
                query_params = [category, min_importance_score]
                
                # Add subcategory filter if specified
                if selected_subcategories:
                    query_conditions.append("a.subcategory = ANY(%s)")
                    query_params.append(selected_subcategories)
                
                # Query for highest importance stories in this category
                query = f"""
                SELECT DISTINCT ON (a.cluster_id)
                    a.article_id,
                    a.cluster_id,
                    a.url,
                    a.source_name,
                    a.title,
                    a.summary,
                    a.publication_timestamp,
                    a.category,
                    a.subcategory,
                    a.tags,
                    a.created_at,
                    sc.canonical_title as story_title,
                    sc.importance_score
                FROM articles a
                INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
                WHERE {' AND '.join(query_conditions)}
                ORDER BY a.cluster_id, sc.importance_score DESC
                LIMIT %s
                """
                
                query_params.append(category_limit * 2)  # Get extra to ensure diversity
                
                cur.execute(query, query_params)
                category_results = cur.fetchall()
                
                # Sort by importance score and take the best ones
                sorted_results = sorted(category_results, key=lambda x: x[12], reverse=True)  # importance_score is index 12
                top_results = sorted_results[:category_limit]
                
                logger.info(f"Found {len(top_results)} articles for {category}")
                
                for row in top_results:
                    article = {
                        'article_id': row[0],
                        'cluster_id': row[1],
                        'url': row[2],
                        'source_name': row[3],
                        'title': row[4],
                        'summary': row[5],
                        'publication_timestamp': row[6].isoformat() if row[6] else None,
                        'category': row[7],
                        'subcategory': row[8],
                        'tags': row[9] or [],
                        'created_at': row[10].isoformat() if row[10] else None,
                        'story_title': row[11],
                        'importance_score': row[12]
                    }
                    all_articles.append(article)
            
            cur.close()
            conn.close()
            
            # Final sort by importance score across all categories
            final_articles = sorted(all_articles, key=lambda x: x['importance_score'], reverse=True)
            
            logger.info(f"Selected {len(final_articles)} total articles for podcast")
            if final_articles:
                score_range = f"{min(a['importance_score'] for a in final_articles)}-{max(a['importance_score'] for a in final_articles)}"
                logger.info(f"Importance score range: {score_range}")
            
            return final_articles[:total_articles]  # Ensure we don't exceed the limit
            
        except Exception as e:
            logger.error(f"Error getting articles for podcast: {str(e)}")
            return []
    
    def get_articles_by_subcategories(
        self,
        selected_subcategories: List[str],
        user_id: Optional[str] = None,
        total_articles: int = 8,
        min_importance_score: int = 40,
        custom_tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get articles filtered by subcategories and custom tags with balanced representation.

        Phase 1: Guarantees minimum representation:
        - At least 1 article per subcategory (if available above threshold)
        - At least 1 article per custom tag (if available above threshold)

        Phase 2: Fills remaining slots with highest scoring articles.

        Excludes clusters the user has already heard in previous episodes.

        Args:
            selected_subcategories: List of subcategory names to include
            user_id: User ID to filter out already-heard clusters
            total_articles: Total number of articles to return
            min_importance_score: Minimum importance score to include (1-100)
            custom_tags: Optional list of custom tags - each gets guaranteed 1 article

        Returns:
            List of article dictionaries from the specified subcategories and tags
        """
        custom_tags = custom_tags or []

        try:
            conn = self._get_connection()
            cur = conn.cursor()

            if not selected_subcategories and not custom_tags:
                logger.warning("No subcategories or tags selected")
                return []

            # Get clusters user has already heard
            heard_cluster_ids = set()
            if user_id:
                heard_query = """
                SELECT DISTINCT s.cluster_id
                FROM sources s
                JOIN episodes e ON s.episode_id = e.id
                WHERE e.user_id = %s AND s.cluster_id IS NOT NULL
                """
                cur.execute(heard_query, (user_id,))
                heard_results = cur.fetchall()
                heard_cluster_ids = {row[0] for row in heard_results}
                if heard_cluster_ids:
                    logger.info(f"Excluding {len(heard_cluster_ids)} already-heard clusters for user {user_id}")

            # Fetch ALL eligible articles in one query with coverage boost score
            cutoff_date = datetime.now() - timedelta(days=self.ARTICLE_FRESHNESS_DAYS)

            if custom_tags:
                logger.info(f"Fetching articles from subcategories {selected_subcategories} OR custom tags {custom_tags}")
            else:
                logger.info(f"Fetching all eligible articles from selected subcategories")

            # Single query to get all eligible articles with coverage boost AND time decay
            # Include articles that match subcategories OR custom tags
            if custom_tags:
                query = """
                SELECT DISTINCT ON (a.cluster_id)
                    a.article_id,
                    a.cluster_id,
                    a.url,
                    a.source_name,
                    a.title,
                    a.summary,
                    a.publication_timestamp,
                    a.category,
                    a.subcategory,
                    a.tags,
                    a.created_at,
                    sc.canonical_title as story_title,
                    sc.importance_score,
                    (SELECT COUNT(*) FROM articles WHERE cluster_id = a.cluster_id) as article_count,
                    (
                        (sc.importance_score + (%s * LOG(GREATEST((SELECT COUNT(*) FROM articles WHERE cluster_id = a.cluster_id), 1))))
                        * EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(a.publication_timestamp, a.created_at))) / 3600 *
                            CASE a.category
                                WHEN 'World News' THEN %s
                                WHEN 'Politics & Government' THEN %s
                                WHEN 'Business' THEN %s
                                WHEN 'Technology' THEN %s
                                WHEN 'Science & Environment' THEN %s
                                WHEN 'Sports' THEN %s
                                WHEN 'Arts & Culture' THEN %s
                                WHEN 'Health' THEN %s
                                WHEN 'Lifestyle' THEN %s
                                ELSE %s
                            END
                        )
                    ) as combined_score
                FROM articles a
                INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
                WHERE (
                    a.subcategory = ANY(%s)
                    OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(a.tags::jsonb) tag
                        WHERE LOWER(tag) = ANY(
                            SELECT LOWER(unnest(%s::text[]))
                        )
                    )
                )
                AND sc.importance_score >= %s
                AND COALESCE(a.publication_timestamp, a.created_at) >= %s
                ORDER BY a.cluster_id, combined_score DESC
                """
                cur.execute(query, (
                    self.COVERAGE_BOOST_MULTIPLIER,
                    self.TIME_DECAY_RATES["World News"],
                    self.TIME_DECAY_RATES["Politics & Government"],
                    self.TIME_DECAY_RATES["Business"],
                    self.TIME_DECAY_RATES["Technology"],
                    self.TIME_DECAY_RATES["Science & Environment"],
                    self.TIME_DECAY_RATES["Sports"],
                    self.TIME_DECAY_RATES["Arts & Culture"],
                    self.TIME_DECAY_RATES["Health"],
                    self.TIME_DECAY_RATES["Lifestyle"],
                    self.TIME_DECAY_RATES["default"],
                    selected_subcategories,
                    custom_tags,
                    min_importance_score,
                    cutoff_date
                ))
            else:
                query = """
                SELECT DISTINCT ON (a.cluster_id)
                    a.article_id,
                    a.cluster_id,
                    a.url,
                    a.source_name,
                    a.title,
                    a.summary,
                    a.publication_timestamp,
                    a.category,
                    a.subcategory,
                    a.tags,
                    a.created_at,
                    sc.canonical_title as story_title,
                    sc.importance_score,
                    (SELECT COUNT(*) FROM articles WHERE cluster_id = a.cluster_id) as article_count,
                    (
                        (sc.importance_score + (%s * LOG(GREATEST((SELECT COUNT(*) FROM articles WHERE cluster_id = a.cluster_id), 1))))
                        * EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(a.publication_timestamp, a.created_at))) / 3600 *
                            CASE a.category
                                WHEN 'World News' THEN %s
                                WHEN 'Politics & Government' THEN %s
                                WHEN 'Business' THEN %s
                                WHEN 'Technology' THEN %s
                                WHEN 'Science & Environment' THEN %s
                                WHEN 'Sports' THEN %s
                                WHEN 'Arts & Culture' THEN %s
                                WHEN 'Health' THEN %s
                                WHEN 'Lifestyle' THEN %s
                                ELSE %s
                            END
                        )
                    ) as combined_score
                FROM articles a
                INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
                WHERE a.subcategory = ANY(%s)
                AND sc.importance_score >= %s
                AND COALESCE(a.publication_timestamp, a.created_at) >= %s
                ORDER BY a.cluster_id, combined_score DESC
                """
                cur.execute(query, (
                    self.COVERAGE_BOOST_MULTIPLIER,
                    self.TIME_DECAY_RATES["World News"],
                    self.TIME_DECAY_RATES["Politics & Government"],
                    self.TIME_DECAY_RATES["Business"],
                    self.TIME_DECAY_RATES["Technology"],
                    self.TIME_DECAY_RATES["Science & Environment"],
                    self.TIME_DECAY_RATES["Sports"],
                    self.TIME_DECAY_RATES["Arts & Culture"],
                    self.TIME_DECAY_RATES["Health"],
                    self.TIME_DECAY_RATES["Lifestyle"],
                    self.TIME_DECAY_RATES["default"],
                    selected_subcategories,
                    min_importance_score,
                    cutoff_date
                ))
            all_results = cur.fetchall()

            cur.close()
            conn.close()

            logger.info(f"Fetched {len(all_results)} eligible articles before filtering")

            # Convert to article dictionaries and filter out heard clusters
            eligible_articles = []
            for row in all_results:
                cluster_id = row[1]
                if cluster_id not in heard_cluster_ids:
                    article = {
                        'article_id': row[0],
                        'cluster_id': cluster_id,
                        'url': row[2],
                        'source_name': row[3],
                        'title': row[4],
                        'summary': row[5],
                        'publication_timestamp': row[6].isoformat() if row[6] else None,
                        'category': row[7],
                        'subcategory': row[8],
                        'tags': row[9] or [],
                        'created_at': row[10].isoformat() if row[10] else None,
                        'story_title': row[11],
                        'importance_score': row[12],
                        'article_count': row[13],
                        'combined_score': row[14]
                    }
                    eligible_articles.append(article)

            logger.info(f"After filtering heard clusters: {len(eligible_articles)} eligible articles")

            if not eligible_articles:
                logger.warning("No eligible articles found after filtering")
                return []

            # Group articles by subcategory for selection
            articles_by_subcat = {}
            for article in eligible_articles:
                subcat = article['subcategory']
                if subcat not in articles_by_subcat:
                    articles_by_subcat[subcat] = []
                articles_by_subcat[subcat].append(article)

            # Sort each subcategory's articles by combined score
            for subcat in articles_by_subcat:
                articles_by_subcat[subcat].sort(key=lambda x: x['combined_score'], reverse=True)

            # World News subcategories (group these together)
            world_news_subcats = ["Africa", "Asia", "Europe", "Middle East", "North America", "South America", "Oceania"]
            world_news_selected = [sub for sub in selected_subcategories if sub in world_news_subcats]
            non_world_news_selected = [sub for sub in selected_subcategories if sub not in world_news_subcats]

            articles = []
            selected_cluster_ids = set()

            # NEW THREE-PHASE SELECTION SYSTEM
            # Phase 1: Guaranteed minimums (custom tags + World News if selected)
            # Phase 2a: At least 1 from each other subcategory
            # Phase 2b: Fill remaining with best overall from ALL sources

            logger.info("=" * 70)
            logger.info("PHASE 1: Guaranteed Minimums")
            logger.info("=" * 70)

            # Phase 1: Custom tags (1 per tag, guaranteed)
            if custom_tags:
                logger.info(f"Custom tags: Selecting 1 best article per tag")
                for tag in custom_tags:
                    tag_lower = tag.lower()
                    all_tag_matches = [
                        a for a in eligible_articles
                        if any(t.lower() == tag_lower for t in a.get('tags', []))
                    ]
                    logger.info(f"  Found {len(all_tag_matches)} articles matching '{tag}'")

                    tag_articles = [
                        a for a in all_tag_matches
                        if a['cluster_id'] not in selected_cluster_ids
                    ]
                    if tag_articles:
                        tag_articles.sort(key=lambda x: x['combined_score'], reverse=True)
                        best = tag_articles[0]
                        articles.append(best)
                        selected_cluster_ids.add(best['cluster_id'])
                        logger.info(f"  ✓ '{tag}': {best['title'][:60]}... (score: {best['importance_score']})")
                    else:
                        if len(all_tag_matches) > 0:
                            logger.warning(f"  ✗ '{tag}': All articles already heard")
                        else:
                            logger.warning(f"  ✗ '{tag}': No articles (filtered by date/importance)")

            # Phase 1: World News (at least 2, if selected)
            if world_news_selected:
                logger.info(f"World News: Selecting at least 2 from {len(world_news_selected)} regions")
                world_news_articles = []
                for subcat in world_news_selected:
                    if subcat in articles_by_subcat:
                        world_news_articles.extend(articles_by_subcat[subcat])

                world_news_articles = [a for a in world_news_articles if a['cluster_id'] not in selected_cluster_ids]
                world_news_articles.sort(key=lambda x: x['combined_score'], reverse=True)
                top_world_news = world_news_articles[:2]

                for article in top_world_news:
                    articles.append(article)
                    selected_cluster_ids.add(article['cluster_id'])
                    logger.info(f"  ✓ ({article['subcategory']}): {article['title'][:60]}... (score: {article['importance_score']})")

            logger.info(f"After Phase 1: {len(articles)} articles")

            logger.info("=" * 70)
            logger.info("PHASE 2a: Subcategory Diversity")
            logger.info("=" * 70)

            # Phase 2a: At least 1 from each other subcategory
            if non_world_news_selected:
                logger.info(f"Ensuring at least 1 from each of {len(non_world_news_selected)} subcategories")
                for subcategory in non_world_news_selected:
                    if subcategory in articles_by_subcat:
                        for article in articles_by_subcat[subcategory]:
                            if article['cluster_id'] not in selected_cluster_ids:
                                articles.append(article)
                                selected_cluster_ids.add(article['cluster_id'])
                                logger.info(f"  ✓ {subcategory}: {article['title'][:60]}... (score: {article['importance_score']})")
                                break
                        else:
                            logger.warning(f"  ✗ {subcategory}: No unselected articles")
                    else:
                        logger.warning(f"  ✗ {subcategory}: No articles found")

            logger.info(f"After Phase 2a: {len(articles)} articles")

            logger.info("=" * 70)
            logger.info(f"PHASE 2b: Fill Remaining (target: {total_articles})")
            logger.info("=" * 70)

            # Phase 2b: Fill remaining with best from ALL sources
            remaining_slots = total_articles - len(articles)
            if remaining_slots > 0:
                logger.info(f"Filling {remaining_slots} slots with best from ALL sources")
                unselected = [a for a in eligible_articles if a['cluster_id'] not in selected_cluster_ids]
                unselected.sort(key=lambda x: x['combined_score'], reverse=True)

                for article in unselected[:remaining_slots]:
                    articles.append(article)
                    selected_cluster_ids.add(article['cluster_id'])
                    logger.info(f"  Added {article['subcategory']}: {article['title'][:60]}... (score: {article['importance_score']}, combined: {article['combined_score']:.1f})")
            else:
                logger.info("No remaining slots needed")

            logger.info("=" * 70)
            logger.info(f"FINAL: {len(articles)} articles selected")
            logger.info("=" * 70)

            # Remove temporary fields used for selection
            for article in articles:
                article.pop('article_count', None)
                article.pop('combined_score', None)

            # Final sort by importance for consistent ordering
            articles.sort(key=lambda x: x['importance_score'], reverse=True)

            logger.info(f"Selected {len(articles)} total articles from subcategories: {selected_subcategories}")
            if articles:
                score_range = f"{min(a['importance_score'] for a in articles)}-{max(a['importance_score'] for a in articles)}"
                logger.info(f"Importance score range: {score_range}")

                # Log subcategory distribution
                subcat_counts = {}
                for article in articles:
                    subcat = article['subcategory']
                    subcat_counts[subcat] = subcat_counts.get(subcat, 0) + 1
                logger.info(f"Distribution: {dict(subcat_counts)}")

            return articles

        except Exception as e:
            logger.error(f"Error getting articles by subcategories: {str(e)}")
            return []

    def get_cluster_backups(self, cluster_id: str, exclude_article_ids: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get backup articles from the same cluster

        Args:
            cluster_id: The cluster ID to fetch articles from
            exclude_article_ids: Article IDs to exclude (typically the main article)
            limit: Maximum number of backup articles to return

        Returns:
            List of backup article dictionaries from the same cluster
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            query = """
            SELECT
                a.article_id,
                a.cluster_id,
                a.url,
                a.source_name,
                a.title,
                a.summary,
                a.publication_timestamp,
                a.category,
                a.subcategory,
                a.tags,
                a.created_at,
                sc.canonical_title as story_title,
                sc.importance_score
            FROM articles a
            INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
            WHERE a.cluster_id = %s
            AND a.article_id != ALL(%s)
            ORDER BY sc.importance_score DESC, a.publication_timestamp DESC
            LIMIT %s
            """

            cur.execute(query, (cluster_id, exclude_article_ids, limit))
            rows = cur.fetchall()

            backups = []
            for row in rows:
                backups.append({
                    'article_id': row[0],
                    'cluster_id': row[1],
                    'url': row[2],
                    'source_name': row[3],
                    'title': row[4],
                    'summary': row[5],
                    'publication_timestamp': row[6].isoformat() if row[6] else None,  # Convert to string like main query
                    'category': row[7],
                    'subcategory': row[8],
                    'tags': row[9] or [],
                    'created_at': row[10].isoformat() if row[10] else None,  # Convert to string like main query
                    'story_title': row[11],
                    'importance_score': row[12]
                })

            cur.close()
            conn.close()

            return backups

        except Exception as e:
            logger.error(f"Error getting cluster backups: {str(e)}")
            return []

    def get_available_categories(self) -> List[Dict[str, Any]]:
        """Get categories and subcategories from RSS config with article counts from database"""
        try:
            # Get database stats for existing articles
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Query to get article counts and importance stats per category/subcategory
            # Only for categories that exist in RSS config
            valid_categories = list(RSS_FEEDS_CONFIG.keys())
            stats_query = """
            SELECT 
                a.category,
                a.subcategory,
                COUNT(*) as article_count,
                AVG(sc.importance_score) as avg_importance,
                MAX(sc.importance_score) as max_importance,
                MAX(a.publication_timestamp) as latest_article
            FROM articles a
            INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
            WHERE a.publication_timestamp >= %s
            AND a.category = ANY(%s)
            GROUP BY a.category, a.subcategory
            """
            
            # Look back 7 days for recent articles
            cutoff_time = datetime.now() - timedelta(days=7)
            cur.execute(stats_query, (cutoff_time, valid_categories))
            
            # Build database stats lookup
            db_stats = {}
            for row in cur.fetchall():
                category, subcategory, count, avg_importance, max_importance, latest = row
                if category not in db_stats:
                    db_stats[category] = {}
                db_stats[category][subcategory] = {
                    'article_count': count,
                    'avg_importance': round(avg_importance, 1) if avg_importance else 50.0,
                    'max_importance': max_importance or 50,
                    'latest_article': latest.isoformat() if latest else None
                }
            
            cur.close()
            conn.close()
            
            # Build categories from RSS config with database stats in the desired order
            result = []
            
            # Build categories in the predefined order
            for category_name in CATEGORY_ORDER:
                if category_name not in RSS_FEEDS_CONFIG:
                    continue  # Skip if category doesn't exist in config
                    
                category_data = RSS_FEEDS_CONFIG[category_name]
                category_info = {
                    'category': category_name,
                    'subcategories': [],
                    'total_articles': 0,
                    'avg_importance': 50.0,
                    'max_importance': 50
                }
                
                # Add subcategories from RSS config with database stats
                total_weighted_importance = 0
                total_articles = 0
                max_importance = 50
                
                for subcategory_name in category_data['subcategories']:
                    # Get database stats for this subcategory if available
                    subcat_stats = db_stats.get(category_name, {}).get(subcategory_name, {
                        'article_count': 0,
                    'avg_importance': 50.0,
                    'max_importance': 50,
                        'latest_article': None
                    })
                    
                    category_info['subcategories'].append({
                        'subcategory': subcategory_name,
                        'article_count': subcat_stats['article_count'],
                        'avg_importance': subcat_stats['avg_importance'],
                        'max_importance': subcat_stats['max_importance'],
                        'latest_article': subcat_stats['latest_article']
                    })
                    
                    # Accumulate for category totals
                    article_count = subcat_stats['article_count']
                    total_articles += article_count
                    if article_count > 0:
                        total_weighted_importance += subcat_stats['avg_importance'] * article_count
                        max_importance = max(max_importance, subcat_stats['max_importance'])
                
                # Calculate category-level stats
                category_info['total_articles'] = total_articles
                category_info['max_importance'] = max_importance
                if total_articles > 0:
                    category_info['avg_importance'] = round(total_weighted_importance / total_articles, 1)
                
                result.append(category_info)
            
            # Categories are already in the desired order, no sorting needed
            
            logger.info(f"Built {len(result)} categories from RSS config with database stats")
            return result
            
        except Exception as e:
            logger.error(f"Error getting available categories: {str(e)}")
            # Fallback to RSS config only if database fails - use predefined order
            result = []
            for category_name in CATEGORY_ORDER:
                if category_name not in RSS_FEEDS_CONFIG:
                    continue  # Skip if category doesn't exist in config
                    
                category_data = RSS_FEEDS_CONFIG[category_name]
                category_info = {
                    'category': category_name,
                    'subcategories': [],
                    'total_articles': 0,
                    'avg_importance': 50.0,
                    'max_importance': 50
                }
                
                for subcategory_name in category_data['subcategories']:
                    category_info['subcategories'].append({
                        'subcategory': subcategory_name,
                        'article_count': 0,
                        'avg_importance': 50.0,
                        'max_importance': 50,
                        'latest_article': None
                    })
                
                result.append(category_info)
            
            return result
    
    def get_top_stories_by_importance(
        self, 
        limit: int = 10, 
        min_importance: int = 70,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get top stories by importance score for breaking news or highlights"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            query = """
            SELECT DISTINCT ON (a.cluster_id)
                a.article_id,
                a.cluster_id,
                a.url,
                a.source_name,
                a.title,
                a.summary,
                a.publication_timestamp,
                a.category,
                a.subcategory,
                a.tags,
                sc.canonical_title as story_title,
                sc.importance_score
            FROM articles a
            INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
            WHERE a.publication_timestamp >= %s 
            AND sc.importance_score >= %s
            ORDER BY a.cluster_id, sc.importance_score DESC, a.publication_timestamp DESC
            """
            
            cur.execute(query, (cutoff_time, min_importance))
            results = cur.fetchall()
            
            # Sort by importance score and take top stories
            sorted_results = sorted(results, key=lambda x: x[11], reverse=True)  # importance_score is index 11
            top_stories = sorted_results[:limit]
            
            articles = []
            for row in top_stories:
                article = {
                    'article_id': row[0],
                    'cluster_id': row[1],
                    'url': row[2],
                    'source_name': row[3],
                    'title': row[4],
                    'summary': row[5],
                    'publication_timestamp': row[6].isoformat() if row[6] else None,
                    'category': row[7],
                    'subcategory': row[8],
                    'tags': row[9] or [],
                    'story_title': row[10],
                    'importance_score': row[11]
                }
                articles.append(article)
            
            cur.close()
            conn.close()
            
            logger.info(f"Found {len(articles)} top stories with importance >= {min_importance}")
            return articles
            
        except Exception as e:
            logger.error(f"Error getting top stories: {str(e)}")
            return []
    
    def get_article_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about articles in the database"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Get overall stats
            stats_query = """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(DISTINCT a.cluster_id) as unique_stories,
                COUNT(DISTINCT a.category) as categories,
                AVG(sc.importance_score) as avg_importance,
                MIN(a.publication_timestamp) as oldest_article,
                MAX(a.publication_timestamp) as newest_article
            FROM articles a
            INNER JOIN story_clusters sc ON a.cluster_id = sc.cluster_id
            """
            
            cur.execute(stats_query)
            row = cur.fetchone()
            
            stats = {
                'total_articles': row[0],
                'unique_stories': row[1], 
                'categories_count': row[2],
                'avg_importance_score': round(row[3], 1) if row[3] else 50.0,
                'oldest_article': row[4].isoformat() if row[4] else None,
                'newest_article': row[5].isoformat() if row[5] else None
            }
            
            # Get importance score distribution
            importance_query = """
            SELECT 
                sc.importance_score,
                COUNT(*) as story_count
            FROM story_clusters sc
            GROUP BY sc.importance_score
            ORDER BY sc.importance_score
            """
            
            cur.execute(importance_query)
            importance_distribution = {}
            for row in cur.fetchall():
                importance_distribution[row[0]] = row[1]
            
            stats['importance_distribution'] = importance_distribution
            
            # Get recent articles count (last 24 hours)
            recent_query = """
            SELECT COUNT(*) FROM articles 
            WHERE publication_timestamp >= %s
            """
            
            cutoff_time = datetime.now() - timedelta(hours=24)
            cur.execute(recent_query, (cutoff_time,))
            stats['recent_articles_24h'] = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting article stats: {str(e)}")
            return {}
