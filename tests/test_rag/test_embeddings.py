"""
Tests for the Embedding Generator module.

This test suite covers all aspects of embedding generation,
including API interactions, caching, batch processing, and cost tracking.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from rag.embeddings import (
    CostTracker,
    EmbeddingCache,
    EmbeddingGenerator,
    EmbeddingResult,
)


class TestEmbeddingResult:
    """Test the EmbeddingResult model."""

    def test_embedding_result_creation(self):
        """Test creating an embedding result."""
        # Create a sample embedding result
        result = EmbeddingResult(
            text="Sample text",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            model="text-embedding-3-small",
            token_count=3,
        )

        # Verify all fields
        assert result.text == "Sample text"
        assert result.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert result.model == "text-embedding-3-small"
        assert result.token_count == 3

    def test_to_numpy_conversion(self):
        """Test converting embedding to numpy array."""
        # Create result with embedding
        result = EmbeddingResult(
            text="Test",
            embedding=[1.0, 2.0, 3.0],
            model="test-model",
            token_count=1,
        )

        # Convert to numpy
        np_array = result.to_numpy()

        # Verify conversion
        assert isinstance(np_array, np.ndarray)
        assert np_array.shape == (3,)
        assert np.array_equal(np_array, np.array([1.0, 2.0, 3.0]))


class TestEmbeddingCache:
    """Test the embedding cache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        # Create cache
        cache = EmbeddingCache()

        # Verify initial state
        assert len(cache.cache) == 0
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        assert cache.hit_rate == 0.0

    def test_cache_hash_generation(self):
        """Test consistent hash generation."""
        # Create cache
        cache = EmbeddingCache()

        # Generate hashes for same text
        hash1 = cache.get_hash("Hello, world!")
        hash2 = cache.get_hash("Hello, world!")
        hash3 = cache.get_hash("Different text")

        # Verify consistency
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 produces 64 character hex string

    def test_cache_put_and_get(self):
        """Test storing and retrieving from cache."""
        # Create cache
        cache = EmbeddingCache()

        # Create sample result
        result = EmbeddingResult(
            text="Cached text",
            embedding=[0.1, 0.2],
            model="test",
            token_count=2,
        )

        # Store in cache
        cache.put("Cached text", result)

        # Retrieve from cache
        retrieved = cache.get("Cached text")

        # Verify retrieval
        assert retrieved is not None
        assert retrieved.text == "Cached text"
        assert cache.hit_count == 1
        assert cache.miss_count == 0

    def test_cache_miss(self):
        """Test cache miss behavior."""
        # Create cache
        cache = EmbeddingCache()

        # Try to get non-existent item
        result = cache.get("Not in cache")

        # Verify miss
        assert result is None
        assert cache.hit_count == 0
        assert cache.miss_count == 1

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        # Create cache
        cache = EmbeddingCache()

        # Create sample result
        result = EmbeddingResult(
            text="Test",
            embedding=[0.1],
            model="test",
            token_count=1,
        )

        # Simulate hits and misses
        cache.put("Test", result)
        cache.get("Test")  # Hit
        cache.get("Test")  # Hit
        cache.get("Miss1")  # Miss
        cache.get("Miss2")  # Miss

        # Verify hit rate (2 hits, 2 misses = 50%)
        assert cache.hit_count == 2
        assert cache.miss_count == 2
        assert cache.hit_rate == 50.0

    def test_cache_clear(self):
        """Test clearing the cache."""
        # Create cache and add items
        cache = EmbeddingCache()
        result = EmbeddingResult(
            text="Test",
            embedding=[0.1],
            model="test",
            token_count=1,
        )

        # Add items and generate statistics
        cache.put("Test1", result)
        cache.put("Test2", result)
        cache.get("Test1")
        cache.get("Miss")

        # Clear cache
        cache.clear()

        # Verify cleared state
        assert len(cache.cache) == 0
        assert cache.hit_count == 0
        assert cache.miss_count == 0


