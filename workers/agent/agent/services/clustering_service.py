import logging
import hashlib
import uuid
import json
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from agent.config import settings
from agent.services.embedding_service import EmbeddingService
from agent.services.llm_service import LLMService
from agent.rss_config import get_feed_category, get_category_subcategories

# Import models (we'll need to update the import path based on your structure)
# from app.models.article import Article
# from app.models.story_cluster import StoryCluster

logger = logging.getLogger(__name__)

class ClusteringService:
    def __init__(self, db_session: Session, debug_llm_responses: bool = False):
        """Initialize the clustering service"""
        self.db = db_session
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.similarity_threshold = 0.85
        self.debug_llm_responses = debug_llm_responses
        
    def process_article(self, article_data: Dict[str, Any]) -> Optional[str]:
        """
        Process a single article through the clustering pipeline
        
        Args:
            article_data: Dictionary containing article metadata
            
        Returns:
            Article ID if successful, None if failed or duplicate
        """
        try:
            # Step 1: Calculate uniqueness hash
            uniqueness_hash = self._calculate_hash(article_data['url'])
            
            # Step 2: Check for duplicates
            if self._is_duplicate(uniqueness_hash):
                logger.info(f"Skipping duplicate article: {article_data['title']}")
                return None
            
            # Step 3: Generate embedding
            embedding_text = f"{article_data['title']} {article_data.get('summary', '')}"
            embedding = self.embedding_service.generate_embedding(embedding_text)
            
            if embedding is None:
                logger.error(f"Failed to generate embedding for: {article_data['title']}")
                return None
            
            # Step 4: Find similar articles and clusters
            similar_articles, cluster_candidates = self._find_similar_articles(embedding)
            
            # Step 5: Use AI judge to determine clustering
            cluster_decision = self._ai_judge_clustering(article_data, similar_articles)
            
            # Step 6: Process clustering decision
            if cluster_decision['action'] == 'create_new':
                cluster_id = self._create_new_cluster(article_data, cluster_decision)
            else:
                cluster_id = cluster_decision['cluster_id']
            
            # Step 7: Save article to database
            article_id = self._save_article(
                article_data, 
                uniqueness_hash, 
                embedding, 
                cluster_id,
                cluster_decision
            )
            
            logger.info(f"Successfully processed article: {article_data['title']} -> {cluster_id}")
            return article_id
            
        except Exception as e:
            logger.error(f"Failed to process article {article_data.get('title', 'Unknown')}: {str(e)}")
            # Rollback any failed transaction to reset connection state
            try:
                self.db.rollback()
            except:
                pass
            return None
    
    def process_articles_batch(self, articles_data: List[Dict[str, Any]]) -> List[Optional[str]]:
        """Process multiple articles in a batch"""
        results = []
        for article_data in articles_data:
            result = self.process_article(article_data)
            results.append(result)
        return results
    
    def _calculate_hash(self, url: str) -> str:
        """Calculate MD5 hash of URL for duplicate detection"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_duplicate(self, uniqueness_hash: str) -> bool:
        """Check if article hash already exists in database"""
        # TODO: Replace with actual database query
        # query = self.db.query(Article).filter(Article.uniqueness_hash == uniqueness_hash).first()
        # return query is not None
        
        # Placeholder implementation
        result = self.db.execute(
            text("SELECT 1 FROM articles WHERE uniqueness_hash = :hash LIMIT 1"),
            {"hash": uniqueness_hash}
        ).fetchone()
        return result is not None
    
    def _find_similar_articles(self, embedding: np.ndarray) -> Tuple[List[Dict], List[str]]:
        """
        Find articles with similar embeddings using pgvector
        
        Returns:
            Tuple of (similar_articles_data, cluster_ids)
        """
        try:
            # Convert numpy array to list for SQL
            embedding_list = embedding.tolist()
            
            # Use pgvector's cosine similarity search
            # This query finds articles with similarity > threshold
            # Use CAST syntax instead of ::vector with bind parameters
            query = text("""
                SELECT
                    article_id, title, summary, cluster_id, source_name, publication_timestamp,
                    1 - (embedding <=> CAST(:embedding_param AS vector)) as similarity
                FROM articles
                WHERE 1 - (embedding <=> CAST(:embedding_param AS vector)) > :threshold_param
                ORDER BY similarity DESC
                LIMIT 10
            """)
            
            results = self.db.execute(query, {
                "embedding_param": json.dumps(embedding_list),
                "threshold_param": self.similarity_threshold
            }).fetchall()
            
            similar_articles = []
            cluster_candidates = set()
            
            for row in results:
                similar_articles.append({
                    'article_id': row.article_id,
                    'title': row.title,
                    'summary': row.summary,
                    'cluster_id': row.cluster_id,
                    'source_name': row.source_name,
                    'publication_timestamp': row.publication_timestamp,
                    'similarity': row.similarity
                })
                cluster_candidates.add(row.cluster_id)
            
            return similar_articles, list(cluster_candidates)
            
        except Exception as e:
            logger.error(f"Failed to find similar articles: {str(e)}")
            try:
                self.db.rollback()
            except:
                pass
            return [], []
    
    def _ai_judge_clustering(self, new_article: Dict[str, Any], similar_articles: List[Dict]) -> Dict[str, Any]:
        """
        Use AI to determine if article should join existing cluster or create new one
        """
        # Use feed category if available, otherwise fall back to keyword categorization
        feed_category = new_article.get('feed_category', self._categorize_article(new_article))
        
        if not similar_articles:
            # Still call AI judge to generate subcategories and tags, even without similar articles
            try:
                # Use the existing clustering prompt but with empty similar_articles list
                prompt = self._create_clustering_prompt(new_article, [])
                response = self.llm_service.generate_text(prompt)
                
                # Debug: Log the LLM response if enabled
                if self.debug_llm_responses:
                    print(f"\n🤖 LLM Response for '{new_article['title'][:50]}...':")
                    print(f"📝 Response: {response}")
                    print("-" * 80)
                
                decision = self._parse_ai_decision(response, [])
                
                # Ensure it's marked as create_new
                decision['action'] = 'create_new'
                decision['reason'] = 'No similar articles found'
                decision['cluster_id'] = None
                
                return decision
                
            except Exception as e:
                logger.error(f"AI categorization failed: {str(e)}")
                return {
                    'action': 'create_new',
                    'reason': 'No similar articles found, AI categorization failed',
                    'category': feed_category,
                    'subcategory': None,
                    'tags': []
                }
        
        try:
            # Prepare context for AI judge
            similar_context = []
            for article in similar_articles[:5]:  # Limit to top 5 most similar
                similar_context.append({
                    'title': article['title'],
                    'summary': article['summary'],
                    'cluster_id': article['cluster_id'],
                    'similarity': article['similarity']
                })
            
            # Create prompt for AI judge
            prompt = self._create_clustering_prompt(new_article, similar_context)
            
            # Get AI decision
            response = self.llm_service.generate_text(prompt)
            
            # Debug: Log the LLM response if enabled
            if self.debug_llm_responses:
                print(f"\n🤖 LLM Response for '{new_article['title'][:50]}...':")
                print(f"📝 Response: {response}")
                print("-" * 80)
            
            decision = self._parse_ai_decision(response, similar_articles)
            
            return decision
            
        except Exception as e:
            logger.error(f"AI judge failed, creating new cluster: {str(e)}")
            return {
                'action': 'create_new',
                'reason': 'AI judge error',
                'category': self._categorize_article(new_article),
                'subcategory': None,
                'tags': []
            }
    
    def _create_clustering_prompt(self, new_article: Dict[str, Any], similar_articles: List[Dict]) -> str:
        """Create prompt for AI clustering decision"""

        # Build flat list of ALL subcategories across all categories
        from agent.rss_config import RSS_FEEDS_CONFIG
        all_subcategories = []
        for category, data in RSS_FEEDS_CONFIG.items():
            all_subcategories.extend(data.get('subcategories', []))

        subcategories_str = ', '.join(sorted(all_subcategories))

        # Format publication date for new article
        from datetime import timezone
        new_pub_date = new_article.get('publication_timestamp')
        new_pub_str = new_pub_date.strftime('%Y-%m-%d %H:%M UTC') if new_pub_date else 'Unknown'

        prompt = f"""You are a news editor determining if articles belong to the same story.

