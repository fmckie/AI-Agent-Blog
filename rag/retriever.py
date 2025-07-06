"""
Research Retriever Module for RAG System.

This module orchestrates the retrieval-augmented generation process,
managing cache lookups, semantic search, and storage of new research.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from models import AcademicSource, ResearchFindings

from .config import get_rag_config
from .embeddings import EmbeddingGenerator
from .processor import TextProcessor
from .storage import VectorStorage

logger = logging.getLogger(__name__)


class RetrievalStatistics:
    """Track retrieval performance and usage statistics."""

    def __init__(self):
        """Initialize statistics tracking."""
        # Initialize counters for cache performance
        self.exact_hits = 0
        self.semantic_hits = 0
        self.cache_misses = 0
        self.total_requests = 0

        # Track timing metrics
        self.cache_response_times: List[float] = []
        self.api_response_times: List[float] = []

        # Track errors
        self.errors = 0

    def record_exact_hit(self, response_time: float):
        """Record an exact cache hit."""
        # Update statistics for exact match
        self.exact_hits += 1
        self.total_requests += 1
        self.cache_response_times.append(response_time)

    def record_semantic_hit(self, response_time: float):
        """Record a semantic cache hit."""
        # Update statistics for semantic match
        self.semantic_hits += 1
        self.total_requests += 1
        self.cache_response_times.append(response_time)

    def record_cache_miss(self, response_time: float):
        """Record a cache miss."""
        # Update statistics for cache miss
        self.cache_misses += 1
        self.total_requests += 1
        self.api_response_times.append(response_time)

    def record_error(self):
        """Record an error during retrieval."""
        # Increment error counter
        self.errors += 1
        self.total_requests += 1

    @property
    def cache_hit_rate(self) -> float:
        """Calculate overall cache hit rate."""
        # Calculate percentage of requests served from cache
        if self.total_requests == 0:
            return 0.0

        cache_hits = self.exact_hits + self.semantic_hits
        return (cache_hits / self.total_requests) * 100

    @property
    def average_cache_response_time(self) -> float:
        """Calculate average response time for cached requests."""
        # Return average or 0 if no cached responses
        if not self.cache_response_times:
            return 0.0
        return sum(self.cache_response_times) / len(self.cache_response_times)

    @property
    def average_api_response_time(self) -> float:
        """Calculate average response time for API requests."""
        # Return average or 0 if no API responses
        if not self.api_response_times:
            return 0.0
        return sum(self.api_response_times) / len(self.api_response_times)

    def get_summary(self) -> Dict[str, Any]:
        """Get statistics summary."""
        # Compile all statistics into a dictionary
        return {
            "total_requests": self.total_requests,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "cache_misses": self.cache_misses,
            "errors": self.errors,
            "cache_hit_rate": f"{self.cache_hit_rate:.1f}%",
            "avg_cache_response_ms": f"{self.average_cache_response_time * 1000:.1f}",
            "avg_api_response_ms": f"{self.average_api_response_time * 1000:.1f}",
        }


class ResearchRetriever:
    """
    Orchestrates the RAG system for intelligent research caching.

    This class manages the entire retrieval pipeline:
    1. Check exact cache for keyword match
    2. Perform semantic search if no exact match
    3. Call research function if cache miss
    4. Store new research for future use
    """

    # Class-level instance tracking for statistics
    _instances = []

    def __init__(self):
        """Initialize the retriever with all required components."""
        # Get configuration
        self.config = get_rag_config()

        # Initialize components
        self.processor = TextProcessor(self.config)
        self.embeddings = EmbeddingGenerator()
        self.storage = VectorStorage()

        # Initialize statistics tracking
        self.stats = RetrievalStatistics()

        # Track this instance for statistics access
        ResearchRetriever._instances.append(self)

        logger.info("Initialized ResearchRetriever")

    async def retrieve_or_research(
        self, keyword: str, research_function: Callable[[], Any]
    ) -> ResearchFindings:
        """
        Main retrieval method with intelligent caching.

        Args:
            keyword: Search keyword/topic
            research_function: Async function to call if cache miss

        Returns:
            ResearchFindings from cache or fresh research
        """
        # Track start time for performance metrics
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Check exact cache
            logger.info(f"Checking cache for keyword: {keyword}")
            cached_response = await self._check_exact_cache(keyword)

            if cached_response:
                # Calculate response time
                response_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()
                self.stats.record_exact_hit(response_time)

                logger.info(f"Exact cache hit for keyword: {keyword}")
                return self._reconstruct_findings_from_cache(cached_response)

            # Step 2: Perform semantic search
            logger.info(f"No exact match, trying semantic search for: {keyword}")
            semantic_results = await self._semantic_search(keyword)

            if semantic_results:
                # Calculate response time
                response_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()
                self.stats.record_semantic_hit(response_time)

                logger.info(f"Semantic cache hit for keyword: {keyword}")
                return semantic_results

            # Step 3: Cache miss - call research function
            logger.info(f"Cache miss, calling research function for: {keyword}")

            # Call the research function
            research_result = await research_function()

            # Convert to ResearchFindings if needed
            if isinstance(research_result, dict):
                findings = self._dict_to_findings(research_result, keyword)
            else:
                findings = research_result

            # Calculate response time
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.stats.record_cache_miss(response_time)

            # Step 4: Store new research
            await self._store_research(findings)

            logger.info(f"Stored new research for keyword: {keyword}")
            return findings

        except Exception as e:
            # Record error and re-raise
            self.stats.record_error()
            logger.error(f"Error in retrieve_or_research: {e}")
            raise

    async def _check_exact_cache(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Check for exact keyword match in cache.

        Args:
            keyword: Search keyword

        Returns:
            Cached response or None
        """
        try:
            # Use storage to check cache
            cached = await self.storage.get_cached_response(keyword)

            if cached:
                logger.debug(f"Found exact cache entry for: {keyword}")
                return cached

            return None

        except Exception as e:
            logger.warning(f"Error checking exact cache: {e}")
            return None

    async def _semantic_search(self, keyword: str) -> Optional[ResearchFindings]:
        """
        Perform semantic similarity search.

        Args:
            keyword: Search keyword

        Returns:
            ResearchFindings from similar content or None
        """
        try:
            # Generate embedding for the keyword
            keyword_embedding = await self.embeddings.generate_embedding(keyword)

            # Search for similar chunks
            similar_chunks = await self.storage.search_similar_chunks(
                query_embedding=keyword_embedding.embedding,
                limit=50,  # Get more chunks to reconstruct full findings
                similarity_threshold=self.config.cache_similarity_threshold,
            )

            if not similar_chunks:
                return None

            # Group chunks by keyword to find the best match
            keyword_chunks = {}
            for chunk_data, similarity in similar_chunks:
                chunk_keyword = chunk_data.get("keyword", "")
                if chunk_keyword not in keyword_chunks:
                    keyword_chunks[chunk_keyword] = []
                keyword_chunks[chunk_keyword].append((chunk_data, similarity))

            # Find the keyword with highest average similarity
            best_keyword = None
            best_avg_similarity = 0

            for kw, chunks in keyword_chunks.items():
                avg_similarity = sum(sim for _, sim in chunks) / len(chunks)
                if avg_similarity > best_avg_similarity:
                    best_avg_similarity = avg_similarity
                    best_keyword = kw

            # Check if best match meets threshold
            if best_avg_similarity < self.config.cache_similarity_threshold:
                logger.info(
                    f"Best semantic match ({best_avg_similarity:.2f}) below threshold"
                )
                return None

            # Reconstruct findings from the best matching keyword's chunks
            logger.info(
                f"Found semantic match with keyword '{best_keyword}' (similarity: {best_avg_similarity:.2f})"
            )
            return self._reconstruct_findings_from_chunks(
                keyword_chunks[best_keyword], original_keyword=keyword
            )

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return None

    def _reconstruct_findings_from_cache(
        self, cache_entry: Dict[str, Any]
    ) -> ResearchFindings:
        """
        Reconstruct ResearchFindings from cache entry.

        Args:
            cache_entry: Cache entry from database

        Returns:
            Reconstructed ResearchFindings
        """
        # Extract metadata
        metadata = cache_entry.get("metadata", {})

        # Reconstruct academic sources from chunks
        academic_sources = []
        for chunk in cache_entry.get("chunks", []):
            chunk_metadata = chunk.get("metadata", {})

            # Only process academic source chunks
            if chunk_metadata.get("source_type") == "academic_source":
                # Truncate excerpt to max 500 chars to comply with model validation
                excerpt = chunk.get("content", "")[:500]
                
                source = AcademicSource(
                    title=chunk_metadata.get("source_title", ""),
                    url=chunk_metadata.get("source_url", ""),
                    excerpt=excerpt,
                    domain=chunk_metadata.get("domain", ".com"),
                    credibility_score=chunk_metadata.get("credibility_score", 0.5),
                    authors=chunk_metadata.get("authors"),
                    publication_date=chunk_metadata.get("publication_date"),
                    journal_name=chunk_metadata.get("journal_name"),
                )
                academic_sources.append(source)

        # Create ResearchFindings
        findings = ResearchFindings(
            keyword=cache_entry.get("keyword", ""),
            research_summary=cache_entry.get("research_summary", ""),
            academic_sources=academic_sources,
            key_statistics=metadata.get("key_statistics", []),
            research_gaps=metadata.get("research_gaps", []),
            main_findings=metadata.get("main_findings", []),
            total_sources_analyzed=metadata.get(
                "total_sources_analyzed", len(academic_sources)
            ),
            search_query_used=metadata.get(
                "search_query_used", cache_entry.get("keyword", "")
            ),
        )

        return findings

    def _reconstruct_findings_from_chunks(
        self, chunks: List[tuple], original_keyword: str
    ) -> ResearchFindings:
        """
        Reconstruct ResearchFindings from semantic search results.

        Args:
            chunks: List of (chunk_data, similarity) tuples
            original_keyword: The original search keyword

        Returns:
            Reconstructed ResearchFindings
        """
        # Initialize containers for different types of content
        research_summary = ""
        academic_sources = []
        main_findings = []
        key_statistics = []

        # Process chunks by type
        for chunk_data, _ in chunks:
            metadata = chunk_data.get("metadata", {})
            source_type = metadata.get("source_type", "")

            if source_type == "research_summary":
                # Use the summary chunk
                research_summary = chunk_data.get("content", "")

            elif source_type == "academic_source":
                # Reconstruct academic source
                # Truncate excerpt to max 500 chars to comply with model validation
                excerpt = chunk_data.get("content", "")[:500]
                
                source = AcademicSource(
                    title=metadata.get("source_title", ""),
                    url=metadata.get("source_url", ""),
                    excerpt=excerpt,
                    domain=metadata.get("domain", ".com"),
                    credibility_score=metadata.get("credibility_score", 0.5),
                    authors=metadata.get("authors"),
                    publication_date=metadata.get("publication_date"),
                    journal_name=metadata.get("journal_name"),
                )
                # Avoid duplicates based on URL
                if not any(s.url == source.url for s in academic_sources):
                    academic_sources.append(source)

            elif source_type == "main_findings":
                # Extract findings from chunk
                findings_text = chunk_data.get("content", "")
                # Split by newlines to get individual findings
                findings_list = [
                    f.strip() for f in findings_text.split("\n\n") if f.strip()
                ]
                main_findings.extend(findings_list)

            elif source_type == "statistics":
                # Extract statistics from chunk
                stats_text = chunk_data.get("content", "")
                # Split by newlines to get individual stats
                stats_list = [s.strip() for s in stats_text.split("\n") if s.strip()]
                key_statistics.extend(stats_list)

        # Remove duplicates while preserving order
        main_findings = list(dict.fromkeys(main_findings))
        key_statistics = list(dict.fromkeys(key_statistics))

        # Create ResearchFindings with reconstructed data
        findings = ResearchFindings(
            keyword=original_keyword,
            research_summary=research_summary
            or f"Research findings related to {original_keyword}",
            academic_sources=academic_sources,
            key_statistics=key_statistics,
            research_gaps=[],  # Not stored in chunks currently
            main_findings=main_findings,
            total_sources_analyzed=len(academic_sources),
            search_query_used=original_keyword,
        )

        return findings

    def _dict_to_findings(
        self, result_dict: Dict[str, Any], keyword: str
    ) -> ResearchFindings:
        """
        Convert dictionary response to ResearchFindings.

        Args:
            result_dict: Dictionary from research function
            keyword: Search keyword

        Returns:
            ResearchFindings object
        """
        # Handle the case where research function returns a dict
        # This happens with the current Tavily integration

        # Extract results
        results = result_dict.get("results", [])

        # Convert to academic sources
        academic_sources = []
        for result in results:
            # Calculate credibility based on domain
            domain = self._extract_domain(result.get("url", ""))
            credibility = self._calculate_credibility(domain, result)

            source = AcademicSource(
                title=result.get("title", ""),
                url=result.get("url", ""),
                excerpt=result.get("content", "")[:500],  # Limit excerpt length
                domain=domain,
                credibility_score=credibility,
                source_type="web",
            )
            academic_sources.append(source)

        # Create research summary
        research_summary = result_dict.get("answer", f"Research findings for {keyword}")

        # Extract any statistics or findings from the answer
        main_findings = []
        if "answer" in result_dict and result_dict["answer"]:
            # Simple extraction - can be enhanced
            sentences = result_dict["answer"].split(". ")
            main_findings = [s.strip() + "." for s in sentences if len(s.strip()) > 20][
                :5
            ]

        # Create ResearchFindings
        findings = ResearchFindings(
            keyword=keyword,
            research_summary=research_summary,
            academic_sources=academic_sources,
            key_statistics=[],  # Could extract from content
            research_gaps=[],  # Could analyze for gaps
            main_findings=main_findings,
            total_sources_analyzed=len(results),
            search_query_used=result_dict.get("query", keyword),
        )

        return findings

    def _extract_domain(self, url: str) -> str:
        """Extract domain extension from URL."""
        # Simple domain extraction
        if ".edu" in url:
            return ".edu"
        elif ".gov" in url:
            return ".gov"
        elif ".org" in url:
            return ".org"
        elif ".ac.uk" in url:
            return ".ac.uk"
        else:
            return ".com"

    def _calculate_credibility(self, domain: str, result: Dict[str, Any]) -> float:
        """Calculate credibility score based on domain and content."""
        # Base score by domain type
        domain_scores = {
            ".edu": 0.9,
            ".gov": 0.9,
            ".org": 0.7,
            ".ac.uk": 0.9,
            ".com": 0.5,
        }

        score = domain_scores.get(domain, 0.5)

        # Boost score if certain keywords present
        content = result.get("content", "").lower()
        if any(
            term in content
            for term in ["study", "research", "journal", "peer-reviewed"]
        ):
            score = min(1.0, score + 0.1)

        return score

    async def _store_research(self, findings: ResearchFindings) -> None:
        """
        Store research findings in the cache.

        Args:
            findings: Research findings to store
        """
        try:
            # Process findings into chunks
            chunks = self.processor.process_research_findings(findings)

            if not chunks:
                logger.warning("No chunks generated from research findings")
                return

            # Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embeddings.generate_embeddings(chunk_texts)

            # Store chunks with embeddings
            chunk_ids = await self.storage.store_research_chunks(
                chunks=chunks, embeddings=embeddings, keyword=findings.keyword
            )

            # Prepare metadata for cache entry
            metadata = {
                "key_statistics": findings.key_statistics,
                "research_gaps": findings.research_gaps,
                "main_findings": findings.main_findings,
                "total_sources_analyzed": findings.total_sources_analyzed,
                "search_query_used": findings.search_query_used,
                "timestamp": findings.research_timestamp.isoformat(),
            }

            # Store cache entry
            await self.storage.store_cache_entry(
                keyword=findings.keyword,
                research_summary=findings.research_summary,
                chunk_ids=chunk_ids,
                metadata=metadata,
            )

            logger.info(f"Successfully stored research with {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Error storing research: {e}")
            # Don't raise - allow retrieval to continue even if storage fails

    async def warm_cache(
        self, keywords: List[str], research_function: Callable
    ) -> Dict[str, Any]:
        """
        Pre-populate cache with common keywords.

        Args:
            keywords: List of keywords to cache
            research_function: Function to generate research

        Returns:
            Summary of cache warming results
        """
        results = {"successful": 0, "failed": 0, "already_cached": 0, "keywords": {}}

        for keyword in keywords:
            try:
                # Check if already cached
                cached = await self._check_exact_cache(keyword)
                if cached:
                    results["already_cached"] += 1
                    results["keywords"][keyword] = "already_cached"
                    continue

                # Generate and store research
                findings = await self.retrieve_or_research(keyword, research_function)
                results["successful"] += 1
                results["keywords"][keyword] = "success"

                # Add small delay to avoid rate limits
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to warm cache for '{keyword}': {e}")
                results["failed"] += 1
                results["keywords"][keyword] = f"error: {str(e)}"

        return results

    def get_instance_statistics(self) -> Dict[str, Any]:
        """Get retriever statistics for this instance."""
        # Combine retriever stats with component stats
        stats = {
            "retriever": self.stats.get_summary(),
            "embeddings": self.embeddings.get_statistics(),
            "storage": {},  # Storage stats would go here
        }

        return stats

    @classmethod
    def get_statistics(cls) -> Optional[Dict[str, Any]]:
        """
        Get combined statistics from all retriever instances.

        Returns:
            Combined statistics or None if no instances exist
        """
        if not cls._instances:
            return None

        # Combine statistics from all instances
        combined_stats = {
            "cache_requests": 0,
            "cache_hits": 0,
            "exact_hits": 0,
            "semantic_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "avg_retrieval_time": 0.0,
            "hit_rate": 0.0,
        }

        total_response_times = []

        for instance in cls._instances:
            stats = instance.stats
            combined_stats["cache_requests"] += stats.total_requests
            combined_stats["cache_hits"] += stats.exact_hits + stats.semantic_hits
            combined_stats["exact_hits"] += stats.exact_hits
            combined_stats["semantic_hits"] += stats.semantic_hits
            combined_stats["cache_misses"] += stats.cache_misses
            combined_stats["errors"] += stats.errors

            # Collect all response times
            total_response_times.extend(stats.cache_response_times)
            total_response_times.extend(stats.api_response_times)

        # Calculate averages
        if total_response_times:
            combined_stats["avg_retrieval_time"] = sum(total_response_times) / len(
                total_response_times
            )

        # Calculate hit rate
        if combined_stats["cache_requests"] > 0:
            combined_stats["hit_rate"] = (
                combined_stats["cache_hits"] / combined_stats["cache_requests"]
            )

        return combined_stats

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Close storage connections
        await self.storage.close()
        logger.info("ResearchRetriever cleanup completed")
