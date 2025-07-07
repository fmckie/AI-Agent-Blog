"""
Tests for connection pool warming functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag.retriever import ResearchRetriever
from rag.storage import VectorStorage


@pytest.mark.asyncio
async def test_storage_warm_pool():
    """Test that VectorStorage.warm_pool establishes connections."""
    # Create storage instance
    storage = VectorStorage()

    # Mock the connection pool
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    # Create a mock connection context manager
    class MockConnectionContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch get_connection to return our mock
    with patch.object(storage, "get_connection", return_value=MockConnectionContext()):
        with patch.object(storage, "_get_pool", return_value=mock_pool):
            # Call warm_pool
            result = await storage.warm_pool()

            # Verify it succeeded
            assert result is True

            # Verify connections were tested
            assert mock_conn.fetchval.call_count >= 1
            mock_conn.fetchval.assert_called_with("SELECT 1")


@pytest.mark.asyncio
async def test_storage_warm_pool_handles_errors():
    """Test that warm_pool handles errors gracefully."""
    # Create storage instance
    storage = VectorStorage()

    # Mock _get_pool to raise an error
    with patch.object(storage, "_get_pool", side_effect=Exception("Connection failed")):
        # Call warm_pool
        result = await storage.warm_pool()

        # Should return False on error
        assert result is False


@pytest.mark.asyncio
async def test_retriever_warms_pool_on_first_use():
    """Test that ResearchRetriever warms pool on first retrieval."""
    # Create retriever instance
    retriever = ResearchRetriever()

    # Mock the storage warm_pool method
    retriever.storage.warm_pool = AsyncMock(return_value=True)

    # Mock other methods to avoid actual database calls
    retriever._check_exact_cache = AsyncMock(return_value=None)
    retriever._semantic_search = AsyncMock(return_value=None)

    # Create a mock research function
    mock_research = AsyncMock(
        return_value={
            "query": "test",
            "results": [],
            "answer": "test answer",
            "processing_metadata": {},
        }
    )

    # Mock the storage method
    retriever._store_new_research = AsyncMock()

    # First call should warm the pool
    assert retriever._pool_warmed is False

    try:
        await retriever.retrieve_or_research("test keyword", mock_research)
    except Exception:
        # We expect this to fail due to mocking, but pool should still be warmed
        pass

    # Verify pool was warmed
    retriever.storage.warm_pool.assert_called_once()
    assert retriever._pool_warmed is True

    # Reset the mock
    retriever.storage.warm_pool.reset_mock()

    # Second call should not warm again
    try:
        await retriever.retrieve_or_research("another keyword", mock_research)
    except Exception:
        pass

    # Verify pool was not warmed again
    retriever.storage.warm_pool.assert_not_called()


@pytest.mark.asyncio
async def test_retriever_continues_on_warming_failure():
    """Test that retriever continues even if pool warming fails."""
    # Create retriever instance
    retriever = ResearchRetriever()

    # Mock the storage warm_pool to fail
    retriever.storage.warm_pool = AsyncMock(side_effect=Exception("Warming failed"))

    # Mock other methods
    retriever._check_exact_cache = AsyncMock(return_value=None)
    retriever._semantic_search = AsyncMock(return_value=None)

    # Create a mock research function
    mock_research = AsyncMock(
        return_value={
            "query": "test",
            "results": [],
            "answer": "test answer",
            "processing_metadata": {},
        }
    )

    retriever._store_new_research = AsyncMock()

    # Should not raise an error even if warming fails
    assert retriever._pool_warmed is False

    try:
        await retriever.retrieve_or_research("test keyword", mock_research)
    except Exception:
        # Expected due to mocking
        pass

    # Verify pool warming was attempted but marked as done
    retriever.storage.warm_pool.assert_called_once()
    assert retriever._pool_warmed is True


@pytest.mark.asyncio
async def test_warm_pool_concurrency():
    """Test that warm_pool runs connections concurrently."""
    # Create storage instance with specific pool size
    storage = VectorStorage()
    storage.config.connection_pool_size = 5

    # Track connection order
    connection_order = []

    async def mock_fetchval(query):
        connection_order.append(asyncio.current_task())
        await asyncio.sleep(0.01)  # Simulate some work
        return 1

    # Mock connections
    mock_conn = AsyncMock()
    mock_conn.fetchval = mock_fetchval

    class MockConnectionContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch methods
    with patch.object(storage, "get_connection", return_value=MockConnectionContext()):
        with patch.object(storage, "_get_pool", return_value=AsyncMock()):
            # Call warm_pool
            await storage.warm_pool()

            # Should have warmed 3 connections (min of 3 or pool size)
            assert len(connection_order) == 3

            # Verify they ran concurrently (different tasks)
            assert len(set(connection_order)) == 3