NEW ARTICLE:
Title: {new_article['title']}
Summary: {new_article.get('summary', 'No summary')}
Source: {new_article['source_name']}
Publication Date: {new_pub_str}

SIMILAR EXISTING ARTICLES:
"""

        for i, article in enumerate(similar_articles, 1):
            # Calculate age relative to new article
            article_pub_date = article.get('publication_timestamp')
            if article_pub_date and new_pub_date:
                age_hours = (new_pub_date - article_pub_date).total_seconds() / 3600
                age_str = f"{age_hours:.1f} hours ago"
                pub_str = article_pub_date.strftime('%Y-%m-%d %H:%M UTC')
            else:
                age_str = "Unknown"
                pub_str = "Unknown"

            prompt += f"""
{i}. Title: {article['title']}
   Summary: {article['summary']}
   Publication Date: {pub_str} ({age_str})
   Cluster ID: {article['cluster_id']}
   Similarity: {article['similarity']:.3f}
"""

        # Get feed category hint for few-shot examples only
        feed_category = new_article.get('feed_category', self._categorize_article(new_article))
        examples = self._get_few_shot_examples(feed_category)
        
        prompt += f"""
INSTRUCTIONS:
1. Determine if the new article is about the same story as any existing article
2. Consider: same event, same people/companies, same timeframe, same core topic
3. Don't cluster if articles are just in the same category but about different events
4. IMPORTANT - DISCRETE EVENTS: Separate instances/episodes within a series are DIFFERENT stories → create_new
   Examples:
   - Different matches in a tournament (India vs Australia semi-final ≠ India vs South Africa final)
   - Different episodes in a TV series
   - Different hearings/sessions in a trial
   - Different debates in an election season
   - Different quarterly earnings reports from the same company
   Only cluster if covering the exact same specific instance/episode
