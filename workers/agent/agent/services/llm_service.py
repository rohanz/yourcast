import logging
import os
from google import genai
from typing import List, Dict, Any
from dataclasses import dataclass
from agent.config import settings, config

logger = logging.getLogger(__name__)

@dataclass
class PodcastScript:
    paragraphs: List[Dict[str, Any]]
    estimated_duration: int
    topics: List[Dict[str, Any]]  # List of topics with their metadata

class LLMService:
    # World News subcategories that should be grouped together
    WORLD_NEWS_SUBCATEGORIES = {
        "Africa", "Asia", "Europe", "Middle East",
        "North America", "South America", "Oceania"
    }

    def __init__(self):
        # Initialize Google Gen AI SDK with Vertex AI backend
        project = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")

        # Use new Google Gen AI SDK with Vertex AI backend
        self.client = genai.Client(
            vertexai=True,  # Use Vertex AI (not AI Studio)
            project=project,
            location=location
        )
        self.model_name = 'gemini-2.0-flash-lite'

    def _normalize_topic_name(self, subcategory: str) -> str:
        """Map world news subcategories to 'World News', keep others as-is"""
        if subcategory in self.WORLD_NEWS_SUBCATEGORIES:
            return "World News"
        return subcategory

    def generate_podcast_script(self, sources: List[Dict[str, Any]], duration_minutes: int, user_name: str = None) -> PodcastScript:
        """Generate a podcast script from news sources, organized by topic"""
        target_words = duration_minutes * config.llm_words_per_minute  # Configurable WPM target

        # Group sources by subcategory (topic), mapping world news subcategories to "World News"
        topics_map = {}
        for source in sources:
            subcategory = source.get("subcategory", "General News")
            topic_name = self._normalize_topic_name(subcategory)
            if topic_name not in topics_map:
                topics_map[topic_name] = []
            topics_map[topic_name].append(source)

        logger.info(f"Grouped {len(sources)} sources into {len(topics_map)} topics: {list(topics_map.keys())}")

        # Prepare summaries grouped by topic
        topics_data = []
        for topic_name, topic_sources in topics_map.items():
            summaries = []
            for source in topic_sources:
                full_text = source.get("full_text", "")

                # Only summarize if we have substantial content (more than just RSS summary)
                if full_text and len(full_text) > 500:
                    # We have full article text - summarize it for title/description only
                    try:
                        summary = self._summarize_article(full_text, source["title"])
                        summaries.append({
                            "source_id": source["id"],
                            "title": source["title"],
                            "summary": summary,  # Used for title/description
                            "full_text": full_text,  # Used for script generation
                            "url": source["url"],
                            "source_name": source.get("source_name", "Unknown")
                        })
                    except Exception as e:
                        logger.warning(f"Failed to summarize article {source['title']}: {str(e)}")
                        # Fallback to RSS summary
                        summaries.append({
                            "source_id": source["id"],
                            "title": source["title"],
                            "summary": source.get("summary", ""),
                            "full_text": full_text,  # Still use full text for script
                            "url": source["url"],
                            "source_name": source.get("source_name", "Unknown")
                        })
                else:
                    # Short content or just RSS summary - use it directly
                    summaries.append({
                        "source_id": source["id"],
                        "title": source["title"],
                        "summary": source.get("summary", full_text),
                        "full_text": full_text or source.get("summary", ""),  # Use whatever we have
                        "url": source["url"],
                        "source_name": source.get("source_name", "Unknown")
                    })

            topics_data.append({
                "topic_name": topic_name,
                "summaries": summaries
            })

        # Calculate words per topic
        words_per_topic = target_words // len(topics_data) if topics_data else target_words

        # Generate script for each topic separately
        all_paragraphs = []
        topics_metadata = []

        # Generate dynamic intro (not using user_name for now)
        intro_text = self._generate_intro(None, list(topics_map.keys()))
        intro_paragraph = {
            "text": intro_text,
            "source_ids": [],
            "topic": "Introduction"
        }
        all_paragraphs.append(intro_paragraph)

        for topic_data in topics_data:
            topic_name = topic_data["topic_name"]
            summaries = topic_data["summaries"]

            logger.info(f"Generating script for topic: {topic_name}")

            # Generate focused script for this topic
            script_text = self._generate_topic_script(topic_name, summaries, words_per_topic)

            # Keep topic script as single block (don't split into paragraphs)
            # Collect all source IDs for this topic
            topic_source_ids = [s["source_id"] for s in summaries]

            # Add as single "paragraph" entry (actually full topic block)
            topic_paragraph = {
                "text": script_text,
                "source_ids": topic_source_ids,
                "topic": topic_name
            }
            all_paragraphs.append(topic_paragraph)

            # Track topic metadata
            topics_metadata.append({
                "topic_name": topic_name,
                "start_paragraph_index": len(all_paragraphs) - 1,
                "end_paragraph_index": len(all_paragraphs) - 1,
                "source_ids": topic_source_ids
            })

        # Generate outro
        outro_text = self._generate_outro()
        outro_paragraph = {
            "text": outro_text,
            "source_ids": [],
            "topic": "Outro"
        }
        all_paragraphs.append(outro_paragraph)

        return PodcastScript(
            paragraphs=all_paragraphs,
            estimated_duration=duration_minutes * 60,  # Convert to seconds
            topics=topics_metadata
        )
    
    def _generate_intro(self, user_name: str = None, topics: List[str] = None) -> str:
        """Generate a dynamic, engaging intro with user's name and topics"""
        topics_text = ", ".join(topics) if topics else "today's top stories"

        # If no user name, generate a generic but varied intro
        if not user_name:
            prompt = f"""
            Generate a brief podcast intro (1-2 sentences max) for "Your Cast" - a personalized news podcast.

            Today's topics: {topics_text}

            Requirements:
            - Create a VARIATION on the theme "Welcome to Your Cast, your world update without the noise"
            - Be welcoming and conversational, not over-the-top
            - Keep it under 20 words

            Return ONLY the intro text, nothing else.
            """
        else:
            prompt = f"""
            Generate a brief podcast intro (1-2 sentences max) for "Your Cast" - a personalized news podcast.

            User's name: {user_name}
            Today's topics: {topics_text}

            Requirements:
            - Greet the user by name naturally (e.g., "Hey {user_name}!" or "{user_name}, welcome back!")
            - Create a VARIATION on the theme "Welcome to Your Cast, your world update without the noise"
            - Be welcoming and conversational, not over-the-top
            - Keep it under 25 words

            Return ONLY the intro text, nothing else.
            """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            intro = response.text.strip().strip('"')
            logger.info(f"Generated intro: {intro}")
            return intro
        except Exception as e:
            logger.error(f"Failed to generate intro: {e}")
            # Fallback to static intro
            if user_name:
                return f"Hey {user_name}! Welcome to Your Cast, your world update without the noise."
            return "Welcome to Your Cast, your world update without the noise."

    def _generate_outro(self) -> str:
        """Generate a brief, varied outro"""
        prompt = """
        Generate a brief podcast outro (1 sentence max) for "Your Cast" - a personalized news podcast.

        Requirements:
        - Create a VARIATION on thanking the listener and signing off
        - Be warm and conversational, not over-the-top
        - Keep it under 15 words
        - Examples: "That's your world update. Thanks for listening to Your Cast.", "And that's the news. Stay informed, stay curious."

        Return ONLY the outro text, nothing else.
        """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            outro = response.text.strip().strip('"')
            logger.info(f"Generated outro: {outro}")
            return outro
        except Exception as e:
            logger.error(f"Failed to generate outro: {e}")
            # Fallback to static outro
            return "That's your world update. Thanks for listening to Your Cast."

    def _summarize_article(self, full_text: str, title: str) -> str:
        """Summarize a single article"""
        prompt = f"""
        Please provide a concise summary of this news article in 4-6 bullet points. Focus on the key facts and developments, naming any key entities.

        IMPORTANT GROUNDING RULE:
        - Use ONLY information from the article text below
        - DO NOT add context from your general knowledge
        - DO NOT change titles, roles, or positions based on what you think you know
        - Stick to the facts as stated in the article

        Title: {title}

        Article:
        {full_text[:2000]}  # Truncate to fit context

        Summary (as bullet points):
        """
        
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to summarize article with Gemini: {str(e)}")
            # Fallback summary
            return f"• {title}\n• Key developments in this story\n• Further details available"
    
    def _generate_topic_script(self, topic_name: str, summaries: List[Dict], target_words: int) -> str:
        """Generate script for a single topic section"""
        sources_text = "\n\n".join([
            f"Source {i+1} - {s['title']} ({s['source_name']}):\n{s['full_text'][:5000]}\nURL: {s['url']}"
            for i, s in enumerate(summaries)
        ])

        prompt = f"""
        SYSTEM ROLE: You are a professional podcast scriptwriter. Your output will be read DIRECTLY by text-to-speech software, so you must write in PLAIN TEXT ONLY - absolutely no formatting, no asterisks, no special characters.

        TASK: Write a brief news segment for a podcast about {topic_name}.

        CRITICAL GROUNDING RULE - READ THIS CAREFULLY:
        - Use ONLY information explicitly stated in the provided news sources below
        - DO NOT use your general knowledge or training data to fill in details
        - DO NOT make assumptions about people's current roles, titles, or positions
        - If a source says "President Donald Trump", use that exact phrasing - don't change it to "former President" or any other variation based on what you think you know
        - If information is not in the sources, DO NOT include it
        - When in doubt, stick to exactly what the article says, word for word

        CRITICAL CONSTRAINT: Your response MUST be under {target_words} words total. This is NON-NEGOTIABLE.

        FORMATTING RULES (MUST FOLLOW):
        - Write in plain text ONLY - imagine you are speaking directly to a listener
        - NO asterisks (*), stars, or markdown formatting like **bold** or *italic*
        - NO special characters, markup, or symbols
        - NO transition words between stories like "finally", "first up", "moving on", "in addition", "moreover"
        - START with a brief natural intro to the topic (e.g., "In tech news...", "Turning to sports...", "On the political front...")
        - NO formal welcomes or goodbyes

        GOOD EXAMPLE (correct format):
        "In business news, the S&P 500 closed at a record high on Friday, gaining 2.3 percent following strong earnings reports. According to Reuters, tech stocks led the rally with Apple and Microsoft both up over 4 percent. Jane Smith, chief economist at Goldman Sachs, noted that consumer spending remains robust despite inflation concerns."

        BAD EXAMPLE (avoid this - has asterisks and transition words):
        "**Finally**, let's talk about the markets. The S&P 500..."

        CONTENT GUIDELINES:
        1. Assume the listener knows nothing - provide context about who people are and what's happening
        2. Cover only the most important highlights from the sources
        3. Use direct quotes from people in the articles to add credibility
        4. Cite sources naturally (e.g., "According to Reuters...", "As reported by BBC...")
        5. Include specific dates when discussing events if it adds context (e.g., "On October 30th...", "November 2nd...") - avoid relative dates like "Tuesday" or "last week"
        6. Be {config.llm_target_style}
        7. Flow as a single narrative voice
        8. Report news objectively - no warnings or personal opinions

        News Sources about {topic_name}:
        {sources_text}
        """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate script for topic {topic_name}: {str(e)}")
            raise
    
    def _parse_script_paragraphs(self, script_text: str, summaries: List[Dict], topic_name: str) -> List[Dict[str, Any]]:
        """Parse script into paragraphs with source attribution and topic metadata"""
        paragraphs = []
        script_paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]

        for paragraph_text in script_paragraphs:
            # Try to identify which sources are referenced in this paragraph
            source_ids = []

            for summary in summaries:
                # Simple heuristic: if title keywords or source name mentioned
                title_words = summary["title"].lower().split()[:3]  # First 3 words of title

                if any(word in paragraph_text.lower() for word in title_words if len(word) > 3):
                    source_ids.append(summary["source_id"])

            paragraphs.append({
                "text": paragraph_text,
                "source_ids": source_ids,
                "topic": topic_name
            })

        return paragraphs
    
    def generate_title(self, sources: List[Dict]) -> str:
        """Generate an engaging title for the episode using top-scoring articles"""
        # Get top 3 articles by importance score
        sorted_sources = sorted(sources, key=lambda s: s.get("importance_score", 0), reverse=True)
        top_articles = [s["title"] for s in sorted_sources[:3]]
        top_articles_text = "\n".join([f"- {title}" for title in top_articles])

        prompt = f"""
        Generate a compelling podcast episode title based on these top stories.

        Top 3 stories:
        {top_articles_text}

        The title should be:
        - Engaging and clickable
        - Under 60 characters
        - Reflective of the main stories covered
        - Professional but accessible

        Return just the title, no quotes or extra text.
        """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip().strip('"')
        except Exception as e:
            logger.error(f"Failed to generate title with Gemini: {str(e)}")
            # Fallback title using first article
            return top_articles[0][:60] if top_articles else "Daily News Update"
    
    def generate_description(self, sources: List[Dict], script: PodcastScript) -> str:
        """Generate episode description using all selected articles"""
        # Sort by importance_score to list most important stories first
        sorted_sources = sorted(sources, key=lambda s: s.get("importance_score", 0), reverse=True)

        # Create a concise prompt for the LLM
        source_summaries = []
        for source in sorted_sources[:8]:  # Top 8 stories
            source_summaries.append(f"- {source['title']}")

        prompt = f"""Generate a concise, engaging 1-2 sentence description for a news podcast episode covering these stories:

{chr(10).join(source_summaries)}

The description should:
- Be natural and conversational (not a list)
- Highlight the main themes or most interesting stories
- Be brief (under 200 characters if possible)
- Not use phrases like "this episode covers" or "we discuss"

Just write the description directly, no preamble."""

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            description = response.text.strip()
            logger.info(f"Generated description: {description}")
            return description
        except Exception as e:
            logger.error(f"Failed to generate description: {str(e)}")
            # Fallback to simple format
            top_3_titles = [s["title"] for s in sorted_sources[:3]]
            return f"Today's news: {', '.join(top_3_titles)}, and more."
    
    def generate_text(self, prompt: str) -> str:
        """Generate text response for clustering and categorization tasks"""
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate text with Gemini: {str(e)}")
            raise
