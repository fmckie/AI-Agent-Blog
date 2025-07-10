"""
Unit tests for EnhancedVectorStorage class.

Tests all methods in the enhanced storage system including:
- Research source management
- Crawl result storage
- Source relationship mapping
- Advanced search methods
- Batch operations
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from models import (
    AcademicSource,
    ExtractedContent,
    CrawledPage,
    StoredSource,
    SourceRelationship,
    SearchResult,
)
from rag.enhanced_storage import EnhancedVectorStorage


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock()
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-key"
    config.connection_pool_size = 5
    config.connection_timeout = 30
    config.cache_ttl_hours = 24
    config.similarity_threshold = 0.7
    return config


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    client = Mock()

    # Mock table method to return self for chaining
    table_mock = Mock()
    table_mock.insert = Mock(return_value=table_mock)
    table_mock.upsert = Mock(return_value=table_mock)
    table_mock.update = Mock(return_value=table_mock)
    table_mock.select = Mock(return_value=table_mock)
    table_mock.delete = Mock(return_value=table_mock)
    table_mock.eq = Mock(return_value=table_mock)
    table_mock.neq = Mock(return_value=table_mock)
    table_mock.gte = Mock(return_value=table_mock)
    table_mock.lte = Mock(return_value=table_mock)
    table_mock.gt = Mock(return_value=table_mock)
    table_mock.lt = Mock(return_value=table_mock)
    table_mock.ilike = Mock(return_value=table_mock)
    table_mock.order = Mock(return_value=table_mock)
    table_mock.limit = Mock(return_value=table_mock)
    table_mock.execute = Mock()

    client.table = Mock(return_value=table_mock)
    client.rpc = Mock()

    return client


@pytest.fixture
def sample_academic_source():
    """Create sample academic source."""
    return AcademicSource(
        title="Understanding Deep Learning",
        url="https://example.edu/deep-learning",
        authors=["Dr. Jane Smith", "Prof. John Doe"],
        publication_date="2024-01-15",
        journal_name="AI Research Journal",
        excerpt="Deep learning has revolutionized artificial intelligence...",
        domain=".edu",
        credibility_score=0.95,
        source_type="journal",
    )


@pytest.fixture
async def storage(mock_config, mock_supabase):
    """Create EnhancedVectorStorage instance with mocks."""
    with patch("rag.enhanced_storage.create_client", return_value=mock_supabase):
        with patch("rag.enhanced_storage.get_rag_config", return_value=mock_config):
            storage = EnhancedVectorStorage()
            # Mock the pool to avoid connection attempts
            storage._pool = AsyncMock()
            storage._get_pool = AsyncMock(return_value=storage._pool)
            yield storage


class TestResearchSourceManagement:
    """Test research source management methods."""

    @pytest.mark.asyncio
    async def test_store_research_source_basic(
        self, storage, mock_supabase, sample_academic_source
    ):
        """Test basic source storage without full content."""
        # Setup mock response
        source_id = str(uuid4())
        mock_supabase.table().upsert().execute.return_value = Mock(
            data=[{"id": source_id}]
        )

        # Store source
        result = await storage.store_research_source(
            sample_academic_source, generate_embedding=False
        )

        # Verify
        assert result == source_id
        mock_supabase.table.assert_called_with("research_sources")
        mock_supabase.table().upsert.assert_called_once()

        # Check data passed
        call_args = mock_supabase.table().upsert.call_args[0][0]
        assert call_args["url"] == sample_academic_source.url
        assert call_args["title"] == sample_academic_source.title
        assert (
            call_args["credibility_score"] == sample_academic_source.credibility_score
        )

    @pytest.mark.asyncio
    async def test_store_research_source_with_content(
        self, storage, mock_supabase, sample_academic_source
    ):
        """Test source storage with full content and embedding generation."""
        # Setup mocks
        source_id = str(uuid4())
        mock_supabase.table().upsert().execute.return_value = Mock(
            data=[{"id": source_id}]
        )

        # Mock embedding queue
        mock_supabase.table().insert().execute.return_value = Mock(
            data=[{"id": "queue-id"}]
        )

        # Mock chunk processing
        with patch.object(
            storage, "_process_and_store_chunks", return_value=["chunk1", "chunk2"]
        ):
            # Store source with content
            full_content = "This is the full article content about deep learning..."
            result = await storage.store_research_source(
                sample_academic_source,
                full_content=full_content,
                generate_embedding=True,
            )

        # Verify
        assert result == source_id
        # Should have called embedding queue
        assert mock_supabase.table.call_count >= 2  # sources + queue

    @pytest.mark.asyncio
    async def test_update_source_credibility(self, storage, mock_supabase):
        """Test updating source credibility score."""
        # Setup mocks
        source_id = str(uuid4())
        mock_supabase.table().select().eq().execute.return_value = Mock(
            data=[{"metadata": json.dumps({"original": "data"})}]
        )
        mock_supabase.table().update().eq().execute.return_value = Mock(
            data=[{"id": source_id}]
        )

        # Update credibility
        result = await storage.update_source_credibility(
            source_id, 0.85, "Updated based on peer review"
        )

        # Verify
        assert result is True
        mock_supabase.table().update.assert_called_once()

        # Check update data
        update_args = mock_supabase.table().update.call_args[0][0]
        assert update_args["credibility_score"] == 0.85
        assert "metadata" in update_args

    @pytest.mark.asyncio
    async def test_get_source_by_url(self, storage, mock_supabase):
        """Test retrieving source by URL."""
        # Setup mocks
        source_id = str(uuid4())
        url = "https://example.edu/test"

        mock_supabase.table().select().eq().execute.return_value = Mock(
            data=[
                {
                    "id": source_id,
                    "url": url,
                    "title": "Test Article",
                    "credibility_score": 0.9,
                }
            ]
        )

        # Mock relationships
        with patch.object(storage, "_get_source_relationships", return_value=[]):
            # Get source
            result = await storage.get_source_by_url(url)

        # Verify
        assert result is not None
        assert result["id"] == source_id
        assert result["url"] == url
        assert "relationships" in result
        assert "chunk_count" in result
        assert "embedding_status" in result


class TestCrawlResultStorage:
    """Test crawl result storage methods."""

    @pytest.mark.asyncio
    async def test_store_crawl_results(self, storage, mock_supabase):
        """Test storing crawl results."""
        # Setup crawl data
        parent_url = "https://example.edu"
        crawl_data = {
            "results": [
                {
                    "url": "https://example.edu/page1",
                    "title": "Page 1",
                    "content": "Content of page 1",
                    "depth": 1,
                },
                {
                    "url": "https://example.edu/page2",
                    "title": "Page 2",
                    "content": "Content of page 2",
                    "depth": 1,
                },
            ]
        }

        # Mock responses
        source_ids = [str(uuid4()) for _ in crawl_data["results"]]
        mock_supabase.table().upsert().execute.side_effect = [
            Mock(data=[{"id": sid}]) for sid in source_ids
        ]

        # Mock parent source lookup
        parent_id = str(uuid4())
        with patch.object(storage, "get_source_by_url", return_value={"id": parent_id}):
            with patch.object(storage, "create_source_relationship", return_value=True):
                # Store crawl results
                result = await storage.store_crawl_results(
                    crawl_data, parent_url, "deep learning"
                )

        # Verify
        assert len(result) == 2
        assert all(isinstance(sid, str) for sid in result)

    @pytest.mark.asyncio
    async def test_get_crawl_hierarchy(self, storage, mock_supabase):
        """Test retrieving crawl hierarchy."""
        # Setup mocks
        root_url = "https://example.edu"
        root_id = str(uuid4())

        # Mock root source
        with patch.object(
            storage,
            "get_source_by_url",
            return_value={"id": root_id, "title": "Root Page", "url": root_url},
        ):
            # Mock relationships
            mock_supabase.table().select().eq().execute.return_value = Mock(
                data=[
                    {
                        "source_id": "child1",
                        "research_sources": {
                            "url": "https://example.edu/child1",
                            "title": "Child 1",
                        },
                    }
                ]
            )

            # Get hierarchy
            result = await storage.get_crawl_hierarchy(root_url)

        # Verify
        assert result["url"] == root_url
        assert result["title"] == "Root Page"
        assert "children" in result


class TestSourceRelationshipMapping:
    """Test source relationship mapping methods."""

    @pytest.mark.asyncio
    async def test_create_source_relationship(self, storage, mock_supabase):
        """Test creating relationship between sources."""
        # Setup
        source_id = str(uuid4())
        related_id = str(uuid4())

        mock_supabase.table().upsert().execute.return_value = Mock(
            data=[{"id": "rel-id"}]
        )

        # Create relationship
        result = await storage.create_source_relationship(
            source_id, related_id, "cites", similarity=0.85
        )

        # Verify
        assert result is True
        mock_supabase.table().upsert.assert_called_once()

        # Check data
        rel_data = mock_supabase.table().upsert.call_args[0][0]
        assert rel_data["source_id"] == source_id
        assert rel_data["related_source_id"] == related_id
        assert rel_data["relationship_type"] == "cites"
        assert rel_data["similarity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_calculate_source_similarities(self, storage, mock_supabase):
        """Test calculating similarities with other sources."""
        # Setup
        source_id = str(uuid4())

        # Mock RPC response
        mock_supabase.rpc.return_value.execute.return_value = Mock(
            data=[
                {
                    "related_source_id": "related1",
                    "title": "Related Article 1",
                    "url": "https://example.edu/related1",
                    "avg_similarity": 0.82,
                },
                {
                    "related_source_id": "related2",
                    "title": "Related Article 2",
                    "url": "https://example.edu/related2",
                    "avg_similarity": 0.75,
                },
            ]
        )

        # Mock relationship creation
        with patch.object(storage, "create_source_relationship", return_value=True):
            # Calculate similarities
            result = await storage.calculate_source_similarities(
                source_id, threshold=0.7
            )

        # Verify
        assert result == 2  # Created 2 relationships
        mock_supabase.rpc.assert_called_once_with(
            "find_related_sources",
            {
                "source_id_input": source_id,
                "similarity_threshold": 0.7,
                "max_results": 10,
            },
        )

    @pytest.mark.asyncio
    async def test_get_related_sources(self, storage, mock_supabase):
        """Test getting related sources."""
        # Setup
        source_id = str(uuid4())

        mock_supabase.table().select().eq().execute.return_value = Mock(
            data=[
                {
                    "id": "rel1",
                    "relationship_type": "cites",
                    "similarity_score": None,
                    "research_sources": {
                        "id": "source1",
                        "title": "Cited Source",
                        "url": "https://example.edu/cited",
                    },
                },
                {
                    "id": "rel2",
                    "relationship_type": "similar",
                    "similarity_score": 0.85,
                    "research_sources": {
                        "id": "source2",
                        "title": "Similar Source",
                        "url": "https://example.edu/similar",
                    },
                },
            ]
        )

        # Get related sources
        result = await storage.get_related_sources(source_id)

        # Verify
        assert len(result) == 2
        assert result[0]["relationship_type"] == "cites"
        assert result[1]["similarity_score"] == 0.85


class TestAdvancedSearchMethods:
    """Test advanced search methods."""

    @pytest.mark.asyncio
    async def test_search_by_criteria(self, storage, mock_supabase):
        """Test multi-criteria search."""
        # Setup mock response
        mock_supabase.table().select().gte().order().limit().execute.return_value = (
            Mock(
                data=[
                    {
                        "id": "source1",
                        "title": "High Quality Source",
                        "credibility_score": 0.95,
                        "domain": ".edu",
                    }
                ]
            )
        )

        # Search
        result = await storage.search_by_criteria(
            domain=".edu", min_credibility=0.8, limit=10
        )

        # Verify
        assert len(result) == 1
        assert result[0]["credibility_score"] == 0.95
        mock_supabase.table().select.assert_called_with("*")
        mock_supabase.table().select().gte.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_relationships(self, storage, mock_supabase):
        """Test semantic search with relationships."""
        # Mock vector search results
        with patch.object(
            storage,
            "search_similar_chunks",
            return_value=[
                ({"source_id": "source1", "content": "Content 1"}, 0.9),
                ({"source_id": "source2", "content": "Content 2"}, 0.85),
            ],
        ):
            # Mock related sources
            with patch.object(
                storage,
                "get_related_sources",
                return_value=[
                    {
                        "source": {"title": "Related 1"},
                        "relationship_type": "cites",
                        "similarity_score": None,
                    }
                ],
            ):
                # Search
                query_embedding = [0.1] * 1536
                result = await storage.search_with_relationships(
                    query_embedding, include_related=True
                )

        # Verify
        assert len(result) == 2
        assert "primary" in result[0]
        assert "related" in result[0]
        assert result[0]["similarity"] == 0.9

    @pytest.mark.asyncio
    async def test_hybrid_search(self, storage, mock_supabase):
        """Test hybrid keyword + vector search."""
        # Mock keyword search
        with patch.object(
            storage,
            "search_by_criteria",
            return_value=[{"id": "source1", "title": "Keyword Match"}],
        ):
            # Mock vector search
            with patch.object(
                storage,
                "search_similar_chunks",
                return_value=[
                    ({"source_id": "source2", "content": "Vector Match"}, 0.88),
                    ({"source_id": "source1", "content": "Both Match"}, 0.75),
                ],
            ):
                # Perform hybrid search
                result = await storage.hybrid_search(
                    "deep learning",
                    [0.1] * 1536,
                    weights={"keyword": 0.4, "vector": 0.6},
                )

        # Verify
        assert len(result) >= 2
        # source1 should have highest score (matches both)
        assert "combined_score" in result[0]


class TestBatchOperations:
    """Test batch operations."""

    @pytest.mark.asyncio
    async def test_batch_store_sources(
        self, storage, mock_supabase, sample_academic_source
    ):
        """Test batch storing multiple sources."""
        # Create multiple sources
        sources = [
            sample_academic_source,
            AcademicSource(
                title="Another Article",
                url="https://example.org/article2",
                excerpt="Another excerpt",
                domain=".org",
                credibility_score=0.8,
                source_type="web",
            ),
        ]

        # Mock responses
        mock_supabase.table().upsert().execute.return_value = Mock(
            data=[{"id": f"source{i}"} for i in range(len(sources))]
        )

        # Store batch
        result = await storage.batch_store_sources(sources, generate_embeddings=False)

        # Verify
        assert len(result) == 2
        mock_supabase.table().upsert.assert_called_once()

        # Check batch data
        batch_data = mock_supabase.table().upsert.call_args[0][0]
        assert len(batch_data) == 2
        assert batch_data[0]["url"] == sources[0].url
        assert batch_data[1]["url"] == sources[1].url

    @pytest.mark.asyncio
    async def test_batch_process_embeddings(self, storage, mock_supabase):
        """Test batch processing embedding queue."""
        # Setup queue items
        queue_items = [
            {
                "id": "queue1",
                "source_id": "source1",
                "status": "pending",
                "research_sources": {
                    "id": "source1",
                    "full_content": "Content to embed",
                },
            }
        ]

        mock_supabase.table().select().eq().order().limit().execute.return_value = Mock(
            data=queue_items
        )

        # Mock chunk processing
        with patch.object(
            storage, "_process_and_store_chunks", return_value=["chunk1"]
        ):
            # Process batch
            result = await storage.batch_process_embeddings(batch_size=5)

        # Verify
        assert result == 1
        # Should update status to processing then completed
        assert mock_supabase.table().update.call_count >= 2


class TestHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_queue_for_embeddings(self, storage, mock_supabase):
        """Test queuing source for embeddings."""
        # Setup
        source_id = str(uuid4())
        mock_supabase.table().insert().execute.return_value = Mock(
            data=[{"id": "queue-id"}]
        )

        # Queue
        result = await storage._queue_for_embeddings(source_id)

        # Verify
        assert result is True
        mock_supabase.table().insert.assert_called_once()

        # Check data
        queue_data = mock_supabase.table().insert.call_args[0][0]
        assert queue_data["source_id"] == source_id
        assert queue_data["status"] == "pending"

    def test_extract_domain(self, storage):
        """Test domain extraction from URL."""
        # Test various URLs
        assert storage._extract_domain("https://example.edu/page") == ".edu"
        assert storage._extract_domain("http://site.org") == ".org"
        assert storage._extract_domain("https://commercial.com/product") == ".com"
        assert storage._extract_domain("invalid-url") == ".com"  # Default

    def test_calculate_crawl_credibility(self, storage):
        """Test crawl credibility calculation."""
        # Test with minimal content
        page_data = {"content": "Short"}
        assert storage._calculate_crawl_credibility(page_data) == 0.5

        # Test with good content
        page_data = {"title": "Good Article", "content": "a" * 6000}  # Long content
        score = storage._calculate_crawl_credibility(page_data)
        assert score == 0.8  # Max score for crawled

        # Test medium content
        page_data = {"title": "Medium Article", "content": "b" * 2000}
        score = storage._calculate_crawl_credibility(page_data)
        assert 0.5 < score < 0.8


@pytest.mark.asyncio
async def test_error_handling(storage, mock_supabase):
    """Test error handling across methods."""
    # Simulate database error
    mock_supabase.table().upsert().execute.side_effect = Exception("Database error")

    # Test source storage error
    source = AcademicSource(
        title="Test",
        url="https://test.com",
        excerpt="Test",
        domain=".com",
        credibility_score=0.5,
    )

    with pytest.raises(Exception):
        await storage.store_research_source(source)

    # Test that other methods handle errors gracefully
    mock_supabase.table().select().eq().execute.side_effect = Exception("Query error")

    result = await storage.get_source_by_url("https://test.com")
    assert result is None  # Should return None on error
