"""
Google ADK Proper Multi-Agent Implementation for YourCast Podcast Generation.

Uses the real Google Agent Development Kit (ADK) SDK with LlmAgent and SequentialAgent.

Agent 1 (MetadataAgent):
  → Analyzes all sources
  → Decides: theme, tone
  → Generates: title
  → Saves to session.state via output_key

Agent 2 (SummarizerAgent):
  → Reads: theme, tone from {metadata}
  → Generates: description matching theme/tone

Agent 3 (FramingAgent):
  → Reads: theme, tone from {metadata}
  → Generates: intro & outro matching theme/tone

Agent 4 (ScriptWriterAgent):
  → Reads: theme, tone from {metadata}, intro from {framing}
  → Generates: all topic scripts matching theme/tone/intro
"""

import logging
import json
from typing import List, Dict, Any, AsyncGenerator
from google.adk.agents import LlmAgent, SequentialAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from agent.services.llm_service import PodcastScript
from agent.config import config

logger = logging.getLogger(__name__)


class SourceAccessAgent(BaseAgent):
    """Base agent that provides access to sources data and Gen AI client."""

    # Allow extra fields (Pydantic config)
    model_config = {"extra": "allow"}

    def __init__(self, name: str, sources: List[Dict[str, Any]], duration_minutes: int, genai_client, model_name: str, user_name: str = None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.sources = sources
        self.duration_minutes = duration_minutes
        self.genai_client = genai_client  # Google Gen AI Client
        self.model_name = model_name  # Model name (e.g., 'gemini-2.0-flash-lite')
        self.user_name = user_name


class MetadataAgent(SourceAccessAgent):
    """Agent 1: Analyzes sources and generates title, theme, tone."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info("📊 MetadataAgent: Analyzing sources and setting strategy...")

        # Get top 3 articles by importance score
        sorted_sources = sorted(self.sources, key=lambda s: s.get("importance_score", 0), reverse=True)
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
- Plain text only - NO asterisks (*), NO markdown, NO special characters

Also briefly identify the TONE (in 1-2 words):
- TONE: What tone fits this mix of news? (e.g., "Informative", "Upbeat", "Serious")

Return ONLY valid JSON:
{{
    "title": "Your Title Here",
    "tone": "Brief Tone"
}}"""

        # Use Gen AI client to generate metadata
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        # Parse JSON response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        metadata = json.loads(response_text)

        # Save to session state
        ctx.session.state["metadata"] = metadata

        logger.info(f"   ✓ Tone: {metadata.get('tone', 'N/A')}")
        logger.info(f"   ✓ Title: {metadata.get('title', 'N/A')}")

        yield Event(
            author=self.name,
            actions=EventActions()
        )


class SummarizerAgent(SourceAccessAgent):
    """Agent 2: Generates description using metadata from Agent 1."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info("📝 SummarizerAgent: Generating description...")

        # Get top 8 stories for description
        sorted_sources = sorted(self.sources, key=lambda s: s.get('importance_score', 0), reverse=True)
        source_summaries = []
        for source in sorted_sources[:8]:
            source_summaries.append(f"- {source['title']}")

        prompt = f"""Generate a concise, engaging 1-2 sentence description for a news podcast episode covering these stories:

{chr(10).join(source_summaries)}

The description should:
- Be natural and conversational (not a list)
- Highlight the main themes or most interesting stories
- Be brief (under 200 characters if possible)
- Not use phrases like "this episode covers" or "we discuss"
- Plain text only - NO asterisks (*), NO markdown, NO special characters

Just write the description directly, no preamble."""

        # Use Gen AI client
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        description = response.text.strip()
        ctx.session.state["description"] = description

        logger.info(f"   ✓ Description: {description[:60]}...")

        yield Event(
            author=self.name,
            actions=EventActions()
        )


class FramingAgent(SourceAccessAgent):
    """Agent 3: Generates intro and outro using metadata from Agent 1."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info("🎬 FramingAgent: Generating intro/outro...")

        # Get metadata from session state
        metadata = ctx.session.state.get("metadata", {})
        tone = metadata.get("tone", "informative")

        # Generate intro
        if not self.user_name:
            intro_prompt = f"""
Generate a brief podcast intro (1-2 sentences max) for "Your Cast" - a personalized news podcast.

Requirements:
- Create a VARIATION on the theme "Welcome to Your Cast, your world update without the noise"
- Be welcoming and conversational, not over-the-top
- Use a {tone} tone
- Keep it under 20 words
- Plain text only - NO asterisks (*), NO markdown, NO special characters

Return ONLY the intro text, nothing else.
"""
        else:
            intro_prompt = f"""
Generate a brief podcast intro (1-2 sentences max) for "Your Cast" - a personalized news podcast.

User's name: {self.user_name}

Requirements:
- Greet the user by name naturally (e.g., "Hey {self.user_name}!" or "{self.user_name}, welcome back!")
- Create a VARIATION on the theme "Welcome to Your Cast, your world update without the noise"
- Be welcoming and conversational, not over-the-top
- Use a {tone} tone
- Keep it under 25 words
- Plain text only - NO asterisks (*), NO markdown, NO special characters

Return ONLY the intro text, nothing else.
"""

        # Generate outro
        outro_prompt = f"""
Generate a brief podcast outro (1 sentence max) for "Your Cast" - a personalized news podcast.

Requirements:
- Create a VARIATION on thanking the listener and signing off
- Be warm and conversational, not over-the-top
- Use a {tone} tone
- Keep it under 15 words
- Plain text only - NO asterisks (*), NO markdown, NO special characters
- Examples: "That's your world update. Thanks for listening to Your Cast.", "And that's the news. Stay informed, stay curious."

Return ONLY the outro text, nothing else.
"""

        # Use Gen AI client
        intro_response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=intro_prompt
        )
        intro = intro_response.text.strip()

        outro_response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=outro_prompt
        )
        outro = outro_response.text.strip()

        # Save to session state
        ctx.session.state["framing"] = {"intro": intro, "outro": outro}

        logger.info(f"   ✓ Intro generated")
        logger.info(f"   ✓ Outro generated")

        yield Event(
            author=self.name,
            actions=EventActions()
        )


