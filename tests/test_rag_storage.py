"""
Comprehensive test suite for RAG storage module.

This module tests the vector storage functionality including
connection pooling, chunk storage, retrieval, and cache management.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from supabase import Client

from rag.config import RAGConfig
from rag.embeddings import EmbeddingResult
from rag.processor import TextChunk
from rag.storage import VectorStorage


class TestVectorStorage:
    """Test suite for VectorStorage class."""

    @pytest.fixture
    def mock_rag_config(self):
        """Create mock RAG configuration."""
        config = Mock(spec=RAGConfig)
        config.supabase_url = "https://test.supabase.co"
        config.supabase_service_key = "test-service-key"
        config.database_url = "postgresql://test:test@localhost:5432/test"
        config.database_pool_url = None
        config.connection_pool_size = 10
        config.connection_timeout = 60
        config.cache_ttl_hours = 24
        config.similarity_threshold = 0.7
        return config

    @pytest.fixture
    def sample_chunks(self):
        """Create sample text chunks for testing."""
        return [
            TextChunk(
                content="This is the first chunk of content about AI and machine learning.",
                chunk_index=0,
                source_id="doc1",
                metadata={"type": "intro", "page": 1},
            ),
            TextChunk(
                content="The second chunk discusses deep learning architectures and neural networks.",
                chunk_index=1,
                source_id="doc1",
                metadata={"type": "technical", "page": 2},
            ),
            TextChunk(
                content="Final chunk covers practical applications and future research directions.",
                chunk_index=2,
                source_id="doc1",
                metadata={"type": "conclusion", "page": 3},
            ),
        ]

    @pytest.fixture
    def sample_embeddings(self):
        """Create sample embeddings for testing."""
        return [
            EmbeddingResult(
                text="This is the first chunk of content about AI and machine learning.",
                embedding=[0.1] * 1536,
                model="text-embedding-ada-002",
                token_count=10,
            ),
            EmbeddingResult(
                text="The second chunk discusses deep learning architectures and neural networks.",
                embedding=[0.2] * 1536,
                model="text-embedding-ada-002",
                token_count=12,
            ),
            EmbeddingResult(
                text="Final chunk covers practical applications and future research directions.",
                embedding=[0.3] * 1536,
                model="text-embedding-ada-002",
                token_count=15,
            ),
        ]

    @pytest.mark.asyncio
    async def test_vector_storage_initialization(self, mock_rag_config):
        """Test VectorStorage initialization."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)

            assert storage.config == mock_rag_config
            assert storage.supabase == mock_client
            assert storage._pool is None
            mock_create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_rag_config):
        """Test VectorStorage as async context manager."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            async with VectorStorage(mock_rag_config) as storage:
                assert storage.supabase == mock_client

    @pytest.mark.asyncio
    async def test_connection_pool_creation(self, mock_rag_config):
        """Test connection pool creation."""
        with patch("rag.storage.create_client"):
            # Need to properly create async context manager
            mock_pool = MagicMock()

            # Create the coroutine properly
            async def mock_create_pool(*args, **kwargs):
                return mock_pool

            with patch(
                "rag.storage.asyncpg.create_pool", side_effect=mock_create_pool
            ) as mock_create:
                storage = VectorStorage(mock_rag_config)
                pool = await storage._get_pool()

                assert pool == mock_pool
                mock_create.assert_called_once_with(
                    mock_rag_config.database_url,
                    min_size=2,
                    max_size=mock_rag_config.connection_pool_size,
                    max_inactive_connection_lifetime=300,
                    command_timeout=mock_rag_config.connection_timeout,
                    statement_cache_size=0,
                )

    @pytest.mark.asyncio
    async def test_store_research_chunks(
        self, mock_rag_config, sample_chunks, sample_embeddings
    ):
        """Test storing research chunks with embeddings."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_upsert = Mock()
            mock_execute = Mock()

            # Setup mock chain
            mock_execute.return_value = Mock(
                data=[{"id": f"chunk_{i}"} for i in range(3)]
            )
            mock_upsert.return_value = mock_execute
            mock_table.return_value.upsert = mock_upsert
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            result = await storage.store_research_chunks(
                sample_chunks, sample_embeddings, "test keyword"
            )

            assert len(result) == 3
            assert all(id.startswith("chunk_") for id in result)
            mock_client.table.assert_called_with("research_chunks")
            mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_research_chunks_validation(
        self, mock_rag_config, sample_chunks, sample_embeddings
    ):
        """Test validation in store_research_chunks."""
        with patch("rag.storage.create_client"):
            storage = VectorStorage(mock_rag_config)

            # Test mismatched lengths
            with pytest.raises(ValueError) as exc_info:
                await storage.store_research_chunks(
                    sample_chunks[:2], sample_embeddings, "test"
                )
            assert "must match" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_cache_entry(self, mock_rag_config):
        """Test storing cache entries."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_upsert = Mock()
            mock_execute = Mock()

            # Setup mock chain
            mock_execute.return_value = Mock(data=[{"id": "cache123"}])
            mock_upsert.return_value = mock_execute
            mock_table.return_value.upsert = mock_upsert
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            result = await storage.store_cache_entry(
                "test keyword",
                "Research summary",
                ["chunk1", "chunk2"],
                {"source_count": 5},
            )

            assert result == "cache123"
            mock_client.table.assert_called_with("cache_entries")

    @pytest.mark.asyncio
    async def test_search_similar_chunks(self, mock_rag_config):
        """Test vector similarity search."""
        with patch("rag.storage.create_client"):
            # Create a proper mock pool with async context manager
            mock_pool = MagicMock()
            mock_conn = MagicMock()

            # Create async context manager for pool.acquire()
            async def async_context_manager():
                return mock_conn

            mock_acquire = MagicMock()
            mock_acquire.__aenter__ = MagicMock(return_value=async_context_manager())
            mock_acquire.__aexit__ = MagicMock(
                return_value=asyncio.coroutine(lambda *args: None)()
            )
            mock_pool.acquire.return_value = mock_acquire

            # Mock query results
            async def mock_fetch(*args, **kwargs):
                return [
                    {
                        "id": "chunk1",
                        "content": "Test content",
                        "metadata": json.dumps({"type": "test"}),
                        "keyword": "test",
                        "chunk_index": 0,
                        "source_id": "doc1",
                        "created_at": datetime.now(timezone.utc),
                        "similarity": 0.95,
                    }
                ]

            mock_conn.fetch = mock_fetch

            # Create the coroutine for create_pool
            async def mock_create_pool(*args, **kwargs):
                return mock_pool

            with patch("rag.storage.asyncpg.create_pool", side_effect=mock_create_pool):
                storage = VectorStorage(mock_rag_config)
                results = await storage.search_similar_chunks([0.1] * 1536, limit=5)

                assert len(results) == 1
                assert results[0][1] == 0.95  # similarity score
                assert results[0][0]["id"] == "chunk1"

    @pytest.mark.asyncio
    async def test_get_cached_response(self, mock_rag_config):
        """Test retrieving cached responses."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_select = Mock()
            mock_eq = Mock()
            mock_execute = Mock()
            mock_update = Mock()

            # Setup mock chain for select
            cache_entry = {
                "id": "cache123",
                "keyword": "test",
                "research_summary": "Summary",
                "chunk_ids": ["chunk1", "chunk2"],
                "hit_count": 5,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
            }
            mock_execute.return_value = Mock(data=[cache_entry])
            mock_eq.return_value = mock_execute
            mock_select.return_value.eq = mock_eq
            mock_table.return_value.select = mock_select

            # Setup mock for update
            mock_update_execute = Mock(return_value=Mock(data=[]))
            mock_update_eq = Mock(return_value=mock_update_execute)
            mock_update.return_value.eq = mock_update_eq
            mock_table.return_value.update = mock_update

            # Setup mock for chunks
            mock_in = Mock()
            mock_in_execute = Mock(return_value=Mock(data=[]))
            mock_in.return_value = mock_in_execute
            mock_select.return_value.in_ = mock_in

            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            result = await storage.get_cached_response("test")

            assert result is not None
            assert result["id"] == "cache123"
            assert result["keyword"] == "test"

    @pytest.mark.asyncio
    async def test_get_cached_response_expired(self, mock_rag_config):
        """Test handling of expired cache entries."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_select = Mock()
            mock_eq = Mock()
            mock_execute = Mock()

            # Setup expired cache entry
            cache_entry = {
                "id": "cache123",
                "expires_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ).isoformat(),
            }
            mock_execute.return_value = Mock(data=[cache_entry])
            mock_eq.return_value = mock_execute
            mock_select.return_value.eq = mock_eq
            mock_table.return_value.select = mock_select
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            result = await storage.get_cached_response("test")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_statistics(self, mock_rag_config):
        """Test getting storage statistics."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_select = Mock()
            mock_execute = Mock()

            # Mock chunks count
            mock_execute.return_value = Mock(
                data=[{"id": f"chunk{i}"} for i in range(10)]
            )
            mock_select.return_value = mock_execute
            mock_table.return_value.select = mock_select

            # Mock cache entries with hit counts
            cache_data = [{"hit_count": 5}, {"hit_count": 10}, {"hit_count": 3}]
            mock_select.return_value.execute.side_effect = [
                Mock(data=[{"id": f"chunk{i}"} for i in range(10)]),
                Mock(data=[{"id": f"cache{i}"} for i in range(3)]),
                Mock(data=cache_data),
            ]

            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            stats = await storage.get_statistics()

            assert stats["total_chunks"] == 10
            assert stats["total_cache_entries"] == 3
            assert stats["total_cache_hits"] == 18
            assert stats["average_hits_per_entry"] == 6.0

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self, mock_rag_config):
        """Test cleaning up expired cache entries."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_delete = Mock()
            mock_lt = Mock()
            mock_execute = Mock()

            # Setup mock chain
            mock_execute.return_value = Mock(
                data=[{"id": f"expired{i}"} for i in range(5)]
            )
            mock_lt.return_value = mock_execute
            mock_delete.return_value.lt = mock_lt
            mock_table.return_value.delete = mock_delete
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            deleted_count = await storage.cleanup_expired_cache()

            assert deleted_count == 5
            mock_client.table.assert_called_with("cache_entries")
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_search(self, mock_rag_config):
        """Test bulk similarity search."""
        with patch("rag.storage.create_client"):
            storage = VectorStorage(mock_rag_config)

            # Mock search_similar_chunks
            with patch.object(storage, "search_similar_chunks") as mock_search:
                mock_search.return_value = [({"id": "chunk1", "content": "Test"}, 0.9)]

                embeddings = [[0.1] * 1536, [0.2] * 1536]
                results = await storage.bulk_search(embeddings, limit_per_query=3)

                assert len(results) == 2
                assert mock_search.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_cache_by_age(self, mock_rag_config):
        """Test cache cleanup by age."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_delete = Mock()
            mock_lt = Mock()
            mock_execute = Mock()

            # Setup mock chains for both tables
            mock_execute.return_value = Mock(data=[{"id": f"old{i}"} for i in range(3)])
            mock_lt.return_value = mock_execute
            mock_delete.return_value.lt = mock_lt
            mock_table.return_value.delete = mock_delete

            # Different return values for each table
            mock_table.side_effect = [
                Mock(
                    delete=Mock(
                        return_value=Mock(
                            lt=Mock(
                                return_value=Mock(
                                    execute=Mock(
                                        return_value=Mock(
                                            data=[{"id": f"cache{i}"} for i in range(3)]
                                        )
                                    )
                                )
                            )
                        )
                    )
                ),
                Mock(
                    delete=Mock(
                        return_value=Mock(
                            lt=Mock(
                                return_value=Mock(
                                    execute=Mock(
                                        return_value=Mock(
                                            data=[{"id": f"chunk{i}"} for i in range(5)]
                                        )
                                    )
                                )
                            )
                        )
                    )
                ),
            ]

            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            deleted_count = await storage.cleanup_cache(older_than_days=7)

            assert deleted_count == 8  # 3 cache entries + 5 chunks

    @pytest.mark.asyncio
    async def test_cleanup_cache_by_keyword(self, mock_rag_config):
        """Test cache cleanup by keyword."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()

            # Setup different mocks for different tables
            cache_table_mock = Mock()
            chunks_table_mock = Mock()

            # Cache entries deletion
            cache_delete = Mock()
            cache_eq = Mock(
                return_value=Mock(
                    execute=Mock(return_value=Mock(data=[{"id": "cache1"}]))
                )
            )
            cache_delete.return_value.eq = cache_eq
            cache_table_mock.delete = Mock(return_value=cache_delete)

            # Chunks deletion
            chunks_delete = Mock()
            chunks_ilike = Mock(
                return_value=Mock(
                    execute=Mock(
                        return_value=Mock(data=[{"id": f"chunk{i}"} for i in range(3)])
                    )
                )
            )
            chunks_delete.return_value.ilike = chunks_ilike
            chunks_table_mock.delete = Mock(return_value=chunks_delete)

            # Return different table mocks based on call
            mock_table.side_effect = [cache_table_mock, chunks_table_mock]
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            deleted_count = await storage.cleanup_cache(keyword="test keyword")

            assert deleted_count == 4  # 1 cache entry + 3 chunks

    @pytest.mark.asyncio
    async def test_warm_pool(self, mock_rag_config):
        """Test connection pool warming."""
        with patch("rag.storage.create_client"):
            with patch("rag.storage.asyncpg.create_pool") as mock_create_pool:
                mock_pool = AsyncMock()
                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(return_value=1)
                mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
                mock_create_pool.return_value = mock_pool

                storage = VectorStorage(mock_rag_config)
                result = await storage.warm_pool()

                assert result is True
                assert mock_conn.fetchval.call_count >= 3

    @pytest.mark.asyncio
    async def test_warm_pool_failure(self, mock_rag_config):
        """Test connection pool warming failure."""
        with patch("rag.storage.create_client"):
            with patch("rag.storage.asyncpg.create_pool") as mock_create_pool:
                mock_create_pool.side_effect = Exception("Connection failed")

                storage = VectorStorage(mock_rag_config)
                result = await storage.warm_pool()

                assert result is False

    @pytest.mark.asyncio
    async def test_generate_chunk_id(self, mock_rag_config, sample_chunks):
        """Test chunk ID generation."""
        with patch("rag.storage.create_client"):
            storage = VectorStorage(mock_rag_config)

            # Test with source_id
            chunk_id = storage._generate_chunk_id(sample_chunks[0])
            assert "doc1_0_" in chunk_id

            # Test without source_id
            chunk = TextChunk(
                content="Test content",
                chunk_index=5,
                source_id=None,
                metadata={},
            )
            chunk_id = storage._generate_chunk_id(chunk)
            assert chunk_id.startswith("chunk_5_")

    @pytest.mark.asyncio
    async def test_generate_cache_key(self, mock_rag_config):
        """Test cache key generation."""
        with patch("rag.storage.create_client"):
            storage = VectorStorage(mock_rag_config)

            # Test normalization
            key1 = storage._generate_cache_key("Test Keyword")
            key2 = storage._generate_cache_key("  test keyword  ")
            assert key1 == key2

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, mock_rag_config):
        """Test comprehensive cache statistics."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()

            # Mock responses for different queries
            chunks_data = [
                {"content": "x" * 100, "keyword": "test1"},
                {"content": "y" * 200, "keyword": "test2"},
            ]
            cache_data = [
                {
                    "keyword": "test1",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ]

            mock_select = Mock()
            mock_select.return_value.execute.side_effect = [
                Mock(data=chunks_data),  # chunks query
                Mock(data=cache_data),  # cache query
            ]
            mock_table.return_value.select = mock_select
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            stats = await storage.get_cache_stats()

            assert stats["research_chunks"] == 2
            assert stats["cache_entries"] == 1
            assert stats["unique_keywords"] == 1
            assert stats["avg_chunk_size"] == 150

    @pytest.mark.asyncio
    async def test_get_keyword_distribution(self, mock_rag_config):
        """Test keyword distribution analysis."""
        with patch("rag.storage.create_client") as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_select = Mock()
            mock_execute = Mock()

            # Mock keyword data
            chunks_data = [
                {"keyword": "AI"},
                {"keyword": "AI"},
                {"keyword": "ML"},
                {"keyword": "AI"},
                {"keyword": "ML"},
                {"keyword": "DL"},
            ]
            mock_execute.return_value = Mock(data=chunks_data)
            mock_select.return_value = mock_execute
            mock_table.return_value.select = mock_select
            mock_client.table = mock_table
            mock_create_client.return_value = mock_client

            storage = VectorStorage(mock_rag_config)
            distribution = await storage.get_keyword_distribution(limit=2)

            assert len(distribution) == 2
            assert distribution[0] == ("AI", 3)
            assert distribution[1] == ("ML", 2)

    @pytest.mark.asyncio
    async def test_search_similar_empty_results(self, mock_rag_config):
        """Test search similar with no results."""
        with patch("rag.storage.create_client"):
            storage = VectorStorage(mock_rag_config)

            with patch.object(storage, "search_similar_chunks") as mock_search:
                mock_search.return_value = []

                results = await storage.search_similar([0.1] * 1536)

                assert results == []

    @pytest.mark.asyncio
    async def test_close_connection_pool(self, mock_rag_config):
        """Test closing the connection pool."""
        with patch("rag.storage.create_client"):
            with patch("rag.storage.asyncpg.create_pool") as mock_create_pool:
                mock_pool = AsyncMock()
                mock_pool.close = AsyncMock()
                mock_create_pool.return_value = mock_pool

                storage = VectorStorage(mock_rag_config)

                # Get pool to create it
                await storage._get_pool()
                assert storage._pool is not None

                # Close it
                await storage.close()
                mock_pool.close.assert_called_once()
                assert storage._pool is None
