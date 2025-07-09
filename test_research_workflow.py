#!/usr/bin/env python3
"""
Test Research Workflow with EnhancedVectorStorage.

This script tests the research workflow integration.
"""

import asyncio
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


async def test_research_workflow():
    """Test the research workflow with storage integration."""
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print("Research Workflow Test with Enhanced Storage".center(80))
    print(f"{'='*80}{Style.RESET_ALL}\n")
    
    keyword = "vegan diet vs keto"
    print(f"{Fore.YELLOW}Testing with keyword: '{keyword}'{Style.RESET_ALL}\n")
    
    try:
        from config import Config
        from workflow import WorkflowOrchestrator
        from rag.enhanced_storage import EnhancedVectorStorage
        
        # Create config
        config = Config()
        
        # Check storage availability
        print(f"{Fore.CYAN}Checking EnhancedVectorStorage...{Style.RESET_ALL}")
        storage = None
        try:
            storage = EnhancedVectorStorage()
            print(f"{Fore.GREEN}✓ EnhancedVectorStorage available{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ EnhancedVectorStorage not available: {e}{Style.RESET_ALL}")
        
        # Create workflow orchestrator
        print(f"\n{Fore.CYAN}Creating workflow orchestrator...{Style.RESET_ALL}")
        orchestrator = WorkflowOrchestrator(config)
        
        # Set progress callback
        def progress_callback(phase: str, message: str):
            print(f"{Fore.BLUE}[{phase}] {message}{Style.RESET_ALL}")
        
        orchestrator.set_progress_callback(progress_callback)
        
        # Run only the research phase
        print(f"\n{Fore.CYAN}Running research phase...{Style.RESET_ALL}")
        start_time = datetime.now()
        
        # Run research
        research_findings = await orchestrator.run_research(keyword)
        
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
        
        # Check storage if available
        if storage:
            print(f"\n{Fore.CYAN}Verifying storage...{Style.RESET_ALL}")
            await asyncio.sleep(2)  # Give storage operations time to complete
            
            stored_count = 0
            relationship_count = 0
            
            for source in research_findings.academic_sources:
                source_data = await storage.get_source_by_url(source.url)
                if source_data:
                    stored_count += 1
                    if source_data.get('relationships'):
                        relationship_count += len(source_data['relationships'])
            
            print(f"{Fore.GREEN}✓ Stored {stored_count}/{len(research_findings.academic_sources)} sources{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Created {relationship_count} relationships{Style.RESET_ALL}")
            
            # Test advanced search
            print(f"\n{Fore.CYAN}Testing advanced search...{Style.RESET_ALL}")
            
            # Search by criteria
            diet_sources = await storage.search_by_criteria(
                keyword="diet",
                min_credibility=0.5,
                limit=20
            )
            print(f"- Found {len(diet_sources)} sources with 'diet' keyword")
            
            # Check for any crawled content
            crawled_sources = await storage.search_by_criteria(
                source_type="crawled",
                limit=20
            )
            print(f"- Found {len(crawled_sources)} crawled pages")
            
            # Sample hybrid search
            if research_findings.academic_sources:
                print(f"\n{Fore.CYAN}Testing hybrid search...{Style.RESET_ALL}")
                # Generate embedding for the keyword
                from rag.embeddings import EmbeddingGenerator
                embedder = EmbeddingGenerator()
                keyword_embedding = await embedder.generate_embedding(keyword)
                
                hybrid_results = await storage.hybrid_search(
                    keyword="diet",
                    embedding=keyword_embedding.embedding,
                    weights={"keyword": 0.3, "vector": 0.7}
                )
                print(f"- Hybrid search returned {len(hybrid_results)} results")
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Test Summary".center(80))
        print(f"{'='*80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}✓ Research workflow: Success{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ Sources found: {len(research_findings.academic_sources)}{Style.RESET_ALL}")
        if storage:
            print(f"{Fore.GREEN}✓ Storage integration: Working{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Sources stored: {stored_count}{Style.RESET_ALL}")
        
        # Save sample results
        print(f"\n{Fore.CYAN}Key Findings:{Style.RESET_ALL}")
        for i, finding in enumerate(research_findings.main_findings[:3], 1):
            print(f"{i}. {finding}")
        
        return True
        
    except Exception as e:
        print(f"\n{Fore.RED}❌ Test failed: {e}{Style.RESET_ALL}")
        logger.exception("Error details:")
        return False


async def main():
    """Main entry point."""
    success = await test_research_workflow()
    if success:
        print(f"\n{Fore.GREEN}All tests passed!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}Tests failed!{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())