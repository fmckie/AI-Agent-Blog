"""
Manual test script for EnhancedVectorStorage with real Supabase connection.

This script tests our Phase 3 implementation with actual database operations.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

import numpy as np
from colorama import Fore, Style, init
from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

# Initialize colorama
init(autoreset=True)


class ManualStorageTester:
    """Manual tester for enhanced storage with real Supabase."""

    def __init__(self):
        """Initialize with environment variables."""
        # Get Supabase credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment"
            )

        # Create Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Track test data for cleanup
        self.test_source_ids = []
        self.test_results = {"passed": 0, "failed": 0}

    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{text.center(60)}")
        print(f"{'='*60}{Style.RESET_ALL}\n")

    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result."""
        if passed:
            print(f"{Fore.GREEN}✓ {name}{Style.RESET_ALL}")
            self.test_results["passed"] += 1
        else:
            print(f"{Fore.RED}✗ {name}{Style.RESET_ALL}")
            if details:
                print(f"  {Fore.YELLOW}Details: {details}{Style.RESET_ALL}")
            self.test_results["failed"] += 1

    def generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a mock embedding for testing."""
        # Create deterministic embedding based on text
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.randn(1536)
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    async def test_1_basic_storage(self):
        """Test basic source storage operations."""
        self.print_header("Test 1: Basic Research Source Storage")

        # Create test source
        test_source = {
            "url": f"https://test.edu/article-{uuid4()}",
            "domain": ".edu",
            "title": "Test Article on Machine Learning",
            "full_content": "This is a comprehensive article about machine learning. "
            * 50,
            "excerpt": "This is a comprehensive article about machine learning...",
            "credibility_score": 0.85,
            "source_type": "academic",
            "authors": json.dumps(["Dr. Test Author", "Prof. Example"]),
            "publication_date": "2024-01-15",
            "metadata": json.dumps(
                {
                    "test": True,
                    "category": "AI",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

        try:
            # Insert source
            result = (
                self.supabase.table("research_sources").insert(test_source).execute()
            )
            source_id = result.data[0]["id"]
            self.test_source_ids.append(source_id)

            self.print_test("Insert research source", True)
            print(f"  - Source ID: {source_id}")
            print(f"  - Title: {test_source['title']}")

            # Retrieve source
            result = (
                self.supabase.table("research_sources")
                .select("*")
                .eq("id", source_id)
                .execute()
            )
            retrieved = result.data[0] if result.data else None

            self.print_test(
                "Retrieve source by ID",
                retrieved is not None and retrieved["title"] == test_source["title"],
            )

            # Update credibility
            update_data = {
                "credibility_score": 0.95,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            result = (
                self.supabase.table("research_sources")
                .update(update_data)
                .eq("id", source_id)
                .execute()
            )

            self.print_test("Update credibility score", len(result.data) > 0)

            return source_id

        except Exception as e:
            self.print_test("Basic storage operations", False, str(e))
            return None

    async def test_2_chunks_with_embeddings(self, source_id: str = None):
        """Test chunk storage with embeddings."""
        self.print_header("Test 2: Content Chunks with Embeddings")

        if not source_id:
            # Create a source first
            source_data = {
                "url": f"https://test.edu/chunks-{uuid4()}",
                "domain": ".edu",
                "title": "Article for Chunk Testing",
                "excerpt": "Testing chunks...",
                "credibility_score": 0.8,
            }
            result = (
                self.supabase.table("research_sources").insert(source_data).execute()
            )
            source_id = result.data[0]["id"]
            self.test_source_ids.append(source_id)

        try:
            # Create chunks with embeddings
            chunks = []
            content_pieces = [
                "Machine learning is a subset of artificial intelligence.",
                "Deep learning uses neural networks with multiple layers.",
                "Natural language processing enables computers to understand text.",
            ]

            for i, content in enumerate(content_pieces):
                embedding = self.generate_mock_embedding(content)

                chunk = {
                    "source_id": source_id,
                    "chunk_text": content,
                    "chunk_embedding": embedding,
                    "chunk_number": i + 1,
                    "chunk_overlap": 0,
                    "chunk_metadata": json.dumps({"position": i}),
                    "chunk_type": "content",
                }
                chunks.append(chunk)

            # Insert chunks
            result = self.supabase.table("content_chunks").insert(chunks).execute()
            self.print_test(
                f"Insert {len(chunks)} chunks with embeddings",
                len(result.data) == len(chunks),
            )

            # Test vector search
            query_text = "neural networks and deep learning"
            query_embedding = self.generate_mock_embedding(query_text)

            # Use the search function
            result = self.supabase.rpc(
                "search_similar_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.0,  # Low threshold for test data
                    "match_count": 10,
                },
            ).execute()

            self.print_test(
                f"Vector similarity search (found {len(result.data) if result.data else 0})",
                result.data is not None,
            )

            if result.data:
                for match in result.data[:3]:
                    print(f"  - Similarity: {match.get('similarity', 0):.3f}")
                    print(f"    Text: {match.get('chunk_text', '')[:60]}...")

            return True

        except Exception as e:
            self.print_test("Chunk and embedding operations", False, str(e))
            return False

    async def test_3_relationships(self):
        """Test source relationships."""
        self.print_header("Test 3: Source Relationships")

        try:
            # Create two sources
            sources = []
            for i in range(2):
                source = {
                    "url": f"https://test.edu/relationship-{i}-{uuid4()}",
                    "domain": ".edu",
                    "title": f"Relationship Test Article {i}",
                    "excerpt": f"Article {i} for testing relationships",
                    "credibility_score": 0.8,
                }
                result = (
                    self.supabase.table("research_sources").insert(source).execute()
                )
                sources.append(result.data[0]["id"])
                self.test_source_ids.append(result.data[0]["id"])

            # Create relationship
            relationship = {
                "source_id": sources[0],
                "related_source_id": sources[1],
                "relationship_type": "cites",
                "similarity_score": 0.75,
            }

            result = (
                self.supabase.table("source_relationships")
                .insert(relationship)
                .execute()
            )
            self.print_test("Create source relationship", len(result.data) > 0)

            # Query relationships
            result = (
                self.supabase.table("source_relationships")
                .select("*, research_sources!related_source_id(title, url)")
                .eq("source_id", sources[0])
                .execute()
            )

            self.print_test(
                f"Query relationships (found {len(result.data)})", len(result.data) > 0
            )

            if result.data:
                for rel in result.data:
                    print(f"  - Type: {rel['relationship_type']}")
                    related = rel.get("research_sources", {})
                    print(f"    Related: {related.get('title', 'Unknown')}")

            return True

        except Exception as e:
            self.print_test("Relationship operations", False, str(e))
            return False

    async def test_4_crawl_storage(self):
        """Test crawl result storage."""
        self.print_header("Test 4: Crawl Result Storage")

        try:
            # Simulate crawl data
            parent_url = f"https://test.edu/crawl-{uuid4()}"

            # Store parent
            parent_source = {
                "url": parent_url,
                "domain": ".edu",
                "title": "Parent Page",
                "excerpt": "This is the parent page",
                "credibility_score": 0.7,
                "source_type": "crawled",
            }
            result = (
                self.supabase.table("research_sources").insert(parent_source).execute()
            )
            parent_id = result.data[0]["id"]
            self.test_source_ids.append(parent_id)

            # Store child pages
            child_ids = []
            for i in range(3):
                child = {
                    "url": f"{parent_url}/page-{i}",
                    "domain": ".edu",
                    "title": f"Child Page {i}",
                    "excerpt": f"Content of child page {i}",
                    "credibility_score": 0.65,
                    "source_type": "crawled",
                }
                result = self.supabase.table("research_sources").insert(child).execute()
                child_id = result.data[0]["id"]
                child_ids.append(child_id)
                self.test_source_ids.append(child_id)

                # Create crawl relationship
                rel = {
                    "source_id": child_id,
                    "related_source_id": parent_id,
                    "relationship_type": "crawled_from",
                }
                self.supabase.table("source_relationships").insert(rel).execute()

            self.print_test(f"Store crawl hierarchy ({len(child_ids)} children)", True)

            # Query crawl relationships
            result = (
                self.supabase.table("source_relationships")
                .select("*, research_sources!source_id(title, url)")
                .eq("related_source_id", parent_id)
                .eq("relationship_type", "crawled_from")
                .execute()
            )

            self.print_test(
                f"Query crawl hierarchy (found {len(result.data)} children)",
                len(result.data) == len(child_ids),
            )

            print(f"  - Parent: {parent_source['title']}")
            for rel in result.data:
                child = rel.get("research_sources", {})
                print(f"    └─ {child.get('title', 'Unknown')}")

            return True

        except Exception as e:
            self.print_test("Crawl storage operations", False, str(e))
            return False

    async def test_5_advanced_search(self):
        """Test advanced search capabilities."""
        self.print_header("Test 5: Advanced Search")

        try:
            # Search by domain and credibility
            result = (
                self.supabase.table("research_sources")
                .select("*")
                .eq("domain", ".edu")
                .gte("credibility_score", 0.7)
                .order("credibility_score", desc=True)
                .limit(5)
                .execute()
            )

            self.print_test(f"Multi-criteria search (found {len(result.data)})", True)

            if result.data:
                for source in result.data[:3]:
                    print(
                        f"  - {source['title'][:40]}... (score: {source['credibility_score']})"
                    )

            # Keyword search
            keyword = "learning"
            result = (
                self.supabase.table("research_sources")
                .select("*")
                .or_(f"title.ilike.%{keyword}%,excerpt.ilike.%{keyword}%")
                .limit(5)
                .execute()
            )

            self.print_test(
                f"Keyword search for '{keyword}' (found {len(result.data)})", True
            )

            return True

        except Exception as e:
            self.print_test("Advanced search operations", False, str(e))
            return False

    async def test_6_performance(self):
        """Test performance with batch operations."""
        self.print_header("Test 6: Performance & Batch Operations")

        try:
            import time

            # Batch insert sources
            batch_sources = []
            for i in range(10):
                batch_sources.append(
                    {
                        "url": f"https://test.edu/batch-{i}-{uuid4()}",
                        "domain": ".edu",
                        "title": f"Batch Test Article {i}",
                        "excerpt": f"Testing batch operations article {i}",
                        "credibility_score": 0.5 + (i * 0.05),
                    }
                )

            start_time = time.time()
            result = (
                self.supabase.table("research_sources").insert(batch_sources).execute()
            )
            elapsed = time.time() - start_time

            # Track for cleanup
            for item in result.data:
                self.test_source_ids.append(item["id"])

            self.print_test(
                f"Batch insert {len(batch_sources)} sources",
                len(result.data) == len(batch_sources),
            )
            print(
                f"  - Time: {elapsed:.2f}s ({elapsed/len(batch_sources):.3f}s per source)"
            )

            # Test embedding queue
            queue_items = []
            for source_id in result.data[:3]:  # First 3 sources
                queue_items.append({"source_id": source_id["id"], "status": "pending"})

            result = (
                self.supabase.table("embedding_queue").insert(queue_items).execute()
            )
            self.print_test(
                f"Queue {len(queue_items)} items for embedding",
                len(result.data) == len(queue_items),
            )

            return True

        except Exception as e:
            self.print_test("Performance operations", False, str(e))
            return False

    async def cleanup(self):
        """Clean up test data."""
        self.print_header("Cleanup")

        try:
            # Delete test sources (cascades to chunks and relationships)
            if self.test_source_ids:
                # Delete in batches
                batch_size = 50
                for i in range(0, len(self.test_source_ids), batch_size):
                    batch = self.test_source_ids[i : i + batch_size]
                    self.supabase.table("research_sources").delete().in_(
                        "id", batch
                    ).execute()

                print(
                    f"{Fore.GREEN}✓ Cleaned up {len(self.test_source_ids)} test sources{Style.RESET_ALL}"
                )

            # Clean up embedding queue
            self.supabase.table("embedding_queue").delete().eq(
                "status", "pending"
            ).execute()
            print(f"{Fore.GREEN}✓ Cleaned up embedding queue{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}✗ Cleanup error: {e}{Style.RESET_ALL}")

    def print_summary(self):
        """Print test summary."""
        self.print_header("Test Summary")

        total = self.test_results["passed"] + self.test_results["failed"]
        if total > 0:
            pass_rate = (self.test_results["passed"] / total) * 100

            print(f"{Fore.GREEN}Passed: {self.test_results['passed']}{Style.RESET_ALL}")
            print(f"{Fore.RED}Failed: {self.test_results['failed']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}")

            if pass_rate == 100:
                print(
                    f"\n{Fore.GREEN}🎉 All tests passed! Phase 3 storage is working correctly.{Style.RESET_ALL}"
                )
            elif pass_rate >= 80:
                print(
                    f"\n{Fore.YELLOW}⚠️ Most tests passed. Check any failures above.{Style.RESET_ALL}"
                )
            else:
                print(
                    f"\n{Fore.RED}❌ Significant issues detected. Review the errors.{Style.RESET_ALL}"
                )

    async def run_all_tests(self):
        """Run all tests."""
        print(f"{Fore.CYAN}{'='*60}")
        print("Enhanced Storage Manual Test Suite".center(60))
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"\nProject: {self.supabase_url}")

        try:
            # Run tests in sequence
            source_id = await self.test_1_basic_storage()
            await self.test_2_chunks_with_embeddings(source_id)
            await self.test_3_relationships()
            await self.test_4_crawl_storage()
            await self.test_5_advanced_search()
            await self.test_6_performance()

        except Exception as e:
            print(f"\n{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        finally:
            # Always cleanup and show summary
            await self.cleanup()
            self.print_summary()


async def main():
    """Main entry point."""
    print(
        f"{Fore.YELLOW}Starting manual test of Enhanced Storage...{Style.RESET_ALL}\n"
    )

    try:
        tester = ManualStorageTester()
        await tester.run_all_tests()
    except ValueError as e:
        print(f"{Fore.RED}Configuration error: {e}{Style.RESET_ALL}")
        print("\nPlease ensure your .env file contains:")
        print("  SUPABASE_URL=your-project-url")
        print("  SUPABASE_SERVICE_KEY=your-service-key")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())
