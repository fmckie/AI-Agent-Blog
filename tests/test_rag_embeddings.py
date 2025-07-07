"""
Comprehensive test suite for RAG embeddings module.

This module tests the embedding generation functionality including
caching, cost tracking, and similarity calculations.
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from openai import AsyncOpenAI

from rag.embeddings import (
    CostTracker,
    EmbeddingCache,
    EmbeddingGenerator,
    EmbeddingResult,
)


class TestEmbeddingResult:
    """Test cases for EmbeddingResult model."""

    def test_embedding_result_creation(self):
        """Test creating an EmbeddingResult."""
        result = EmbeddingResult(
            text="Test text",
            embedding=[0.1, 0.2, 0.3],
            model="text-embedding-ada-002",
            token_count=10,
        )

        assert result.text == "Test text"
        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.model == "text-embedding-ada-002"
        assert result.token_count == 10

    def test_to_numpy_conversion(self):
        """Test converting embedding to numpy array."""
        result = EmbeddingResult(
            text="Test",
            embedding=[0.1, 0.2, 0.3, 0.4],
            model="test-model",
            token_count=5,
        )

        np_array = result.to_numpy()
        assert isinstance(np_array, np.ndarray)
        assert np_array.shape == (4,)
        assert np.allclose(np_array, [0.1, 0.2, 0.3, 0.4])

    def test_embedding_result_validation(self):
        """Test EmbeddingResult field validation."""
        # Valid result
        result = EmbeddingResult(
            text="Valid text",
            embedding=[0.5] * 10,
            model="model",
            token_count=1,
        )
        assert result.token_count >= 1

        # Test with empty embedding
        result = EmbeddingResult(
            text="Text",
            embedding=[],
            model="model",
            token_count=0,
        )
        assert result.embedding == []


class TestEmbeddingCache:
    """Test cases for EmbeddingCache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = EmbeddingCache()

        assert cache.cache == {}
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        assert cache.hit_rate == 0.0

    def test_cache_hash_generation(self):
        """Test consistent hash generation."""
        cache = EmbeddingCache()

        text = "Test text for hashing"
        hash1 = cache.get_hash(text)
        hash2 = cache.get_hash(text)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

        # Different text should produce different hash
        hash3 = cache.get_hash("Different text")
        assert hash3 != hash1

    def test_cache_miss(self):
        """Test cache miss scenario."""
        cache = EmbeddingCache()

        result = cache.get("Non-existent text")

        assert result is None
        assert cache.miss_count == 1
        assert cache.hit_count == 0

    def test_cache_hit(self):
        """Test cache hit scenario."""
        cache = EmbeddingCache()

        # Store an embedding
        embedding_result = EmbeddingResult(
            text="Cached text",
            embedding=[0.1, 0.2],
            model="test",
            token_count=5,
        )
        cache.put("Cached text", embedding_result)

        # Retrieve it
        retrieved = cache.get("Cached text")

        assert retrieved == embedding_result
        assert cache.hit_count == 1
        assert cache.miss_count == 0

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        cache = EmbeddingCache()

        # Initial rate should be 0
        assert cache.hit_rate == 0.0

        # Add some hits and misses
        cache.miss_count = 3
        cache.hit_count = 7

        assert cache.hit_rate == 70.0

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = EmbeddingCache()

        # Add some data
        cache.put("text1", Mock())
        cache.put("text2", Mock())
        cache.hit_count = 5
        cache.miss_count = 3

        # Clear cache
        cache.clear()

        assert len(cache.cache) == 0
        assert cache.hit_count == 0
        assert cache.miss_count == 0


