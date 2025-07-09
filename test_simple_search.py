#!/usr/bin/env python3
"""Simple test of just the search functionality."""

import asyncio
from config import get_config
from tools import TavilyClient

async def test_search():
    config = get_config()
    
    async with TavilyClient(config) as client:
        print("Testing basic search...")
        result = await client.search("test query")
        print(f"Success! Found {len(result.results)} results")
        return result

if __name__ == "__main__":
    asyncio.run(test_search())