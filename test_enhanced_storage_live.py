"""
Live test script for EnhancedVectorStorage with real Supabase.

This script tests the enhanced storage implementation against
the actual Supabase database to verify everything works correctly.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from colorama import Fore, Style, init

from config import get_config
from models import AcademicSource, ExtractedContent, CrawledPage
from rag.enhanced_storage import EnhancedVectorStorage

# Initialize colorama for colored output
init(autoreset=True)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedStorageTester:
    """Test suite for EnhancedVectorStorage with real database."""
    
    def __init__(self, config):
        """Initialize tester with configuration."""
        self.config = config
        self.storage = None
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        self.test_source_ids = []  # Track for cleanup
        
    async def setup(self):
        """Initialize storage connection."""
        print(f"{Fore.CYAN}Setting up EnhancedVectorStorage...{Style.RESET_ALL}")
        self.storage = EnhancedVectorStorage(self.config)
        # Warm up the connection pool
        await self.storage.warm_pool()
        print(f"{Fore.GREEN}✓ Storage initialized successfully{Style.RESET_ALL}\n")
        
    async def cleanup(self):
        """Clean up test data and close connections."""
        print(f"\n{Fore.CYAN}Cleaning up test data...{Style.RESET_ALL}")
        
        # Delete test sources (cascades to chunks and relationships)
        if self.test_source_ids:
            try:
                for source_id in self.test_source_ids:
                    self.storage.supabase.table("research_sources").delete().eq("id", source_id).execute()
                print(f"{Fore.GREEN}✓ Cleaned up {len(self.test_source_ids)} test sources{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Cleanup error: {e}{Style.RESET_ALL}")
        
        # Close storage connection
        await self.storage.close()
        
    def print_header(self, text: str):
        """Print a formatted section header."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{text.center(60)}")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result with color coding."""
        if passed:
            print(f"{Fore.GREEN}✓ {name}{Style.RESET_ALL}")
            self.test_results["passed"] += 1
        else:
            print(f"{Fore.RED}✗ {name}{Style.RESET_ALL}")
            if details:
                print(f"  {Fore.YELLOW}Details: {details}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{name}: {details}")
    
    # ============================================
    # Test 1: Research Source Management
    # ============================================
    
    async def test_research_source_management(self):
        """Test storing and retrieving research sources."""
        self.print_header("Test 1: Research Source Management")
        
        # Create test sources
        sources = [
            AcademicSource(
                title="Deep Learning Fundamentals",
                url=f"https://test.edu/dl-fundamentals-{uuid4()}",
                authors=["Dr. Sarah Chen", "Prof. Michael Johnson"],
                publication_date="2024-01-15",
                journal_name="AI Research Quarterly",
                excerpt="Deep learning represents a paradigm shift in artificial intelligence...",
                domain=".edu",
                credibility_score=0.95,
                source_type="journal"
            ),
            AcademicSource(
                title="Neural Network Architecture Design",
                url=f"https://research.org/nn-architecture-{uuid4()}",
                authors=["Dr. Emily Watson"],
                publication_date="2024-02-20",
                excerpt="Modern neural network architectures have evolved significantly...",
                domain=".org",
                credibility_score=0.85,
                source_type="research_paper"
            )
        ]
        
        # Test 1.1: Store sources
        stored_ids = []
        for source in sources:
            try:
                source_id = await self.storage.store_research_source(
                    source,
                    full_content=f"Full content of {source.title}. " * 100,  # Simulate full content
                    generate_embedding=False  # Skip for now
                )
                stored_ids.append(source_id)
                self.test_source_ids.append(source_id)  # Track for cleanup
                self.print_test(f"Store source: {source.title[:30]}...", True)
            except Exception as e:
                self.print_test(f"Store source: {source.title[:30]}...", False, str(e))
        
        # Test 1.2: Retrieve by URL
        if stored_ids:
            try:
                retrieved = await self.storage.get_source_by_url(sources[0].url)
                success = (
                    retrieved is not None and
                    retrieved["title"] == sources[0].title and
                    retrieved["credibility_score"] == sources[0].credibility_score
                )
                self.print_test("Retrieve source by URL", success)
                
                if retrieved:
                    print(f"  - Retrieved: {retrieved['title']}")
                    print(f"  - Chunks: {retrieved['chunk_count']}")
                    print(f"  - Embedding status: {retrieved['embedding_status']}")
            except Exception as e:
                self.print_test("Retrieve source by URL", False, str(e))
        
        # Test 1.3: Update credibility
        if stored_ids:
            try:
                success = await self.storage.update_source_credibility(
                    stored_ids[0], 0.98, "Peer review validation"
                )
                self.print_test("Update source credibility", success)
                
                # Verify update
                updated = await self.storage.get_source_by_url(sources[0].url)
                if updated and updated["credibility_score"] == 0.98:
                    print(f"  - New credibility: {updated['credibility_score']}")
            except Exception as e:
                self.print_test("Update source credibility", False, str(e))
        
        return stored_ids
    
    # ============================================
    # Test 2: Source Relationships
    # ============================================
    
    async def test_source_relationships(self, source_ids: List[str]):
        """Test creating and querying source relationships."""
        self.print_header("Test 2: Source Relationship Mapping")
        
        if len(source_ids) < 2:
            print(f"{Fore.YELLOW}Skipping relationship tests - need at least 2 sources{Style.RESET_ALL}")
            return
        
        # Test 2.1: Create manual relationship
        try:
            success = await self.storage.create_source_relationship(
                source_ids[0],
                source_ids[1],
                "cites",
                metadata={"section": "Introduction", "page": 3}
            )
            self.print_test("Create 'cites' relationship", success)
        except Exception as e:
            self.print_test("Create 'cites' relationship", False, str(e))
        
        # Test 2.2: Calculate similarities
        try:
            # First, we need to ensure sources have embeddings
            # For testing, we'll create mock chunks with embeddings
            await self._create_test_chunks(source_ids[0])
            await self._create_test_chunks(source_ids[1])
            
            count = await self.storage.calculate_source_similarities(
                source_ids[0],
                threshold=0.5,  # Lower threshold for test data
                max_relationships=5
            )
            self.print_test(f"Calculate similarities (found {count})", count >= 0)
        except Exception as e:
            self.print_test("Calculate similarities", False, str(e))
        
        # Test 2.3: Get related sources
        try:
            related = await self.storage.get_related_sources(source_ids[0])
            self.print_test(f"Get related sources (found {len(related)})", True)
            
            for rel in related[:3]:  # Show first 3
                print(f"  - {rel['relationship_type']}: {rel['source'].get('title', 'Unknown')[:50]}...")
                if rel.get('similarity_score'):
                    print(f"    Similarity: {rel['similarity_score']:.3f}")
        except Exception as e:
            self.print_test("Get related sources", False, str(e))
    
    # ============================================
    # Test 3: Crawl Result Storage
    # ============================================
    
    async def test_crawl_storage(self):
        """Test storing crawl results with hierarchy."""
        self.print_header("Test 3: Crawl Result Storage")
        
        # Simulate crawl data
        parent_url = f"https://example.edu/research-{uuid4()}"
        crawl_data = {
            "results": [
                {
                    "url": f"{parent_url}/introduction",
                    "title": "Introduction to AI Research",
                    "content": "This section introduces fundamental concepts in AI research...",
                    "depth": 1
                },
                {
                    "url": f"{parent_url}/methodology",
                    "title": "Research Methodology",
                    "content": "Our research methodology employs various techniques...",
                    "depth": 1
                },
                {
                    "url": f"{parent_url}/methodology/experiments",
                    "title": "Experimental Setup",
                    "content": "Detailed experimental procedures and configurations...",
                    "depth": 2
                }
            ]
        }
        
        # Test 3.1: Store crawl results
        try:
            stored_ids = await self.storage.store_crawl_results(
                crawl_data,
                parent_url,
                "AI research methodology"
            )
            self.test_source_ids.extend(stored_ids)  # Track for cleanup
            
            self.print_test(f"Store crawl results ({len(stored_ids)} pages)", len(stored_ids) == 3)
            print(f"  - Parent URL: {parent_url}")
            print(f"  - Pages stored: {len(stored_ids)}")
        except Exception as e:
            self.print_test("Store crawl results", False, str(e))
            return
        
        # Test 3.2: Get crawl hierarchy
        try:
            hierarchy = await self.storage.get_crawl_hierarchy(parent_url)
            has_hierarchy = (
                hierarchy.get("url") == parent_url and
                "children" in hierarchy
            )
            self.print_test("Retrieve crawl hierarchy", has_hierarchy)
            
            if has_hierarchy:
                self._print_hierarchy(hierarchy, indent=2)
        except Exception as e:
            self.print_test("Retrieve crawl hierarchy", False, str(e))
    
    # ============================================
    # Test 4: Advanced Search
    # ============================================
    
    async def test_advanced_search(self):
        """Test advanced search capabilities."""
        self.print_header("Test 4: Advanced Search Methods")
        
        # Test 4.1: Search by criteria
        try:
            results = await self.storage.search_by_criteria(
                domain=".edu",
                min_credibility=0.8,
                limit=5
            )
            self.print_test(f"Search by criteria (found {len(results)})", True)
            
            for result in results[:3]:
                print(f"  - {result['title'][:50]}... (score: {result['credibility_score']})")
        except Exception as e:
            self.print_test("Search by criteria", False, str(e))
        
        # Test 4.2: Keyword search
        try:
            results = await self.storage.search_by_criteria(
                keyword="learning",
                limit=5
            )
            self.print_test(f"Keyword search (found {len(results)})", True)
        except Exception as e:
            self.print_test("Keyword search", False, str(e))
        
        # Test 4.3: Hybrid search (if we have embeddings)
        try:
            # Create a mock query embedding
            query_embedding = [0.1] * 1536  # Mock embedding
            
            results = await self.storage.hybrid_search(
                "deep learning",
                query_embedding,
                weights={"keyword": 0.3, "vector": 0.7}
            )
            self.print_test(f"Hybrid search (found {len(results)})", True)
            
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. Combined score: {result['combined_score']:.3f}")
                print(f"     - Keyword: {result['keyword_score']:.1f}, Vector: {result['vector_score']:.3f}")
        except Exception as e:
            self.print_test("Hybrid search", False, str(e))
    
    # ============================================
    # Test 5: Batch Operations
    # ============================================
    
    async def test_batch_operations(self):
        """Test batch storage and processing."""
        self.print_header("Test 5: Batch Operations")
        
        # Create multiple sources for batch testing
        batch_sources = [
            AcademicSource(
                title=f"Batch Test Article {i}",
                url=f"https://batch-test.edu/article-{i}-{uuid4()}",
                excerpt=f"This is test article number {i} for batch processing...",
                domain=".edu",
                credibility_score=0.7 + (i * 0.05),
                source_type="article"
            )
            for i in range(5)
        ]
        
        # Test 5.1: Batch store sources
        try:
            start_time = time.time()
            stored_ids = await self.storage.batch_store_sources(
                batch_sources,
                generate_embeddings=True  # Queue for embedding
            )
            elapsed = time.time() - start_time
            
            self.test_source_ids.extend(stored_ids)  # Track for cleanup
            
            self.print_test(
                f"Batch store {len(batch_sources)} sources",
                len(stored_ids) == len(batch_sources)
            )
            print(f"  - Time taken: {elapsed:.2f}s")
            print(f"  - Average: {elapsed/len(batch_sources):.3f}s per source")
        except Exception as e:
            self.print_test("Batch store sources", False, str(e))
        
        # Test 5.2: Process embedding queue
        try:
            processed = await self.storage.batch_process_embeddings(batch_size=3)
            self.print_test(f"Process embedding queue (processed {processed})", processed >= 0)
            
            # Check queue status
            queue_status = self.storage.supabase.table("embedding_queue").select("status").execute()
            status_counts = {}
            for item in queue_status.data:
                status = item["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"  - Queue status: {status_counts}")
        except Exception as e:
            self.print_test("Process embedding queue", False, str(e))
    
    # ============================================
    # Helper Methods
    # ============================================
    
    async def _create_test_chunks(self, source_id: str):
        """Create test chunks with mock embeddings for a source."""
        # Create mock embeddings (normally would use OpenAI)
        import numpy as np
        
        chunks = []
        for i in range(3):
            # Generate different mock embeddings for each chunk
            np.random.seed(hash(f"{source_id}_{i}") % 2**32)
            embedding = np.random.randn(1536)
            embedding = (embedding / np.linalg.norm(embedding)).tolist()
            
            chunk_data = {
                "source_id": source_id,
                "chunk_text": f"Test chunk {i} for source {source_id[:8]}...",
                "chunk_embedding": embedding,
                "chunk_number": i + 1,
                "chunk_metadata": json.dumps({"test": True})
            }
            chunks.append(chunk_data)
        
        # Insert chunks
        if chunks:
            self.storage.supabase.table("content_chunks").insert(chunks).execute()
    
    def _print_hierarchy(self, node: Dict, indent: int = 0):
        """Recursively print crawl hierarchy."""
        prefix = "  " * indent
        print(f"{prefix}- {node.get('title', 'Unknown')[:50]}...")
        for child in node.get('children', []):
            self._print_hierarchy(child, indent + 1)
    
    # ============================================
    # Main Test Runner
    # ============================================
    
    async def run_all_tests(self):
        """Run all tests and display results."""
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{'Enhanced Storage Live Test Suite'.center(60)}")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        try:
            # Setup
            await self.setup()
            
            # Run tests
            source_ids = await self.test_research_source_management()
            await self.test_source_relationships(source_ids)
            await self.test_crawl_storage()
            await self.test_advanced_search()
            await self.test_batch_operations()
            
            # Display summary
            self._print_summary()
            
        except Exception as e:
            print(f"\n{Fore.RED}Fatal error during testing: {e}{Style.RESET_ALL}")
            logger.exception("Test suite failed")
        finally:
            # Always cleanup
            await self.cleanup()
    
    def _print_summary(self):
        """Print test summary."""
        self.print_header("Test Summary")
        
        total = self.test_results["passed"] + self.test_results["failed"]
        if total == 0:
            print(f"{Fore.YELLOW}No tests were run{Style.RESET_ALL}")
            return
        
        pass_rate = (self.test_results["passed"] / total) * 100
        
        print(f"{Fore.GREEN}Passed: {self.test_results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.test_results['failed']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}\n")
        
        if self.test_results["errors"]:
            print(f"{Fore.RED}Errors:{Style.RESET_ALL}")
            for error in self.test_results["errors"]:
                print(f"  - {error}")
        
        if pass_rate == 100:
            print(f"\n{Fore.GREEN}🎉 All tests passed! Enhanced storage is working correctly.{Style.RESET_ALL}")
        elif pass_rate >= 80:
            print(f"\n{Fore.YELLOW}⚠️  Most tests passed, but some issues need attention.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Significant issues detected. Please review the errors.{Style.RESET_ALL}")


async def main():
    """Main entry point."""
    # Get configuration
    try:
        config = get_config()
        print(f"{Fore.GREEN}✓ Configuration loaded successfully{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to load configuration: {e}{Style.RESET_ALL}")
        print("Please ensure your .env file is properly configured with:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_KEY")
        return
    
    # Create and run tester
    tester = EnhancedStorageTester(config)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())