class TestCostTracker:
    """Test cases for CostTracker functionality."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker initialization."""
        tracker = CostTracker()

        assert tracker.total_tokens == 0
        assert tracker.total_requests == 0
        assert isinstance(tracker.start_time, datetime)
        assert tracker.total_cost == 0.0

    def test_add_usage(self):
        """Test adding token usage."""
        tracker = CostTracker()

        tracker.add_usage(100)
        assert tracker.total_tokens == 100
        assert tracker.total_requests == 1

        tracker.add_usage(200)
        assert tracker.total_tokens == 300
        assert tracker.total_requests == 2

    def test_cost_calculation(self):
        """Test cost calculation based on tokens."""
        tracker = CostTracker()

        # Add 1 million tokens
        tracker.add_usage(1_000_000)

        # Cost should be $0.02 (OpenAI pricing)
        assert tracker.total_cost == 0.02

        # Add another 500k tokens
        tracker.add_usage(500_000)
        assert tracker.total_cost == 0.03

    def test_average_tokens_per_request(self):
        """Test average tokens calculation."""
        tracker = CostTracker()

        # No requests
        assert tracker.average_tokens_per_request == 0.0

        # Add some requests
        tracker.add_usage(100)
        tracker.add_usage(200)
        tracker.add_usage(300)

        assert tracker.average_tokens_per_request == 200.0


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configurations."""
        main_config = Mock()
        main_config.openai_api_key = "test-key"

        rag_config = Mock()
        rag_config.embedding_model_name = "text-embedding-3-small"
        rag_config.embedding_batch_size = 10

        return main_config, rag_config

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI embedding response."""
        response = Mock()
        embedding_data = Mock()
        embedding_data.embedding = [0.1] * 1536
        response.data = [embedding_data]
        return response

    def test_generator_initialization(self, mock_config):
        """Test EmbeddingGenerator initialization."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                assert generator.model == "text-embedding-3-small"
                assert isinstance(generator.cache, EmbeddingCache)
                assert isinstance(generator.cost_tracker, CostTracker)

    def test_generator_with_custom_api_key(self, mock_config):
        """Test generator with custom API key."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator(api_key="custom-key")

                # Verify custom key is used
                assert generator.client.api_key == "custom-key"

    def test_token_estimation(self, mock_config):
        """Test token count estimation."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Test various text lengths
                assert generator._estimate_tokens("test") == 1
                assert generator._estimate_tokens("a" * 40) == 10
                assert generator._estimate_tokens("") == 1  # Minimum 1

    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, mock_config, mock_openai_response):
        """Test generating a single embedding."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Mock the OpenAI client
                generator.client.embeddings.create = AsyncMock(
                    return_value=mock_openai_response
                )

                result = await generator._generate_single_embedding("Test text")

                assert result.text == "Test text"
                assert len(result.embedding) == 1536
                assert result.model == "text-embedding-3-small"
                assert result.token_count > 0

    @pytest.mark.asyncio
    async def test_generate_embedding_with_cache_hit(self, mock_config):
        """Test embedding generation with cache hit."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Pre-populate cache
                cached_result = EmbeddingResult(
                    text="Cached text",
                    embedding=[0.5] * 1536,
                    model="test",
                    token_count=10,
                )
                generator.cache.put("Cached text", cached_result)

                # Should return from cache
                result = await generator.generate_embedding("Cached text")

                assert result == cached_result
                assert generator.cache.hit_count == 1

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, mock_config):
        """Test embedding generation with empty text."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.AsyncOpenAI"):
                    generator = EmbeddingGenerator()

                    # The retry library wraps exceptions in RetryError
                    from tenacity import RetryError

                    with pytest.raises((ValueError, RetryError)):
                        await generator._generate_single_embedding("  ")

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, mock_config, mock_openai_response):
        """Test batch embedding generation."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Mock the OpenAI client
                generator.client.embeddings.create = AsyncMock(
                    return_value=mock_openai_response
                )

                texts = ["Text 1", "Text 2", "Text 3"]
                results = await generator.generate_embeddings(texts)

                assert len(results) == 3
                for i, result in enumerate(results):
                    assert result.text == texts[i]
                    assert len(result.embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_errors(self, mock_config):
        """Test batch generation with errors."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.AsyncOpenAI"):
                    generator = EmbeddingGenerator()

                    # Mock to raise error
                    generator.client.embeddings.create = AsyncMock(
                        side_effect=Exception("API Error")
                    )

                    with pytest.raises(Exception, match="API Error"):
                        await generator.generate_embeddings(["Text 1"])

    def test_calculate_similarity(self, mock_config):
        """Test cosine similarity calculation."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Test identical vectors
                vec1 = [1.0, 0.0, 0.0]
                similarity = generator.calculate_similarity(vec1, vec1)
                assert similarity == 1.0

                # Test orthogonal vectors
                vec2 = [0.0, 1.0, 0.0]
                similarity = generator.calculate_similarity(vec1, vec2)
                assert similarity == 0.0

                # Test opposite vectors
                vec3 = [-1.0, 0.0, 0.0]
                similarity = generator.calculate_similarity(vec1, vec3)
                assert similarity == -1.0

    def test_calculate_similarity_zero_vectors(self, mock_config):
        """Test similarity with zero vectors."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                zero_vec = [0.0, 0.0, 0.0]
                normal_vec = [1.0, 0.0, 0.0]

                similarity = generator.calculate_similarity(zero_vec, normal_vec)
                assert similarity == 0.0

    def test_find_most_similar(self, mock_config):
        """Test finding most similar embeddings."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                query = [1.0, 0.0, 0.0]
                embeddings = [
                    ("doc1", [0.9, 0.1, 0.0]),  # Very similar
                    ("doc2", [0.0, 1.0, 0.0]),  # Orthogonal
                    ("doc3", [0.8, 0.2, 0.0]),  # Similar
                    ("doc4", [-1.0, 0.0, 0.0]),  # Opposite
                    ("doc5", [0.7, 0.3, 0.0]),  # Somewhat similar
                ]

                results = generator.find_most_similar(query, embeddings, top_k=3)

                assert len(results) == 3
                assert results[0][0] == "doc1"  # Most similar
                assert results[1][0] == "doc3"  # Second most similar
                assert results[2][0] == "doc5"  # Third most similar

    def test_get_statistics(self, mock_config):
        """Test statistics collection."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Add some activity
                generator.cache.hit_count = 10
                generator.cache.miss_count = 5
                generator.cache.cache["hash1"] = Mock()
                generator.cost_tracker.add_usage(1000)
                generator.cost_tracker.add_usage(500)

                stats = generator.get_statistics()

                assert stats["cache_hit_rate"] == "66.7%"
                assert stats["cache_hits"] == 10
                assert stats["cache_misses"] == 5
                assert stats["cached_embeddings"] == 1
                assert stats["total_tokens"] == 1500
                assert stats["total_requests"] == 2
                assert "total_cost_usd" in stats
                assert "uptime_minutes" in stats

    def test_clear_cache(self, mock_config):
        """Test cache clearing."""
        main_config, rag_config = mock_config

        with patch("rag.embeddings.get_config", return_value=main_config):
            with patch("rag.embeddings.get_rag_config", return_value=rag_config):
                generator = EmbeddingGenerator()

                # Add cache data
                generator.cache.put("text", Mock())
                generator.cache.hit_count = 5

                # Clear cache
                generator.clear_cache()

                assert len(generator.cache.cache) == 0
                assert generator.cache.hit_count == 0


