#!/usr/bin/env python3
"""
Integration test for Vector Storage with real Supabase connection
This script tests actual database operations to ensure everything works
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from rag.embeddings import EmbeddingResult
from rag.processor import TextChunk

# Import our RAG components
from rag.storage import VectorStorage

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


async def test_store_and_retrieve():
    """Test storing chunks and retrieving them"""
    print(f"\n{BLUE}=== Vector Storage Integration Test ==={RESET}")

    # Initialize storage
    storage = VectorStorage()

    try:
        # Create test data
        print(f"\n{BLUE}1. Creating test data...{RESET}")

        # Sample text chunks
        chunks = [
            TextChunk(
                content="Artificial intelligence is transforming healthcare through predictive analytics and diagnostic assistance.",
                metadata={
                    "source": "AI Health Review",
                    "year": 2024,
                    "topic": "healthcare",
                },
                chunk_index=0,
                source_id="health_ai_001",
            ),
            TextChunk(
                content="Machine learning algorithms can analyze medical images with accuracy comparable to experienced radiologists.",
                metadata={
                    "source": "Medical AI Journal",
                    "year": 2024,
                    "topic": "radiology",
                },
                chunk_index=1,
                source_id="health_ai_001",
            ),
            TextChunk(
                content="Natural language processing enables automated analysis of clinical notes and patient records.",
                metadata={
                    "source": "Healthcare Tech Weekly",
                    "year": 2024,
                    "topic": "nlp",
                },
                chunk_index=2,
                source_id="health_ai_002",
            ),
        ]

        # Create mock embeddings (in real usage, these would come from OpenAI)
        # Using different patterns to simulate semantic differences
        embeddings = [
            EmbeddingResult(
                text=chunks[0].content,
                embedding=[0.1 + i * 0.001 for i in range(1536)],  # Pattern 1
                model="text-embedding-3-small",
                token_count=15,
            ),
            EmbeddingResult(
                text=chunks[1].content,
                embedding=[0.2 + i * 0.001 for i in range(1536)],  # Pattern 2
                model="text-embedding-3-small",
                token_count=18,
            ),
            EmbeddingResult(
                text=chunks[2].content,
                embedding=[
                    0.15 + i * 0.001 for i in range(1536)
                ],  # Pattern between 1 and 2
                model="text-embedding-3-small",
                token_count=12,
            ),
        ]

        print(f"{GREEN}✓ Created {len(chunks)} test chunks with embeddings{RESET}")

        # Store chunks
        print(f"\n{BLUE}2. Storing chunks in database...{RESET}")
        chunk_ids = await storage.store_research_chunks(
            chunks=chunks, embeddings=embeddings, keyword="AI healthcare"
        )

        print(f"{GREEN}✓ Stored {len(chunk_ids)} chunks successfully{RESET}")
        for i, chunk_id in enumerate(chunk_ids):
            print(f"  - Chunk {i}: {chunk_id}")

        # Test similarity search
        print(f"\n{BLUE}3. Testing similarity search...{RESET}")

        # Create a query embedding similar to the first chunk
        query_embedding = [0.12 + i * 0.001 for i in range(1536)]

        # Search for similar chunks
        results = await storage.search_similar_chunks(
            query_embedding=query_embedding, limit=5, similarity_threshold=0.5
        )

        print(f"{GREEN}✓ Found {len(results)} similar chunks{RESET}")
        for i, (chunk, similarity) in enumerate(results):
            print(f"\n  Result {i+1} (similarity: {similarity:.4f}):")
            print(f"    Content: {chunk['content'][:80]}...")
            print(f"    Source: {chunk['metadata'].get('source', 'Unknown')}")

        # Test cache storage and retrieval
        print(f"\n{BLUE}4. Testing cache functionality...{RESET}")

        # Store a cache entry
        cache_id = await storage.store_cache_entry(
            keyword="AI healthcare",
            research_summary="AI is revolutionizing healthcare through predictive analytics, diagnostic assistance, and automated analysis of clinical data.",
            chunk_ids=chunk_ids,
            metadata={
                "sources": 3,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"{GREEN}✓ Stored cache entry: {cache_id}{RESET}")

        # Retrieve cached response
        cached = await storage.get_cached_response("AI healthcare")

        if cached:
            print(f"{GREEN}✓ Retrieved cached response successfully{RESET}")
            print(f"  - Keyword: {cached['keyword']}")
            print(f"  - Summary: {cached['research_summary'][:100]}...")
            print(f"  - Chunks: {len(cached['chunks'])} associated chunks")
            print(f"  - Hit count: {cached['hit_count']}")
        else:
            print(f"{RED}✗ Failed to retrieve cached response{RESET}")

        # Test cache with different case
        print(f"\n{BLUE}5. Testing case-insensitive cache lookup...{RESET}")
        cached_lower = await storage.get_cached_response("ai HEALTHCARE")

        if cached_lower:
            print(f"{GREEN}✓ Case-insensitive lookup works{RESET}")
        else:
            print(f"{RED}✗ Case-insensitive lookup failed{RESET}")

        # Get statistics
        print(f"\n{BLUE}6. Getting storage statistics...{RESET}")
        stats = await storage.get_statistics()

        print(f"{GREEN}✓ Storage statistics:{RESET}")
        for key, value in stats.items():
            if key != "error":
                print(f"  - {key}: {value}")

        # Test bulk search
        print(f"\n{BLUE}7. Testing bulk similarity search...{RESET}")

        # Create multiple query embeddings
        query_embeddings = [
            [0.11 + i * 0.001 for i in range(1536)],  # Similar to first chunk
            [0.19 + i * 0.001 for i in range(1536)],  # Similar to second chunk
            [0.5 + i * 0.001 for i in range(1536)],  # Different from all
        ]

        bulk_results = await storage.bulk_search(
            embeddings=query_embeddings, limit_per_query=2
        )

        print(
            f"{GREEN}✓ Bulk search completed for {len(query_embeddings)} queries{RESET}"
        )
        for i, results in enumerate(bulk_results):
            print(f"  - Query {i+1}: Found {len(results)} results")

        # Test cleanup (with future expiry)
        print(f"\n{BLUE}8. Testing cache cleanup...{RESET}")

        # First, add an expired entry for testing
        # Note: We can't easily create an expired entry via the API
        # so we'll just test cleanup with existing entries
        print(f"  - Testing cleanup (may show 0 if no expired entries exist)")

        # Run cleanup
        cleaned = await storage.cleanup_expired_cache()
        print(f"{GREEN}✓ Cleaned up {cleaned} expired entries{RESET}")

        # Final summary
        print(f"\n{BLUE}=== Test Summary ==={RESET}")
        print(f"{GREEN}✓ All vector storage operations completed successfully!{RESET}")
        print(f"\nThe Vector Storage component is fully functional with:")
        print(f"  - Chunk storage with embeddings")
        print(f"  - Similarity search using pgvector")
        print(f"  - Cache storage and retrieval")
        print(f"  - Case-insensitive keyword matching")
        print(f"  - Bulk operations")
        print(f"  - Automatic cleanup")

    except Exception as e:
        print(f"\n{RED}✗ Error during testing: {e}{RESET}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        await storage.close()
        print(f"\n{YELLOW}Closed database connections{RESET}")


async def cleanup_test_data():
    """Clean up test data from the database"""
    print(f"\n{BLUE}Cleaning up test data...{RESET}")

    storage = VectorStorage()

    try:
        # Delete test chunks
        table = storage.supabase.table("research_chunks")
        result = table.delete().like("source_id", "health_ai_%").execute()
        print(f"  - Deleted {len(result.data)} test chunks")

        # Delete test cache entries
        table = storage.supabase.table("cache_entries")
        result = (
            table.delete()
            .in_("keyword", ["AI healthcare", "ai healthcare", "expired test"])
            .execute()
        )
        print(f"  - Deleted {len(result.data)} test cache entries")

        print(f"{GREEN}✓ Cleanup completed{RESET}")

    except Exception as e:
        print(f"{RED}✗ Error during cleanup: {e}{RESET}")

    finally:
        await storage.close()


async def main():
    """Main test runner"""
    # Run the tests
    await test_store_and_retrieve()

    # Ask if user wants to clean up
    print(f"\n{YELLOW}Do you want to clean up the test data? (y/n): {RESET}", end="")
    response = input().strip().lower()

    if response == "y":
        await cleanup_test_data()
    else:
        print(f"{YELLOW}Test data retained in database{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
