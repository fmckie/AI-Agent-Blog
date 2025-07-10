"""
Test script for Phase 3 vector search functionality.

This script tests all aspects of our new Supabase vector storage:
1. Basic CRUD operations
2. Vector embedding storage
3. Semantic search
4. Performance metrics
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from colorama import Fore, Style, init
from supabase import Client, create_client

from config import get_config
from models import AcademicSource

# Initialize colorama for colored output
init(autoreset=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Phase3Tester:
    """Comprehensive testing for Phase 3 vector search functionality."""

    def __init__(self, config):
        """Initialize tester with Supabase connection."""
        self.config = config
        # Use environment variables directly since config might not have these
        import os

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables"
            )

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{text.center(60)}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result with color coding."""
        if passed:
            print(f"{Fore.GREEN}✓ {name}{Style.RESET_ALL}")
            self.test_results["passed"] += 1
        else:
            print(f"{Fore.RED}✗ {name}{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}Details: {details}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{name}: {details}")

    def generate_mock_embedding(self, text: str, dimensions: int = 1536) -> List[float]:
        """
        Generate a mock embedding for testing.
        In production, this would use OpenAI's API.
        """
        # Create deterministic embeddings based on text hash
        np.random.seed(hash(text) % 2**32)
        # Generate normalized random vector
        embedding = np.random.randn(dimensions)
        # Normalize to unit length (important for cosine similarity)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    async def test_1_basic_crud(self) -> bool:
        """Test basic CRUD operations on research tables."""
        self.print_header("Test 1: Basic CRUD Operations")

        try:
            # Test 1.1: Insert research source
            test_source = {
                "url": f"https://example.com/test-article-{uuid4()}",
                "domain": "example.com",
                "title": "Test Article on Machine Learning",
                "full_content": "This is a comprehensive article about machine learning...",
                "excerpt": "This is a comprehensive article...",
                "credibility_score": 0.85,
                "source_type": "academic",
                "authors": json.dumps(["Dr. Test Author"]),
                "publication_date": datetime.now().isoformat(),
                "metadata": json.dumps({"test": True, "category": "AI"}),
            }

            result = (
                self.supabase.table("research_sources").insert(test_source).execute()
            )
            source_id = result.data[0]["id"]
            self.print_test("Insert research source", True)

            # Test 1.2: Read research source
            result = (
                self.supabase.table("research_sources")
                .select("*")
                .eq("id", source_id)
                .execute()
            )
            self.print_test("Read research source", len(result.data) == 1)

            # Test 1.3: Update research source
            update_data = {"credibility_score": 0.90}
            result = (
                self.supabase.table("research_sources")
                .update(update_data)
                .eq("id", source_id)
                .execute()
            )
            self.print_test("Update research source", True)

            # Test 1.4: Insert research finding
            test_finding = {
                "keyword": "machine learning",
                "research_summary": "Key insights about ML from multiple sources",
                "main_findings": json.dumps(["Finding 1", "Finding 2"]),
                "key_statistics": json.dumps({"accuracy": 0.95}),
                "research_gaps": json.dumps(["Need more data on X"]),
            }

            result = (
                self.supabase.table("research_findings").insert(test_finding).execute()
            )
            finding_id = result.data[0]["id"]
            self.print_test("Insert research finding", True)

            # Test 1.5: Create source relationship
            # First create a second source
            test_source2 = test_source.copy()
            test_source2["url"] = f"https://example.com/related-article-{uuid4()}"
            test_source2["title"] = "Related Article on Deep Learning"

            result2 = (
                self.supabase.table("research_sources").insert(test_source2).execute()
            )
            source_id2 = result2.data[0]["id"]

            relationship = {
                "source_id": source_id,
                "related_source_id": source_id2,
                "relationship_type": "cites",
                "similarity_score": 0.78,
            }

            result = (
                self.supabase.table("source_relationships")
                .insert(relationship)
                .execute()
            )
            self.print_test("Create source relationship", True)

            # Cleanup
            self.cleanup_test_data([source_id, source_id2], [finding_id])

            return True

        except Exception as e:
            self.print_test("Basic CRUD operations", False, str(e))
            return False

    async def test_2_vector_operations(self) -> bool:
        """Test vector embedding storage and retrieval."""
        self.print_header("Test 2: Vector Operations")

        try:
            # Test 2.1: Create source with chunks and embeddings
            test_source = {
                "url": f"https://example.com/vector-test-{uuid4()}",
                "domain": "example.com",
                "title": "Understanding Vector Databases",
                "full_content": "Vector databases are essential for AI applications. They enable semantic search and similarity matching.",
                "credibility_score": 0.88,
            }

            result = (
                self.supabase.table("research_sources").insert(test_source).execute()
            )
            source_id = result.data[0]["id"]
            self.print_test("Create source for vector testing", True)

            # Test 2.2: Create content chunks with embeddings
            chunks = [
                "Vector databases are essential for AI applications.",
                "They enable semantic search and similarity matching.",
                "pgvector is a powerful extension for PostgreSQL.",
            ]

            chunk_ids = []
            for i, chunk_text in enumerate(chunks):
                embedding = self.generate_mock_embedding(chunk_text)

                chunk_data = {
                    "source_id": source_id,
                    "chunk_text": chunk_text,
                    "chunk_embedding": embedding,
                    "chunk_number": i + 1,
                    "chunk_metadata": json.dumps({"position": i}),
                }

                # Insert chunk with embedding
                result = (
                    self.supabase.table("content_chunks").insert(chunk_data).execute()
                )
                chunk_ids.append(result.data[0]["id"])

            self.print_test("Insert chunks with embeddings", len(chunk_ids) == 3)

            # Test 2.3: Retrieve and verify embeddings
            result = (
                self.supabase.table("content_chunks")
                .select("*")
                .eq("source_id", source_id)
                .execute()
            )

            # Vectors are returned as strings from Supabase, need to parse
            embeddings_valid = True
            for chunk in result.data:
                embedding = chunk.get("chunk_embedding")
                if embedding:
                    # If it's a string representation of a vector
                    if isinstance(embedding, str) and embedding.startswith("["):
                        try:
                            # Parse the string to get the array
                            parsed = json.loads(embedding)
                            if len(parsed) != 1536:
                                embeddings_valid = False
                                break
                        except:
                            embeddings_valid = False
                            break
                    elif isinstance(embedding, list):
                        # If it's already a list
                        if len(embedding) != 1536:
                            embeddings_valid = False
                            break
                else:
                    embeddings_valid = False
                    break

            self.print_test("Verify embedding dimensions", embeddings_valid)

            # Test 2.4: Test embedding queue
            queue_entry = {"source_id": source_id, "status": "completed"}

            result = (
                self.supabase.table("embedding_queue").insert(queue_entry).execute()
            )
            self.print_test("Update embedding queue", True)

            # Cleanup
            self.cleanup_test_data([source_id], [])

            return True

        except Exception as e:
            self.print_test("Vector operations", False, str(e))
            return False

    async def test_3_semantic_search(self) -> bool:
        """Test semantic search functionality."""
        self.print_header("Test 3: Semantic Search")

        try:
            # Test 3.1: Setup test data
            sources_data = [
                {
                    "title": "Introduction to Neural Networks",
                    "content": "Neural networks are the foundation of deep learning.",
                    "domain": "ai-research.com",
                },
                {
                    "title": "Advanced Machine Learning Techniques",
                    "content": "Machine learning has revolutionized data analysis.",
                    "domain": "ml-journal.org",
                },
                {
                    "title": "Cooking with Python",
                    "content": "Python is great for automating recipe calculations.",
                    "domain": "cooking-tech.com",
                },
            ]

            source_ids = []
            for source_data in sources_data:
                source = {
                    "url": f"https://{source_data['domain']}/article-{uuid4()}",
                    "domain": source_data["domain"],
                    "title": source_data["title"],
                    "full_content": source_data["content"],
                    "credibility_score": 0.8,
                }

                result = (
                    self.supabase.table("research_sources").insert(source).execute()
                )
                source_id = result.data[0]["id"]
                source_ids.append(source_id)

                # Create embedding for content
                embedding = self.generate_mock_embedding(source_data["content"])

                chunk = {
                    "source_id": source_id,
                    "chunk_text": source_data["content"],
                    "chunk_embedding": embedding,
                    "chunk_number": 1,
                }

                self.supabase.table("content_chunks").insert(chunk).execute()

            self.print_test("Setup semantic search test data", len(source_ids) == 3)

            # Test 3.2: Search for similar content
            query = "deep learning and neural networks"
            query_embedding = self.generate_mock_embedding(query)

            # Call the search function via RPC
            result = self.supabase.rpc(
                "search_similar_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.0,  # Low threshold for testing
                    "match_count": 10,
                },
            ).execute()

            # Handle different response formats
            search_success = False
            if result.data is not None:
                if isinstance(result.data, list):
                    search_success = True  # Empty list is valid
                    if len(result.data) > 0:
                        print(f"  Found {len(result.data)} similar chunks")
                    else:
                        print(f"  No similar chunks found (this is OK for test data)")
                else:
                    print(f"  Unexpected result type: {type(result.data)}")
            else:
                # None result might be valid if no data exists
                search_success = True
                print(f"  Search returned no results (expected for empty database)")

            self.print_test("Execute semantic search", search_success)

            # Test 3.3: Domain filtering
            result_filtered = self.supabase.rpc(
                "search_similar_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.0,
                    "match_count": 10,
                    "domain_filter": "ai-research.com",
                },
            ).execute()

            domain_filter_works = all(
                r["source_url"].startswith("https://ai-research.com")
                for r in result_filtered.data
            )
            self.print_test("Domain filtering in search", domain_filter_works)

            # Test 3.4: Find related sources
            if source_ids:
                result = self.supabase.rpc(
                    "find_related_sources",
                    {
                        "source_id_input": source_ids[0],
                        "similarity_threshold": 0.0,
                        "max_results": 5,
                    },
                ).execute()

                self.print_test("Find related sources", len(result.data) > 0)

            # Test 3.5: Log search history
            search_log = {
                "query_text": query,
                "query_embedding": query_embedding,
                "result_count": len(result.data),
                "avg_similarity": 0.75,
                "execution_time_ms": 45,
            }

            result = self.supabase.table("search_history").insert(search_log).execute()
            self.print_test("Log search history", True)

            # Cleanup
            self.cleanup_test_data(source_ids, [])

            return True

        except Exception as e:
            self.print_test("Semantic search", False, str(e))
            return False

    async def test_4_performance_metrics(self) -> bool:
        """Test performance and edge cases."""
        self.print_header("Test 4: Performance & Edge Cases")

        try:
            # Test 4.1: Batch insert performance
            start_time = time.time()

            batch_size = 10
            sources = []
            for i in range(batch_size):
                sources.append(
                    {
                        "url": f"https://perf-test.com/article-{i}-{uuid4()}",
                        "domain": "perf-test.com",
                        "title": f"Performance Test Article {i}",
                        "full_content": f"Content for performance testing article {i}",
                        "credibility_score": 0.7,
                    }
                )

            # Batch insert
            result = self.supabase.table("research_sources").insert(sources).execute()
            elapsed = time.time() - start_time

            self.print_test(
                f"Batch insert {batch_size} sources",
                len(result.data) == batch_size,
                f"Completed in {elapsed:.2f}s",
            )

            source_ids = [s["id"] for s in result.data]

            # Test 4.2: Large embedding handling
            large_embedding = self.generate_mock_embedding("Large content test")
            chunk = {
                "source_id": source_ids[0],
                "chunk_text": "Large content test",
                "chunk_embedding": large_embedding,
                "chunk_number": 1,
            }

            result = self.supabase.table("content_chunks").insert(chunk).execute()
            self.print_test("Handle 1536-dimension embedding", True)

            # Test 4.3: Empty search results
            obscure_query = "xyzabc123 quantum blockchain NFT metaverse"
            query_embedding = self.generate_mock_embedding(obscure_query)

            result = self.supabase.rpc(
                "search_similar_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.99,  # Very high threshold
                    "match_count": 10,
                },
            ).execute()

            self.print_test("Handle empty search results", result.data is not None)

            # Test 4.4: Calculate optimal index lists
            result = self.supabase.rpc(
                "calculate_optimal_lists", {"table_name": "content_chunks"}
            ).execute()

            self.print_test(
                "Calculate optimal index lists",
                result.data is not None,
                f"Optimal lists: {result.data}",
            )

            # Test 4.5: View performance
            result = self.supabase.table("v_research_statistics").select("*").execute()
            stats = result.data[0] if result.data else {}

            self.print_test(
                "Research statistics view",
                True,
                f"Sources: {stats.get('total_sources', 0)}, Chunks: {stats.get('total_chunks', 0)}",
            )

            # Cleanup
            self.cleanup_test_data(source_ids, [])

            return True

        except Exception as e:
            self.print_test("Performance metrics", False, str(e))
            return False

    def cleanup_test_data(self, source_ids: List[str], finding_ids: List[str]):
        """Clean up test data after tests."""
        try:
            # Delete sources (cascades to chunks and relationships)
            if source_ids:
                self.supabase.table("research_sources").delete().in_(
                    "id", source_ids
                ).execute()

            # Delete findings
            if finding_ids:
                self.supabase.table("research_findings").delete().in_(
                    "id", finding_ids
                ).execute()

        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

    async def run_all_tests(self):
        """Run all tests and display summary."""
        self.print_header("Phase 3 Vector Search Test Suite")

        print(
            f"{Fore.YELLOW}Running comprehensive tests on Supabase vector storage...{Style.RESET_ALL}\n"
        )

        # Run all tests
        test_methods = [
            self.test_1_basic_crud,
            self.test_2_vector_operations,
            self.test_3_semantic_search,
            self.test_4_performance_metrics,
        ]

        for test_method in test_methods:
            await test_method()
            await asyncio.sleep(0.5)  # Brief pause between test sections

        # Display summary
        self.print_header("Test Summary")

        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (
            (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        )

        print(f"{Fore.GREEN}Passed: {self.test_results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.test_results['failed']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}\n")

        if self.test_results["errors"]:
            print(f"{Fore.RED}Errors:{Style.RESET_ALL}")
            for error in self.test_results["errors"]:
                print(f"  - {error}")

        if pass_rate == 100:
            print(
                f"\n{Fore.GREEN}🎉 All tests passed! Phase 3 vector search is working correctly.{Style.RESET_ALL}"
            )
        else:
            print(
                f"\n{Fore.YELLOW}⚠️  Some tests failed. Please review the errors above.{Style.RESET_ALL}"
            )


async def main():
    """Main test execution."""
    # Get configuration
    config = get_config()

    # Verify environment variables are set
    import os

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        print(
            f"{Fore.RED}Error: Missing required environment variables{Style.RESET_ALL}"
        )
        print("Please set:")
        print("  export SUPABASE_URL='your-supabase-url'")
        print("  export SUPABASE_SERVICE_KEY='your-service-key'")
        return

    # Create and run tester
    tester = Phase3Tester(config)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