class TestEmbeddingGeneratorRetry:
    """Test retry logic in EmbeddingGenerator."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that retry logic works on API failures."""
        with patch("rag.embeddings.get_config"):
            with patch("rag.embeddings.get_rag_config"):
                with patch("rag.embeddings.AsyncOpenAI"):
                    generator = EmbeddingGenerator()

                    # Mock to fail twice then succeed
                    call_count = 0

                    async def mock_create(*args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        if call_count < 3:
                            raise Exception("Temporary failure")

                        response = Mock()
                        embedding_data = Mock()
                        embedding_data.embedding = [0.1] * 1536
                        response.data = [embedding_data]
                        return response

                    generator.client.embeddings.create = mock_create

                    # Should retry and eventually succeed
                    result = await generator._generate_single_embedding("Test")

                    assert call_count == 3
                    assert result.text == "Test"
                    assert len(result.embedding) == 1536

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry exhaustion after max attempts."""
        with patch("rag.embeddings.get_config"):
            with patch("rag.embeddings.get_rag_config"):
                with patch("rag.embeddings.AsyncOpenAI"):
                    generator = EmbeddingGenerator()

                    # Mock to always fail
                    generator.client.embeddings.create = AsyncMock(
                        side_effect=Exception("Permanent failure")
                    )

                    # Should fail after 3 attempts - the retry library may wrap in RetryError
                    with pytest.raises(Exception):
                        await generator._generate_single_embedding("Test")
