import logging
import uuid
from typing import List, Dict, Any
from agent.services.smart_article_service import SmartArticleService
from agent.services.article_content_service import ArticleContentService
from agent.services.llm_service import LLMService
from agent.services.tts_service import TTSService
from agent.services.transcript_service import TranscriptService
from agent.services.storage_service import StorageService
from agent.services.episode_service import EpisodeService
from agent.adk_agents import create_podcast_generation_workflow

logger = logging.getLogger(__name__)

class PodcastGenerator:
    def __init__(self, episode_service: EpisodeService):
        self.episode_service = episode_service
        self.smart_article_service = SmartArticleService()
        self.article_content_service = ArticleContentService()
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.transcript_service = TranscriptService()
        self.storage_service = StorageService()

        # Initialize ADK multi-agent workflow
        self.adk_workflow = create_podcast_generation_workflow(self.llm_service)
        logger.info("🤖 Initialized with Google ADK multi-agent workflow")
    
    async def generate_episode(self, episode_id: str, subcategories: List[str], duration_minutes: int, custom_tags: List[str] = None):
        """Execute the full podcast generation pipeline"""
        try:
            # Get episode details including user_id for storage organization
            episode = self.episode_service.get_episode(episode_id)
            user_id = episode.user_id if episode and hasattr(episode, 'user_id') else None
            logger.info(f"Generating episode {episode_id} for user: {user_id or 'anonymous'}")

            # Stage 1: Discover articles
            self.episode_service.set_episode_status(
                episode_id, "discovering_articles", stage="discovering_articles", progress=10
            )
            # Use smart article service to get articles from our clustered database
            # Get articles filtered purely by the user's selected subcategories
            # Automatically excludes clusters the user has already heard
            articles = self.smart_article_service.get_articles_by_subcategories(
                selected_subcategories=subcategories,
                user_id=user_id,  # Filter out already-heard clusters
                total_articles=8,  # More articles for better content variety
                min_importance_score=40,  # Minimum quality threshold
                custom_tags=custom_tags or []  # Optional custom tags for targeted article selection
            )
            logger.info(f"Found {len(articles)} articles for episode {episode_id}")

            # Check if we found any articles
            if len(articles) == 0:
                error_msg = "No new articles available for your selected topics. You've already heard all recent content! Try selecting different topics or check back tomorrow for fresh articles."
                logger.warning(f"Episode {episode_id}: {error_msg}")
                raise Exception(error_msg)

            # Stage 2: Fetch full article content and convert to sources format
            self.episode_service.set_episode_status(
                episode_id, "extracting_content", stage="extracting_content", progress=20
            )
            sources = self._convert_articles_to_sources(articles, fetch_full_content=True)
            article_to_source_map = self.episode_service.store_sources(episode_id, sources)
            
            # Stage 3: Generate script using ADK multi-agent workflow
            self.episode_service.set_episode_status(
                episode_id, "generating_script", stage="generating_script", progress=40
            )
            # Get user name for personalization
            user_name = episode.name if episode and hasattr(episode, 'name') else None

            # Use ADK workflow which coordinates 4 specialized agents
            logger.info("🤖 Invoking ADK multi-agent workflow for podcast generation...")
            podcast_result = await self.adk_workflow.generate_podcast(sources, duration_minutes, user_name)
            script = podcast_result["script"]
            # ADK workflow also generates title and description
            adk_title = podcast_result["title"]
            adk_description = podcast_result["description"]
            
            # Stage 4: Convert to audio
            self.episode_service.set_episode_status(
                episode_id, "generating_audio", stage="generating_audio", progress=60
            )
            audio_chunks, chunk_timestamps = self.tts_service.generate_audio_chunks(script.paragraphs)
            combined_audio_path = self.tts_service.combine_audio_chunks(audio_chunks)
            
            # Stage 5: Generate timestamps and WebVTT
            self.episode_service.set_episode_status(
                episode_id, "generating_timestamps", stage="generating_timestamps", progress=80
            )
            transcript_data = self.transcript_service.generate_forced_alignment(
                combined_audio_path, script, chunk_timestamps
            )
            vtt_content = self.transcript_service.generate_webvtt(transcript_data)
            
            # Stage 6: Upload files
            self.episode_service.set_episode_status(
                episode_id, "uploading_files", stage="uploading_files", progress=90
            )
            audio_url = self.storage_service.upload_audio(episode_id, combined_audio_path, user_id=user_id)
            transcript_url = self.storage_service.upload_transcript(episode_id, transcript_data)
            vtt_url = self.storage_service.upload_vtt(episode_id, vtt_content)
            
            # Stage 7: Update episode with final data
            self.episode_service.set_episode_status(
                episode_id, "finalizing", stage="finalizing", progress=95
            )

            # Use title and description from ADK workflow (already generated by Metadata Agent)
            title = adk_title
            description = adk_description
            logger.info(f"Using ADK-generated title: {title}")
            
            # Update episode in database
            self.episode_service.update_episode(
                episode_id=episode_id,
                title=title,
                description=description,
                duration_seconds=int(transcript_data[-1]["end"]),
                audio_url=audio_url,
                transcript_url=transcript_url,
                vtt_url=vtt_url,
                status="completed"
            )
            
            # Store episode segments for chapter navigation
            self.episode_service.store_episode_segments(episode_id, transcript_data, article_to_source_map)
            
            # Final status update
            self.episode_service.set_episode_status(
                episode_id, "completed", stage="completed", progress=100
            )
            
            logger.info(f"Successfully generated podcast episode {episode_id}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for episode {episode_id}: {str(e)}")
            self.episode_service.set_episode_status(
                episode_id, "failed", error=str(e)
            )
            raise
    
    def _convert_articles_to_sources(self, articles: List[Dict[str, Any]], fetch_full_content: bool = False) -> List[Dict[str, Any]]:
        """
        Convert smart article service format to sources format expected by LLM service
        With cluster fallback: if article content fetch fails, try other articles from same cluster

        Args:
            articles: List of articles from smart_article_service
            fetch_full_content: If True, fetch full article content from URLs with cluster fallback
        """
        sources = []

        for article in articles:
            url = article.get("url", "")
            cluster_id = article.get("cluster_id", "")
            article_id = article.get("article_id", "")
            full_text = None

            # Try to fetch full content with cluster fallback
            if fetch_full_content and url:
                logger.info(f"Fetching article content from: {article.get('title', 'Unknown')[:60]}...")
                full_text = self.article_content_service.fetch_article_content(url)

                # If failed and we have a cluster, try backups from same cluster
                if not full_text and cluster_id:
                    logger.warning(f"Failed to fetch {article.get('source_name', 'Unknown')}, trying backups from cluster {cluster_id}")
                    backups = self.smart_article_service.get_cluster_backups(
                        cluster_id=cluster_id,
                        exclude_article_ids=[article_id],
                        limit=3
                    )

                    # Try each backup article
                    for i, backup in enumerate(backups, 1):
                        backup_url = backup.get("url", "")
                        if backup_url:
                            logger.info(f"  Trying backup {i}/{len(backups)}: {backup.get('source_name', 'Unknown')}")
                            full_text = self.article_content_service.fetch_article_content(backup_url)
                            if full_text:
                                # Use the backup article instead
                                logger.info(f"  ✓ Success! Using {backup.get('source_name', 'Unknown')} instead")
                                article = backup  # Replace with backup article
                                url = backup_url
                                break

                    if not full_text:
                        logger.warning(f"  All {len(backups)} backups failed for cluster {cluster_id}, using RSS summary")

            # Determine what to use as full_text
            if full_text:
                logger.info(f"Using fetched content ({len(full_text)} chars) for: {article.get('title', 'Unknown')[:50]}")
            else:
                # Fallback to RSS summary
                full_text = article.get("summary", "")
                if fetch_full_content:
                    logger.warning(f"Using RSS summary for: {article.get('title', 'Unknown')[:50]}")

            # Create source in the format expected by LLM service
            source = {
                "id": article.get("article_id", str(uuid.uuid4())),
                "title": article.get("title", ""),
                "url": url,
                "published_date": article.get("publication_timestamp", ""),
                "excerpt": article.get("summary", "")[:200] + "..." if len(article.get("summary", "")) > 200 else article.get("summary", ""),
                "full_text": full_text,  # Full article content or RSS summary
                "source_name": article.get("source_name", "Unknown"),
                "summary": article.get("summary", ""),  # Keep original RSS summary
                # Additional metadata from our smart system
                "category": article.get("category", ""),
                "subcategory": article.get("subcategory", ""),
                "importance_score": article.get("importance_score", 50),
                "story_title": article.get("story_title", ""),
                "cluster_id": article.get("cluster_id", ""),
                "tags": article.get("tags", [])
            }
            sources.append(source)

        logger.info(f"Converted {len(sources)} articles to sources format")
        return sources
