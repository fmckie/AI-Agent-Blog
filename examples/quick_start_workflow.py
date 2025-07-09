#!/usr/bin/env python3
"""
Quick start example for the enhanced research workflow.

This is a minimal example showing how to get started with the
new workflow capabilities in just a few lines of code.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from research_agent import create_research_agent, run_research_workflow


async def quick_research(keyword: str):
    """
    Perform research using the enhanced workflow system.
    
    Args:
        keyword: The topic to research
        
    Returns:
        ResearchFindings with comprehensive analysis
    """
    # Step 1: Get configuration
    config = get_config()
    
    # Step 2: Create research agent
    agent = create_research_agent(config)
    
    # Step 3: Run research workflow
    print(f"Researching: {keyword}")
    findings = await run_research_workflow(agent, keyword, config)
    
    # Step 4: Display results
    print(f"\n✅ Research Complete!")
    print(f"📚 Sources found: {len(findings.academic_sources)}")
    print(f"💡 Main findings: {len(findings.main_findings)}")
    print(f"📊 Key statistics: {len(findings.key_statistics)}")
    print(f"\nSummary: {findings.research_summary[:200]}...")
    
    return findings


# With progress tracking
async def research_with_progress(keyword: str):
    """
    Research with simple progress updates.
    """
    config = get_config()
    agent = create_research_agent(config)
    
    # Simple progress callback
    def show_progress(progress):
        print(f"Progress: {progress.get_completion_percentage():.0f}% - {progress.current_stage.value}")
    
    print(f"Researching: {keyword}\n")
    findings = await run_research_workflow(
        agent, keyword, config, 
        progress_callback=show_progress
    )
    
    print(f"\n✅ Done! Found {len(findings.academic_sources)} credible sources.")
    return findings


# Different strategies
async def compare_strategies(keyword: str):
    """
    Compare different research strategies.
    """
    config = get_config()
    agent = create_research_agent(config)
    
    for strategy in ["basic", "standard", "comprehensive"]:
        config.research_strategy = strategy
        print(f"\n🔍 Researching with {strategy} strategy...")
        
        findings = await run_research_workflow(agent, keyword, config)
        print(f"   → Found {len(findings.academic_sources)} sources")


# Main function
async def main():
    """Run quick examples."""
    print("🚀 QUICK START: Enhanced Research Workflow\n")
    
    # Example 1: Basic usage
    print("1️⃣ Basic Research:")
    await quick_research("artificial intelligence trends 2024")
    
    # Example 2: With progress
    print("\n2️⃣ Research with Progress:")
    await research_with_progress("quantum computing applications")
    
    # Example 3: Strategy comparison
    print("\n3️⃣ Strategy Comparison:")
    await compare_strategies("renewable energy")
    
    print("\n✨ Quick start complete! See research_workflow_example.py for advanced usage.")


if __name__ == "__main__":
    asyncio.run(main())