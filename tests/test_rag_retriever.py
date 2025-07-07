"""
Comprehensive test suite for RAG retriever module.

This module tests the research retrieval functionality including
cache management, semantic search, and statistics tracking.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from models import AcademicSource, ResearchFindings
from rag.embeddings import EmbeddingResult
from rag.processor import TextChunk
from rag.retriever import ResearchRetriever, RetrievalStatistics


class TestRetrievalStatistics:
    """Test cases for RetrievalStatistics tracking."""

    def test_statistics_initialization(self):
        """Test statistics initialization."""
        stats = RetrievalStatistics()

        assert stats.exact_hits == 0
        assert stats.semantic_hits == 0
        assert stats.cache_misses == 0
        assert stats.total_requests == 0
        assert stats.errors == 0
        assert stats.cache_response_times == []
        assert stats.api_response_times == []

    def test_record_exact_hit(self):
        """Test recording an exact cache hit."""
        stats = RetrievalStatistics()

        stats.record_exact_hit(0.05)

        assert stats.exact_hits == 1
        assert stats.total_requests == 1
        assert stats.cache_response_times == [0.05]
        assert stats.api_response_times == []

    def test_record_semantic_hit(self):
        """Test recording a semantic cache hit."""
        stats = RetrievalStatistics()

        stats.record_semantic_hit(0.1)

        assert stats.semantic_hits == 1
        assert stats.total_requests == 1
        assert stats.cache_response_times == [0.1]

    def test_record_cache_miss(self):
        """Test recording a cache miss."""
        stats = RetrievalStatistics()

        stats.record_cache_miss(2.5)

        assert stats.cache_misses == 1
        assert stats.total_requests == 1
        assert stats.api_response_times == [2.5]
        assert stats.cache_response_times == []

    def test_record_error(self):
        """Test recording an error."""
        stats = RetrievalStatistics()

        stats.record_error()

        assert stats.errors == 1
        assert stats.total_requests == 1

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        stats = RetrievalStatistics()

        # No requests
        assert stats.cache_hit_rate == 0.0

        # Mix of hits and misses
        stats.exact_hits = 3
        stats.semantic_hits = 2
        stats.cache_misses = 5
        stats.total_requests = 10

        assert stats.cache_hit_rate == 50.0

    def test_average_response_times(self):
        """Test average response time calculations."""
        stats = RetrievalStatistics()

        # No data
        assert stats.average_cache_response_time == 0.0
        assert stats.average_api_response_time == 0.0

        # Add cache response times
        stats.cache_response_times = [0.1, 0.2, 0.3]
        assert abs(stats.average_cache_response_time - 0.2) < 0.0001

        # Add API response times
        stats.api_response_times = [1.0, 2.0, 3.0]
        assert stats.average_api_response_time == 2.0

    def test_get_summary(self):
        """Test statistics summary generation."""
        stats = RetrievalStatistics()

        # Add some data
        stats.record_exact_hit(0.05)
        stats.record_semantic_hit(0.1)
        stats.record_cache_miss(2.0)
        stats.record_error()

        summary = stats.get_summary()

        assert summary["total_requests"] == 4
        assert summary["exact_hits"] == 1
        assert summary["semantic_hits"] == 1
        assert summary["cache_misses"] == 1
        assert summary["errors"] == 1
        assert "cache_hit_rate" in summary
        assert "avg_cache_response_ms" in summary
        assert "avg_api_response_ms" in summary


class TestResearchRetriever:
    """Test cases for ResearchRetriever."""

    @pytest.fixture
    def mock_rag_config(self):
        """Create mock RAG configuration."""
        config = Mock()
        config.cache_similarity_threshold = 0.8
        config.cache_ttl_hours = 24
        return config

    @pytest.fixture
    def mock_components(self):
        """Create mock components for retriever."""
        processor = Mock()
        embeddings = Mock()
        storage = Mock()

        # Configure storage as async context manager
        storage.__aenter__ = AsyncMock(return_value=storage)
        storage.__aexit__ = AsyncMock()

        return processor, embeddings, storage

    @pytest.fixture
    def sample_research_findings(self):
        """Create sample research findings."""
        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="AI is transforming technology",
            academic_sources=[
                AcademicSource(
                    title="AI Study",
                    url="https://example.edu/ai",
                    excerpt="AI research findings",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            key_statistics=["90% accuracy"],
            research_gaps=["Long-term studies needed"],
            main_findings=["AI improves efficiency"],
            total_sources_analyzed=5,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def mock_cache_entry(self):
        """Create mock cache entry."""
        return {
            "id": "cache123",
            "keyword": "artificial intelligence",
            "research_summary": "AI is transforming technology",
            "chunk_ids": ["chunk1", "chunk2"],
            "metadata": {
                "key_statistics": ["90% accuracy"],
                "research_gaps": ["Long-term studies needed"],
                "main_findings": ["AI improves efficiency"],
                "total_sources_analyzed": 5,
                "search_query_used": "artificial intelligence research",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "chunks": [
                {
                    "id": "chunk1",
                    "content": "AI research findings",
                    "metadata": {
                        "source_type": "academic_source",
                        "source_title": "AI Study",
                        "source_url": "https://example.edu/ai",
                        "domain": ".edu",
                        "credibility_score": 0.9,
                    },
                }
            ],
        }

    def test_retriever_initialization(self, mock_rag_config):
        """Test ResearchRetriever initialization."""
        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor") as mock_processor:
                with patch("rag.retriever.EmbeddingGenerator") as mock_embeddings:
                    with patch("rag.retriever.VectorStorage") as mock_storage:
                        retriever = ResearchRetriever()

                        assert retriever.config == mock_rag_config
                        assert retriever._pool_warmed is False
                        assert isinstance(retriever.stats, RetrievalStatistics)
                        mock_processor.assert_called_once()
                        mock_embeddings.assert_called_once()
                        mock_storage.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_warming(self, mock_rag_config, mock_components):
        """Test connection pool warming."""
        processor, embeddings, storage = mock_components
        storage.warm_pool = AsyncMock(return_value=True)

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # First call should warm pool
                        await retriever._ensure_pool_warmed()
                        assert retriever._pool_warmed is True
                        storage.warm_pool.assert_called_once()

                        # Second call should not warm again
                        await retriever._ensure_pool_warmed()
                        storage.warm_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_warming_failure(self, mock_rag_config, mock_components):
        """Test pool warming with failure."""
        processor, embeddings, storage = mock_components
        storage.warm_pool = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Should not raise, just log warning
                        await retriever._ensure_pool_warmed()
                        assert retriever._pool_warmed is True

    @pytest.mark.asyncio
    async def test_retrieve_with_exact_cache_hit(
        self,
        mock_rag_config,
        mock_components,
        mock_cache_entry,
        sample_research_findings,
    ):
        """Test retrieval with exact cache hit."""
        processor, embeddings, storage = mock_components
        storage.get_cached_response = AsyncMock(return_value=mock_cache_entry)
        storage.warm_pool = AsyncMock(return_value=True)

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock research function
                        research_func = AsyncMock(return_value=sample_research_findings)

                        result = await retriever.retrieve_or_research(
                            "artificial intelligence", research_func
                        )

                        # Should get exact cache hit
                        assert result.keyword == "artificial intelligence"
                        assert retriever.stats.exact_hits == 1
                        assert retriever.stats.cache_misses == 0
                        research_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_with_semantic_cache_hit(
        self, mock_rag_config, mock_components, sample_research_findings
    ):
        """Test retrieval with semantic cache hit."""
        processor, embeddings, storage = mock_components

        # No exact match
        storage.get_cached_response = AsyncMock(return_value=None)
        storage.warm_pool = AsyncMock(return_value=True)

        # Mock embedding generation
        keyword_embedding = EmbeddingResult(
            text="AI research",
            embedding=[0.1] * 1536,
            model="test",
            token_count=10,
        )
        embeddings.generate_embedding = AsyncMock(return_value=keyword_embedding)

        # Mock semantic search results
        similar_chunks = [
            (
                {
                    "id": "chunk1",
                    "content": "AI research content",
                    "keyword": "artificial intelligence",
                    "metadata": {
                        "source_type": "research_summary",
                    },
                },
                0.9,  # High similarity
            ),
            (
                {
                    "id": "chunk2",
                    "content": "AI findings",
                    "keyword": "artificial intelligence",
                    "metadata": {
                        "source_type": "academic_source",
                        "source_title": "AI Study",
                        "source_url": "https://example.edu/ai",
                        "domain": ".edu",
                        "credibility_score": 0.9,
                    },
                },
                0.85,
            ),
        ]
        storage.search_similar_chunks = AsyncMock(return_value=similar_chunks)

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock research function
                        research_func = AsyncMock(return_value=sample_research_findings)

                        result = await retriever.retrieve_or_research(
                            "AI research", research_func
                        )

                        # Should get semantic cache hit
                        # The keyword is the original search term, not the matched keyword
                        assert result.keyword == "AI research"
                        assert retriever.stats.semantic_hits == 1
                        assert retriever.stats.exact_hits == 0
                        research_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_with_cache_miss(
        self, mock_rag_config, mock_components, sample_research_findings
    ):
        """Test retrieval with cache miss."""
        processor, embeddings, storage = mock_components

        # No cache hits
        storage.get_cached_response = AsyncMock(return_value=None)
        storage.search_similar_chunks = AsyncMock(return_value=[])
        storage.warm_pool = AsyncMock(return_value=True)

        # Mock embedding generation
        embeddings.generate_embedding = AsyncMock(
            return_value=Mock(embedding=[0.1] * 1536)
        )

        # Mock storage operations
        embeddings.generate_embeddings = AsyncMock(
            return_value=[Mock(embedding=[0.1] * 1536)]
        )
        storage.store_research_chunks = AsyncMock(return_value=["chunk1", "chunk2"])
        storage.store_cache_entry = AsyncMock(return_value="cache123")

        # Mock processing
        processor.process_research_findings = Mock(
            return_value=[Mock(content="Test chunk")]
        )

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock research function
                        research_func = AsyncMock(return_value=sample_research_findings)

                        result = await retriever.retrieve_or_research(
                            "new topic", research_func
                        )

                        # Should call research function
                        assert result == sample_research_findings
                        assert retriever.stats.cache_misses == 1
                        research_func.assert_called_once()
                        storage.store_research_chunks.assert_called_once()
                        storage.store_cache_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_with_dict_response(self, mock_rag_config, mock_components):
        """Test retrieval when research function returns dict."""
        processor, embeddings, storage = mock_components

        # No cache hits
        storage.get_cached_response = AsyncMock(return_value=None)
        storage.search_similar_chunks = AsyncMock(return_value=[])
        storage.warm_pool = AsyncMock(return_value=True)
        storage.store_research_chunks = AsyncMock(return_value=["chunk1"])
        storage.store_cache_entry = AsyncMock(return_value="cache123")

        embeddings.generate_embedding = AsyncMock(
            return_value=Mock(embedding=[0.1] * 1536)
        )
        embeddings.generate_embeddings = AsyncMock(
            return_value=[Mock(embedding=[0.1] * 1536)]
        )

        processor.process_research_findings = Mock(return_value=[Mock(content="Test")])

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock research function returning dict
                        dict_response = {
                            "query": "test query",
                            "answer": "Test answer about the topic.",
                            "results": [
                                {
                                    "title": "Test Result",
                                    "url": "https://example.edu/test",
                                    "content": "Test content",
                                }
                            ],
                        }
                        research_func = AsyncMock(return_value=dict_response)

                        result = await retriever.retrieve_or_research(
                            "test topic", research_func
                        )

                        # Should convert dict to ResearchFindings
                        assert isinstance(result, ResearchFindings)
                        assert result.keyword == "test topic"
                        assert len(result.academic_sources) == 1
                        assert result.academic_sources[0].domain == ".edu"

    @pytest.mark.asyncio
    async def test_retrieve_with_error(self, mock_rag_config, mock_components):
        """Test retrieval with error handling."""
        processor, embeddings, storage = mock_components
        storage.warm_pool = AsyncMock(return_value=True)

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock to raise error after pool warming
                        retriever._check_exact_cache = AsyncMock(
                            side_effect=Exception("Database error")
                        )

                        research_func = AsyncMock()

                        with pytest.raises(Exception, match="Database error"):
                            await retriever.retrieve_or_research("test", research_func)

                        assert retriever.stats.errors == 1

    def test_reconstruct_findings_from_cache(self, mock_rag_config, mock_cache_entry):
        """Test reconstructing findings from cache entry."""
        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            retriever = ResearchRetriever()

            findings = retriever._reconstruct_findings_from_cache(mock_cache_entry)

            assert isinstance(findings, ResearchFindings)
            assert findings.keyword == "artificial intelligence"
            assert findings.research_summary == "AI is transforming technology"
            assert len(findings.academic_sources) == 1
            assert findings.academic_sources[0].title == "AI Study"

    def test_reconstruct_findings_from_chunks(self, mock_rag_config):
        """Test reconstructing findings from semantic search chunks."""
        chunks = [
            (
                {
                    "content": "Research summary content",
                    "metadata": {"source_type": "research_summary"},
                },
                0.9,
            ),
            (
                {
                    "content": "Finding 1\n\nFinding 2",
                    "metadata": {"source_type": "main_findings"},
                },
                0.85,
            ),
            (
                {
                    "content": "stat1: 90%\nstat2: 80%",
                    "metadata": {"source_type": "statistics"},
                },
                0.8,
            ),
        ]

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            retriever = ResearchRetriever()

            findings = retriever._reconstruct_findings_from_chunks(
                chunks, "test keyword"
            )

            assert findings.keyword == "test keyword"
            assert findings.research_summary == "Research summary content"
            assert len(findings.main_findings) == 2
            assert len(findings.key_statistics) == 2

    def test_extract_domain(self, mock_rag_config):
        """Test domain extraction from URLs."""
        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            retriever = ResearchRetriever()

            assert retriever._extract_domain("https://example.edu/page") == ".edu"
            assert retriever._extract_domain("https://example.gov/page") == ".gov"
            assert retriever._extract_domain("https://example.org/page") == ".org"
            assert retriever._extract_domain("https://example.ac.uk/page") == ".ac.uk"
            assert retriever._extract_domain("https://example.com/page") == ".com"

    def test_calculate_credibility(self, mock_rag_config):
        """Test credibility score calculation."""
        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            retriever = ResearchRetriever()

            # Test .edu domain
            result = {"content": "Regular content"}
            score = retriever._calculate_credibility(".edu", result)
            assert score == 0.9

            # Test with research keywords
            result = {"content": "This peer-reviewed study shows..."}
            score = retriever._calculate_credibility(".com", result)
            assert score == 0.6  # Base 0.5 + 0.1 boost

    @pytest.mark.asyncio
    async def test_warm_cache(self, mock_rag_config, mock_components):
        """Test cache warming functionality."""
        processor, embeddings, storage = mock_components
        storage.get_cached_response = AsyncMock(return_value=None)
        storage.search_similar_chunks = AsyncMock(return_value=[])
        storage.warm_pool = AsyncMock(return_value=True)
        storage.store_research_chunks = AsyncMock(return_value=["chunk1"])
        storage.store_cache_entry = AsyncMock(return_value="cache123")

        embeddings.generate_embedding = AsyncMock(
            return_value=Mock(embedding=[0.1] * 1536)
        )
        embeddings.generate_embeddings = AsyncMock(
            return_value=[Mock(embedding=[0.1] * 1536)]
        )

        processor.process_research_findings = Mock(return_value=[Mock(content="Test")])

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Mock research function
                        research_func = AsyncMock(
                            return_value=Mock(
                                keyword="test",
                                research_summary="Summary",
                                academic_sources=[],
                                key_statistics=[],
                                research_gaps=[],
                                main_findings=[],
                                total_sources_analyzed=0,
                                search_query_used="test",
                                research_timestamp=datetime.now(),
                            )
                        )

                        keywords = ["keyword1", "keyword2"]
                        results = await retriever.warm_cache(keywords, research_func)

                        assert results["successful"] == 2
                        assert results["failed"] == 0
                        assert results["already_cached"] == 0

    @pytest.mark.asyncio
    async def test_warm_cache_with_existing(self, mock_rag_config, mock_components):
        """Test cache warming with already cached keywords."""
        processor, embeddings, storage = mock_components

        # First keyword already cached
        storage.get_cached_response = AsyncMock(side_effect=[{"cached": True}, None])
        storage.warm_pool = AsyncMock(return_value=True)

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        research_func = AsyncMock()

                        keywords = ["cached_keyword", "new_keyword"]
                        with patch.object(
                            retriever, "retrieve_or_research"
                        ) as mock_retrieve:
                            mock_retrieve.return_value = Mock()

                            results = await retriever.warm_cache(
                                keywords, research_func
                            )

                            assert results["already_cached"] == 1
                            assert results["successful"] == 1

    def test_get_instance_statistics(self, mock_rag_config, mock_components):
        """Test getting instance statistics."""
        processor, embeddings, storage = mock_components
        embeddings.get_statistics = Mock(
            return_value={"cache_hits": 10, "total_cost": 0.05}
        )

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Add some stats
                        retriever.stats.record_exact_hit(0.1)
                        retriever.stats.record_semantic_hit(0.2)

                        stats = retriever.get_instance_statistics()

                        assert "retriever" in stats
                        assert "embeddings" in stats
                        assert stats["retriever"]["exact_hits"] == 1
                        assert stats["retriever"]["semantic_hits"] == 1

    def test_get_class_statistics(self, mock_rag_config):
        """Test getting class-level statistics."""
        # Clear any existing instances
        ResearchRetriever._instances.clear()

        # No instances
        assert ResearchRetriever.get_statistics() is None

        # Create instances
        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor"):
                with patch("rag.retriever.EmbeddingGenerator"):
                    with patch("rag.retriever.VectorStorage"):
                        retriever1 = ResearchRetriever()
                        retriever2 = ResearchRetriever()

                        # Add stats to instances
                        retriever1.stats.exact_hits = 5
                        retriever1.stats.semantic_hits = 3
                        retriever1.stats.cache_misses = 2
                        retriever1.stats.total_requests = 10
                        retriever1.stats.cache_response_times = [0.1, 0.2]

                        retriever2.stats.exact_hits = 2
                        retriever2.stats.semantic_hits = 1
                        retriever2.stats.cache_misses = 2
                        retriever2.stats.total_requests = 5
                        retriever2.stats.api_response_times = [1.0, 2.0]

                        combined = ResearchRetriever.get_statistics()

                        assert combined["cache_requests"] == 15
                        assert combined["exact_hits"] == 7
                        assert combined["semantic_hits"] == 4
                        assert combined["cache_misses"] == 4
                        assert combined["hit_rate"] == 11 / 15

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_rag_config, mock_components):
        """Test cleanup functionality."""
        processor, embeddings, storage = mock_components
        storage.close = AsyncMock()

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        await retriever.cleanup()

                        storage.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_below_threshold(
        self, mock_rag_config, mock_components
    ):
        """Test semantic search with results below threshold."""
        processor, embeddings, storage = mock_components

        # Mock low similarity results
        similar_chunks = [
            (
                {
                    "content": "Unrelated content",
                    "keyword": "different topic",
                    "metadata": {},
                },
                0.5,  # Below threshold
            )
        ]

        storage.get_cached_response = AsyncMock(return_value=None)
        storage.search_similar_chunks = AsyncMock(return_value=similar_chunks)
        storage.warm_pool = AsyncMock(return_value=True)

        embeddings.generate_embedding = AsyncMock(
            return_value=Mock(embedding=[0.1] * 1536)
        )

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        result = await retriever._semantic_search("test keyword")

                        assert result is None

    @pytest.mark.asyncio
    async def test_store_research_with_no_chunks(
        self, mock_rag_config, mock_components, sample_research_findings
    ):
        """Test storing research when no chunks are generated."""
        processor, embeddings, storage = mock_components

        # No chunks generated
        processor.process_research_findings = Mock(return_value=[])

        with patch("rag.retriever.get_rag_config", return_value=mock_rag_config):
            with patch("rag.retriever.TextProcessor", return_value=processor):
                with patch("rag.retriever.EmbeddingGenerator", return_value=embeddings):
                    with patch("rag.retriever.VectorStorage", return_value=storage):
                        retriever = ResearchRetriever()

                        # Should not raise, just log warning
                        await retriever._store_research(sample_research_findings)

                        # Should not call storage methods
                        embeddings.generate_embeddings.assert_not_called()
                        storage.store_research_chunks.assert_not_called()
