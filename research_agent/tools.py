"""
Tools for the Research Agent.

This module contains the tool functions that the Research Agent uses
to search for and analyze academic sources.
"""

import logging
from typing import Any, Dict

from pydantic_ai import RunContext

from config import Config
from tools import search_academic_sources

logger = logging.getLogger(__name__)


async def search_academic(
    ctx: RunContext[None], query: str, config: Config
) -> Dict[str, Any]:
    """
    Search for academic sources using Tavily API.

    This tool is used by the Research Agent to find academic sources
    relevant to the given query.

    Args:
        ctx: PydanticAI run context
        query: Search query for academic sources
        config: System configuration with API keys

    Returns:
        Search results from Tavily with credibility scores
    """
    logger.debug(f"Searching academic sources for: {query}")

    # Use the Tavily integration from the main tools module
    response = await search_academic_sources(query, config)

    # Convert the Pydantic model to dict for the agent
    result_dict = {
        "query": response.query,
        "results": [result.model_dump() for result in response.results],
        "answer": response.answer,
        "processing_metadata": response.processing_metadata,
    }

    logger.info(f"Found {len(response.results)} academic sources")
    return result_dict
