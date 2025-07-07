"""
Vector Storage Module for RAG System.

This module handles all interactions with Supabase for storing and retrieving
embeddings using pgvector for similarity search.
"""

import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_rag_config
from .embeddings import EmbeddingResult
from .processor import TextChunk

logger = logging.getLogger(__name__)


class VectorStorage:
    """Manages vector storage and retrieval using Supabase with pgvector."""

    def __init__(self, config=None):
        """Initialize the vector storage with Supabase client."""
        # Get configuration
        self.config = config or get_rag_config()

        # Initialize Supabase client with custom options
        options = ClientOptions(auto_refresh_token=True, persist_session=True)

        self.supabase: Client = create_client(
            self.config.supabase_url, self.config.supabase_service_key, options=options
        )

        # Connection pool for direct database access
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_lock = asyncio.Lock()

        logger.info("Initialized VectorStorage with Supabase")

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.close()

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        # Use lock to ensure only one pool is created
        async with self._pool_lock:
            if self._pool is None:
                # Use DATABASE_URL from .env if available
                if hasattr(self.config, "database_url") and self.config.database_url:
                    db_url = self.config.database_url
                    logger.info("Using DATABASE_URL from .env")
                elif self.config.database_pool_url:
                    db_url = self.config.database_pool_url
                    logger.info("Using DATABASE_POOL_URL from .env")
                else:
                    # Fallback: try to construct from Supabase URL
                    project_ref = self.config.supabase_url.split("//")[1].split(".")[0]
                    db_url = f"postgresql://postgres.{project_ref}:password@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
                    logger.warning(
                        "Using constructed database URL - consider setting DATABASE_URL in .env"
                    )

                # Create the connection pool
                # Disable prepared statements for pgbouncer compatibility
                self._pool = await asyncpg.create_pool(
                    db_url,
                    min_size=2,
                    max_size=self.config.connection_pool_size,
                    max_inactive_connection_lifetime=300,
                    command_timeout=self.config.connection_timeout,
                    statement_cache_size=0,  # Disable prepared statements for pgbouncer
                )

                logger.info(
                    f"Created connection pool with {self.config.connection_pool_size} connections"
                )

        return self._pool

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        # Get the pool
        pool = await self._get_pool()

        # Acquire a connection
        async with pool.acquire() as connection:
            yield connection

    async def close(self):
        """Close the connection pool."""
        # Close the pool if it exists
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed connection pool")

    def _generate_chunk_id(self, chunk: TextChunk) -> str:
        """Generate a unique ID for a chunk."""
        # Create a hash of the content and metadata
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()

        # Include source_id if available
        if chunk.source_id:
            return f"{chunk.source_id}_{chunk.chunk_index}_{content_hash[:8]}"

        # Otherwise use content hash
        return f"chunk_{chunk.chunk_index}_{content_hash[:16]}"

    def _generate_cache_key(self, keyword: str) -> str:
        """Generate a cache key for a keyword."""
        # Normalize the keyword and create a hash
        normalized = keyword.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def store_research_chunks(
        self, chunks: List[TextChunk], embeddings: List[EmbeddingResult], keyword: str
    ) -> List[str]:
        """
        Store research chunks with their embeddings.

        Args:
            chunks: List of text chunks
            embeddings: Corresponding embeddings
            keyword: Research keyword

        Returns:
            List of stored chunk IDs
        """
        # Validate inputs
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        # Prepare data for insertion
        chunk_records = []

        for chunk, embedding in zip(chunks, embeddings):
            # Generate chunk ID
            chunk_id = self._generate_chunk_id(chunk)

            # Prepare record
            record = {
                "id": chunk_id,
                "content": chunk.content,
                "embedding": embedding.embedding,  # pgvector handles the array
                "metadata": chunk.metadata,
                "keyword": keyword,
                "chunk_index": chunk.chunk_index,
                "source_id": chunk.source_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            chunk_records.append(record)

        # Store in database using Supabase client
        try:
            # Insert chunks in batches
            batch_size = 100
            stored_ids = []

            for i in range(0, len(chunk_records), batch_size):
                batch = chunk_records[i : i + batch_size]

                # Use upsert to handle duplicates
                result = (
                    self.supabase.table("research_chunks")
                    .upsert(batch, on_conflict="id")
                    .execute()
                )

                # Extract IDs from result
                stored_ids.extend([r["id"] for r in result.data])

            logger.info(f"Stored {len(stored_ids)} chunks for keyword: {keyword}")
            return stored_ids

        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def store_cache_entry(
        self,
        keyword: str,
        research_summary: str,
        chunk_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a cache entry for quick keyword lookup.

        Args:
            keyword: Search keyword
            research_summary: Summary of research findings
            chunk_ids: IDs of related chunks
            metadata: Additional metadata

        Returns:
            Cache entry ID
        """
        # Generate cache key
        cache_key = self._generate_cache_key(keyword)

        # Prepare cache entry
        cache_entry = {
            "id": cache_key,
            "keyword": keyword,
            "keyword_normalized": keyword.lower().strip(),
            "research_summary": research_summary,
            "chunk_ids": chunk_ids,
            "metadata": metadata or {},
            "hit_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(hours=self.config.cache_ttl_hours)
            ).isoformat(),
        }

        # Store in database
        try:
            result = (
                self.supabase.table("cache_entries")
                .upsert(cache_entry, on_conflict="id")
                .execute()
            )

            logger.info(f"Stored cache entry for keyword: {keyword}")
            return result.data[0]["id"]

        except Exception as e:
            logger.error(f"Failed to store cache entry: {e}")
            raise

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of (chunk_data, similarity_score) tuples
        """
        # Use config threshold if not specified
        if similarity_threshold is None:
            similarity_threshold = self.config.similarity_threshold

        # Perform vector similarity search using raw SQL
        async with self.get_connection() as conn:
            # Query using pgvector's <=> operator for cosine distance
            # Note: pgvector returns distance, so we convert to similarity
            query = """
                SELECT 
                    id,
                    content,
                    metadata,
                    keyword,
                    chunk_index,
                    source_id,
                    created_at,
                    1 - (embedding <=> $1::vector) as similarity
                FROM research_chunks
                WHERE 1 - (embedding <=> $1::vector) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """

            # Convert embedding list to PostgreSQL vector format string
            # Format: '[0.1, 0.2, 0.3, ...]'
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

            # Execute query
            rows = await conn.fetch(query, embedding_str, similarity_threshold, limit)

            # Convert results
            results = []
            for row in rows:
                chunk_data = {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": (
                        json.loads(row["metadata"])
                        if isinstance(row["metadata"], str)
                        else row["metadata"]
                    ),
                    "keyword": row["keyword"],
                    "chunk_index": row["chunk_index"],
                    "source_id": row["source_id"],
                    "created_at": row["created_at"],
                }
                similarity = row["similarity"]
                results.append((chunk_data, similarity))

            logger.info(f"Found {len(results)} similar chunks")
            return results

    async def get_cached_response(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for a keyword.

        Args:
            keyword: Search keyword

        Returns:
            Cached response data or None
        """
        # Generate cache key
        cache_key = self._generate_cache_key(keyword)

        try:
            # Query cache entry
            result = (
                self.supabase.table("cache_entries")
                .select("*")
                .eq("id", cache_key)
                .execute()
            )

            if not result.data:
                return None

            cache_entry = result.data[0]

            # Check if expired
            expires_at = datetime.fromisoformat(
                cache_entry["expires_at"].replace("Z", "+00:00")
            )
            if expires_at < datetime.now(timezone.utc):
                logger.info(f"Cache entry expired for keyword: {keyword}")
                return None

            # Update hit count and last accessed
            self.supabase.table("cache_entries").update(
                {
                    "hit_count": cache_entry["hit_count"] + 1,
                    "last_accessed": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", cache_key).execute()

            # Fetch associated chunks
            chunk_ids = cache_entry["chunk_ids"]
            if chunk_ids:
                chunks_result = (
                    self.supabase.table("research_chunks")
                    .select("*")
                    .in_("id", chunk_ids)
                    .execute()
                )

                cache_entry["chunks"] = chunks_result.data
            else:
                cache_entry["chunks"] = []

            logger.info(f"Retrieved cached response for keyword: {keyword}")
            return cache_entry

        except Exception as e:
            logger.error(f"Failed to retrieve cached response: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            # Get counts using Supabase client
            chunks_count = len(
                self.supabase.table("research_chunks")
                .select("id", count="exact")
                .execute()
                .data
            )

            cache_count = len(
                self.supabase.table("cache_entries")
                .select("id", count="exact")
                .execute()
                .data
            )

            # Get cache statistics
            cache_stats = (
                self.supabase.table("cache_entries").select("hit_count").execute().data
            )

            total_hits = sum(entry["hit_count"] for entry in cache_stats)
            avg_hits = total_hits / len(cache_stats) if cache_stats else 0

            return {
                "total_chunks": chunks_count,
                "total_cache_entries": cache_count,
                "total_cache_hits": total_hits,
                "average_hits_per_entry": round(avg_hits, 2),
                "storage_initialized": True,
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e),
                "storage_initialized": False,
            }

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        try:
            # Delete expired entries
            now = datetime.now(timezone.utc).isoformat()
            result = (
                self.supabase.table("cache_entries")
                .delete()
                .lt("expires_at", now)
                .execute()
            )

            deleted_count = len(result.data)
            logger.info(f"Cleaned up {deleted_count} expired cache entries")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return 0

    async def bulk_search(
        self, embeddings: List[List[float]], limit_per_query: int = 5
    ) -> List[List[Tuple[Dict[str, Any], float]]]:
        """
        Perform bulk similarity search for multiple embeddings.

        Args:
            embeddings: List of embedding vectors
            limit_per_query: Results per query

        Returns:
            List of results for each query
        """
        # Perform searches in parallel
        tasks = [
            self.search_similar_chunks(embedding, limit_per_query)
            for embedding in embeddings
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content in cache entries and chunks.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of similar content with metadata
        """
        # Search in chunks
        chunk_results = await self.search_similar_chunks(
            query_embedding, limit, similarity_threshold
        )

        # Format results for display
        results = []
        for chunk_data, similarity in chunk_results:
            results.append(
                {
                    "similarity": similarity,
                    "keyword": chunk_data.get("keyword", "Unknown"),
                    "content": chunk_data.get("content", ""),
                    "created_at": chunk_data.get("created_at", ""),
                    "metadata": chunk_data.get("metadata", {}),
                }
            )

        return results

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get basic counts
            chunks_result = (
                self.supabase.table("research_chunks")
                .select("*", count="exact")
                .execute()
            )
            chunks_count = len(chunks_result.data) if chunks_result.data else 0

            cache_result = (
                self.supabase.table("cache_entries")
                .select("*", count="exact")
                .execute()
            )
            cache_count = len(cache_result.data) if cache_result.data else 0
            cache_entries = cache_result.data if cache_result.data else []

            # Calculate storage size (approximate)
            total_size = 0
            unique_keywords = set()
            oldest_entry = None
            newest_entry = None

            if cache_entries:
                for entry in cache_entries:
                    # Estimate size
                    entry_size = len(json.dumps(entry))
                    total_size += entry_size

                    # Track unique keywords
                    unique_keywords.add(entry.get("keyword", ""))

                    # Track dates
                    created_at = entry.get("created_at")
                    if created_at:
                        if not oldest_entry or created_at < oldest_entry:
                            oldest_entry = created_at
                        if not newest_entry or created_at > newest_entry:
                            newest_entry = created_at

            # Calculate average chunk size
            avg_chunk_size = 0
            if chunks_result.data:
                total_chunk_chars = sum(
                    len(chunk.get("content", "")) for chunk in chunks_result.data
                )
                avg_chunk_size = (
                    total_chunk_chars / chunks_count if chunks_count > 0 else 0
                )

            return {
                "total_entries": chunks_count + cache_count,
                "research_chunks": chunks_count,
                "cache_entries": cache_count,
                "unique_keywords": len(unique_keywords),
                "storage_bytes": total_size,
                "avg_chunk_size": avg_chunk_size,
                "oldest_entry": oldest_entry,
                "newest_entry": newest_entry,
                "total_embeddings": chunks_count,  # Each chunk has an embedding
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "total_entries": 0,
                "unique_keywords": 0,
                "storage_bytes": 0,
                "avg_chunk_size": 0,
                "error": str(e),
            }

    async def get_keyword_distribution(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get distribution of keywords in cache.

        Args:
            limit: Maximum number of keywords to return

        Returns:
            List of (keyword, count) tuples
        """
        try:
            # Get all keywords from chunks
            chunks_result = (
                self.supabase.table("research_chunks").select("keyword").execute()
            )

            if not chunks_result.data:
                return []

            # Count keywords
            keyword_counts = {}
            for chunk in chunks_result.data:
                keyword = chunk.get("keyword", "Unknown")
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            # Sort by count and return top N
            sorted_keywords = sorted(
                keyword_counts.items(), key=lambda x: x[1], reverse=True
            )

            return sorted_keywords[:limit]

        except Exception as e:
            logger.error(f"Failed to get keyword distribution: {e}")
            return []

    async def cleanup_cache(
        self, older_than_days: Optional[int] = None, keyword: Optional[str] = None
    ) -> int:
        """
        Clean up cache entries based on criteria.

        Args:
            older_than_days: Remove entries older than N days
            keyword: Remove entries for specific keyword

        Returns:
            Number of deleted entries
        """
        try:
            deleted_count = 0

            # Delete from cache_entries table
            if older_than_days:
                # Calculate cutoff date
                cutoff_date = (
                    datetime.now(timezone.utc) - timedelta(days=older_than_days)
                ).isoformat()

                # Delete old cache entries
                cache_result = (
                    self.supabase.table("cache_entries")
                    .delete()
                    .lt("created_at", cutoff_date)
                    .execute()
                )
                deleted_count += len(cache_result.data) if cache_result.data else 0

                # Delete old chunks
                chunks_result = (
                    self.supabase.table("research_chunks")
                    .delete()
                    .lt("created_at", cutoff_date)
                    .execute()
                )
                deleted_count += len(chunks_result.data) if chunks_result.data else 0

            elif keyword:
                # Delete cache entries for keyword
                normalized_keyword = keyword.lower().strip()
                cache_result = (
                    self.supabase.table("cache_entries")
                    .delete()
                    .eq("keyword_normalized", normalized_keyword)
                    .execute()
                )
                deleted_count += len(cache_result.data) if cache_result.data else 0

                # Delete chunks for keyword
                chunks_result = (
                    self.supabase.table("research_chunks")
                    .delete()
                    .ilike("keyword", f"%{keyword}%")
                    .execute()
                )
                deleted_count += len(chunks_result.data) if chunks_result.data else 0

            else:
                # Clear all cache entries
                cache_result = (
                    self.supabase.table("cache_entries")
                    .delete()
                    .neq("id", "")
                    .execute()
                )
                deleted_count += len(cache_result.data) if cache_result.data else 0

                # Clear all chunks
                chunks_result = (
                    self.supabase.table("research_chunks")
                    .delete()
                    .neq("id", "")
                    .execute()
                )
                deleted_count += len(chunks_result.data) if chunks_result.data else 0

            logger.info(f"Cleaned up {deleted_count} cache entries")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return 0

    async def warm_pool(self) -> bool:
        """
        Warm the connection pool by establishing connections.

        This method pre-establishes database connections to avoid cold start
        latency on first use. It's especially useful when starting the application.

        Returns:
            True if warming successful, False otherwise
        """
        try:
            logger.info("Warming connection pool...")

            # Get the pool to trigger creation
            pool = await self._get_pool()

            # Execute a simple query on each connection to warm them up
            # This ensures connections are fully established and ready
            tasks = []
            for i in range(min(3, self.config.connection_pool_size)):

                async def warm_connection():
                    async with self.get_connection() as conn:
                        # Simple query to test connection
                        await conn.fetchval("SELECT 1")

                tasks.append(warm_connection())

            # Run warming tasks concurrently
            await asyncio.gather(*tasks)

            logger.info(f"Successfully warmed {len(tasks)} connections")
            return True

        except Exception as e:
            logger.error(f"Failed to warm connection pool: {e}")
            return False
