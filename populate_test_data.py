#!/usr/bin/env python3
"""
Populate Supabase with test data for visual verification
This script creates sample data that's easy to identify in the dashboard
"""

import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from rag.embeddings import EmbeddingResult
from rag.processor import TextChunk

# Import our RAG components
from rag.storage import VectorStorage

# ANSI color codes
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"


async def populate_test_data():
    """Insert test data that's easy to spot in Supabase dashboard"""

    print(f"\n{BLUE}=== Populating Supabase with Test Data ==={RESET}")

    storage = VectorStorage()

    try:
        # Create test chunks with clear, identifiable content
        print(f"\n{BLUE}Creating test chunks...{RESET}")

        chunks = [
            TextChunk(
                content="TEST CHUNK 1: Machine learning is revolutionizing healthcare diagnostics",
                metadata={
                    "source": "Test Source 1",
                    "type": "demo",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                chunk_index=0,
                source_id="DEMO_001",
            ),
            TextChunk(
                content="TEST CHUNK 2: Natural language processing enables better patient communication",
                metadata={
                    "source": "Test Source 2",
                    "type": "demo",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                chunk_index=1,
                source_id="DEMO_001",
            ),
            TextChunk(
                content="TEST CHUNK 3: Computer vision helps radiologists detect anomalies faster",
                metadata={
                    "source": "Test Source 3",
                    "type": "demo",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                chunk_index=2,
                source_id="DEMO_002",
            ),
        ]

        # Create simple embeddings (in production, these come from OpenAI)
        embeddings = []
        for i, chunk in enumerate(chunks):
            # Create distinct patterns for each chunk
            base_value = 0.1 * (i + 1)  # 0.1, 0.2, 0.3
            embedding_vector = [base_value + (j * 0.0001) for j in range(1536)]

            embeddings.append(
                EmbeddingResult(
                    text=chunk.content,
                    embedding=embedding_vector,
                    model="demo-model",
                    token_count=len(chunk.content.split()),
                )
            )

        # Store chunks
        print(f"\n{BLUE}Storing chunks in database...{RESET}")
        chunk_ids = await storage.store_research_chunks(
            chunks=chunks, embeddings=embeddings, keyword="DEMO TEST"
        )

        print(f"{GREEN}✓ Stored {len(chunk_ids)} chunks:{RESET}")
        for i, cid in enumerate(chunk_ids):
            print(f"  - Chunk {i+1}: {cid}")

        # Create cache entries
        print(f"\n{BLUE}Creating cache entries...{RESET}")

        cache_keywords = [
            (
                "DEMO TEST",
                "This is a demo cache entry for testing Supabase visualization",
            ),
            (
                "AI Healthcare Demo",
                "Cached summary about AI in healthcare for dashboard viewing",
            ),
            ("Test Query", "Sample cached response to verify cache functionality"),
        ]

        for keyword, summary in cache_keywords:
            cache_id = await storage.store_cache_entry(
                keyword=keyword,
                research_summary=summary,
                chunk_ids=chunk_ids[:2],  # Associate with first 2 chunks
                metadata={
                    "demo": True,
                    "created_by": "populate_test_data.py",
                    "purpose": "dashboard_verification",
                },
            )
            print(f"{GREEN}✓ Created cache entry: {keyword}{RESET}")

        # Test retrieval to increment hit counts
        print(f"\n{BLUE}Testing cache retrieval (to increment hit counts)...{RESET}")

        for keyword, _ in cache_keywords:
            result = await storage.get_cached_response(keyword)
            if result:
                print(
                    f"{GREEN}✓ Retrieved cache for: {keyword} (hit_count will increase){RESET}"
                )

        # Get statistics
        print(f"\n{BLUE}Final statistics:{RESET}")
        stats = await storage.get_statistics()

        for key, value in stats.items():
            if key != "error":
                print(f"  - {key}: {value}")

        print(f"\n{YELLOW}=== Data Successfully Populated ==={RESET}")
        print(f"\n{YELLOW}Now check your Supabase dashboard:{RESET}")
        print(f"1. Go to https://supabase.com/dashboard")
        print(f"2. Select your project")
        print(f"3. Click 'Table Editor' in the sidebar")
        print(f"4. Look for entries with:")
        print(f"   - source_id starting with 'DEMO_'")
        print(f"   - keyword 'DEMO TEST'")
        print(f"   - metadata containing 'demo': true")

    except Exception as e:
        print(f"\n{YELLOW}Error: {e}{RESET}")
        import traceback

        traceback.print_exc()

    finally:
        await storage.close()


async def main():
    """Run the population script"""
    await populate_test_data()

    print(
        f"\n{YELLOW}Do you want to view a SQL query to check this data? (y/n): {RESET}",
        end="",
    )
    response = input().strip().lower()

    if response == "y":
        print(f"\n{BLUE}Copy and paste this SQL in Supabase SQL Editor:{RESET}")
        print(
            """
-- View test data with formatted output
SELECT 
    substring(id, 1, 20) as id_preview,
    substring(content, 1, 50) || '...' as content_preview,
    keyword,
    metadata->>'source' as source,
    created_at
FROM research_chunks
WHERE source_id LIKE 'DEMO_%'
ORDER BY created_at DESC;

-- View cache entries
SELECT 
    keyword,
    substring(research_summary, 1, 50) || '...' as summary_preview,
    hit_count,
    array_length(chunk_ids, 1) as associated_chunks,
    metadata->>'purpose' as purpose
FROM cache_entries
WHERE metadata->>'demo' = 'true'
ORDER BY created_at DESC;
"""
        )


if __name__ == "__main__":
    asyncio.run(main())
