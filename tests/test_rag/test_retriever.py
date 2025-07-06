"""
Tests for the Research Retriever module.

This test suite comprehensively tests the ResearchRetriever class,
including cache lookup, semantic search, and storage operations.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from models import AcademicSource, ResearchFindings
from rag.retriever import ResearchRetriever, RetrievalStatistics


class TestRetrievalStatistics:
    """Test the RetrievalStatistics class."""

    def test_initialization(self):
        """Test statistics initialization."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Verify initial values
        assert stats.exact_hits == 0
        assert stats.semantic_hits == 0
        assert stats.cache_misses == 0
        assert stats.total_requests == 0
        assert stats.errors == 0
        assert stats.cache_response_times == []
        assert stats.api_response_times == []

    def test_record_exact_hit(self):
        """Test recording an exact cache hit."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Record an exact hit
        response_time = 0.1
        stats.record_exact_hit(response_time)

        # Verify counters updated
        assert stats.exact_hits == 1
        assert stats.total_requests == 1
        assert stats.cache_response_times == [response_time]

    def test_record_semantic_hit(self):
        """Test recording a semantic cache hit."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Record a semantic hit
        response_time = 0.2
        stats.record_semantic_hit(response_time)

        # Verify counters updated
        assert stats.semantic_hits == 1
        assert stats.total_requests == 1
        assert stats.cache_response_times == [response_time]

    def test_record_cache_miss(self):
        """Test recording a cache miss."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Record a cache miss
        response_time = 1.5
        stats.record_cache_miss(response_time)

        # Verify counters updated
        assert stats.cache_misses == 1
        assert stats.total_requests == 1
        assert stats.api_response_times == [response_time]

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Initially, hit rate should be 0
        assert stats.cache_hit_rate == 0.0

        # Record some hits and misses
        stats.record_exact_hit(0.1)
        stats.record_semantic_hit(0.2)
        stats.record_cache_miss(1.0)

        # Hit rate should be 66.7% (2 hits out of 3 requests)
        assert pytest.approx(stats.cache_hit_rate, 0.1) == 66.7

    def test_average_response_times(self):
        """Test average response time calculations."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Initially, averages should be 0
        assert stats.average_cache_response_time == 0.0
        assert stats.average_api_response_time == 0.0

        # Record some response times
        stats.record_exact_hit(0.1)
        stats.record_semantic_hit(0.3)
        stats.record_cache_miss(2.0)

        # Check averages
        assert stats.average_cache_response_time == 0.2  # (0.1 + 0.3) / 2
        assert stats.average_api_response_time == 2.0

    def test_get_summary(self):
        """Test statistics summary generation."""
        # Create statistics instance
        stats = RetrievalStatistics()

        # Record various events
        stats.record_exact_hit(0.1)
        stats.record_semantic_hit(0.2)
        stats.record_cache_miss(1.0)
        stats.record_error()

        # Get summary
        summary = stats.get_summary()

        # Verify summary contents
        assert summary["total_requests"] == 4
        assert summary["exact_hits"] == 1
        assert summary["semantic_hits"] == 1
        assert summary["cache_misses"] == 1
        assert summary["errors"] == 1
        assert "cache_hit_rate" in summary
        assert "avg_cache_response_ms" in summary
        assert "avg_api_response_ms" in summary