5. IMPORTANT - TIME SENSITIVITY: Pay close attention to publication dates and age differences
   - Events >24 hours apart are usually different stories unless clearly ongoing (e.g., natural disaster, war coverage)
   - Consider natural event boundaries: matches end, hearings conclude, votes happen
   - Cluster only if articles cover the exact same event instance, not just the same topic
6. Assign the most appropriate subcategory from this list: {subcategories_str}
7. Generate 5-6 relevant tags that capture key entities, topics, or themes:
   - Full names of important people (e.g., "Jensen Huang", "Elon Musk", not just titles like "CEO")
   - Companies, organizations, or institutions
   - Specific products, technologies, or initiatives
   - Core topics or themes
   - Locations if relevant to the story
8. FOUR FACTOR SCORES (1–100, integer values)
   Score **relative to what's typical for the SAME feed_category** (and subcategory if applicable) to avoid cross-category bias. 
   Use these anchors:
   - Surprise Factor (1=very expected; 50=somewhat novel; 100=highly counterintuitive or unexpected pivot/angle)
     Consider divergence from common narratives or unexpected outcomes/coalitions/causes.
   - Prominence of Entities (1=unknown locals; 50=regionally notable; 100=globally famous heads of state, Tier-1 brands, top leagues)
     Consider real-world fame/importance, not social media hype alone.
   - Event Magnitude (1=minor/localized; 50=moderate/regional impact; 100=large-scale with national/global impact, major $$, casualties, or policy shifts)
   - Emotional Charge (1=low affect; 50=moderate sentiment/concern; 100=intense emotions such as fear/anger/joy with clear stakes)

   IMPORTANT FAIRNESS RULES:
   - Always judge *within-category*. Do NOT reward certain beats (e.g., celebrity or geopolitics) just because they commonly feature famous names or big numbers.
   - If any factor cannot be reasonably inferred, assign 50 (neutral) rather than guessing high/low.
   - Keep the final distribution reasonable: most routine updates should cluster near 40–60 unless the article truly merits extremes.

