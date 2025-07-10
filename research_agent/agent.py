"""
Research Agent implementation.

This module contains the main Research Agent that searches for and analyzes
academic sources to support content generation.
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from pydantic_ai import Agent, RunContext

from config import Config
from models import AcademicSource, ResearchFindings, TavilySearchResponse
from model_factories.openrouter import create_openrouter_model
from tools import extract_key_statistics

from .prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from .prompts_enhanced import ENHANCED_RESEARCH_AGENT_SYSTEM_PROMPT
from .tools import (
    search_academic,
    extract_full_content,
    crawl_domain,
    analyze_domain_structure,
    multi_step_research,
)

# Set up logging
logger = logging.getLogger(__name__)


def create_research_agent(config: Config) -> Agent[None, ResearchFindings]:
    """
    Create and configure the Research Agent.

    This agent is responsible for:
    - Searching academic sources via Tavily
    - Analyzing and summarizing findings
    - Extracting key statistics and insights
    - Identifying research gaps

    Args:
        config: System configuration

    Returns:
        Configured PydanticAI agent for research
    """
    # Create the agent with specific model and output type
    # Using enhanced prompt for advanced Tavily capabilities
    
    # Determine which model to use based on configuration
    if config.use_openrouter:
        # Use OpenRouter for multi-model support
        logger.info(f"Using OpenRouter model: {config.get_model_for_task('research')}")
        model = create_openrouter_model(
            model_name=config.get_model_for_task("research"),
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url,
            extra_headers={
                "HTTP-Referer": config.openrouter_site_url,
                "X-Title": config.openrouter_app_name,
            } if config.openrouter_site_url else None
        )
    else:
        # Fallback to direct OpenAI
        logger.info(f"Using OpenAI model: {config.llm_model}")
        model = f"openai:{config.llm_model}"
    
    research_agent = Agent(
        model=model,
        output_type=ResearchFindings,
        system_prompt=ENHANCED_RESEARCH_AGENT_SYSTEM_PROMPT,
    )

    # Register the Tavily search tool
    @research_agent.tool
    async def search_academic_tool(ctx: RunContext[None], query: str) -> Dict[str, Any]:
        """
        Search for academic sources using Tavily API.

        Args:
            query: Search query for academic sources

        Returns:
            Search results from Tavily
        """
        return await search_academic(ctx, query, config)

    # Register a tool for extracting key statistics
    @research_agent.tool
    def extract_statistics_tool(ctx: RunContext[None], text: str) -> List[str]:
        """
        Extract key statistics from research text.

        Args:
            text: Text to analyze for statistics

        Returns:
            List of extracted statistics
        """
        return extract_key_statistics(text)

    # Register a tool for analyzing research gaps
    @research_agent.tool
    def identify_research_gaps_tool(
        ctx: RunContext[None], sources: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Identify research gaps from academic sources.

        Args:
            sources: List of academic sources to analyze

        Returns:
            List of identified research gaps
        """
        if sources is None:
            return []
        return _identify_research_gaps(sources)

    # Register extract full content tool
    @research_agent.tool
    async def extract_content_tool(
        ctx: RunContext[None], urls: List[str]
    ) -> Dict[str, Any]:
        """
        Extract full content from URLs for deep analysis.

        Args:
            urls: List of URLs to extract content from

        Returns:
            Extracted content for each URL
        """
        return await extract_full_content(ctx, urls, config)

    # Register domain crawling tool
    @research_agent.tool
    async def crawl_website_tool(
        ctx: RunContext[None], url: str, instructions: str
    ) -> Dict[str, Any]:
        """
        Crawl a website domain for comprehensive research.

        Args:
            url: Base URL to crawl
            instructions: Natural language instructions for focused crawling

        Returns:
            Crawled pages and content
        """
        return await crawl_domain(ctx, url, instructions, config)

    # Register domain analysis tool
    @research_agent.tool
    async def analyze_website_tool(
        ctx: RunContext[None], url: str, focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze website structure to identify key research areas.

        Args:
            url: Base URL to analyze
            focus_area: Optional area of focus

        Returns:
            Site structure analysis
        """
        return await analyze_domain_structure(ctx, url, focus_area, config)

    # Register multi-step research tool
    @research_agent.tool
    async def comprehensive_research_tool(
        ctx: RunContext[None], keyword: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive multi-step research.

        Combines search, extract, and crawl for thorough analysis.

        Args:
            keyword: Research topic

        Returns:
            Comprehensive research findings
        """
        return await multi_step_research(ctx, keyword, config)

    return research_agent


def _identify_research_gaps(sources: List[Dict[str, Any]]) -> List[str]:
    """
    Analyze sources to identify potential research gaps.

    Args:
        sources: List of source dictionaries

    Returns:
        List of identified research gaps
    """
    # Common phrases that indicate research gaps
    gap_indicators = [
        "further research",
        "more studies needed",
        "limited data",
        "unclear",
        "not well understood",
        "requires investigation",
        "gap in knowledge",
        "future work",
        "remains to be",
        "yet to be determined",
    ]

    gaps = []

    # Analyze each source for gap indicators
    for source in sources:
        content = source.get("content", "").lower()

        # Look for gap indicators
        for indicator in gap_indicators:
            if indicator in content:
                # Extract the sentence containing the indicator
                sentences = content.split(".")
                for sentence in sentences:
                    if indicator in sentence:
                        # Clean and add the gap
                        gap = sentence.strip()
                        if gap and len(gap) > 20:  # Ensure it's meaningful
                            gaps.append(gap.capitalize())
                        break

    # Remove duplicates while preserving order
    seen = set()
    unique_gaps = []
    for gap in gaps:
        if gap not in seen:
            seen.add(gap)
            unique_gaps.append(gap)

    # Return top 5 most relevant gaps
    return unique_gaps[:5]


async def run_research_agent(
    agent: Agent[None, ResearchFindings], keyword: str
) -> ResearchFindings:
    """
    Execute the research agent for a given keyword.

    Args:
        agent: The configured research agent
        keyword: The keyword to research

    Returns:
        ResearchFindings with academic sources and analysis

    Raises:
        Exception: If research fails
    """
    try:
        # Create a comprehensive research prompt
        prompt = f"""
        Research the topic '{keyword}' comprehensively using academic sources.
        
        Your task:
        1. Search for peer-reviewed academic sources about '{keyword}'
        2. Focus on .edu, .gov, and journal domains
        3. Analyze the credibility of each source
        4. Extract key findings and statistics
        5. Identify gaps in current research
        6. Provide a comprehensive summary
        
        Requirements:
        - Find at least 3 credible academic sources
        - Extract specific statistics and data points
        - Identify 3-5 main findings
        - Note any research gaps or areas needing further study
        - Ensure sources are recent (preferably within last 5 years)
        
        The search query used should be: '{keyword}'
        """

        # Run the agent
        logger.info(f"Running research agent for keyword: {keyword}")
        result = await agent.run(prompt)

        # PydanticAI returns an AgentRunResult, access the data attribute
        research_findings = result.data

        # Validate the result
        if not research_findings.academic_sources:
            raise ValueError("No academic sources found")

        # Log success
        logger.info(
            f"Research completed successfully. "
            f"Found {len(research_findings.academic_sources)} sources, "
            f"{len(research_findings.main_findings)} main findings"
        )

        return research_findings

    except Exception as e:
        logger.error(f"Research agent failed: {e}")
        raise


async def run_research_workflow(
    agent: Agent[None, ResearchFindings],
    keyword: str,
    config: Config,
    progress_callback: Optional[Callable[[Any], None]] = None,
) -> ResearchFindings:
    """
    Execute research using the advanced workflow system.

    This function uses ResearchWorkflow for orchestrated multi-step research
    with progress tracking and adaptive strategy.

    Args:
        agent: The configured research agent
        keyword: The keyword to research
        config: System configuration
        progress_callback: Optional callback for progress updates

    Returns:
        ResearchFindings with comprehensive analysis

    Raises:
        WorkflowError: If the workflow fails
    """
    try:
        # Import here to avoid circular imports
        from .workflow import ResearchWorkflow

        # Create workflow instance
        workflow = ResearchWorkflow(
            agent=agent, config=config, progress_callback=progress_callback
        )

        # Get strategy from config
        strategy = config.research_strategy
        max_retries = config.workflow_max_retries

        logger.info(
            f"Starting research workflow for '{keyword}' " f"with strategy: {strategy}"
        )

        # Execute the workflow
        findings = await workflow.execute_research_pipeline(
            keyword=keyword, strategy=strategy, max_retries=max_retries
        )

        # Log completion
        logger.info(
            f"Workflow completed successfully. "
            f"Sources: {len(findings.academic_sources)}, "
            f"Findings: {len(findings.main_findings)}"
        )

        return findings

    except Exception as e:
        logger.error(f"Research workflow failed: {e}")
        raise
