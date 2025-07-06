"""
Tests for the Vector Storage module.

This test suite covers all storage operations including
chunk storage, similarity search, caching, and cleanup.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from rag.embeddings import EmbeddingResult
from rag.processor import TextChunk
from rag.storage import VectorStorage


class TestVectorStorage:
    """Test the VectorStorage class."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        # Create mock client
        client = MagicMock()

        # Mock table method to return chainable object
        mock_table = MagicMock()
        client.table.return_value = mock_table

        # Setup chainable methods
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.lt.return_value = mock_table

        # Mock execute to return data
        mock_table.execute.return_value = MagicMock(data=[])

        return client

    @pytest.fixture
    async def mock_connection_pool(self):
        """Create a mock connection pool."""
        # Create mock pool
        pool = MagicMock()

        # Mock connection
        mock_conn = AsyncMock()

        # Setup context manager for acquire
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)
        pool.acquire.return_value = mock_acquire

        return pool, mock_conn

    @pytest.fixture
    def storage_with_mocks(self, mock_supabase_client):
        """Create storage with mocked Supabase client."""
        # Patch the create_client function
        with patch("rag.storage.create_client", return_value=mock_supabase_client):
            storage = VectorStorage()
            return storage

    @pytest.fixture
    def sample_chunks(self):
        """Create sample text chunks for testing."""
        return [
            TextChunk(
                content="Machine learning algorithms",
                metadata={"source": "paper1", "page": 1},
                chunk_index=0,
                source_id="doc1",
            ),
            TextChunk(
                content="Deep learning neural networks",
                metadata={"source": "paper2", "page": 2},
                chunk_index=1,
                source_id="doc2",
            ),
        ]

    @pytest.fixture
    def sample_embeddings(self):
        """Create sample embeddings for testing."""
        return [
            EmbeddingResult(
                text="Machine learning algorithms",
                embedding=[0.1] * 1536,  # Simplified embedding
                model="test-model",
                token_count=3,
            ),
            EmbeddingResult(
                text="Deep learning neural networks",
                embedding=[0.2] * 1536,  # Simplified embedding
                model="test-model",
                token_count=4,
            ),
        ]

    def test_storage_initialization(self, storage_with_mocks):
        """Test storage initialization."""
        # Verify storage is initialized
        assert storage_with_mocks.supabase is not None
        assert storage_with_mocks._pool is None  # Pool created on demand
        assert storage_with_mocks._pool_lock is not None

    def test_generate_chunk_id(self, storage_with_mocks, sample_chunks):
        """Test chunk ID generation."""
        # Test with source_id
        chunk_id = storage_with_mocks._generate_chunk_id(sample_chunks[0])
        assert chunk_id.startswith("doc1_0_")
        assert len(chunk_id) > 10

        # Test without source_id
        chunk_no_source = TextChunk(
            content="Test content", metadata={}, chunk_index=5, source_id=None
        )
        chunk_id = storage_with_mocks._generate_chunk_id(chunk_no_source)
        assert chunk_id.startswith("chunk_5_")

    def test_generate_cache_key(self, storage_with_mocks):
        """Test cache key generation."""
        # Test key generation
        key1 = storage_with_mocks._generate_cache_key("Machine Learning")
        key2 = storage_with_mocks._generate_cache_key("machine learning")
        key3 = storage_with_mocks._generate_cache_key("  Machine Learning  ")

        # Should normalize to same key
        assert key1 == key2 == key3
        assert len(key1) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_get_pool(self, storage_with_mocks):
        """Test connection pool creation."""
        # Mock asyncpg.create_pool
        mock_pool = MagicMock()

        with patch(
            "rag.storage.asyncpg.create_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            # Get pool
            pool = await storage_with_mocks._get_pool()

            # Verify pool created
            assert pool == mock_pool
            assert storage_with_mocks._pool == mock_pool

            # Get pool again (should return same instance)
            pool2 = await storage_with_mocks._get_pool()
            assert pool2 == mock_pool

    @pytest.mark.asyncio
    async def test_get_connection(self, storage_with_mocks, mock_connection_pool):
        """Test getting a database connection."""
        pool, mock_conn = mock_connection_pool

        # Mock the _get_pool method
        storage_with_mocks._get_pool = AsyncMock(return_value=pool)

        # Use connection
        async with storage_with_mocks.get_connection() as conn:
            assert conn == mock_conn

        # Verify pool methods called
        pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, storage_with_mocks):
        """Test closing the connection pool."""
        # Create mock pool
        mock_pool = AsyncMock()
        storage_with_mocks._pool = mock_pool

        # Close storage
        await storage_with_mocks.close()

        # Verify pool closed
        mock_pool.close.assert_called_once()
        assert storage_with_mocks._pool is None

    @pytest.mark.asyncio
    async def test_store_research_chunks(
        self, storage_with_mocks, sample_chunks, sample_embeddings
    ):
        """Test storing research chunks."""
        # Setup mock response
        mock_data = [{"id": "chunk1"}, {"id": "chunk2"}]
        storage_with_mocks.supabase.table().upsert().execute.return_value = MagicMock(
            data=mock_data
        )

        # Store chunks
        result = await storage_with_mocks.store_research_chunks(
            sample_chunks, sample_embeddings, "test keyword"
        )

        # Verify results
        assert result == ["chunk1", "chunk2"]

        # Verify Supabase called correctly
        storage_with_mocks.supabase.table.assert_called_with("research_chunks")
        assert storage_with_mocks.supabase.table().upsert.call_count >= 1

    @pytest.mark.asyncio
    async def test_store_research_chunks_mismatch(
        self, storage_with_mocks, sample_chunks, sample_embeddings
    ):
        """Test storing chunks with mismatched embeddings."""
        # Remove one embedding
        embeddings = sample_embeddings[:1]

        # Should raise RetryError due to retry logic wrapping ValueError
        from tenacity import RetryError

        with pytest.raises(RetryError):
            await storage_with_mocks.store_research_chunks(
                sample_chunks, embeddings, "test"
            )

    @pytest.mark.asyncio
    async def test_store_cache_entry(self, storage_with_mocks):
        """Test storing a cache entry."""
        # Setup mock response
        mock_data = [{"id": "cache123"}]
        storage_with_mocks.supabase.table().upsert().execute.return_value = MagicMock(
            data=mock_data
        )

        # Store cache entry
        result = await storage_with_mocks.store_cache_entry(
            keyword="machine learning",
            research_summary="Summary of ML research",
            chunk_ids=["chunk1", "chunk2"],
            metadata={"source_count": 5},
        )

        # Verify result
        assert result == "cache123"

        # Verify Supabase called
        storage_with_mocks.supabase.table.assert_called_with("cache_entries")
        assert storage_with_mocks.supabase.table().upsert.call_count >= 1

        # Check the data passed
        call_args = storage_with_mocks.supabase.table().upsert.call_args[0][0]
        assert call_args["keyword"] == "machine learning"
        assert call_args["research_summary"] == "Summary of ML research"
        assert call_args["chunk_ids"] == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_search_similar_chunks(
        self, storage_with_mocks, mock_connection_pool
    ):
        """Test similarity search."""
        pool, mock_conn = mock_connection_pool

        # Mock the _get_pool method
        storage_with_mocks._get_pool = AsyncMock(return_value=pool)

        # Mock query results
        mock_rows = [
            {
                "id": "chunk1",
                "content": "Machine learning content",
                "metadata": json.dumps({"source": "paper1"}),
                "keyword": "ML",
                "chunk_index": 0,
                "source_id": "doc1",
                "created_at": "2024-01-01T00:00:00Z",
                "similarity": 0.95,
            },
            {
                "id": "chunk2",
                "content": "Deep learning content",
                "metadata": {"source": "paper2"},  # Already dict
                "keyword": "DL",
                "chunk_index": 1,
                "source_id": "doc2",
                "created_at": "2024-01-01T00:00:00Z",
                "similarity": 0.85,
            },
        ]
        mock_conn.fetch.return_value = mock_rows

        # Perform search
        query_embedding = [0.15] * 1536
        results = await storage_with_mocks.search_similar_chunks(
            query_embedding, limit=10, similarity_threshold=0.8
        )

        # Verify results
        assert len(results) == 2
        assert results[0][1] == 0.95  # Similarity score
        assert results[0][0]["content"] == "Machine learning content"
        assert results[1][1] == 0.85

        # Verify query executed
        mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_response(self, storage_with_mocks):
        """Test retrieving cached response."""
        # Setup mock cache entry
        cache_entry = {
            "id": "cache123",
            "keyword": "machine learning",
            "research_summary": "ML summary",
            "chunk_ids": ["chunk1", "chunk2"],
            "hit_count": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "metadata": {},
        }

        # Setup mock to return cache entry first, then chunks
        mock_execute = MagicMock()

        # First call returns cache entry
        mock_execute.side_effect = [
            MagicMock(data=[cache_entry]),  # First select (cache entry)
            MagicMock(data=[]),  # Update call
            MagicMock(
                data=[
                    {"id": "chunk1", "content": "Content 1"},
                    {"id": "chunk2", "content": "Content 2"},
                ]
            ),  # Second select (chunks)
        ]

        storage_with_mocks.supabase.table().select().eq().execute = mock_execute
        storage_with_mocks.supabase.table().update().eq().execute = mock_execute
        storage_with_mocks.supabase.table().select().in_().execute = mock_execute
        storage_with_mocks.supabase.table().execute = mock_execute

        # Get cached response
        result = await storage_with_mocks.get_cached_response("machine learning")

        # Verify result
        assert result is not None
        assert result["keyword"] == "machine learning"
        assert len(result["chunks"]) == 2

        # Verify cache hit update was called
        assert storage_with_mocks.supabase.table().update.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_cached_response_expired(self, storage_with_mocks):
        """Test retrieving expired cached response."""
        # Setup expired cache entry
        cache_entry = {
            "id": "cache123",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }

        # Mock the query
        storage_with_mocks.supabase.table().select().eq().execute.return_value = (
            MagicMock(data=[cache_entry])
        )

        # Get cached response
        result = await storage_with_mocks.get_cached_response("expired keyword")

        # Should return None for expired entry
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_not_found(self, storage_with_mocks):
        """Test retrieving non-existent cached response."""
        # Mock empty result
        storage_with_mocks.supabase.table().select().eq().execute.return_value = (
            MagicMock(data=[])
        )

        # Get cached response
        result = await storage_with_mocks.get_cached_response("not found")

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_statistics(self, storage_with_mocks):
        """Test getting storage statistics."""
        # Mock chunk count
        storage_with_mocks.supabase.table().select().execute.side_effect = [
            MagicMock(data=[{"id": "1"}, {"id": "2"}, {"id": "3"}]),  # chunks
            MagicMock(data=[{"id": "1"}, {"id": "2"}]),  # cache entries
            MagicMock(data=[{"hit_count": 10}, {"hit_count": 5}]),  # hit counts
        ]

        # Get statistics
        stats = await storage_with_mocks.get_statistics()

        # Verify statistics
        assert stats["total_chunks"] == 3
        assert stats["total_cache_entries"] == 2
        assert stats["total_cache_hits"] == 15
        assert stats["average_hits_per_entry"] == 7.5
        assert stats["storage_initialized"] is True

    @pytest.mark.asyncio
    async def test_get_statistics_error(self, storage_with_mocks):
        """Test getting statistics with error."""
        # Mock error
        storage_with_mocks.supabase.table().select().execute.side_effect = Exception(
            "DB error"
        )

        # Get statistics
        stats = await storage_with_mocks.get_statistics()

        # Should return error info
        assert "error" in stats
        assert stats["storage_initialized"] is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self, storage_with_mocks):
        """Test cleaning up expired cache entries."""
        # Mock deleted entries
        deleted_entries = [{"id": "1"}, {"id": "2"}]
        storage_with_mocks.supabase.table().delete().lt().execute.return_value = (
            MagicMock(data=deleted_entries)
        )

        # Cleanup cache
        count = await storage_with_mocks.cleanup_expired_cache()

        # Verify result
        assert count == 2

        # Verify delete called
        assert storage_with_mocks.supabase.table().delete.call_count >= 1

    @pytest.mark.asyncio
    async def test_bulk_search(self, storage_with_mocks, mock_connection_pool):
        """Test bulk similarity search."""
        pool, mock_conn = mock_connection_pool

        # Mock the _get_pool method
        storage_with_mocks._get_pool = AsyncMock(return_value=pool)

        # Mock query results for each search
        mock_conn.fetch.return_value = [
            {
                "id": "chunk1",
                "content": "Content",
                "metadata": {},
                "keyword": "test",
                "chunk_index": 0,
                "source_id": "doc1",
                "created_at": "2024-01-01",
                "similarity": 0.9,
            }
        ]

        # Perform bulk search
        embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        results = await storage_with_mocks.bulk_search(embeddings, limit_per_query=5)

        # Verify results
        assert len(results) == 3
        assert all(len(r) == 1 for r in results)  # Each has 1 result

        # Verify queries executed
        assert mock_conn.fetch.call_count == 3
