"""
Writer Agent implementation.

This module contains the main Writer Agent that transforms research findings
into SEO-optimized articles.
"""

import logging
from typing import Any, Dict, List

from pydantic_ai import Agent, RunContext

from config import Config
from models import ArticleOutput, ArticleSection, ResearchFindings

from .prompts import WRITER_AGENT_SYSTEM_PROMPT
from .tools import (
    calculate_keyword_density,
    check_seo_requirements,
    format_sources_for_citation,
    generate_keyword_variations,
    get_research_context,
)

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
        system_prompt=WRITER_AGENT_SYSTEM_PROMPT,
    )

    # Register the tool to access research context
    @writer_agent.tool
    def get_research_context_tool(ctx: RunContext[Dict[str, Any]]) -> ResearchFindings:
        """Access the research findings from context."""
        return get_research_context(ctx)

    # Register the tool to check keyword density
    @writer_agent.tool
    def calculate_keyword_density_tool(
        ctx: RunContext[Dict[str, Any]], content: str, keyword: str
    ) -> float:
        """Calculate keyword density in content."""
        return calculate_keyword_density(ctx, content, keyword)

    # Register the tool to format sources for citation
    @writer_agent.tool
    def format_sources_tool(
        ctx: RunContext[Dict[str, Any]], source_urls: List[str]
    ) -> List[str]:
        """Format source URLs into proper citations."""
        return format_sources_for_citation(ctx, source_urls)

    # Register the tool to check SEO requirements
    @writer_agent.tool
    def check_seo_tool(
        ctx: RunContext[Dict[str, Any]],
        title: str,
        meta_description: str,
        content: str,
        keyword: str,
    ) -> Dict[str, Any]:
        """Check if content meets SEO requirements."""
        return check_seo_requirements(ctx, title, meta_description, content, keyword)

    # Register the tool to generate keyword variations
    @writer_agent.tool
    def generate_variations_tool(
        ctx: RunContext[Dict[str, Any]], keyword: str
    ) -> List[str]:
        """Generate keyword variations for better SEO."""
        return generate_keyword_variations(ctx, keyword)

    return writer_agent


async def run_writer_agent(
    agent: Agent[Dict[str, Any], ArticleOutput],
    keyword: str,
    research_findings: ResearchFindings,
) -> ArticleOutput:
    """
    Execute the writer agent to generate an SEO-optimized article.

    Args:
        agent: The configured writer agent
        keyword: The target keyword for SEO
        research_findings: Research data to base the article on

    Returns:
        ArticleOutput with the generated article

    Raises:
        Exception: If article generation fails
    """
    try:
        # Create a comprehensive writing prompt
        prompt = f"""
        Create a comprehensive, SEO-optimized article about '{keyword}'.
        
        Requirements:
        1. Write an engaging article based on the research findings
        2. Target keyword: '{keyword}' (use naturally throughout)
        3. Minimum 1000 words for SEO effectiveness
        4. Include all key findings and statistics from research
        5. Cite sources appropriately
        6. Structure with clear H2 and H3 headings
        7. Write for a general audience while maintaining authority
        
        Article Structure:
        - Compelling title (50-60 characters) including the keyword
        - Meta description (150-160 characters) that summarizes and entices
        - Introduction that hooks the reader and previews the content
        - At least 3 main sections covering different aspects
        - Conclusion with actionable takeaways
        
        SEO Guidelines:
        - Maintain keyword density between 1-2%
        - Use keyword variations naturally
        - Create scannable content with short paragraphs
        - Include relevant statistics and data points
        - Ensure high readability
        
        Use the research findings to support all claims and provide evidence-based content.
        """

        # Prepare the context with research findings
        context = {"research": research_findings, "keyword": keyword}

        # Run the agent
        logger.info(f"Running writer agent for keyword: {keyword}")
        result = await agent.run(prompt, deps=context)

        # PydanticAI returns an AgentRunResult, access the data attribute
        article = result.data

        # Validate the output
        if article.word_count < 1000:
            logger.warning(
                f"Article word count ({article.word_count}) is below recommended minimum"
            )

        if not article.sources_used:
            raise ValueError("Article must cite research sources")

        # Log success
        logger.info(
            f"Article generated successfully: "
            f"'{article.title}' - {article.word_count} words, "
            f"{len(article.main_sections)} sections"
        )

        return article

    except Exception as e:
        logger.error(f"Writer agent failed: {e}")
        raise
