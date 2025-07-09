#!/usr/bin/env python3
"""Test script to verify Tavily API authentication fixes."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from config import get_config
from tools import TavilyClient

async def test_tavily_auth():
    """Test all Tavily endpoints with fixed authentication."""
    print("🔍 Testing Tavily API Authentication Fix...\n")
    
    # Get config
    config = get_config()
    print(f"✓ Config loaded")
    print(f"✓ API Key exists: {'TAVILY_API_KEY' in os.environ}")
    
    async with TavilyClient(config) as client:
        print("\n1️⃣ Testing Search Endpoint...")
        try:
            search_result = await client.search("artificial intelligence")
            print(f"✅ Search successful! Found {len(search_result.results)} results")
            if search_result.results:
                print(f"   First result: {search_result.results[0].title[:50]}...")
        except Exception as e:
            print(f"❌ Search failed: {e}")
        
        print("\n2️⃣ Testing Map Endpoint...")
        try:
            map_result = await client.map("https://docs.python.org")
            urls_found = len(map_result.get("results", []))
            print(f"✅ Map successful! Found {urls_found} URLs")
        except Exception as e:
            print(f"❌ Map failed: {e}")
        
        print("\n3️⃣ Testing Extract Endpoint...")
        try:
            urls = ["https://en.wikipedia.org/wiki/Artificial_intelligence"]
            extract_result = await client.extract(urls, extract_depth="basic")
            extracted = len(extract_result.get("results", []))
            print(f"✅ Extract successful! Extracted content from {extracted} URLs")
        except Exception as e:
            print(f"❌ Extract failed: {e}")
        
        print("\n4️⃣ Testing Crawl Endpoint...")
        try:
            crawl_result = await client.crawl(
                "https://docs.python.org/3/tutorial/", 
                max_depth=1, 
                max_breadth=5
            )
            pages = len(crawl_result.get("results", []))
            print(f"✅ Crawl successful! Crawled {pages} pages")
        except Exception as e:
            print(f"❌ Crawl failed: {e}")
    
    print("\n✨ Authentication test complete!")

if __name__ == "__main__":
    asyncio.run(test_tavily_auth())