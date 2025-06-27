"""
Research Agent implementation.

This module contains the main Research Agent that searches for and analyzes
academic sources to support content generation.
"""

import logging
from typing import Any, Dict
from pydantic_ai import Agent, RunContext

from config import Config
from models import ResearchFindings, AcademicSource
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
        system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT
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
    
    return research_agent


# Mock implementation for testing (to be removed in Phase 3)
async def _mock_research_agent_run(prompt: str) -> ResearchFindings:
    """
    Mock research agent run for testing.
    
    This will be replaced with actual agent execution in Phase 3.
    """
    return ResearchFindings(
        keyword="test keyword",
        research_summary="This is a comprehensive test research summary that provides detailed insights into the topic. It includes multiple findings from academic sources and presents a thorough analysis of the current state of research in this field.",
        academic_sources=[
            AcademicSource(
                title="Test Academic Paper",
                url="https://example.edu/paper",
                excerpt="Test excerpt from paper",
                domain=".edu",
                credibility_score=0.9
            )
        ],
        main_findings=["Finding 1", "Finding 2", "Finding 3"],
        total_sources_analyzed=5,
        search_query_used="test query"
    )