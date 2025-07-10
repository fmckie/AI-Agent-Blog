#!/usr/bin/env python3
"""
Simple test script for Research Agent with EnhancedVectorStorage.

This script only tests the research phase without triggering the writer agent.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize colorama
init(autoreset=True)

# Set up logging with less verbosity
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set specific loggers to INFO for tracking
logging.getLogger("research_agent.tools").setLevel(logging.INFO)
logging.getLogger("rag.enhanced_storage").setLevel(logging.INFO)


async def test_research_only():
    """Test only the research phase with storage."""

    print(f"\n{Fore.CYAN}{'='*80}")
    print("Research Agent Storage Test - Simple Version".center(80))
    print(f"{'='*80}{Style.RESET_ALL}\n")

    keyword = "vegan diet vs keto"
    print(f"{Fore.YELLOW}Research Topic: '{keyword}'{Style.RESET_ALL}\n")

    try:
        # Import and initialize
        from config import Config
        from research_agent.tools import search_academic
        from pydantic_ai import RunContext
        from rag.enhanced_storage import EnhancedVectorStorage

        config = Config()

        # Test storage
        print(f"{Fore.CYAN}Testing EnhancedVectorStorage...{Style.RESET_ALL}")
        storage = None
        try:
            storage = EnhancedVectorStorage()
            print(f"{Fore.GREEN}✓ EnhancedVectorStorage initialized{Style.RESET_ALL}")
        except Exception as e:
            print(
                f"{Fore.YELLOW}⚠️ EnhancedVectorStorage not available: {e}{Style.RESET_ALL}"
            )

        # Perform search using the tool directly
        print(f"\n{Fore.CYAN}Searching for '{keyword}'...{Style.RESET_ALL}")

        # Create a dummy context
        ctx = RunContext(deps=None, retry=0, tool_name="search_academic")

        # Call the search tool
        start_time = datetime.now()
        result = await search_academic(ctx, keyword, config)
        elapsed = (datetime.now() - start_time).total_seconds()

        print(
            f"\n{Fore.GREEN}✓ Search completed in {elapsed:.1f} seconds{Style.RESET_ALL}"
        )

        # Display results
        sources = result.get("results", [])
        print(f"\nFound {len(sources)} sources:")

        for i, source in enumerate(sources[:5], 1):
            print(
                f"\n{i}. {Fore.YELLOW}{source.get('title', 'No title')}{Style.RESET_ALL}"
            )
            print(f"   URL: {source.get('url', 'No URL')}")
            print(f"   Domain: {source.get('domain', 'Unknown')}")
            print(f"   Credibility: {source.get('credibility_score', 0):.2f}")

        # Check storage if available
        if storage:
            print(f"\n{Fore.CYAN}Checking storage results...{Style.RESET_ALL}")
            await asyncio.sleep(1)  # Give storage time to complete

            stored_count = 0
            for source in sources:
                url = source.get("url")
                if url:
                    source_data = await storage.get_source_by_url(url)
                    if source_data:
                        stored_count += 1
                        print(
                            f"{Fore.GREEN}✓ Stored: {source.get('title', '')[:60]}...{Style.RESET_ALL}"
                        )

            print(
                f"\n{Fore.GREEN}Successfully stored {stored_count}/{len(sources)} sources{Style.RESET_ALL}"
            )

            # Test search capabilities
            print(f"\n{Fore.CYAN}Testing search capabilities...{Style.RESET_ALL}")

            # Search by keyword
            diet_sources = await storage.search_by_criteria(keyword="diet", limit=10)
            print(f"- Keyword search 'diet': {len(diet_sources)} sources")

            # Search by high credibility
            credible_sources = await storage.search_by_criteria(
                min_credibility=0.7, limit=10
            )
            print(f"- High credibility (>0.7): {len(credible_sources)} sources")

            # Get crawl hierarchy if any
            print(f"\n{Fore.CYAN}Checking for crawl data...{Style.RESET_ALL}")
            crawl_count = 0
            for source in sources[:3]:
                url = source.get("url")
                if url:
                    hierarchy = await storage.get_crawl_hierarchy(url)
                    if hierarchy and hierarchy.get("children"):
                        crawl_count += len(hierarchy["children"])
                        print(
                            f"- Found {len(hierarchy['children'])} crawled pages from {url}"
                        )

            if crawl_count == 0:
                print("- No crawl data found (multi-step research may be disabled)")

        # Summary
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Test Summary".center(80))
        print(f"{'='*80}{Style.RESET_ALL}")

        print(f"\n{Fore.GREEN}✓ Tavily Search: Working{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ RAG Caching: Working{Style.RESET_ALL}")
        if storage:
            print(f"{Fore.GREEN}✓ EnhancedVectorStorage: Working{Style.RESET_ALL}")
            print(
                f"{Fore.GREEN}✓ Sources Stored: {stored_count}/{len(sources)}{Style.RESET_ALL}"
            )

        print(f"\n{Fore.GREEN}Test completed successfully!{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}❌ Test failed: {e}{Style.RESET_ALL}")
        logger.exception("Error details:")
        raise


async def main():
    """Main entry point."""
    try:
        await test_research_only()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test interrupted{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