9. IMPORTANCE SCORE
   - Compute: importance_score = (surprise_score + prominence_score + magnitude_score + emotion_score) / 4.
   - Report the value as a float with 1 decimal place.
   - This final score should reflect the within-category-normalized interest.

EXAMPLES:
{examples}

Respond with JSON only:
{{
    "action": "join_existing" or "create_new",
    "cluster_id": "cluster_id_to_join" or null,
    "reason": "brief explanation",
    "subcategory": "choose from available options above",
    "tags": ["tag1", "tag2", "tag3"],
    "surprise_score": integer 1–100,
    "prominence_score": integer 1–100,
    "magnitude_score": integer 1–100,
    "emotion_score": integer 1–100,
    "importance_score": float between 1.0–100.0 (one decimal)
}}

NOTE: Do NOT include a "category" field - it will be automatically derived from your subcategory choice."""
        
        return prompt
    
    def _get_few_shot_examples(self, category: str) -> str:
        """Get few-shot examples based on category"""
        examples = {
            "Technology": """
Example 1 - CREATE NEW CLUSTER:
Article: "Apple Announces New MacBook Pro with M3 Chip"
Summary: "Apple unveiled its latest MacBook Pro featuring the new M3 processor with improved performance and battery life"
Similar Articles: None found
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "New product announcement, no similar stories found",

    "subcategory": "Gadgets & Consumer Tech",
    "tags": ["Apple", "MacBook Pro", "M3 chip", "product launch", "consumer tech"],
    "surprise_score": 35,
    "prominence_score": 95,
    "magnitude_score": 65,
    "emotion_score": 52,
    "importance_score": 61.8
}

Example 2 - JOIN EXISTING CLUSTER:
Article: "M3 MacBook Pro Shows 20% Performance Boost in Benchmarks"
Summary: "Early benchmark tests reveal significant performance improvements in the new M3-powered MacBook Pro"
Similar Articles: "Apple Announces New MacBook Pro with M3 Chip" (similarity: 0.89)
Decision:
{
    "action": "join_existing",
    "cluster_id": "tech-123-abc",
    "reason": "Same product launch story, just benchmark details",

    "subcategory": "Gadgets & Consumer Tech",
    "tags": ["Apple", "MacBook Pro", "M3 chip", "benchmarks", "performance", "laptop"],
    "surprise_score": 28,
    "prominence_score": 88,
    "magnitude_score": 54,
    "emotion_score": 43,
    "importance_score": 53.3
}

Example 3 - CREATE NEW (Different story):
Article: "Google Releases Gemini 2.0 AI Model"
Summary: "Google announced Gemini 2.0, its most advanced AI model with multimodal capabilities. CEO Sundar Pichai demonstrated the model's capabilities."
Similar Articles: "Apple Announces New MacBook Pro with M3 Chip" (similarity: 0.72)
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "Different company, different product category (AI vs hardware)",

    "subcategory": "AI & Machine Learning",
    "tags": ["Google", "Sundar Pichai", "Gemini", "AI model", "multimodal", "machine learning"],
    "surprise_score": 67,
    "prominence_score": 92,
    "magnitude_score": 76,
    "emotion_score": 61,
    "importance_score": 74.0
}""",

            "Sports": """
Example 1 - CREATE NEW CLUSTER:
Article: "Tiger Woods Wins Masters Tournament by 2 Strokes"
Summary: "Tiger Woods captured his sixth Masters title with a final round 68 at Augusta National"
Similar Articles: None found
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "Major tournament victory, standalone story",

    "subcategory": "Golf",
    "tags": ["Tiger Woods", "Masters Tournament", "Augusta National", "major championship", "golf"],
    "surprise_score": 78,
    "prominence_score": 100,
    "magnitude_score": 94,
    "emotion_score": 87,
    "importance_score": 89.8
}