class TopicScriptAgent(BaseAgent):
    """Generates script for a single topic (used in parallel)."""

    # Allow extra fields (Pydantic config)
    model_config = {"extra": "allow"}

    def __init__(self, name: str, topic_name: str, summaries: List[Dict[str, Any]],
                 tone: str, words_per_topic: int, genai_client, model_name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.topic_name = topic_name
        self.summaries = summaries
        self.tone = tone
        self.words_per_topic = words_per_topic
        self.genai_client = genai_client
        self.model_name = model_name

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"   🔸 TopicScriptAgent[{self.topic_name}]: Generating script...")

        sources_text = "\n\n".join([
            f"Source {i+1} - {s.get('title', 'N/A')} ({s.get('source_name', 'Unknown')}):\n{s.get('full_text', s.get('summary', 'N/A'))[:5000]}\nURL: {s.get('url', 'N/A')}"
            for i, s in enumerate(self.summaries)
        ])

        prompt = f"""
SYSTEM ROLE: You are the Script Writer Agent in a podcast generation system. Your output will be read DIRECTLY by text-to-speech software.

CONTEXT FROM OTHER AGENTS:
- Tone to Match: {self.tone}

TASK: Write ONE cohesive paragraph covering all the {self.topic_name} news below.

CRITICAL GROUNDING RULE - READ THIS CAREFULLY:
- Use ONLY information explicitly stated in the provided news sources below
- DO NOT use your general knowledge or training data to fill in details
- DO NOT make assumptions about people's current roles, titles, or positions
- If a source says "President Donald Trump", use that exact phrasing - don't change it to "former President" or any other variation based on what you think you know
- If information is not in the sources, DO NOT include it
- When in doubt, stick to exactly what the article says, word for word

CRITICAL CONSTRAINT: Target {self.words_per_topic} words total.
- MINIMUM: {int(self.words_per_topic * 0.85)} words (85% of target - don't go under this)
- MAXIMUM: {int(self.words_per_topic * 1.05)} words (105% of target - don't exceed this)
You have {len(self.summaries)} articles to cover, so aim for approximately {self.words_per_topic // max(len(self.summaries), 1)} words per article.
Distribute intelligently - more important/complex stories can get more words, simpler ones fewer.

FORMATTING RULES:
- Write ONE SINGLE CONTINUOUS PARAGRAPH - NO line breaks, NO double newlines
- Write in plain text ONLY - NO asterisks (*), NO markdown, NO special characters
- START with a brief natural intro to the topic (e.g., "In tech news...", "Turning to sports...")
- Weave all the articles together into one flowing narrative
- NO formal welcomes or goodbyes
- Match the TONE: {self.tone}

News Sources about {self.topic_name}:
{sources_text}
"""

        try:
            # Use Gen AI client
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            script_text = response.text.strip()

            # Create single paragraph for this topic (no splitting)
            topic_source_ids = [s["id"] for s in self.summaries]

            # Each topic = one paragraph = one audio chunk
            paragraph = {
                "text": script_text,
                "source_ids": topic_source_ids,
                "topic": self.topic_name
            }

            # Save to session state (each parallel agent writes to its own key)
            ctx.session.state[f"topic_script_{self.topic_name}"] = {
                "paragraphs": [paragraph],  # Single-item list for consistency with SynthesizerAgent
                "metadata": {
                    "name": self.topic_name,
                    "source_ids": topic_source_ids
                }
            }

            logger.info(f"   ✓ TopicScriptAgent[{self.topic_name}]: Generated 1 paragraph ({len(script_text.split())} words)")

            yield Event(
                author=self.name,
                actions=EventActions()
            )

        except Exception as e:
            logger.error(f"TopicScriptAgent[{self.topic_name}] failed: {e}")
            raise