@pytest.mark.asyncio
class TestResearchRetriever:
    """Test the ResearchRetriever class."""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        # Mock the component dependencies
        with (
            patch("rag.retriever.get_rag_config") as mock_config,
            patch("rag.retriever.TextProcessor") as mock_processor,
            patch("rag.retriever.EmbeddingGenerator") as mock_embeddings,
            patch("rag.retriever.VectorStorage") as mock_storage,
        ):

            # Configure mocks
            mock_config.return_value.cache_similarity_threshold = 0.8

            yield {
                "config": mock_config,
                "processor": mock_processor,
                "embeddings": mock_embeddings,
                "storage": mock_storage,
            }

    @pytest.fixture
    def sample_findings(self):
        """Create sample research findings."""
        # Create sample academic sources
        sources = [
            AcademicSource(
                title="Study on Climate Change",
                url="https://example.edu/study1",
                excerpt="Climate change impacts...",
                domain=".edu",
                credibility_score=0.9,
                authors=["Dr. Smith", "Dr. Jones"],
                journal_name="Nature Climate",
            ),
            AcademicSource(
                title="Environmental Research",
                url="https://example.gov/research",
                excerpt="Environmental factors...",
                domain=".gov",
                credibility_score=0.95,
            ),
        ]

        # Create research findings
        return ResearchFindings(
            keyword="climate change",
            research_summary="Comprehensive research on climate change impacts.",
            academic_sources=sources,
            key_statistics=["Global temperature increased by 1.1 degrees C"],
            main_findings=["Climate change is accelerating"],
            total_sources_analyzed=10,
            search_query_used="climate change research",
        )

    async def test_initialization(self, mock_components):
        """Test retriever initialization."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Verify components were initialized
        assert retriever.config is not None
        assert retriever.processor is not None
        assert retriever.embeddings is not None
        assert retriever.storage is not None
        assert retriever.stats is not None

    async def test_exact_cache_hit(self, mock_components, sample_findings):
        """Test exact cache hit scenario."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock storage to return cached response
        cache_entry = {
            "keyword": "climate change",
            "research_summary": sample_findings.research_summary,
            "metadata": {
                "key_statistics": sample_findings.key_statistics,
                "main_findings": sample_findings.main_findings,
                "total_sources_analyzed": sample_findings.total_sources_analyzed,
            },
            "chunks": [],
        }
        retriever.storage.get_cached_response = AsyncMock(return_value=cache_entry)

        # Mock research function (should not be called)
        research_function = AsyncMock()

        # Call retrieve_or_research
        result = await retriever.retrieve_or_research(
            "climate change", research_function
        )

        # Verify exact cache was checked
        retriever.storage.get_cached_response.assert_called_once_with("climate change")

        # Verify research function was not called
        research_function.assert_not_called()

        # Verify statistics
        assert retriever.stats.exact_hits == 1
        assert retriever.stats.cache_misses == 0

    async def test_semantic_cache_hit(self, mock_components, sample_findings):
        """Test semantic cache hit scenario."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock exact cache miss
        retriever.storage.get_cached_response = AsyncMock(return_value=None)

        # Mock embedding generation
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        retriever.embeddings.generate_embedding = AsyncMock(return_value=mock_embedding)

        # Mock semantic search results
        similar_chunks = [
            (
                {
                    "keyword": "global warming",
                    "content": "Research summary about global warming...",
                    "metadata": {"source_type": "research_summary"},
                },
                0.85,
            ),
            (
                {
                    "keyword": "global warming",
                    "content": "Study on Climate Change\n\nClimate change impacts...",
                    "metadata": {
                        "source_type": "academic_source",
                        "source_title": "Study on Climate Change",
                        "source_url": "https://example.edu/study1",
                        "domain": ".edu",
                        "credibility_score": 0.9,
                    },
                },
                0.82,
            ),
        ]
        retriever.storage.search_similar_chunks = AsyncMock(return_value=similar_chunks)

        # Mock research function (should not be called)
        research_function = AsyncMock()

        # Call retrieve_or_research
        result = await retriever.retrieve_or_research(
            "climate crisis", research_function
        )

        # Verify semantic search was performed
        retriever.embeddings.generate_embedding.assert_called_once_with(
            "climate crisis"
        )
        retriever.storage.search_similar_chunks.assert_called_once()

        # Verify research function was not called
        research_function.assert_not_called()

        # Verify statistics
        assert retriever.stats.semantic_hits == 1
        assert retriever.stats.cache_misses == 0

    async def test_cache_miss(self, mock_components, sample_findings):
        """Test cache miss scenario."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock cache misses
        retriever.storage.get_cached_response = AsyncMock(return_value=None)
        retriever.storage.search_similar_chunks = AsyncMock(return_value=[])

        # Mock embedding generation for semantic search
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        retriever.embeddings.generate_embedding = AsyncMock(return_value=mock_embedding)

        # Mock research function to return findings
        research_function = AsyncMock(return_value=sample_findings)

        # Mock storage operations
        retriever.processor.process_research_findings = Mock(
            return_value=[Mock(content="chunk1")]
        )
        retriever.embeddings.generate_embeddings = AsyncMock(
            return_value=[mock_embedding]
        )
        retriever.storage.store_research_chunks = AsyncMock(return_value=["chunk_id_1"])
        retriever.storage.store_cache_entry = AsyncMock(return_value="cache_id_1")

        # Call retrieve_or_research
        result = await retriever.retrieve_or_research("new topic", research_function)

        # Verify research function was called
        research_function.assert_called_once()

        # Verify storage was called
        retriever.processor.process_research_findings.assert_called_once()
        retriever.storage.store_research_chunks.assert_called_once()
        retriever.storage.store_cache_entry.assert_called_once()

        # Verify statistics
        assert retriever.stats.cache_misses == 1
        assert retriever.stats.exact_hits == 0
        assert retriever.stats.semantic_hits == 0

    async def test_dict_to_findings_conversion(self, mock_components):
        """Test conversion from dictionary to ResearchFindings."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Create dictionary response (like from Tavily)
        dict_response = {
            "query": "artificial intelligence",
            "answer": "AI is transforming technology. Machine learning advances rapidly.",
            "results": [
                {
                    "title": "AI Research Paper",
                    "url": "https://example.edu/ai-paper",
                    "content": "Artificial intelligence research findings...",
                },
                {
                    "title": "Government AI Report",
                    "url": "https://example.gov/ai-report",
                    "content": "Government study on AI impacts...",
                },
            ],
        }

        # Convert to findings
        findings = retriever._dict_to_findings(dict_response, "artificial intelligence")

        # Verify conversion
        assert findings.keyword == "artificial intelligence"
        assert findings.research_summary == dict_response["answer"]
        assert len(findings.academic_sources) == 2
        assert findings.academic_sources[0].title == "AI Research Paper"
        assert findings.academic_sources[0].domain == ".edu"
        # .edu domain with research content gets 0.9 + 0.1 = 1.0 (capped at 1.0)
        assert findings.academic_sources[0].credibility_score == 1.0
        assert len(findings.main_findings) > 0

    async def test_error_handling(self, mock_components):
        """Test error handling in retrieval."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock all components to raise an error at the end
        retriever.storage.get_cached_response = AsyncMock(
            side_effect=Exception("Database error")
        )
        retriever.embeddings.generate_embedding = AsyncMock(
            side_effect=Exception("Embedding error")
        )

        # Mock research function to also fail
        research_function = AsyncMock(side_effect=Exception("Research API error"))

        # Call should raise error since all paths fail
        with pytest.raises(Exception) as exc_info:
            await retriever.retrieve_or_research("test", research_function)

        # Verify error was recorded
        assert retriever.stats.errors == 1
        assert "Research API error" in str(exc_info.value)

    async def test_warm_cache(self, mock_components, sample_findings):
        """Test cache warming functionality."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock cache checks - first check returns None, second and third return cached
        # (since retrieve_or_research calls _check_exact_cache internally)
        cache_responses = [
            None,
            None,
            {
                "keyword": "topic2",
                "research_summary": "cached",
                "metadata": {},
                "chunks": [],
            },
        ]
        retriever.storage.get_cached_response = AsyncMock(side_effect=cache_responses)

        # Mock the full retrieval process for uncached keyword
        mock_embedding = Mock(embedding=[0.1] * 1536)
        retriever.embeddings.generate_embedding = AsyncMock(return_value=mock_embedding)
        retriever.storage.search_similar_chunks = AsyncMock(return_value=[])
        retriever.embeddings.generate_embeddings = AsyncMock(
            return_value=[mock_embedding]
        )
        retriever.processor.process_research_findings = Mock(
            return_value=[Mock(content="chunk")]
        )
        retriever.storage.store_research_chunks = AsyncMock(return_value=["chunk_id"])
        retriever.storage.store_cache_entry = AsyncMock(return_value="cache_id")

        # Mock research function
        research_function = AsyncMock(return_value=sample_findings)

        # Warm cache with keywords
        keywords = ["topic1", "topic2"]
        results = await retriever.warm_cache(keywords, research_function)

        # Verify results
        assert results["successful"] == 1
        assert results["already_cached"] == 1
        assert results["failed"] == 0
        assert results["keywords"]["topic1"] == "success"
        assert results["keywords"]["topic2"] == "already_cached"

    async def test_cleanup(self, mock_components):
        """Test cleanup functionality."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock storage cleanup
        retriever.storage.close = AsyncMock()

        # Call cleanup
        await retriever.cleanup()

        # Verify storage was closed
        retriever.storage.close.assert_called_once()

    def test_extract_domain(self, mock_components):
        """Test domain extraction from URLs."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Test various URLs
        assert retriever._extract_domain("https://example.edu/paper") == ".edu"
        assert retriever._extract_domain("https://example.gov/report") == ".gov"
        assert retriever._extract_domain("https://example.org/study") == ".org"
        assert retriever._extract_domain("https://example.ac.uk/research") == ".ac.uk"
        assert retriever._extract_domain("https://example.com/article") == ".com"

    def test_calculate_credibility(self, mock_components):
        """Test credibility score calculation."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Test base scores by domain
        assert retriever._calculate_credibility(".edu", {}) == 0.9
        assert retriever._calculate_credibility(".gov", {}) == 0.9
        assert retriever._calculate_credibility(".org", {}) == 0.7
        assert retriever._calculate_credibility(".com", {}) == 0.5

        # Test boost for research-related content
        result_with_research = {"content": "This peer-reviewed study shows..."}
        assert retriever._calculate_credibility(".com", result_with_research) == 0.6

    async def test_semantic_search_below_threshold(self, mock_components):
        """Test semantic search when similarity is below threshold."""
        # Create retriever instance
        retriever = ResearchRetriever()

        # Mock exact cache miss
        retriever.storage.get_cached_response = AsyncMock(return_value=None)

        # Mock embedding generation
        mock_embedding = Mock(embedding=[0.1] * 1536)
        retriever.embeddings.generate_embedding = AsyncMock(return_value=mock_embedding)

        # Mock semantic search with low similarity scores
        similar_chunks = [
            ({"keyword": "unrelated", "content": "Something different"}, 0.5),
            ({"keyword": "unrelated", "content": "Not similar"}, 0.4),
        ]
        retriever.storage.search_similar_chunks = AsyncMock(return_value=similar_chunks)

        # Mock research function
        research_function = AsyncMock(return_value=Mock())

        # Mock storage for new research
        retriever.processor.process_research_findings = Mock(return_value=[])

        # Call retrieve_or_research
        await retriever.retrieve_or_research("specific topic", research_function)

        # Verify research function was called (cache miss)
        research_function.assert_called_once()

        # Verify statistics show cache miss
        assert retriever.stats.cache_misses == 1
        assert retriever.stats.semantic_hits == 0
