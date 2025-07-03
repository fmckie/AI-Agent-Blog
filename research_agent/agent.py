"""
Research Agent implementation.

This module contains the main Research Agent that searches for and analyzes
academic sources to support content generation.
"""

import logging
import re
from typing import Any, Dict, List, Optional


from pydantic_ai import Agent, RunContext

from config import Config
from models import AcademicSource, ResearchFindings, TavilySearchResponse
from tools import extract_key_statistics

from .prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from .tools import search_academic

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
    research_agent = Agent(
        model=f"openai:{config.llm_model}",
        output_type=ResearchFindings,
        system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
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
