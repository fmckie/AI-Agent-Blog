"""
Writer Agent implementation.

This module contains the main Writer Agent that transforms research findings
into SEO-optimized articles.
"""

import logging
from typing import Any, Dict
from pydantic_ai import Agent, RunContext

from config import Config
from models import ArticleOutput, ArticleSection
from .prompts import WRITER_AGENT_SYSTEM_PROMPT
from .tools import get_research_context, calculate_keyword_density

# Set up logging
logger = logging.getLogger(__name__)


def create_writer_agent(config: Config) -> Agent[Dict[str, Any], ArticleOutput]:
    """
    Create and configure the Writer Agent.
    
    This agent is responsible for:
    - Transforming research into engaging articles
    - Applying SEO best practices
    - Structuring content hierarchically
    - Maintaining appropriate keyword density
    
    Args:
        config: System configuration
        
    Returns:
        Configured PydanticAI agent for writing
    """
    # Create the agent with context dependency for research data
    writer_agent = Agent(
        model=f"openai:{config.llm_model}",
        deps_type=Dict[str, Any],  # Expects research context
        output_type=ArticleOutput,
        system_prompt=WRITER_AGENT_SYSTEM_PROMPT
    )
    
    # Register the tool to access research context
    @writer_agent.tool
    def get_research_context_tool(ctx: RunContext[Dict[str, Any]]) -> Any:
        """Access the research findings from context."""
        return get_research_context(ctx)
    
    # Register the tool to check keyword density
    @writer_agent.tool
    def calculate_keyword_density_tool(
        ctx: RunContext[Dict[str, Any]], 
        content: str, 
        keyword: str
    ) -> float:
        """Calculate keyword density in content."""
        return calculate_keyword_density(ctx, content, keyword)
    
    return writer_agent


# Mock implementation for testing (to be removed in Phase 4)
async def _mock_writer_agent_run(
    prompt: str, 
    context: Dict[str, Any]
) -> ArticleOutput:
    """
    Mock writer agent run for testing.
    
    This will be replaced with actual agent execution in Phase 4.
    """
    return ArticleOutput(
        title="Test Article Title",
        meta_description="A comprehensive test meta description for SEO that summarizes the article content and encourages clicks from search results.",
        focus_keyword="test keyword",
        introduction="This is a detailed test introduction that provides context for the article. It engages readers with compelling information about the topic, sets expectations for what they'll learn, and includes relevant keywords naturally throughout the text to ensure proper SEO optimization.",
        main_sections=[
            ArticleSection(
                heading="Test Section 1",
                content="Test content for section 1. " * 50  # Make it long enough
            ),
            ArticleSection(
                heading="Test Section 2", 
                content="Test content for section 2. " * 50
            ),
            ArticleSection(
                heading="Test Section 3",
                content="Test content for section 3. " * 50
            )
        ],
        conclusion="This is a comprehensive test conclusion that summarizes the key points discussed in the article and provides readers with actionable next steps to apply what they've learned.",
        word_count=1200,
        reading_time_minutes=6,
        keyword_density=0.015,
        sources_used=["https://example.edu/paper"]
    )