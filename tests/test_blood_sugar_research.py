"""
Test script to demonstrate research agent with "blood sugar monitoring" keyword.

This script shows what the research agent finds for a real-world health topic.
"""

import asyncio
import json
import logging
from datetime import datetime
from unittest.mock import patch

from config import Config
from models import AcademicSource, ResearchFindings
from research_agent import create_research_agent, run_research_agent
from research_agent.utilities import (
    assess_research_quality,
    calculate_source_diversity,
    extract_research_themes,
    format_apa_citation,
)

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def create_mock_agent_result(data):
    """Create a mock AgentRunResult with data attribute."""
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.data = data
    return mock_result


async def test_blood_sugar_research():
    """
    Test research agent with blood sugar monitoring keyword.

    This simulates what the agent would find for this health-related topic.
    """
    # Create configuration
    config = Config(
        tavily_api_key="tvly-test1234567890abcdef1234567890ab",
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890ab",
        llm_model="gpt-4",
        output_dir="./test_output",
    )

    # Create the research agent
    logger.info("🔬 Creating research agent for blood sugar monitoring research...\n")
    agent = create_research_agent(config)

    # Mock realistic research findings for blood sugar monitoring
    mock_findings = ResearchFindings(
        keyword="blood sugar monitoring",
        research_summary=(
            "Recent academic research on blood sugar monitoring reveals significant advancements in continuous glucose monitoring (CGM) technology "
            "and non-invasive measurement methods. Studies from Harvard Medical School (2024) demonstrate that modern CGM devices achieve 95% accuracy "
            "compared to traditional fingerstick methods. Research from Stanford University shows that real-time monitoring reduces hypoglycemic events "
            "by 72% in Type 1 diabetes patients. Multiple studies emphasize the importance of personalized monitoring schedules based on individual "
            "glycemic patterns and lifestyle factors."
        ),
        academic_sources=[
            AcademicSource(
                title="Advances in Continuous Glucose Monitoring: A Systematic Review",
                url="https://medicine.harvard.edu/cgm-review-2024",
                authors=["Dr. Sarah Chen", "Prof. Michael Roberts", "Dr. Emily Watson"],
                publication_date="March 2024",
                journal_name="Journal of Diabetes Technology",
                excerpt="Our systematic review of 147 studies shows CGM devices now achieve 95% accuracy with MARD values below 9%. Real-world data from 12,000 patients demonstrates significant improvements in glycemic control.",
                domain=".edu",
                credibility_score=0.95,
                source_type="journal",
            ),
            AcademicSource(
                title="Non-Invasive Blood Glucose Monitoring: Current State and Future Directions",
                url="https://engineering.stanford.edu/non-invasive-glucose",
                authors=["Dr. James Liu", "Dr. Patricia Anderson"],
                publication_date="February 2024",
                journal_name="Biomedical Engineering Review",
                excerpt="Novel optical and electromagnetic sensing technologies show promise for non-invasive monitoring. Our trials with 500 participants achieved 88% correlation with laboratory values.",
                domain=".edu",
                credibility_score=0.92,
                source_type="journal",
            ),
            AcademicSource(
                title="CDC Guidelines for Blood Glucose Self-Monitoring in Diabetes Management",
                url="https://www.cdc.gov/diabetes/monitoring-guidelines-2024",
                authors=["CDC Diabetes Prevention Program"],
                publication_date="January 2024",
                journal_name="CDC Morbidity and Mortality Weekly Report",
                excerpt="Updated guidelines recommend individualized monitoring frequencies: 4-10 times daily for Type 1 diabetes, 1-2 times for diet-controlled Type 2. Continuous monitoring shows 72% reduction in severe hypoglycemic events.",
                domain=".gov",
                credibility_score=0.94,
                source_type="report",
            ),
            AcademicSource(
                title="Machine Learning Applications in Predictive Glucose Monitoring",
                url="https://cs.mit.edu/ml-glucose-prediction",
                authors=["Dr. Alan Zhang", "Prof. Maria Gonzalez", "Dr. Robert Kim"],
                publication_date="April 2024",
                journal_name="AI in Medicine",
                excerpt="Deep learning models predict blood glucose levels 30-60 minutes ahead with 85% accuracy. Integration with insulin pumps enables automated adjustments, reducing glycemic variability by 43%.",
                domain=".edu",
                credibility_score=0.90,
                source_type="journal",
            ),
            AcademicSource(
                title="Cost-Effectiveness Analysis of Continuous Glucose Monitoring",
                url="https://healthpolicy.duke.edu/cgm-cost-analysis",
                authors=["Dr. Jennifer Smith", "Dr. Mark Thompson"],
                publication_date="March 2024",
                journal_name="Health Economics Quarterly",
                excerpt="Economic analysis shows CGM reduces long-term complications, saving $8,000-12,000 per patient over 10 years despite higher upfront costs. Quality-adjusted life years increased by 1.2.",
                domain=".edu",
                credibility_score=0.88,
                source_type="journal",
            ),
        ],
        main_findings=[
            "Continuous glucose monitoring (CGM) devices now achieve 95% accuracy compared to traditional methods",
            "Real-time monitoring reduces severe hypoglycemic events by 72% in Type 1 diabetes patients",
            "Machine learning models can predict glucose levels 30-60 minutes in advance with 85% accuracy",
            "Non-invasive monitoring technologies show 88% correlation with laboratory blood glucose values",
            "Personalized monitoring schedules based on individual patterns improve outcomes by 45%",
            "CGM technology saves $8,000-12,000 per patient over 10 years through complication reduction",
        ],
        key_statistics=[
            "95% accuracy",
            "72% reduction in hypoglycemic events",
            "12,000 patients studied",
            "85% prediction accuracy",
            "43% reduction in glycemic variability",
            "$8,000-12,000 savings",
            "1.2 QALY increase",
            "147 studies reviewed",
            "4-10 daily checks for Type 1",
        ],
        research_gaps=[
            "Long-term effects of continuous monitoring on patient psychology and behavior need further study",
            "Non-invasive technologies require improvement to match invasive method accuracy",
            "More research needed on optimal alert thresholds for different patient populations",
            "Limited data on CGM effectiveness in pediatric and geriatric populations",
            "Integration challenges between different device manufacturers remain unresolved",
        ],
        total_sources_analyzed=8,
        search_query_used="blood sugar monitoring diabetes CGM continuous glucose",
    )

    # Mock the agent's run method to return AgentRunResult
    with patch.object(agent, "run", return_value=create_mock_agent_result(mock_findings)):
        # Run the research
        logger.info("🔍 Researching: 'blood sugar monitoring'...\n")
        findings = await run_research_agent(agent, "blood sugar monitoring")

        # Display results
        logger.info("=" * 70)
        logger.info("📊 RESEARCH FINDINGS: BLOOD SUGAR MONITORING")
        logger.info("=" * 70)

        # Summary
        logger.info(f"\n📝 EXECUTIVE SUMMARY:")
        logger.info(f"{findings.research_summary}")

        # Main findings
        logger.info(f"\n🔍 KEY FINDINGS ({len(findings.main_findings)}):")
        for i, finding in enumerate(findings.main_findings, 1):
            logger.info(f"{i}. {finding}")

        # Statistics
        logger.info(f"\n📈 KEY STATISTICS ({len(findings.key_statistics)}):")
        for stat in findings.key_statistics[:6]:  # Show top 6
            logger.info(f"   • {stat}")

        # Academic sources
        logger.info(
            f"\n📚 TOP ACADEMIC SOURCES ({len(findings.academic_sources)} found):"
        )
        for i, source in enumerate(findings.academic_sources[:3], 1):  # Top 3
            logger.info(f"\n{i}. {source.title}")
            logger.info(f"   📍 {source.journal_name} - {source.publication_date}")
            logger.info(
                f"   👥 {', '.join(source.authors[:2]) if source.authors else 'Unknown'}"
            )
            logger.info(f"   🎯 Credibility: {source.credibility_score:.2f}")
            logger.info(f"   📝 {source.excerpt[:150]}...")

        # Research gaps
        logger.info(f"\n🔬 RESEARCH GAPS IDENTIFIED:")
        for i, gap in enumerate(findings.research_gaps[:3], 1):
            logger.info(f"{i}. {gap}")

        # Quality assessment
        logger.info("\n" + "=" * 70)
        logger.info("⭐ RESEARCH QUALITY ASSESSMENT")
        logger.info("=" * 70)

        quality = assess_research_quality(findings)
        logger.info(f"\n📊 Overall Quality Score: {quality['overall_score']:.2f}/1.00")
        logger.info(f"\n✅ Strengths:")
        for strength in quality["strengths"]:
            logger.info(f"   • {strength}")

        # Diversity analysis
        diversity = calculate_source_diversity(findings.academic_sources)
        logger.info(f"\n🌍 Source Diversity:")
        logger.info(f"   • Domains: {list(diversity['domain_distribution'].keys())}")
        logger.info(f"   • Diversity Score: {diversity['diversity_score']:.2f}")

        # Themes
        themes = extract_research_themes(findings)
        logger.info(f"\n🏷️ Research Themes Identified:")
        for theme in themes[:5]:
            logger.info(f"   • {theme}")

        # Citations
        logger.info("\n" + "=" * 70)
        logger.info("📖 FORMATTED CITATIONS (APA Style)")
        logger.info("=" * 70)
        for source in findings.academic_sources[:2]:
            citation = format_apa_citation(source)
            logger.info(f"\n{citation}")

        # Save to file
        output_file = "blood_sugar_research_results.json"
        with open(output_file, "w") as f:
            json.dump(findings.model_dump(), f, indent=2, default=str)
        logger.info(f"\n💾 Full results saved to: {output_file}")

        logger.info("\n✅ Research demonstration completed!")

        return findings


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_blood_sugar_research())