class TestCostTracker:
    """Test the cost tracking functionality."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker initialization."""
        # Create tracker
        tracker = CostTracker()

        # Verify initial state
        assert tracker.total_tokens == 0
        assert tracker.total_requests == 0
        assert tracker.total_cost == 0.0
        assert isinstance(tracker.start_time, datetime)

    def test_add_usage(self):
        """Test adding token usage."""
        # Create tracker
        tracker = CostTracker()

        # Add usage
        tracker.add_usage(100)
        tracker.add_usage(200)

        # Verify tracking
        assert tracker.total_tokens == 300
        assert tracker.total_requests == 2
        assert tracker.average_tokens_per_request == 150.0

    def test_cost_calculation(self):
        """Test cost calculation."""
        # Create tracker
        tracker = CostTracker()

        # Add 1 million tokens (should cost $0.02)
        tracker.add_usage(1_000_000)

        # Verify cost
        assert tracker.total_cost == 0.02

        # Add more tokens
        tracker.add_usage(500_000)

        # Verify updated cost
        assert tracker.total_cost == 0.03

    def test_average_tokens_with_no_requests(self):
        """Test average calculation with no requests."""
        # Create tracker
        tracker = CostTracker()

        # Verify average is 0
        assert tracker.average_tokens_per_request == 0.0


