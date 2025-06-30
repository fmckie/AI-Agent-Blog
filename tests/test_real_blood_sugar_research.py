"""
Test script to demonstrate REAL research with actual API calls.

This script uses the actual Tavily API to find real academic sources
about blood sugar monitoring.
"""

import asyncio
import logging
from datetime import datetime

from config import get_config
from research_agent.utilities import (
    assess_research_quality,
    calculate_source_diversity,
    extract_research_themes,
    format_apa_citation,
)
from workflow import WorkflowOrchestrator

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_real_blood_sugar_research():
    """
    Test with REAL API calls to find actual academic sources.
    """
    try:
        # Load real configuration from .env
        logger.info("🔑 Loading configuration from .env file...")
        config = get_config()

        # Verify we have real API keys
        if config.tavily_api_key.startswith(
            "tvly-test"
        ) or config.openai_api_key.startswith("sk-test"):
            logger.error(
                "❌ Error: Still using test API keys. Please set real keys in .env file"
            )
            return

        logger.info("✅ Real API keys loaded successfully\n")

        # Create workflow orchestrator
        logger.info("🔬 Creating workflow orchestrator...")
        orchestrator = WorkflowOrchestrator(config)

        # Run ONLY the research phase (since Writer Agent is not implemented yet)
        keyword = "blood sugar monitoring"
        logger.info(f"🔍 Starting REAL research for: '{keyword}'")
        logger.info(
            "⏳ This may take 10-30 seconds as we search real academic databases...\n"
        )

        # Execute research with real API
        research_findings = await orchestrator.run_research(keyword)

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("📊 REAL RESEARCH FINDINGS: BLOOD SUGAR MONITORING")
        logger.info("=" * 70)

        # Summary
        logger.info(f"\n📝 EXECUTIVE SUMMARY:")
        logger.info(f"{research_findings.research_summary}")

        # Main findings
        logger.info(f"\n🔍 KEY FINDINGS ({len(research_findings.main_findings)}):")
        for i, finding in enumerate(research_findings.main_findings, 1):
            logger.info(f"{i}. {finding}")

        # Statistics
        logger.info(
            f"\n📈 KEY STATISTICS FOUND ({len(research_findings.key_statistics)}):"
        )
        for stat in research_findings.key_statistics[:10]:  # Show top 10
            logger.info(f"   • {stat}")

        # Academic sources with REAL URLs
        logger.info(
            f"\n📚 REAL ACADEMIC SOURCES ({len(research_findings.academic_sources)} found):"
        )
        logger.info("🌐 These are actual URLs you can visit:\n")

        for i, source in enumerate(research_findings.academic_sources, 1):
            logger.info(f"{i}. {source.title}")
            logger.info(f"   🔗 URL: {source.url}")
            logger.info(f"   📍 Domain: {source.domain}")
            logger.info(f"   🎯 Credibility: {source.credibility_score:.2f}")
            logger.info(f"   📝 Excerpt: {source.excerpt[:200]}...")
            if source.authors:
                logger.info(f"   👥 Authors: {', '.join(source.authors[:3])}")
            if source.publication_date:
                logger.info(f"   📅 Published: {source.publication_date}")
            logger.info("")

        # Research gaps
        logger.info(f"🔬 RESEARCH GAPS IDENTIFIED:")
        for i, gap in enumerate(research_findings.research_gaps, 1):
            logger.info(f"{i}. {gap}")

        # Quality assessment
        logger.info("\n" + "=" * 70)
        logger.info("⭐ RESEARCH QUALITY ASSESSMENT")
        logger.info("=" * 70)

        quality = assess_research_quality(research_findings)
        logger.info(f"\n📊 Overall Quality Score: {quality['overall_score']:.2f}/1.00")

        logger.info(f"\n✅ Strengths:")
        for strength in quality["strengths"]:
            logger.info(f"   • {strength}")

        if quality["weaknesses"]:
            logger.info(f"\n⚠️ Areas for Improvement:")
            for weakness in quality["weaknesses"]:
                logger.info(f"   • {weakness}")

        # Diversity analysis
        diversity = calculate_source_diversity(research_findings.academic_sources)
        logger.info(f"\n🌍 Source Diversity:")
        logger.info(f"   • Domain Distribution: {diversity['domain_distribution']}")
        logger.info(f"   • Diversity Score: {diversity['diversity_score']:.2f}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"real_blood_sugar_research_{timestamp}.json"

        import json

        with open(output_file, "w") as f:
            json.dump(research_findings.model_dump(), f, indent=2, default=str)

        logger.info(f"\n💾 Full results saved to: {output_file}")
        logger.info("\n✅ Real research completed successfully!")

        # Show search query used
        logger.info(
            f"\n🔎 Tavily Search Query Used: '{research_findings.search_query_used}'"
        )
        logger.info(
            f"📊 Total Sources Analyzed: {research_findings.total_sources_analyzed}"
        )

        return research_findings

    except Exception as e:
        logger.error(f"\n❌ Error during research: {e}")
        logger.error("Please check:")
        logger.error("1. Your .env file has valid API keys")
        logger.error("2. You have internet connection")
        logger.error("3. Your API keys have not exceeded rate limits")
        raise


if __name__ == "__main__":
    # Run the real test
    logger.info("🚀 Starting REAL API test for blood sugar monitoring research\n")
    asyncio.run(test_real_blood_sugar_research())
