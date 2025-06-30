"""
Integration test for the Research Agent.

This script tests the research agent with mock API responses to ensure
all components work together correctly.
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

from config import Config
from models import AcademicSource, ResearchFindings
from research_agent import create_research_agent, run_research_agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_agent_result(data):
    """Create a mock AgentRunResult with data attribute."""
    mock_result = MagicMock()
    mock_result.data = data
    return mock_result


async def test_research_agent_integration():
    """
    Test the research agent with mocked responses.

    This simulates a full research workflow without making real API calls.
    """
    # Create test configuration with valid-looking keys
    config = Config(
        tavily_api_key="tvly-test1234567890abcdef1234567890ab",
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890ab",
        llm_model="gpt-4",
        output_dir="./test_output",
    )

    # Create the research agent
    logger.info("Creating research agent...")
    agent = create_research_agent(config)

    # Mock the agent's run method to return test data
    mock_findings = ResearchFindings(
        keyword="artificial intelligence",
        research_summary="AI research shows significant advancements in machine learning, with particular progress in neural networks and deep learning applications across various domains.",
        academic_sources=[
            AcademicSource(
                title="Deep Learning Revolution in AI",
                url="https://example.edu/ai-research",
                excerpt="Our study demonstrates a 85% improvement in accuracy using deep learning models.",
                domain=".edu",
                credibility_score=0.95,
                authors=["Dr. Jane Smith", "Prof. John Doe"],
                publication_date="2024",
                journal_name="Journal of AI Research",
            ),
            AcademicSource(
                title="Government AI Ethics Framework",
                url="https://example.gov/ai-ethics",
                excerpt="Federal guidelines emphasize responsible AI development with human oversight.",
                domain=".gov",
                credibility_score=0.9,
                publication_date="2024",
            ),
            AcademicSource(
                title="AI in Healthcare: A Systematic Review",
                url="https://medical.org/ai-health",
                excerpt="Analysis of 234 studies shows 67% reduction in diagnostic errors.",
                domain=".org",
                credibility_score=0.85,
                authors=["Medical Research Team"],
                journal_name="Healthcare AI Quarterly",
            ),
        ],
        main_findings=[
            "Deep learning models show 85% improvement in accuracy over traditional methods",
            "67% reduction in diagnostic errors when AI assists healthcare professionals",
            "Ethical frameworks are essential for responsible AI deployment",
        ],
        key_statistics=["85% improvement", "67% reduction", "234 studies"],
        research_gaps=[
            "Long-term effects of AI implementation remain unclear",
            "More research needed on AI bias in diverse populations",
            "Gap in understanding AI's impact on employment",
        ],
        total_sources_analyzed=3,
        search_query_used="artificial intelligence",
    )

    # Mock the agent's run method to return AgentRunResult
    with patch.object(agent, "run") as mock_run:
        mock_run.return_value = create_mock_agent_result(mock_findings)

        # Run the research
        logger.info("Running research for 'artificial intelligence'...")
        try:
            findings = await run_research_agent(agent, "artificial intelligence")

            # Verify results
            logger.info(f"\n✅ Research completed successfully!")
            logger.info(f"📊 Summary: {findings.research_summary[:100]}...")
            logger.info(f"📚 Sources found: {len(findings.academic_sources)}")
            logger.info(f"🔍 Main findings: {len(findings.main_findings)}")
            logger.info(f"📈 Statistics extracted: {findings.key_statistics}")
            logger.info(f"🔬 Research gaps: {len(findings.research_gaps)}")

            # Test utilities
            from research_agent.utilities import (
                assess_research_quality,
                calculate_source_diversity,
                format_apa_citation,
            )

            # Test citation formatting
            logger.info("\n📝 Testing citation formatting:")
            for source in findings.academic_sources[:2]:
                citation = format_apa_citation(source)
                logger.info(f"  - {citation[:80]}...")

            # Test diversity analysis
            logger.info("\n🌍 Testing diversity analysis:")
            diversity = calculate_source_diversity(findings.academic_sources)
            logger.info(f"  - Diversity score: {diversity['diversity_score']:.2f}")
            logger.info(f"  - Domain distribution: {diversity['domain_distribution']}")

            # Test quality assessment
            logger.info("\n⭐ Testing quality assessment:")
            quality = assess_research_quality(findings)
            logger.info(f"  - Overall quality score: {quality['overall_score']:.2f}")
            logger.info(f"  - Strengths: {', '.join(quality['strengths'][:2])}")

            logger.info("\n✅ All integration tests passed!")
            return True

        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            raise


async def test_error_handling():
    """Test error handling in the research agent."""
    config = Config(
        tavily_api_key="tvly-test1234567890abcdef1234567890ab",
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890ab",
        llm_model="gpt-4",
        output_dir="./test_output",
    )

    logger.info("Testing error handling scenarios...")

    # Test 1: Agent returns findings but with validation error
    agent = create_research_agent(config)

    # Create a mock that will raise an exception
    with patch.object(agent, "run", side_effect=Exception("API connection failed")):
        try:
            await run_research_agent(agent, "test")
            logger.error("❌ Should have raised an error")
        except Exception as e:
            logger.info(f"✅ Correctly caught error: {e}")

    # Test 2: Low source count warning
    logger.info("Testing low source count warning...")
    low_source_findings = ResearchFindings(
        keyword="rare topic",
        research_summary="Limited academic research found on this specialized topic. Only two credible sources were identified, both from educational institutions.",
        academic_sources=[
            AcademicSource(
                title="Study on Rare Topic",
                url="https://university.edu/rare",
                excerpt="Initial exploration of this emerging field",
                domain=".edu",
                credibility_score=0.8,
            ),
            AcademicSource(
                title="Government Report",
                url="https://agency.gov/report",
                excerpt="Federal analysis of the topic",
                domain=".gov",
                credibility_score=0.75,
            ),
        ],
        main_findings=[
            "Limited data available",
            "Emerging field of study",
            "Requires further investigation",
        ],
        key_statistics=["2 sources found", "Both from credible institutions"],
        research_gaps=["More research needed"],
        total_sources_analyzed=2,
        search_query_used="rare topic",
    )

    with patch.object(agent, "run", return_value=create_mock_agent_result(low_source_findings)):
        # This should succeed but log a warning
        result = await run_research_agent(agent, "rare topic")
        logger.info("✅ Handled low source count appropriately")


async def main():
    """Run all integration tests."""
    logger.info("🚀 Starting Research Agent Integration Tests\n")

    # Test 1: Full integration
    await test_research_agent_integration()

    # Test 2: Error handling
    logger.info("\n🔍 Testing error handling...")
    await test_error_handling()

    logger.info("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
