#!/usr/bin/env python3
"""
Manual test script for Research Agent with EnhancedVectorStorage integration.

This script tests the research workflow with the keyword "vegan diet vs keto"
and verifies that sources are properly stored in EnhancedVectorStorage.
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_research_with_storage():
    """Test the research agent with EnhancedVectorStorage integration."""
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print("Research Agent + EnhancedVectorStorage Integration Test".center(80))
    print(f"{'='*80}{Style.RESET_ALL}\n")
    
    # Test keyword
    keyword = "vegan diet vs keto"
    print(f"{Fore.YELLOW}Research Topic: '{keyword}'{Style.RESET_ALL}\n")
    
    try:
        # Import required modules
        from config import Config
        from research_agent import create_research_agent, run_research_agent
        from rag.enhanced_storage import EnhancedVectorStorage
        
        # Create configuration
        config = Config()
        
        # Verify API keys
        if not config.openai_api_key:
            print(f"{Fore.RED}❌ OpenAI API key not found in environment{Style.RESET_ALL}")
            return
        if not config.tavily_api_key:
            print(f"{Fore.RED}❌ Tavily API key not found in environment{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}✓ API keys loaded{Style.RESET_ALL}")
        
        # Test EnhancedVectorStorage availability
        print(f"\n{Fore.CYAN}Testing EnhancedVectorStorage...{Style.RESET_ALL}")
        try:
            storage = EnhancedVectorStorage()
            print(f"{Fore.GREEN}✓ EnhancedVectorStorage initialized successfully{Style.RESET_ALL}")
            
            # Test connection
            test_source = await storage.get_source_by_url("https://test.nonexistent.url")
            print(f"{Fore.GREEN}✓ Storage connection verified{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ EnhancedVectorStorage: {e}{Style.RESET_ALL}")
            print("Continuing with basic storage only...")
            storage = None
        
        # Create research agent
        print(f"\n{Fore.CYAN}Creating Research Agent...{Style.RESET_ALL}")
        agent = create_research_agent(config)
        print(f"{Fore.GREEN}✓ Research Agent created{Style.RESET_ALL}")
        
        # Run research
        print(f"\n{Fore.CYAN}Starting research on '{keyword}'...{Style.RESET_ALL}")
        print("This may take 30-60 seconds...\n")
        
        start_time = datetime.now()
        research_findings = await run_research_agent(agent, keyword)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n{Fore.GREEN}✓ Research completed in {elapsed:.1f} seconds{Style.RESET_ALL}")
        
        # Display results
        print(f"\n{Fore.CYAN}Research Results:{Style.RESET_ALL}")
        print(f"- Sources found: {len(research_findings.academic_sources)}")
        print(f"- Main findings: {len(research_findings.main_findings)}")
        print(f"- Key statistics: {len(research_findings.key_statistics)}")
        print(f"- Research gaps: {len(research_findings.research_gaps)}")
        
        # Show top sources
        print(f"\n{Fore.CYAN}Top Sources:{Style.RESET_ALL}")
        for i, source in enumerate(research_findings.academic_sources[:5], 1):
            print(f"\n{i}. {Fore.YELLOW}{source.title}{Style.RESET_ALL}")
            print(f"   URL: {source.url}")
            print(f"   Domain: {source.domain}")
            print(f"   Credibility: {source.credibility_score:.2f}")
            print(f"   Type: {source.source_type}")
        
        # Check storage results if available
        if storage:
            print(f"\n{Fore.CYAN}Checking EnhancedVectorStorage...{Style.RESET_ALL}")
            
            stored_count = 0
            for source in research_findings.academic_sources:
                source_data = await storage.get_source_by_url(source.url)
                if source_data:
                    stored_count += 1
                    print(f"{Fore.GREEN}✓ Found in storage: {source.title[:50]}...{Style.RESET_ALL}")
                    
                    # Check relationships
                    if source_data.get("relationships"):
                        print(f"  - Relationships: {len(source_data['relationships'])}")
                    if source_data.get("chunk_count", 0) > 0:
                        print(f"  - Chunks: {source_data['chunk_count']}")
                    if source_data.get("embedding_status") == "completed":
                        print(f"  - Embeddings: ✓")
            
            print(f"\n{Fore.GREEN}Stored {stored_count}/{len(research_findings.academic_sources)} sources in EnhancedVectorStorage{Style.RESET_ALL}")
            
            # Test advanced search
            print(f"\n{Fore.CYAN}Testing advanced search capabilities...{Style.RESET_ALL}")
            
            # Search by domain
            edu_sources = await storage.search_by_criteria(
                domain=".edu",
                min_credibility=0.7,
                keyword="diet",
                limit=5
            )
            print(f"- Found {len(edu_sources)} .edu sources with 'diet' keyword")
            
            # Test multi-step research if enabled
            if config.enable_multi_step_research:
                print(f"\n{Fore.CYAN}Multi-step research was enabled{Style.RESET_ALL}")
                print("This includes: search → extract → crawl → synthesis")
        
        # Save results
        print(f"\n{Fore.CYAN}Saving test results...{Style.RESET_ALL}")
        
        results = {
            "test_timestamp": datetime.now().isoformat(),
            "keyword": keyword,
            "research_duration_seconds": elapsed,
            "sources_found": len(research_findings.academic_sources),
            "storage_enabled": storage is not None,
            "sources_stored": stored_count if storage else 0,
            "top_sources": [
                {
                    "title": s.title,
                    "url": s.url,
                    "credibility": s.credibility_score,
                    "domain": s.domain
                }
                for s in research_findings.academic_sources[:5]
            ],
            "main_findings": research_findings.main_findings[:3],
            "research_summary": research_findings.research_summary[:500] + "..."
        }
        
        output_file = f"test_research_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"{Fore.GREEN}✓ Results saved to {output_file}{Style.RESET_ALL}")
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Test Summary".center(80))
        print(f"{'='*80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}✓ Research Agent: Working{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ Tavily Integration: Working{Style.RESET_ALL}")
        if storage:
            print(f"{Fore.GREEN}✓ EnhancedVectorStorage: Working{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Source Storage: {stored_count} sources stored{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️ EnhancedVectorStorage: Not available{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}Test completed successfully!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"\n{Fore.RED}❌ Test failed: {e}{Style.RESET_ALL}")
        logger.exception("Test error details:")
        raise


async def main():
    """Main entry point."""
    try:
        await test_research_with_storage()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Test failed: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())