class PodcastGenerationWorkflow:
    """
    Real Google ADK multi-agent workflow using SequentialAgent.

    Uses actual ADK SDK components:
    - BaseAgent implementations for custom logic
    - SequentialAgent for orchestration
    - Session state for agent communication
    """

    # World News subcategories that should be grouped together
    WORLD_NEWS_SUBCATEGORIES = {
        "Africa", "Asia", "Europe", "Middle East",
        "North America", "South America", "Oceania"
    }

    def __init__(self, llm_service):
        self.llm_service = llm_service
        logger.info("✅ Initialized real Google ADK multi-agent workflow")

    def _normalize_topic_name(self, subcategory: str) -> str:
        """Map world news subcategories to 'World News', keep others as-is"""
        if subcategory in self.WORLD_NEWS_SUBCATEGORIES:
            return "World News"
        return subcategory

    async def generate_podcast(self, sources: List[Dict[str, Any]], duration_minutes: int, user_name: str = None):
        """
        Generate podcast using real Google ADK multi-agent coordination with PARALLEL script generation.

        Flow:
        1. MetadataAgent → analyzes & saves title/theme/tone to session.state
        2. SummarizerAgent → reads from session.state → saves description
        3. FramingAgent → reads from session.state → saves intro/outro
        4. ParallelAgent → spawns N TopicScriptAgents (one per topic) running simultaneously
        5. SynthesizerAgent → combines parallel results into final script
        """
        logger.info("🤖 Starting real Google ADK multi-agent podcast generation with PARALLEL topic generation")
        logger.info(f"   Sources: {len(sources)} articles")
        logger.info(f"   Duration: {duration_minutes} minutes")

        # Group sources by normalized subcategory (world news regions → "World News")
        topics_map = {}
        for source in sources:
            subcategory = source.get('subcategory', 'General')
            topic_name = self._normalize_topic_name(subcategory)
            if topic_name not in topics_map:
                topics_map[topic_name] = []
            topics_map[topic_name].append(source)

        # Sort topics by category so similar topics are grouped together
        # (e.g., all sports together, all tech together)
        def get_category_sort_key(topic_name):
            # Get category from first source in this topic
            sources_for_topic = topics_map[topic_name]
            if sources_for_topic:
                category = sources_for_topic[0].get('category', 'ZZZ')  # ZZZ pushes unknowns to end
                return (category, topic_name)  # Sort by category first, then topic name
            return ('ZZZ', topic_name)

        # Create sorted topics_map preserving insertion order
        sorted_topic_names = sorted(topics_map.keys(), key=get_category_sort_key)
        topics_map = {topic_name: topics_map[topic_name] for topic_name in sorted_topic_names}

        logger.info(f"   Topics identified: {list(topics_map.keys())}")

        # Calculate words per topic proportionally based on article count
        target_words = duration_minutes * config.llm_words_per_minute
        total_articles = sum(len(articles) for articles in topics_map.values())

        words_per_topic_map = {}
        if total_articles > 0:
            for topic_name, articles in topics_map.items():
                proportion = len(articles) / total_articles
                allocated = int(target_words * proportion)
                words_per_topic_map[topic_name] = allocated
                logger.info(f"   {topic_name}: {len(articles)} articles → {words_per_topic_map[topic_name]} words ({proportion*100:.1f}%)")
        else:
            words_per_topic_map = {topic: 100 for topic in topics_map.keys()}

        # Create initial agents
        genai_client = self.llm_service.client  # Google Gen AI Client with Vertex AI backend
        model_name = self.llm_service.model_name  # gemini-2.0-flash-lite

        metadata_agent = MetadataAgent(
            name="MetadataAgent",
            sources=sources,
            duration_minutes=duration_minutes,
            genai_client=genai_client,
            model_name=model_name,
            user_name=user_name
        )

        summarizer_agent = SummarizerAgent(
            name="SummarizerAgent",
            sources=sources,
            duration_minutes=duration_minutes,
            genai_client=genai_client,
            model_name=model_name,
            user_name=user_name
        )

        framing_agent = FramingAgent(
            name="FramingAgent",
            sources=sources,
            duration_minutes=duration_minutes,
            genai_client=genai_client,
            model_name=model_name,
            user_name=user_name
        )

        # Import async dependencies
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService, Session
        from google.adk.agents import ParallelAgent
        from google.adk.agents.invocation_context import InvocationContext

        # Create session service
        session_service = InMemorySessionService()

        # Create a session using async method
        session = await session_service.create_session(
            app_name="YourCast",
            user_id="system",
            session_id="podcast-generation"
        )

        # Phase 1: Run setup agents sequentially
        setup_workflow = SequentialAgent(
            name="SetupWorkflow",
            sub_agents=[metadata_agent, summarizer_agent, framing_agent]
        )

        # Create custom workflow agent that runs everything
        class PodcastWorkflowAgent(BaseAgent):
            """Orchestrates the entire podcast generation workflow."""
            model_config = {"extra": "allow"}

            def __init__(self, name: str, setup_workflow, topics_map_data, sources_data, genai_client_inst, model_name_val, words_per_topic_map_val, **kwargs):
                # Register sub_agents for proper ADK lifecycle management (must be before setting attributes)
                super().__init__(
                    name=name,
                    sub_agents=[setup_workflow],
                    **kwargs
                )

                # Store as instance attributes (after super().__init__)
                self.setup_workflow = setup_workflow
                self.topics_map = topics_map_data
                self.sources = sources_data
                self.genai_client_inst = genai_client_inst
                self.model_name_val = model_name_val
                self.words_per_topic_map = words_per_topic_map_val

            async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
                # Phase 1: Run setup (using public API)
                async for event in self.setup_workflow.run_async(ctx):
                    yield event

                # Get context
                metadata = ctx.session.state.get("metadata", {})
                framing = ctx.session.state.get("framing", {})
                tone = metadata.get("tone", "informative")
                intro = framing.get("intro", "Welcome to Your Cast")

                # Phase 2: Create parallel topic agents
                topic_agents = []
                for topic_name, summaries in self.topics_map.items():
                    # Sanitize topic name for ADK agent name (only letters, digits, underscores)
                    safe_name = topic_name.replace(" & ", "_and_").replace("&", "_and_")
                    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_name)
                    safe_name = safe_name.strip("_")  # Remove leading/trailing underscores

                    topic_agent = TopicScriptAgent(
                        name=f"TopicScript_{safe_name}",
                        topic_name=topic_name,
                        summaries=summaries,
                        tone=tone,
                        words_per_topic=self.words_per_topic_map[topic_name],
                        genai_client=self.genai_client_inst,
                        model_name=self.model_name_val
                    )
                    topic_agents.append(topic_agent)

                # Run parallel (using public API)
                parallel_workflow = ParallelAgent(name="ParallelTopicGeneration", sub_agents=topic_agents)
                async for event in parallel_workflow.run_async(ctx):
                    yield event

                # Phase 3: Assemble final script (inline - no separate agent needed)
                logger.info("🔗 Assembling final script from parallel results...")

                # Get context from session state
                metadata = ctx.session.state.get("metadata", {})
                framing = ctx.session.state.get("framing", {})

                intro = framing.get("intro", "Welcome to Your Cast")
                outro = framing.get("outro", "Thanks for listening")

                # Build paragraphs list in order
                all_paragraphs = []
                topics_metadata = []

                # Add intro
                all_paragraphs.append({
                    "text": intro,
                    "source_ids": [],
                    "topic": "Introduction"
                })

                # Add topic paragraphs in original order
                for topic_name in self.topics_map.keys():
                    topic_data = ctx.session.state.get(f"topic_script_{topic_name}")
                    if topic_data:
                        all_paragraphs.extend(topic_data["paragraphs"])
                        topics_metadata.append(topic_data["metadata"])

                # Add outro
                all_paragraphs.append({
                    "text": outro,
                    "source_ids": [],
                    "topic": "Outro"
                })

                # Calculate estimated duration
                total_words = sum(len(p["text"].split()) for p in all_paragraphs)
                estimated_duration = int((total_words / config.llm_words_per_minute) * 60)

                # Create final script object
                from agent.services.llm_service import PodcastScript
                script = PodcastScript(
                    paragraphs=all_paragraphs,
                    estimated_duration=estimated_duration,
                    topics=topics_metadata
                )

                # Save to session state
                ctx.session.state["script"] = script

                logger.info(f"   ✓ Assembled {len(all_paragraphs)} paragraphs (intro + {len(topics_metadata)} topics + outro)")

        # Create and run the complete workflow
        complete_workflow = PodcastWorkflowAgent(
            name="CompleteWorkflow",
            setup_workflow=setup_workflow,
            topics_map_data=topics_map,
            sources_data=sources,
            genai_client_inst=genai_client,
            model_name_val=model_name,
            words_per_topic_map_val=words_per_topic_map
        )

        # Run the workflow using proper ADK public API
        ctx = InvocationContext(
            session_service=session_service,
            invocation_id="podcast-gen",
            agent=complete_workflow,
            session=session
        )
        events = []
        # Use public .run_async() API (not private ._run_async_impl())
        async for event in complete_workflow.run_async(ctx):
            events.append(event)

        final_ctx = ctx

        # Extract results from final context session state
        session = final_ctx.session

        # Debug: check what's in session
        logger.info(f"Final session state keys: {list(session.state.keys())}")

        metadata = session.state.get("metadata", {})
        description = session.state.get("description", "")
        script = session.state.get("script")

        if script is None:
            logger.error("⚠️  Script is None! Session state does not contain 'script' key")
            logger.error(f"Available keys: {list(session.state.keys())}")

        logger.info(f"✅ Podcast generation complete: {len(topics_map)} topics processed in parallel")

        return {
            "title": metadata.get("title", "Your Cast Episode"),
            "description": description,
            "script": script
        }


def create_podcast_generation_workflow(llm_service):
    """Factory function to create the podcast generation workflow."""
    return PodcastGenerationWorkflow(llm_service)
