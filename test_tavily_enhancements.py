#!/usr/bin/env python3
"""
Test script for Tavily API enhancements.

This script tests the new extract, crawl, and map methods
to ensure they're working correctly.
"""

import asyncio
import logging
from datetime import datetime

from config import get_config
from tools import TavilyClient, extract_url_content, crawl_website, map_website

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_search(client: TavilyClient, query: str):
    """Test basic search functionality."""
    logger.info(f"Testing search for: {query}")
    try:
        results = await client.search(query)
        logger.info(f"Found {len(results.results)} results")
        for i, result in enumerate(results.results[:3]):
            logger.info(
                f"  {i+1}. {result.title} (credibility: {result.credibility_score:.2f})"
            )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return None


async def test_extract(client: TavilyClient, urls: list):
    """Test content extraction."""
    logger.info(f"Testing extract for {len(urls)} URLs")
    try:
        results = await client.extract(urls)
        extracted = results.get("results", [])
        logger.info(f"Successfully extracted {len(extracted)} pages")
        for result in extracted:
            content_len = len(result.get("raw_content", ""))
            logger.info(f"  - {result.get('url')}: {content_len} characters")
        return results
    except Exception as e:
        logger.error(f"Extract failed: {e}")
        return None


async def test_crawl(client: TavilyClient, url: str):
    """Test website crawling."""
    logger.info(f"Testing crawl for: {url}")
    try:
        results = await client.crawl(
            url,
            max_depth=1,  # Shallow crawl for testing
            instructions="Find research and academic content",
        )
        pages = results.get("results", [])
        logger.info(f"Crawled {len(pages)} pages")
        for i, page in enumerate(pages[:5]):
            logger.info(f"  {i+1}. {page.get('title', 'No title')}")
        return results
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        return None


async def test_map(client: TavilyClient, url: str):
    """Test website mapping."""
    logger.info(f"Testing map for: {url}")
    try:
        results = await client.map(url)
        links = results.get("links", [])
        logger.info(f"Found {len(links)} links")
        for link in links[:10]:
            logger.info(f"  - {link}")
        return results
    except Exception as e:
        logger.error(f"Map failed: {e}")
        return None


async def test_convenience_functions(config):
    """Test the convenience functions."""
    logger.info("\nTesting convenience functions...")

    # Test extract_url_content
    try:
        urls = ["https://en.wikipedia.org/wiki/Artificial_intelligence"]
        result = await extract_url_content(urls, config)
        logger.info(f"extract_url_content: {len(result.get('results', []))} results")
    except Exception as e:
        logger.error(f"extract_url_content failed: {e}")

    # Test crawl_website
    try:
        result = await crawl_website("https://www.python.org", config, max_depth=1)
        logger.info(f"crawl_website: {len(result.get('results', []))} pages")
    except Exception as e:
        logger.error(f"crawl_website failed: {e}")

    # Test map_website
    try:
        result = await map_website("https://www.python.org", config)
        logger.info(f"map_website: {len(result.get('links', []))} links")
    except Exception as e:
        logger.error(f"map_website failed: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting Tavily enhancement tests...")

    # Get configuration
    config = get_config()

    # Test with context manager
    async with TavilyClient(config) as client:
        # 1. Test search (existing functionality)
        search_results = await test_search(client, "artificial intelligence research")

        # 2. Test extract with URLs from search
        if search_results and search_results.results:
            urls = [r.url for r in search_results.results[:2]]
            await test_extract(client, urls)

        # 3. Test crawl on a known good site
        await test_crawl(client, "https://www.python.org")

        # 4. Test map
        await test_map(client, "https://www.python.org")

    # 5. Test convenience functions
    await test_convenience_functions(config)

    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
