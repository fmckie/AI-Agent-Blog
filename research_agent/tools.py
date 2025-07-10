"""
Tools for the Research Agent.

This module contains the tool functions that the Research Agent uses
to search for and analyze academic sources.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext

from config import Config
from rag.retriever import ResearchRetriever
from tools import (
    search_academic_sources,
    extract_url_content,
    crawl_website,
    map_website,
)
from models import AcademicSource

# Import EnhancedVectorStorage for Phase 3 integration
try:
    from rag.enhanced_storage import EnhancedVectorStorage

    enhanced_storage_available = True
except ImportError:
    enhanced_storage_available = False

logger = logging.getLogger(__name__)

if not enhanced_storage_available:
    logger.warning("EnhancedVectorStorage not available, using basic storage only")

# Create a global retriever instance for caching
# This will be initialized on first use
_retriever_instance: Optional[ResearchRetriever] = None
_enhanced_storage_instance: Optional[EnhancedVectorStorage] = None


def get_retriever() -> ResearchRetriever:
    """Get or create the global retriever instance."""
    # Use lazy initialization to avoid issues during import
    global _retriever_instance
    if _retriever_instance is None:
        logger.info("Initializing RAG retriever for research caching")
        _retriever_instance = ResearchRetriever()
    return _retriever_instance


def get_enhanced_storage() -> Optional[EnhancedVectorStorage]:
    """Get or create the global enhanced storage instance."""
    global _enhanced_storage_instance
    if enhanced_storage_available and _enhanced_storage_instance is None:
        try:
            logger.info("Initializing EnhancedVectorStorage for Phase 3 features")
            _enhanced_storage_instance = EnhancedVectorStorage()
        except Exception as e:
            logger.error(f"Failed to initialize EnhancedVectorStorage: {e}")
            return None
    return _enhanced_storage_instance


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

        # Store sources in EnhancedVectorStorage if available
        if enhanced_storage_available and findings.academic_sources:
            try:
                storage = get_enhanced_storage()
                if storage:
                    stored_count = 0
                    for source in findings.academic_sources:
                        source_id = await storage.store_research_source(
                            source=source,
                            generate_embedding=False,  # Will generate later with full content
                        )
                        if source_id:
                            stored_count += 1
                    logger.info(
                        f"Stored {stored_count} sources in EnhancedVectorStorage"
                    )
            except Exception as e:
                logger.warning(f"Failed to store sources in EnhancedVectorStorage: {e}")

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


async def extract_full_content(
    ctx: RunContext[None], urls: List[str], config: Config
) -> Dict[str, Any]:
    """
    Extract full content from URLs for deep analysis.

    This tool enables the Research Agent to get complete article content
    rather than just snippets, allowing for more thorough analysis.

    Args:
        ctx: PydanticAI run context
        urls: List of URLs to extract content from
        config: System configuration

    Returns:
        Dictionary with extracted content for each URL
    """
    logger.info(f"Extracting full content from {len(urls)} URLs")

    try:
        # Call the Tavily extract API
        extract_results = await extract_url_content(
            urls, config, extract_depth="advanced"
        )

        # Process and enhance results
        processed_results = []
        for result in extract_results.get("results", []):
            if result.get("raw_content"):
                processed_results.append(
                    {
                        "url": result.get("url"),
                        "title": result.get("title", ""),
                        "raw_content": result.get("raw_content"),
                        "content_length": len(result.get("raw_content", "")),
                        "extraction_success": True,
                    }
                )

                # Update source with full content in EnhancedVectorStorage
                if enhanced_storage_available:
                    try:
                        storage = get_enhanced_storage()
                        if storage:
                            source_data = await storage.get_source_by_url(
                                result.get("url")
                            )
                            if source_data:
                                # Update existing source with full content
                                source = AcademicSource(
                                    title=result.get("title", source_data["title"]),
                                    url=result.get("url"),
                                    excerpt=result.get("raw_content", "")[:500],
                                    domain=source_data["domain"],
                                    credibility_score=source_data["credibility_score"],
                                    source_type=source_data.get(
                                        "source_type", "extracted"
                                    ),
                                )
                                await storage.store_research_source(
                                    source=source,
                                    full_content=result.get("raw_content"),
                                    generate_embedding=True,
                                )
                                logger.debug(
                                    f"Updated source with full content: {result.get('url')}"
                                )
                    except Exception as e:
                        logger.warning(f"Failed to update EnhancedVectorStorage: {e}")
            else:
                processed_results.append(
                    {
                        "url": result.get("url"),
                        "error": "Failed to extract content",
                        "extraction_success": False,
                    }
                )

        logger.info(
            f"Successfully extracted content from "
            f"{len([r for r in processed_results if r['extraction_success']])} URLs"
        )

        return {
            "requested_urls": urls,
            "results": processed_results,
            "metadata": {
                "total_requested": len(urls),
                "successful_extractions": len(
                    [r for r in processed_results if r.get("extraction_success")]
                ),
                "timestamp": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        raise


async def crawl_domain(
    ctx: RunContext[None], url: str, instructions: str, config: Config
) -> Dict[str, Any]:
    """
    Crawl a website domain for comprehensive research.

    This tool allows the Research Agent to deeply explore a website,
    following links to gather related content on a topic.

    Args:
        ctx: PydanticAI run context
        url: Base URL to crawl
        instructions: Natural language instructions for focused crawling
        config: System configuration

    Returns:
        Dictionary with crawled pages and content
    """
    logger.info(f"Crawling domain: {url} with instructions: {instructions[:50]}...")

    try:
        # Call the Tavily crawl API
        crawl_results = await crawl_website(
            url, config, max_depth=2, instructions=instructions
        )

        # Process crawl results
        pages = crawl_results.get("results", [])

        # Extract domain statistics
        domain_stats = {
            "total_pages": len(pages),
            "total_content_length": sum(len(p.get("raw_content", "")) for p in pages),
            "unique_domains": len(
                set(p.get("url", "").split("/")[2] for p in pages if p.get("url"))
            ),
        }

        # Categorize pages by relevance
        relevant_pages = []
        for page in pages:
            content = page.get("raw_content", "").lower()
            title = page.get("title", "").lower()

            # Simple relevance scoring based on instructions
            instruction_words = instructions.lower().split()
            relevance_score = sum(
                1 for word in instruction_words if word in content or word in title
            )

            if relevance_score > 0:
                relevant_pages.append(
                    {
                        "url": page.get("url"),
                        "title": page.get("title"),
                        "content_preview": page.get("raw_content", "")[:500],
                        "relevance_score": relevance_score,
                    }
                )

        # Sort by relevance
        relevant_pages.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.info(
            f"Crawled {domain_stats['total_pages']} pages, "
            f"found {len(relevant_pages)} relevant pages"
        )

        # Store crawl results in EnhancedVectorStorage
        if enhanced_storage_available and pages:
            try:
                storage = get_enhanced_storage()
                if storage:
                    # Extract keyword from instructions
                    keyword = (
                        instructions.split("'")[1]
                        if "'" in instructions
                        else "research"
                    )

                    # Store crawl results
                    stored_ids = await storage.store_crawl_results(
                        crawl_data={"results": pages}, parent_url=url, keyword=keyword
                    )
                    logger.info(
                        f"Stored {len(stored_ids)} crawled pages in EnhancedVectorStorage"
                    )

                    # Create relationships between crawled pages
                    if len(stored_ids) > 1:
                        for i in range(len(stored_ids) - 1):
                            await storage.create_source_relationship(
                                source_id=stored_ids[i],
                                related_id=stored_ids[i + 1],
                                relationship_type="related",
                                metadata={"crawl_session": url},
                            )
            except Exception as e:
                logger.warning(f"Failed to store crawl in EnhancedVectorStorage: {e}")

        return {
            "base_url": url,
            "instructions": instructions,
            "domain_stats": domain_stats,
            "relevant_pages": relevant_pages[:10],  # Top 10 most relevant
            "all_pages_count": len(pages),
            "metadata": {
                "crawl_timestamp": datetime.now().isoformat(),
                "crawl_depth": 2,
            },
        }

    except Exception as e:
        logger.error(f"Domain crawl failed: {e}")
        raise


async def analyze_domain_structure(
    ctx: RunContext[None],
    url: str,
    focus_area: Optional[str] = None,
    config: Config = None,
) -> Dict[str, Any]:
    """
    Analyze website structure to identify key research areas.

    This tool helps the Research Agent understand a website's organization
    and identify the most valuable sections for research.

    Args:
        ctx: PydanticAI run context
        url: Base URL to analyze
        focus_area: Optional area of focus for the analysis
        config: System configuration

    Returns:
        Dictionary with site structure analysis
    """
    logger.info(f"Analyzing domain structure: {url}")

    try:
        # Use instructions if focus area is provided
        instructions = None
        if focus_area:
            instructions = f"Focus on sections related to: {focus_area}"

        # Call the Tavily map API
        map_results = await map_website(url, config, instructions=instructions)

        # Analyze the site structure
        links = map_results.get("links", [])

        # Categorize links by type
        categories = {
            "research": [],
            "publications": [],
            "documentation": [],
            "blog": [],
            "about": [],
            "other": [],
        }

        for link in links:
            link_lower = link.lower()

            if any(
                word in link_lower for word in ["research", "study", "paper", "journal"]
            ):
                categories["research"].append(link)
            elif any(
                word in link_lower for word in ["publication", "article", "whitepaper"]
            ):
                categories["publications"].append(link)
            elif any(
                word in link_lower for word in ["doc", "guide", "tutorial", "api"]
            ):
                categories["documentation"].append(link)
            elif any(word in link_lower for word in ["blog", "news", "update"]):
                categories["blog"].append(link)
            elif any(word in link_lower for word in ["about", "team", "mission"]):
                categories["about"].append(link)
            else:
                categories["other"].append(link)

        # Generate insights
        insights = []
        if categories["research"]:
            insights.append(
                f"Found {len(categories['research'])} research-related pages"
            )
        if categories["publications"]:
            insights.append(
                f"Site contains {len(categories['publications'])} publication pages"
            )
        if categories["documentation"]:
            insights.append(
                f"Documentation section with {len(categories['documentation'])} pages"
            )

        logger.info(
            f"Mapped {len(links)} links across {len([c for c in categories if categories[c]])} categories"
        )

        # Store domain analysis in EnhancedVectorStorage
        if enhanced_storage_available:
            try:
                storage = get_enhanced_storage()
                if storage:
                    # Extract domain from URL
                    domain_name = url.split("//")[-1].split("/")[0]
                    domain_ext = (
                        ".edu"
                        if ".edu" in url
                        else (".gov" if ".gov" in url else ".com")
                    )

                    # Create source for domain analysis
                    domain_source = AcademicSource(
                        title=f"Domain Analysis: {domain_name}",
                        url=url,
                        excerpt=f"Analyzed {len(links)} pages focusing on {focus_area or 'general content'}",
                        domain=domain_ext,
                        credibility_score=0.7,
                        source_type="domain_analysis",
                    )
                    source_id = await storage.store_research_source(domain_source)
                    logger.debug(
                        f"Stored domain analysis in EnhancedVectorStorage: {source_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to store domain analysis: {e}")

        return {
            "base_url": url,
            "total_links": len(links),
            "categorized_links": categories,
            "insights": insights,
            "recommended_sections": [
                cat
                for cat, links in categories.items()
                if links and cat in ["research", "publications", "documentation"]
            ],
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "focus_area": focus_area,
            },
        }

    except Exception as e:
        logger.error(f"Domain structure analysis failed: {e}")
        raise


async def multi_step_research(
    ctx: RunContext[None], keyword: str, config: Config
) -> Dict[str, Any]:
    """
    Perform multi-step research combining search, extract, and crawl.

    This orchestrated tool performs a complete research workflow:
    1. Search for sources
    2. Extract content from top results
    3. Crawl promising domains
    4. Synthesize findings

    Args:
        ctx: PydanticAI run context
        keyword: Research keyword/topic
        config: System configuration

    Returns:
        Comprehensive research findings
    """
    logger.info(f"Starting multi-step research for: {keyword}")

    try:
        # Step 1: Initial search
        search_results = await search_academic(ctx, keyword, config)

        # Step 2: Select top URLs for extraction
        top_urls = []
        for result in search_results.get("results", [])[:5]:
            if result.get("credibility_score", 0) > 0.7:
                top_urls.append(result["url"])

        # Step 3: Extract full content
        extracted_content = None
        if top_urls:
            extracted_content = await extract_full_content(ctx, top_urls[:3], config)

        # Step 4: Identify best domain for crawling
        best_domain = None
        if search_results.get("results"):
            # Find .edu or .gov domain with highest credibility
            for result in search_results["results"]:
                domain = result.get("domain", "")
                if (
                    domain in [".edu", ".gov"]
                    and result.get("credibility_score", 0) > 0.8
                ):
                    best_domain = (
                        result["url"].split("/")[0] + "//" + result["url"].split("/")[2]
                    )
                    break

        # Step 5: Crawl the best domain
        crawl_data = None
        if best_domain:
            crawl_instructions = (
                f"Find research, studies, and publications about {keyword}"
            )
            crawl_data = await crawl_domain(
                ctx, best_domain, crawl_instructions, config
            )

        # Step 6: Synthesize findings
        synthesis = {
            "keyword": keyword,
            "total_sources_found": len(search_results.get("results", [])),
            "high_credibility_sources": len(
                [
                    r
                    for r in search_results.get("results", [])
                    if r.get("credibility_score", 0) > 0.7
                ]
            ),
            "content_extracted_from": len(top_urls),
            "domain_crawled": best_domain is not None,
            "research_summary": {
                "search_results": search_results.get("results", [])[:3],
                "extracted_content": (
                    extracted_content.get("results", []) if extracted_content else []
                ),
                "crawled_pages": (
                    crawl_data.get("relevant_pages", [])[:3] if crawl_data else []
                ),
            },
            "metadata": {
                "research_timestamp": datetime.now().isoformat(),
                "steps_completed": [
                    "search",
                    "extract" if extracted_content else None,
                    "crawl" if crawl_data else None,
                ],
            },
        }

        logger.info(
            f"Multi-step research complete: "
            f"{synthesis['total_sources_found']} sources, "
            f"{synthesis['content_extracted_from']} extractions"
        )

        # Create source relationships in EnhancedVectorStorage
        if enhanced_storage_available and search_results.get("results"):
            try:
                storage = get_enhanced_storage()
                if storage:
                    # Get source IDs for top results
                    source_ids = []
                    for result in search_results.get("results", [])[:5]:
                        source_data = await storage.get_source_by_url(result["url"])
                        if source_data:
                            source_ids.append(source_data["id"])

                    # Calculate similarities between sources
                    for source_id in source_ids:
                        await storage.calculate_source_similarities(
                            source_id=source_id, threshold=0.7, max_relationships=3
                        )

                    logger.info(
                        f"Created similarity relationships for {len(source_ids)} sources"
                    )
            except Exception as e:
                logger.warning(f"Failed to create source relationships: {e}")

        return synthesis

    except Exception as e:
        logger.error(f"Multi-step research failed: {e}")
        raise