Example 2 - JOIN EXISTING CLUSTER:
Article: "Woods' Masters Victory Breaks 5-Year Major Drought"
Summary: "Tiger Woods' Masters win ends his longest stretch without a major championship since turning pro"
Similar Articles: "Tiger Woods Wins Masters Tournament by 2 Strokes" (similarity: 0.92)
Decision:
{
    "action": "join_existing",
    "cluster_id": "sports-456-def",
    "reason": "Same tournament victory, additional context about drought",

    "subcategory": "Golf",
    "tags": ["Tiger Woods", "Masters Tournament", "major drought", "comeback"],
    "surprise_score": 62,
    "prominence_score": 100,
    "magnitude_score": 81,
    "emotion_score": 75,
    "importance_score": 79.5
}

Example 3 - CREATE NEW (Discrete event in same series):
Article: "India Beats South Africa to Win Women's World Cup Final"
Publication Date: 2025-11-02 14:30 UTC
Summary: "India clinched their first Women's T20 World Cup title with a 7-wicket victory over South Africa in Dubai"
Similar Articles: "India Beats Australia in World Cup Semi-Final Thriller" (similarity: 0.87, published 72 hours ago)
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "Different match within same tournament - semi-final vs final are discrete events with different opponents, outcomes, and significance. 72-hour gap confirms these are separate matches.",

    "subcategory": "Cricket",
    "tags": ["India", "South Africa", "Women's T20 World Cup", "final", "championship"],
    "surprise_score": 82,
    "prominence_score": 88,
    "magnitude_score": 95,
    "emotion_score": 91,
    "importance_score": 89.0
}""",

            "Business": """
Example 1 - CREATE NEW CLUSTER:
Article: "Tesla Reports Record Q3 Earnings Beat Expectations"
Summary: "Tesla posted quarterly revenue of $25.2B, beating analyst estimates by 8%"
Similar Articles: None found
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "Quarterly earnings report, standalone financial news",

    "subcategory": "Corporations & Earnings",
    "tags": ["Tesla", "Q3 earnings", "revenue beat", "financial results"],
    "surprise_score": 51,
    "prominence_score": 93,
    "magnitude_score": 74,
    "emotion_score": 62,
    "importance_score": 70.0
}

Example 2 - JOIN EXISTING CLUSTER:
Article: "Tesla Stock Surges 12% After Strong Earnings Report"
Summary: "Tesla shares jumped in after-hours trading following better-than-expected quarterly results"
Similar Articles: "Tesla Reports Record Q3 Earnings Beat Expectations" (similarity: 0.85)
Decision:
{
    "action": "join_existing",
    "cluster_id": "biz-789-ghi",
    "reason": "Market reaction to same earnings report",

    "subcategory": "Markets",
    "tags": ["Tesla", "stock surge", "earnings reaction", "market response"],
    "surprise_score": 39,
    "prominence_score": 87,
    "magnitude_score": 61,
    "emotion_score": 54,
    "importance_score": 60.3
}""",

            "Politics & Government": """
Example 1 - CREATE NEW CLUSTER:
Article: "Senate Passes Bipartisan Infrastructure Bill 69-30"
Summary: "The $1.2 trillion infrastructure package received broad bipartisan support in final Senate vote"
Similar Articles: None found
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "Major legislative passage, new policy story",

    "subcategory": "Policy & Legislation",
    "tags": ["infrastructure bill", "bipartisan", "Senate vote", "$1.2 trillion"],
    "surprise_score": 64,
    "prominence_score": 88,
    "magnitude_score": 91,
    "emotion_score": 53,
    "importance_score": 74.0
}

Example 2 - JOIN EXISTING CLUSTER:
Article: "House Expected to Vote on Infrastructure Bill Next Week"
Summary: "House leadership schedules vote on Senate-passed infrastructure package for Tuesday"
Similar Articles: "Senate Passes Bipartisan Infrastructure Bill 69-30" (similarity: 0.88)
Decision:
{
    "action": "join_existing",
    "cluster_id": "pol-321-jkl",
    "reason": "Same legislation, next step in legislative process",

    "subcategory": "Policy & Legislation",
    "tags": ["infrastructure bill", "House vote", "legislative process", "scheduling"],
    "surprise_score": 32,
    "prominence_score": 76,
    "magnitude_score": 79,
    "emotion_score": 44,
    "importance_score": 57.8
}"""
        }
        
        return examples.get(category, """
