"""
Tools for the Research Agent.

This module contains the tool functions that the Research Agent uses
to search for and analyze academic sources.
"""

import logging
from typing import Any, Dict, Optional

from pydantic_ai import RunContext

from config import Config
from rag.retriever import ResearchRetriever
from tools import search_academic_sources

logger = logging.getLogger(__name__)

# Create a global retriever instance for caching
# This will be initialized on first use
_retriever_instance: Optional[ResearchRetriever] = None


def get_retriever() -> ResearchRetriever:
    """Get or create the global retriever instance."""
    # Use lazy initialization to avoid issues during import
    global _retriever_instance
    if _retriever_instance is None:
        logger.info("Initializing RAG retriever for research caching")
        _retriever_instance = ResearchRetriever()
    return _retriever_instance


async def search_academic(
    ctx: RunContext[None], query: str, config: Config
) -> Dict[str, Any]:
    """
    Search for academic sources using Tavily API with intelligent caching.

    This tool is used by the Research Agent to find academic sources
    relevant to the given query. It now includes RAG caching to reduce
    API costs and improve response times.

    Args:
        ctx: PydanticAI run context
        query: Search query for academic sources
        config: System configuration with API keys

    Returns:
        Search results from Tavily with credibility scores
    """
    logger.debug(f"Searching academic sources for: {query}")

    try:
        # Get the retriever instance
        retriever = get_retriever()

        # Define the research function that will be called on cache miss
        async def perform_research():
            # Call the original Tavily API
            response = await search_academic_sources(query, config)

            # Convert to dict for compatibility
            return {
                "query": response.query,
                "results": [result.model_dump() for result in response.results],
                "answer": response.answer,
                "processing_metadata": response.processing_metadata,
            }

        # Use the retriever with caching
        # This will check cache first, then semantic search, then call API if needed
        logger.info(f"Using RAG retriever for query: {query}")
        findings = await retriever.retrieve_or_research(query, perform_research)

        # Convert ResearchFindings back to expected dict format
        # The retriever returns ResearchFindings, but the agent expects a dict
        result_dict = {
            "query": findings.search_query_used,
            "results": [
                {
                    "title": source.title,
                    "url": source.url,
                    "content": source.excerpt,
                    "domain": source.domain,
                    "credibility_score": source.credibility_score,
                    "authors": source.authors,
                    "publication_date": source.publication_date,
                    "journal_name": source.journal_name,
                }
                for source in findings.academic_sources
            ],
            "answer": findings.research_summary,
            "processing_metadata": {
                "total_sources": findings.total_sources_analyzed,
                "timestamp": findings.research_timestamp.isoformat(),
                "cached": True,  # Indicates this might be from cache
            },
        }

        # Log cache statistics periodically
        stats = retriever.get_statistics()
        if stats and "retriever" in stats:
            cache_hit_rate = stats["retriever"]["cache_hit_rate"]
            logger.info(f"Cache hit rate: {cache_hit_rate}")

        logger.info(f"Returned {len(result_dict['results'])} academic sources")
        return result_dict

    except Exception as e:
        # If RAG system fails, fall back to direct API call
        logger.warning(f"RAG retriever failed, falling back to direct API: {e}")

        # Use the original implementation as fallback
        response = await search_academic_sources(query, config)

        # Convert the Pydantic model to dict for the agent
        result_dict = {
            "query": response.query,
            "results": [result.model_dump() for result in response.results],
            "answer": response.answer,
            "processing_metadata": response.processing_metadata,
        }

        logger.info(f"Found {len(response.results)} academic sources (direct API)")
        return result_dict
