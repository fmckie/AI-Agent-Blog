"""
Debug script for testing the writer agent independently.
"""

import asyncio

from config import get_config
from models import AcademicSource, ResearchFindings
from writer_agent import create_writer_agent, run_writer_agent


async def test_writer():
    """Test the writer agent with mock research data."""
    # Get configuration
    config = get_config()

    # Create mock research findings
    mock_research = ResearchFindings(
        keyword="intermittent fasting benefits",
        research_summary="Intermittent fasting shows significant health benefits including weight loss and metabolic improvements.",
        academic_sources=[
            AcademicSource(
                title="Effects of Intermittent Fasting on Health",
                url="https://example.edu/fasting-study",
                excerpt="Study shows 16% reduction in body weight over 12 weeks",
                domain=".edu",
                credibility_score=0.92,
            ),
            AcademicSource(
                title="Metabolic Benefits of Time-Restricted Eating",
                url="https://journal.org/metabolic-fasting",
                excerpt="Improved insulin sensitivity by 23% in participants",
                domain=".org",
                credibility_score=0.88,
            ),
            AcademicSource(
                title="Autophagy and Cellular Renewal",
                url="https://research.edu/autophagy",
                excerpt="Enhanced cellular cleanup processes after 16 hours fasting",
                domain=".edu",
                credibility_score=0.95,
            ),
        ],
        main_findings=[
            "16% average weight loss over 12 weeks",
            "23% improvement in insulin sensitivity",
            "Enhanced autophagy after 16 hours of fasting",
        ],
        key_statistics=["16%", "23%", "16 hours"],
        research_gaps=[
            "Long-term effects beyond 1 year",
            "Optimal fasting windows for different age groups",
        ],
        total_sources_analyzed=5,
        search_query_used="intermittent fasting benefits academic research",
    )

    try:
        # Create writer agent
        print("Creating writer agent...")
        writer_agent = create_writer_agent(config)

        # Run writer agent
        print("Running writer agent...")
        article = await run_writer_agent(
            writer_agent, "intermittent fasting benefits", mock_research
        )

        # Display results
        print("\n✅ Article generated successfully!")
        print(f"Title: {article.title}")
        print(f"Word count: {article.word_count}")
        print(f"Sections: {len(article.main_sections)}")
        print(f"Keyword density: {article.keyword_density:.2%}")

        # Save to file for review
        with open("test_article_output.html", "w") as f:
            f.write(article.to_html())
        print("\n📄 Saved to test_article_output.html")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_writer())
