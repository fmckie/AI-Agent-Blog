"""
Embedding Generator for RAG System.

This module handles the generation of embeddings using OpenAI's API,
with features for batch processing, caching, and cost tracking.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import get_config

from .config import get_rag_config

logger = logging.getLogger(__name__)


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""

    text: str = Field(description="Original text that was embedded")
    embedding: List[float] = Field(description="Embedding vector")
    model: str = Field(description="Model used for embedding")
    token_count: int = Field(description="Number of tokens processed")

    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array."""
        # Convert the embedding list to numpy array for calculations
        return np.array(self.embedding)


class EmbeddingCache(BaseModel):
    """In-memory cache for embeddings."""

    cache: Dict[str, EmbeddingResult] = Field(default_factory=dict)
    hit_count: int = Field(default=0, description="Number of cache hits")
    miss_count: int = Field(default=0, description="Number of cache misses")

    def get_hash(self, text: str) -> str:
        """Generate hash for text."""
        # Create a consistent hash for the text
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[EmbeddingResult]:
        """Get embedding from cache."""
        # Check if we have this text in cache
        text_hash = self.get_hash(text)
        if text_hash in self.cache:
            self.hit_count += 1
            logger.debug(f"Cache hit for text hash: {text_hash[:8]}")
            return self.cache[text_hash]

        # Cache miss
        self.miss_count += 1
        return None

    def put(self, text: str, result: EmbeddingResult) -> None:
        """Store embedding in cache."""
        # Store the embedding result in cache
        text_hash = self.get_hash(text)
        self.cache[text_hash] = result
        logger.debug(f"Cached embedding for text hash: {text_hash[:8]}")

    def clear(self) -> None:
        """Clear the cache."""
        # Reset cache and statistics
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        # Calculate hit rate as percentage
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return (self.hit_count / total) * 100


class CostTracker(BaseModel):
    """Track embedding generation costs."""

    total_tokens: int = Field(default=0, description="Total tokens processed")
    total_requests: int = Field(default=0, description="Total API requests made")
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_cost(self) -> float:
        """Calculate total cost in USD."""
        # OpenAI text-embedding-3-small costs $0.02 per 1M tokens
        return (self.total_tokens / 1_000_000) * 0.02

    @property
    def average_tokens_per_request(self) -> float:
        """Calculate average tokens per request."""
        # Return average or 0 if no requests
        if self.total_requests == 0:
            return 0.0
        return self.total_tokens / self.total_requests

    def add_usage(self, tokens: int) -> None:
        """Add token usage."""
        # Track token usage and increment request count
        self.total_tokens += tokens
        self.total_requests += 1


class EmbeddingGenerator:
    """Generate embeddings using OpenAI's API with caching and retry logic."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the embedding generator."""
        # Get configurations
        self.rag_config = get_rag_config()
        self.main_config = get_config()

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=api_key or self.main_config.openai_api_key)

        # Initialize cache and cost tracker
        self.cache = EmbeddingCache()
        self.cost_tracker = CostTracker()

        # Set model from RAG config
        self.model = self.rag_config.embedding_model_name

        logger.info(f"Initialized EmbeddingGenerator with model: {self.model}")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception),
    )
    async def _generate_single_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text with retry logic."""
        # Clean and validate text
        text = text.strip()
        if not text:
            raise ValueError("Cannot generate embedding for empty text")

        # Make API call
        logger.debug(f"Generating embedding for text of length: {len(text)}")
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        # Extract embedding data
        embedding_data = response.data[0]
        embedding = embedding_data.embedding

        # Estimate tokens (API doesn't return usage for embeddings)
        token_count = self._estimate_tokens(text)

        # Create result
        result = EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model,
            token_count=token_count,
        )

        # Track usage
        self.cost_tracker.add_usage(token_count)

        return result

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text."""
        # Check cache first
        cached_result = self.cache.get(text)
        if cached_result:
            return cached_result

        # Generate new embedding
        result = await self._generate_single_embedding(text)

        # Cache the result
        self.cache.put(text, result)

        return result

    async def generate_embeddings(
        self, texts: List[str], batch_size: Optional[int] = None
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts in batches."""
        # Use RAG config batch size if not specified
        if batch_size is None:
            batch_size = self.rag_config.embedding_batch_size

        # Clean texts
        texts = [text.strip() for text in texts if text.strip()]
        if not texts:
            return []

        # Collect results
        results = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Create tasks for parallel processing
            tasks = [self.generate_embedding(text) for text in batch]

            # Wait for all embeddings in batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to generate embedding for text {i+j}: {result}"
                    )
                    # Re-raise the exception
                    raise result
                results.append(result)

            # Log progress
            logger.info(f"Generated embeddings for batch {i//batch_size + 1}")

        return results

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure result is between -1 and 1
        return float(np.clip(similarity, -1.0, 1.0))

    def find_most_similar(
        self,
        query_embedding: List[float],
        embeddings: List[Tuple[str, List[float]]],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find most similar embeddings to a query."""
        # Calculate similarities for all embeddings
        similarities = []

        for identifier, embedding in embeddings:
            similarity = self.calculate_similarity(query_embedding, embedding)
            similarities.append((identifier, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top k results
        return similarities[:top_k]

    def get_statistics(self) -> Dict[str, any]:
        """Get usage statistics."""
        # Compile statistics
        return {
            "cache_hit_rate": f"{self.cache.hit_rate:.1f}%",
            "cache_hits": self.cache.hit_count,
            "cache_misses": self.cache.miss_count,
            "cached_embeddings": len(self.cache.cache),
            "total_tokens": self.cost_tracker.total_tokens,
            "total_requests": self.cost_tracker.total_requests,
            "total_cost_usd": f"${self.cost_tracker.total_cost:.4f}",
            "average_tokens_per_request": f"{self.cost_tracker.average_tokens_per_request:.1f}",
            "uptime_minutes": (
                datetime.now(timezone.utc) - self.cost_tracker.start_time
            ).total_seconds()
            / 60,
        }

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        # Clear cache
        self.cache.clear()
        logger.info("Cleared embedding cache")