class TestEmbeddingGenerator:
    """Test the main EmbeddingGenerator class."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up environment variables for testing."""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-" + "x" * 30)
        monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key-" + "x" * 30)
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key-" + "x" * 30)

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        # Create mock client
        client = AsyncMock()

        # Mock embedding response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5])]

        # Set up async create method
        client.embeddings.create = AsyncMock(return_value=mock_response)

        return client

    @pytest.fixture
    def generator_with_mock(self, mock_openai_client):
        """Create generator with mocked OpenAI client."""
        # Create generator
        generator = EmbeddingGenerator()

        # Replace client with mock
        generator.client = mock_openai_client

        return generator

    def test_generator_initialization(self):
        """Test generator initialization."""
        # Create generator
        generator = EmbeddingGenerator()

        # Verify initialization
        assert generator.model == "text-embedding-3-small"
        assert isinstance(generator.cache, EmbeddingCache)
        assert isinstance(generator.cost_tracker, CostTracker)

    def test_token_estimation(self):
        """Test token count estimation."""
        # Create generator
        generator = EmbeddingGenerator()

        # Test various text lengths
        assert generator._estimate_tokens("") == 1  # Minimum 1 token
        assert generator._estimate_tokens("Hello") == 1  # 5 chars / 4 = 1.25 -> 1
        assert (
            generator._estimate_tokens("Hello, world!") == 3
        )  # 13 chars / 4 = 3.25 -> 3
        assert generator._estimate_tokens("A" * 100) == 25  # 100 chars / 4 = 25

    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, generator_with_mock):
        """Test generating a single embedding."""
        # Generate embedding
        result = await generator_with_mock.generate_embedding("Test text")

        # Verify result
        assert result.text == "Test text"
        assert result.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert result.model == "text-embedding-3-small"
        assert result.token_count == 2  # "Test text" = 9 chars / 4 = 2.25 -> 2

        # Verify API was called
        generator_with_mock.client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_with_cache(self, generator_with_mock):
        """Test cache behavior with embedding generation."""
        # Generate embedding first time
        result1 = await generator_with_mock.generate_embedding("Cached text")

        # Generate same embedding again (should use cache)
        result2 = await generator_with_mock.generate_embedding("Cached text")

        # Verify same result
        assert result1.text == result2.text
        assert result1.embedding == result2.embedding

        # Verify API was called only once
        assert generator_with_mock.client.embeddings.create.call_count == 1

        # Verify cache statistics
        assert generator_with_mock.cache.hit_count == 1
        assert generator_with_mock.cache.miss_count == 1

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, generator_with_mock):
        """Test handling of empty text."""
        # The retry logic will wrap our ValueError in a RetryError
        from tenacity import RetryError

        # Try to generate embedding for empty text
        with pytest.raises(RetryError):
            await generator_with_mock.generate_embedding("")

        # Try with whitespace only
        with pytest.raises(RetryError):
            await generator_with_mock.generate_embedding("   ")

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, generator_with_mock):
        """Test batch embedding generation."""
        # Generate embeddings for multiple texts
        texts = ["Text 1", "Text 2", "Text 3"]
        results = await generator_with_mock.generate_embeddings(texts, batch_size=2)

        # Verify results
        assert len(results) == 3
        assert results[0].text == "Text 1"
        assert results[1].text == "Text 2"
        assert results[2].text == "Text 3"

        # All should have same embedding (mock returns same)
        for result in results:
            assert result.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

    @pytest.mark.asyncio
    async def test_generate_embeddings_empty_list(self, generator_with_mock):
        """Test batch generation with empty list."""
        # Generate embeddings for empty list
        results = await generator_with_mock.generate_embeddings([])

        # Should return empty list
        assert results == []

    @pytest.mark.asyncio
    async def test_generate_embeddings_filters_empty(self, generator_with_mock):
        """Test batch generation filters empty texts."""
        # Generate embeddings with some empty texts
        texts = ["Valid", "", "  ", "Also valid"]
        results = await generator_with_mock.generate_embeddings(texts)

        # Should only have 2 results
        assert len(results) == 2
        assert results[0].text == "Valid"
        assert results[1].text == "Also valid"

    def test_calculate_similarity(self):
        """Test cosine similarity calculation."""
        # Create generator
        generator = EmbeddingGenerator()

        # Test identical vectors
        similarity = generator.calculate_similarity([1, 0, 0], [1, 0, 0])
        assert pytest.approx(similarity) == 1.0

        # Test orthogonal vectors
        similarity = generator.calculate_similarity([1, 0, 0], [0, 1, 0])
        assert pytest.approx(similarity) == 0.0

        # Test opposite vectors
        similarity = generator.calculate_similarity([1, 0, 0], [-1, 0, 0])
        assert pytest.approx(similarity) == -1.0

        # Test similar vectors
        similarity = generator.calculate_similarity([1, 0.5], [1, 0.6])
        assert 0.9 < similarity < 1.0

    def test_calculate_similarity_zero_vectors(self):
        """Test similarity with zero vectors."""
        # Create generator
        generator = EmbeddingGenerator()

        # Test with zero vectors
        similarity = generator.calculate_similarity([0, 0], [1, 1])
        assert similarity == 0.0

        similarity = generator.calculate_similarity([1, 1], [0, 0])
        assert similarity == 0.0

        similarity = generator.calculate_similarity([0, 0], [0, 0])
        assert similarity == 0.0

    def test_find_most_similar(self):
        """Test finding most similar embeddings."""
        # Create generator
        generator = EmbeddingGenerator()

        # Create query and candidate embeddings
        query_embedding = [1, 0, 0]
        candidates = [
            ("A", [1, 0, 0]),  # Identical
            ("B", [0.9, 0.1, 0]),  # Very similar
            ("C", [0, 1, 0]),  # Orthogonal
            ("D", [-1, 0, 0]),  # Opposite
            ("E", [0.7, 0.3, 0]),  # Somewhat similar
        ]

        # Find top 3 most similar
        results = generator.find_most_similar(query_embedding, candidates, top_k=3)

        # Verify results
        assert len(results) == 3
        assert results[0][0] == "A"  # Most similar
        assert results[1][0] == "B"  # Second most similar
        assert results[2][0] == "E"  # Third most similar

        # Verify similarity scores are descending
        assert results[0][1] > results[1][1] > results[2][1]

    def test_get_statistics(self, generator_with_mock):
        """Test getting usage statistics."""
        # Add some usage
        generator_with_mock.cost_tracker.add_usage(1000)
        generator_with_mock.cost_tracker.add_usage(2000)
        generator_with_mock.cache.hit_count = 5
        generator_with_mock.cache.miss_count = 10

        # Get statistics
        stats = generator_with_mock.get_statistics()

        # Verify statistics
        assert stats["cache_hit_rate"] == "33.3%"
        assert stats["cache_hits"] == 5
        assert stats["cache_misses"] == 10
        assert stats["total_tokens"] == 3000
        assert stats["total_requests"] == 2
        assert stats["total_cost_usd"] == "$0.0001"
        assert stats["average_tokens_per_request"] == "1500.0"
        assert "uptime_minutes" in stats

    def test_clear_cache(self, generator_with_mock):
        """Test clearing the cache."""
        # Add item to cache
        result = EmbeddingResult(
            text="Test",
            embedding=[0.1],
            model="test",
            token_count=1,
        )
        generator_with_mock.cache.put("Test", result)

        # Verify cache has item
        assert len(generator_with_mock.cache.cache) == 1

        # Clear cache
        generator_with_mock.clear_cache()

        # Verify cache is empty
        assert len(generator_with_mock.cache.cache) == 0
