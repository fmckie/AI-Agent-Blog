#!/usr/bin/env python3
"""Simple test to check workflow functionality."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from config import get_config
from research_agent import create_research_agent
from research_agent.workflow import ResearchWorkflow


async def test_workflow():
    """Test basic workflow functionality."""
    print("Testing Phase 2 Workflow...")

    # Check environment
    print(f"TAVILY_API_KEY exists: {'TAVILY_API_KEY' in os.environ}")
    print(f"OPENAI_API_KEY exists: {'OPENAI_API_KEY' in os.environ}")

    # Get config
    config = get_config()
    print(f"Research strategy: {config.research_strategy}")

    # Create agent
    agent = create_research_agent(config)
    print("✓ Agent created")

    # Create workflow
    workflow = ResearchWorkflow(agent, config)
    print("✓ Workflow created")

    # Check stages
    stages = workflow._get_stages_for_strategy(config.research_strategy)
    print(f"✓ Stages for {config.research_strategy}: {len(stages)} stages")

    # Test simple search
    print("\nTesting basic search...")
    try:
        from tools import search_web

        results = await search_web("test query", config, max_results=1)
        print(f"✓ Search successful: {len(results)} results")
    except Exception as e:
        print(f"✗ Search failed: {e}")

    print("\nWorkflow test complete!")


if __name__ == "__main__":
    asyncio.run(test_workflow())