Example - CREATE NEW CLUSTER:
Article: "[Title of article about current topic]"
Summary: "[Brief summary of the article content]"
Similar Articles: None found or different topic
Decision:
{
    "action": "create_new",
    "cluster_id": null,
    "reason": "New story or different from existing articles",

    "subcategory": "[Appropriate subcategory]",
    "tags": ["key-entity", "main-topic", "relevant-theme"],
    "surprise_score": 50,
    "prominence_score": 50,
    "magnitude_score": 50,
    "emotion_score": 50,
    "importance_score": 50.0
}

Example - JOIN EXISTING CLUSTER:
Article: "[Related article title]"
Summary: "[Summary of related content]"
Similar Articles: "[Previous article title]" (similarity: 0.85+)
Decision:
{
    "action": "join_existing",
    "cluster_id": "cluster-id-123",
    "reason": "Same story/event, additional details or perspective",

    "subcategory": "[Appropriate subcategory]",
    "tags": ["shared-entities", "same-topic", "additional-context"],
    "surprise_score": 50,
    "prominence_score": 50,
    "magnitude_score": 50,
    "emotion_score": 50,
    "importance_score": 50.0
}""")
    
    def _parse_ai_decision(self, response: str, similar_articles: List[Dict]) -> Dict[str, Any]:
        """Parse AI response into clustering decision"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            decision = json.loads(response)
            
            # Validate decision
            if decision['action'] not in ['join_existing', 'create_new']:
                raise ValueError("Invalid action")
            
            if decision['action'] == 'join_existing' and not decision.get('cluster_id'):
                # Find the most similar cluster
                if similar_articles:
                    decision['cluster_id'] = similar_articles[0]['cluster_id']
                else:
                    decision['action'] = 'create_new'

            # Automatically derive category from subcategory
            subcategory = decision.get('subcategory')
            if subcategory:
                from agent.rss_config import RSS_FEEDS_CONFIG
                category_found = None

                # Search for which category contains this subcategory
                for cat_name, cat_data in RSS_FEEDS_CONFIG.items():
                    if subcategory in cat_data.get('subcategories', []):
                        category_found = cat_name
                        break

                if category_found:
                    decision['category'] = category_found
                    logger.info(f"Mapped subcategory '{subcategory}' → category '{category_found}'")
                else:
                    # Subcategory not found in any category - log warning and default to General
                    logger.warning(f"Subcategory '{subcategory}' not found in RSS_FEEDS_CONFIG. Defaulting to 'General'")
                    decision['category'] = 'General'
            else:
                # No subcategory provided - default both
                logger.warning("No subcategory in AI response. Defaulting to General/None")
                decision['category'] = 'General'
                decision['subcategory'] = None

            # Parse importance_score if it's a string
            if 'importance_score' in decision:
                importance_str = str(decision['importance_score'])
                # Extract first digit if it's a string like "8 (high importance)"
                import re
                match = re.search(r'(\d+)', importance_str)
                if match:
                    decision['importance_score'] = int(match.group(1))
                else:
                    decision['importance_score'] = 50  # Default

            return decision
            
        except Exception as e:
            logger.warning(f"Failed to parse AI decision: {str(e)}")
            return {
                'action': 'create_new',
                'reason': 'Failed to parse AI response',
                'category': 'General',
                'subcategory': None,
                'tags': []
            }
    
    def _categorize_article(self, article_data: Dict[str, Any]) -> str:
        """Simple categorization fallback"""
        title_lower = article_data['title'].lower()
        
        if any(word in title_lower for word in ['tech', 'ai', 'apple', 'google', 'microsoft']):
            return 'Technology'
        elif any(word in title_lower for word in ['election', 'president', 'congress', 'politics']):
            return 'Politics'
        elif any(word in title_lower for word in ['stock', 'market', 'economy', 'business']):
            return 'Business'
        elif any(word in title_lower for word in ['health', 'medical', 'covid', 'vaccine']):
            return 'Health'
        else:
            return 'General'
    
    def _create_new_cluster(self, article_data: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Create a new story cluster"""
        cluster_id = str(uuid.uuid4())
        canonical_title = article_data['title']  # Use article title as canonical
        
        try:
            # TODO: Replace with actual model insertion
            # new_cluster = StoryCluster(
            #     cluster_id=cluster_id,
            #     canonical_title=canonical_title,
            #     created_at=datetime.now(timezone.utc)
            # )
            # self.db.add(new_cluster)
            
            # Placeholder implementation
            importance_score = decision.get('importance_score', 50)  # Default to 50 if not provided
            self.db.execute(
                text("""
                    INSERT INTO story_clusters (cluster_id, canonical_title, importance_score, created_at)
                    VALUES (:cluster_id, :canonical_title, :importance_score, :created_at)
                """),
                {
                    "cluster_id": cluster_id,
                    "canonical_title": canonical_title,
                    "importance_score": importance_score,
                    "created_at": datetime.now(timezone.utc)
                }
            )
            
            logger.info(f"Created new story cluster: {cluster_id} - {canonical_title}")
            return cluster_id
            
        except Exception as e:
            logger.error(f"Failed to create new cluster: {str(e)}")
            raise
    
    def _save_article(self, article_data: Dict[str, Any], uniqueness_hash: str, 
                     embedding: np.ndarray, cluster_id: str, decision: Dict[str, Any]) -> str:
        """Save article to database"""
        article_id = str(uuid.uuid4())
        
        try:
            # Convert embedding to list for JSON storage
            embedding_list = embedding.tolist()
            
            # TODO: Replace with actual model insertion
            # new_article = Article(
            #     article_id=article_id,
            #     cluster_id=cluster_id,
            #     url=article_data['url'],
            #     uniqueness_hash=uniqueness_hash,
            #     source_name=article_data['source_name'],
            #     title=article_data['title'],
            #     summary=article_data.get('summary'),
            #     publication_timestamp=article_data.get('published_date'),
            #     category=decision.get('category'),
            #     subcategory=decision.get('subcategory'),
            #     tags=json.dumps(decision.get('tags', [])),
            #     embedding=embedding_list
            # )
            # self.db.add(new_article)
            
            # Placeholder implementation
            self.db.execute(
                text("""
                    INSERT INTO articles (
                        article_id, cluster_id, url, uniqueness_hash, source_name,
                        title, summary, publication_timestamp, category, subcategory,
                        tags, embedding, created_at
                    ) VALUES (
                        :article_id, :cluster_id, :url, :uniqueness_hash, :source_name,
                        :title, :summary, :publication_timestamp, :category, :subcategory,
                        :tags, CAST(:embedding AS vector), :created_at
                    )
                """),
                {
                    "article_id": article_id,
                    "cluster_id": cluster_id,
                    "url": article_data['url'],
                    "uniqueness_hash": uniqueness_hash,
                    "source_name": article_data['source_name'],
                    "title": article_data['title'],
                    "summary": article_data.get('summary'),
                    "publication_timestamp": article_data.get('published_date'),
                    "category": decision.get('category'),
                    "subcategory": decision.get('subcategory'),
                    "tags": json.dumps(decision.get('tags', [])),
                    "embedding": json.dumps(embedding_list),
                    "created_at": datetime.now(timezone.utc)
                }
            )
            
            self.db.commit()
            logger.info(f"Saved article: {article_id}")
            return article_id
            
        except Exception as e:
            # Check if this is a duplicate key error (race condition)
            error_str = str(e).lower()
            if 'unique constraint' in error_str and ('url' in error_str or 'uniqueness_hash' in error_str):
                logger.info(f"Article already exists (race condition): {article_data['title']}")
                self.db.rollback()
                return None  # Return None to indicate duplicate, not failure
            else:
                logger.error(f"Failed to save article: {str(e)}")
                self.db.rollback()
                raise
