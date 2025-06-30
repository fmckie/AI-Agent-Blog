"""
Comprehensive tests for all Pydantic models.

This test file covers all models in models.py, testing:
- Field validation
- Custom validators
- Model methods
- Edge cases and error scenarios
"""

from datetime import datetime
from typing import List

# Import testing utilities
import pytest

# Import models to test
from models import (
    AcademicSource,
    ArticleOutput,
    ArticleSection,
    ArticleSubsection,
    ResearchFindings,
    TavilySearchResponse,
    TavilySearchResult,
)


class TestAcademicSource:
    """Test cases for AcademicSource model."""

    def test_valid_academic_source_creation(self):
        """Test creating a valid academic source."""
        # Create a valid academic source
        source = AcademicSource(
            title="Machine Learning in Healthcare",
            url="https://example.edu/paper",
            authors=["Dr. Smith", "Dr. Jones"],
            publication_date="2024-01-15",
            journal_name="Journal of AI Research",
            excerpt="This paper explores ML applications...",
            domain=".edu",
            credibility_score=0.9,
            source_type="journal",
        )

        # Verify all fields are set correctly
        assert source.title == "Machine Learning in Healthcare"
        assert source.url == "https://example.edu/paper"
        assert source.authors == ["Dr. Smith", "Dr. Jones"]
        assert source.credibility_score == 0.9

    def test_minimal_academic_source(self):
        """Test creating source with only required fields."""
        # Create source with minimal required fields
        source = AcademicSource(
            title="Test Paper",
            url="https://test.com",
            excerpt="Test excerpt",
            domain=".com",
            credibility_score=0.5,
        )

        # Verify defaults are applied
        assert source.source_type == "web"
        assert source.authors is None
        assert source.publication_date is None

    def test_url_validation(self):
        """Test URL validation."""
        # Test invalid URL without protocol
        with pytest.raises(ValueError, match="URL must start with http"):
            AcademicSource(
                title="Test",
                url="www.example.com",
                excerpt="Test",
                domain=".com",
                credibility_score=0.5,
            )

    def test_credibility_score_bounds(self):
        """Test credibility score validation."""
        # Test score too high
        with pytest.raises(ValueError):
            AcademicSource(
                title="Test",
                url="https://test.com",
                excerpt="Test",
                domain=".com",
                credibility_score=1.5,
            )

        # Test score too low
        with pytest.raises(ValueError):
            AcademicSource(
                title="Test",
                url="https://test.com",
                excerpt="Test",
                domain=".com",
                credibility_score=-0.1,
            )

    def test_domain_validation(self):
        """Test domain extraction and validation."""
        # Test domain without dot
        source = AcademicSource(
            title="Test",
            url="https://test.edu",
            excerpt="Test",
            domain="edu",
            credibility_score=0.8,
        )
        assert source.domain == ".edu"

        # Test domain with dot
        source2 = AcademicSource(
            title="Test",
            url="https://test.gov",
            excerpt="Test",
            domain=".gov",
            credibility_score=0.9,
        )
        assert source2.domain == ".gov"

    def test_excerpt_length_limit(self):
        """Test excerpt max length validation."""
        # Create very long excerpt
        long_excerpt = "a" * 501

        with pytest.raises(ValueError):
            AcademicSource(
                title="Test",
                url="https://test.com",
                excerpt=long_excerpt,
                domain=".com",
                credibility_score=0.5,
            )

    def test_to_citation_method(self):
        """Test citation generation."""
        # Test with full metadata
        source = AcademicSource(
            title="AI Research Paper",
            url="https://journal.edu/paper",
            authors=["Smith, J.", "Doe, A.", "Brown, B."],
            publication_date="2024-01-01",
            journal_name="AI Journal",
            excerpt="Abstract",
            domain=".edu",
            credibility_score=0.9,
        )

        citation = source.to_citation()
        assert "Smith, J., Doe, A., Brown, B." in citation
        assert '"AI Research Paper"' in citation
        assert "AI Journal" in citation
        assert "(2024-01-01)" in citation
        assert "Available at: https://journal.edu/paper" in citation

        # Test with more than 3 authors
        source.authors = ["A", "B", "C", "D", "E"]
        citation = source.to_citation()
        assert "A, B, C et al." in citation

        # Test without optional fields
        minimal_source = AcademicSource(
            title="Minimal Paper",
            url="https://test.com",
            excerpt="Test",
            domain=".com",
            credibility_score=0.5,
        )
        minimal_citation = minimal_source.to_citation()
        assert '"Minimal Paper"' in minimal_citation
        assert "Available at: https://test.com" in minimal_citation


class TestResearchFindings:
    """Test cases for ResearchFindings model."""

    def test_valid_research_findings(self):
        """Test creating valid research findings."""
        # Create academic sources
        sources = [
            AcademicSource(
                title="Source 1",
                url="https://test.edu/1",
                excerpt="Excerpt 1",
                domain=".edu",
                credibility_score=0.8,
            ),
            AcademicSource(
                title="Source 2",
                url="https://test.gov/2",
                excerpt="Excerpt 2",
                domain=".gov",
                credibility_score=0.9,
            ),
        ]

        # Create research findings
        findings = ResearchFindings(
            keyword="machine learning",
            research_summary="This research explores ML applications in various fields, demonstrating significant improvements in predictive accuracy and operational efficiency across multiple domains.",
            academic_sources=sources,
            key_statistics=["95% accuracy", "50% improvement"],
            research_gaps=["Need for more data", "Limited real-world testing"],
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=10,
            search_query_used="machine learning academic research",
        )

        assert findings.keyword == "machine learning"
        assert len(findings.academic_sources) == 2
        assert len(findings.main_findings) == 3

    def test_research_summary_length_validation(self):
        """Test research summary length constraints."""
        # Test too short summary
        sources = [
            AcademicSource(
                title="Test",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
        ]

        with pytest.raises(ValueError):
            ResearchFindings(
                keyword="test",
                research_summary="Short",  # Less than 20 characters
                academic_sources=sources,
                main_findings=["1", "2", "3"],
                total_sources_analyzed=1,
                search_query_used="test",
            )

        # Test too long summary
        with pytest.raises(ValueError):
            ResearchFindings(
                keyword="test",
                research_summary="a" * 2001,  # More than 2000 characters
                academic_sources=sources,
                main_findings=["1", "2", "3"],
                total_sources_analyzed=1,
                search_query_used="test",
            )

    def test_minimum_sources_requirement(self):
        """Test that empty sources list is now allowed."""
        # Empty sources list is now allowed for edge cases
        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=[],
            main_findings=["1", "2", "3"],
            total_sources_analyzed=0,
            search_query_used="test",
        )
        assert len(findings.academic_sources) == 0

    def test_minimum_findings_requirement(self):
        """Test that empty findings list is now allowed."""
        sources = [
            AcademicSource(
                title="Test",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
        ]

        # Empty findings list is now allowed for edge cases
        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            main_findings=[],  # Empty findings allowed
            total_sources_analyzed=1,
            search_query_used="test",
        )
        assert len(findings.main_findings) == 0

    def test_source_credibility_validation(self):
        """Test that sources with low credibility are now allowed."""
        # Create sources with low credibility
        low_cred_sources = [
            AcademicSource(
                title="Low Cred 1",
                url="https://test.com",
                excerpt="Test",
                domain=".com",
                credibility_score=0.5,
            ),
            AcademicSource(
                title="Low Cred 2",
                url="https://test.net",
                excerpt="Test",
                domain=".net",
                credibility_score=0.6,
            ),
        ]

        # Low credibility sources are now allowed
        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=low_cred_sources,
            main_findings=["1", "2", "3"],
            total_sources_analyzed=2,
            search_query_used="test",
        )
        assert len(findings.academic_sources) == 2

    def test_source_sorting_by_credibility(self):
        """Test that sources are sorted by credibility."""
        # Create sources with different credibility scores
        sources = [
            AcademicSource(
                title="Low",
                url="https://test.com",
                excerpt="Test",
                domain=".com",
                credibility_score=0.7,
            ),
            AcademicSource(
                title="High",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="Medium",
                url="https://test.org",
                excerpt="Test",
                domain=".org",
                credibility_score=0.8,
            ),
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            main_findings=["1", "2", "3"],
            total_sources_analyzed=3,
            search_query_used="test",
        )

        # Check sources are sorted by credibility (highest first)
        assert findings.academic_sources[0].title == "High"
        assert findings.academic_sources[1].title == "Medium"
        assert findings.academic_sources[2].title == "Low"

    def test_get_top_sources_method(self):
        """Test getting top N sources."""
        # Create 5 sources with different credibility
        sources = []
        for i in range(5):
            sources.append(
                AcademicSource(
                    title=f"Source {i}",
                    url=f"https://test{i}.edu",
                    excerpt="Test",
                    domain=".edu",
                    credibility_score=0.9 - (i * 0.05),
                )
            )

        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            main_findings=["1", "2", "3"],
            total_sources_analyzed=5,
            search_query_used="test",
        )

        # Test getting top 3 sources
        top_3 = findings.get_top_sources(3)
        assert len(top_3) == 3
        assert top_3[0].title == "Source 0"
        assert top_3[2].title == "Source 2"

        # Test default (5 sources)
        top_5 = findings.get_top_sources()
        assert len(top_5) == 5

    def test_to_markdown_summary_method(self):
        """Test markdown summary generation."""
        sources = [
            AcademicSource(
                title="Top Source",
                url="https://test.edu",
                excerpt="Important research findings",
                domain=".edu",
                credibility_score=0.95,
            )
        ]

        findings = ResearchFindings(
            keyword="AI Research",
            research_summary="Summary of AI research findings reveals transformative potential across healthcare, finance, and education sectors with measurable improvements in outcomes.",
            academic_sources=sources,
            key_statistics=["95% accuracy", "2x faster"],
            research_gaps=["More data needed"],
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=10,
            search_query_used="AI research query",
        )

        markdown = findings.to_markdown_summary()

        # Check markdown contains expected sections
        assert "# Research Findings: AI Research" in markdown
        assert "## Summary" in markdown
        assert "Summary of AI research findings" in markdown
        assert "## Main Findings" in markdown
        assert "1. Finding 1" in markdown
        assert "## Key Statistics" in markdown
        assert "- 95% accuracy" in markdown
        assert "## Top Academic Sources" in markdown
        assert "### Top Source" in markdown
        assert "**Credibility**: 0.95" in markdown

    def test_research_timestamp_default(self):
        """Test that research timestamp is set by default."""
        sources = [
            AcademicSource(
                title="Test",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            main_findings=["1", "2", "3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        # Check timestamp is recent (within last minute)
        time_diff = datetime.now() - findings.research_timestamp
        assert time_diff.total_seconds() < 60


class TestArticleSection:
    """Test cases for ArticleSection and ArticleSubsection models."""

    def test_valid_article_section(self):
        """Test creating a valid article section."""
        section = ArticleSection(
            heading="Introduction to Machine Learning",
            content="Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. This revolutionary technology has transformed numerous industries...",
        )

        assert section.heading == "Introduction to Machine Learning"
        assert len(section.content) >= 200
        assert section.subsections is None

    def test_section_with_subsections(self):
        """Test creating section with subsections."""
        subsections = [
            ArticleSubsection(
                heading="Supervised Learning",
                content="Supervised learning is a type of machine learning where the algorithm learns from labeled training data.",
            ),
            ArticleSubsection(
                heading="Unsupervised Learning",
                content="Unsupervised learning involves finding patterns in data without pre-existing labels.",
            ),
        ]

        section = ArticleSection(
            heading="Types of Machine Learning",
            content="There are several types of machine learning approaches, each suited for different types of problems and data.",
            subsections=subsections,
        )

        assert len(section.subsections) == 2
        assert section.subsections[0].heading == "Supervised Learning"

    def test_heading_validation(self):
        """Test heading formatting validation."""
        # Test heading with markdown formatting
        section = ArticleSection(heading="## Test Heading ##", content="a" * 200)
        assert section.heading == "Test Heading"

        # Test lowercase heading gets title case
        section2 = ArticleSection(heading="test heading lowercase", content="a" * 200)
        assert section2.heading == "Test Heading Lowercase"

    def test_heading_length_constraints(self):
        """Test heading length validation."""
        # Test too short heading
        with pytest.raises(ValueError):
            ArticleSection(heading="Test", content="a" * 200)  # Less than 5 chars

        # Test too long heading
        with pytest.raises(ValueError):
            ArticleSection(heading="a" * 101, content="a" * 200)  # More than 100 chars

    def test_content_minimum_length(self):
        """Test content minimum length requirement."""
        with pytest.raises(ValueError):
            ArticleSection(
                heading="Valid Heading", content="Too short"  # Less than 200 chars
            )

    def test_subsection_validation(self):
        """Test subsection validation."""
        # Test subsection with short content
        with pytest.raises(ValueError):
            ArticleSubsection(
                heading="Test Subsection", content="Too short"  # Less than 100 chars
            )

        # Valid subsection
        subsection = ArticleSubsection(heading="Valid Subsection", content="a" * 100)
        assert len(subsection.content) >= 100


class TestArticleOutput:
    """Test cases for ArticleOutput model."""

    def test_valid_article_output(self):
        """Test creating a valid article output."""
        sections = [
            ArticleSection(heading="Introduction", content="a" * 200),
            ArticleSection(heading="Main Content", content="b" * 300),
            ArticleSection(heading="Conclusion Section", content="c" * 200),
        ]

        article = ArticleOutput(
            title="The Future of AI in Healthcare",
            meta_description="Explore how artificial intelligence is revolutionizing healthcare with improved diagnostics, personalized treatment, and predictive analytics.",
            focus_keyword="AI healthcare",
            introduction="Artificial intelligence is transforming healthcare in unprecedented ways. This comprehensive guide explores how AI technologies are revolutionizing medical diagnostics, treatment planning, and patient care across the globe.",
            main_sections=sections,
            conclusion="In conclusion, AI will continue to shape healthcare's future, offering unprecedented opportunities for improved patient outcomes and medical breakthroughs.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.02,
            sources_used=["https://source1.edu", "https://source2.gov"],
        )

        assert article.title == "The Future of AI in Healthcare"
        assert len(article.main_sections) == 3
        assert article.word_count == 1500

    def test_seo_field_constraints(self):
        """Test SEO field length constraints."""
        sections = [
            ArticleSection(heading=f"Section {i}", content="a" * 200) for i in range(3)
        ]

        # Test title too short
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Short",  # Less than 10 chars
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

        # Test title too long
        with pytest.raises(ValueError):
            ArticleOutput(
                title="a" * 71,  # More than 70 chars
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

        # Test meta description too short
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="Too short",  # Less than 120 chars
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

        # Test meta description too long
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="a" * 161,  # More than 160 chars
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

    def test_content_length_constraints(self):
        """Test content length requirements."""
        sections = [
            ArticleSection(heading=f"Section {i}", content="a" * 200) for i in range(3)
        ]

        # Test introduction too short
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="Too short",  # Less than 150 chars
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

        # Test conclusion too short
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="Too short",  # Less than 100 chars
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

    def test_minimum_sections_requirement(self):
        """Test that at least 3 main sections are required."""
        # Only 2 sections
        sections = [
            ArticleSection(heading="Section 1", content="a" * 200),
            ArticleSection(heading="Section 2", content="a" * 200),
        ]

        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,  # Only 2 sections
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

    def test_word_count_minimum(self):
        """Test minimum word count requirement."""
        sections = [
            ArticleSection(heading=f"Section {i}", content="a" * 200) for i in range(3)
        ]

        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=999,  # Less than 1000
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=["https://test.com"],
            )

    def test_keyword_density_bounds(self):
        """Test keyword density constraints."""
        sections = [
            ArticleSection(heading=f"Section {i}", content="a" * 200) for i in range(3)
        ]

        # Test density too low
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.004,  # Less than 0.5%
                sources_used=["https://test.com"],
            )

        # Test density too high
        with pytest.raises(ValueError):
            ArticleOutput(
                title="Valid Title",
                meta_description="a" * 150,
                focus_keyword="test",
                introduction="a" * 150,
                main_sections=sections,
                conclusion="a" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.031,  # More than 3%
                sources_used=["https://test.com"],
            )

    def test_to_html_method(self):
        """Test HTML generation."""
        subsections = [
            ArticleSubsection(
                heading="Subsection One",
                content="Subsection content here that meets the minimum 100 character requirement for proper validation and testing purposes.",
            )
        ]

        sections = [
            ArticleSection(
                heading="Introduction Section",
                content="Introduction content here that meets the 200 character minimum requirement. This section provides comprehensive information about the topic with sufficient detail to ensure proper content validation and testing.",
                subsections=subsections,
            ),
            ArticleSection(
                heading="Main Content Section",
                content="Main content here that also meets the 200 character minimum requirement. This section contains detailed information and analysis to provide substantial content for our readers and satisfy validation requirements.",
            ),
            ArticleSection(
                heading="Additional Section",
                content="A third section is required to meet the minimum of three main sections. This content also needs to be at least 200 characters long to satisfy validation requirements. We're providing comprehensive information here.",
            ),
        ]

        article = ArticleOutput(
            title="Test Article for HTML Generation",
            meta_description="Test description for SEO that meets the 120-160 character requirement. This comprehensive meta description provides essential information.",
            focus_keyword="test keyword",
            introduction="This is the introduction that meets the minimum 150 character requirement. We provide comprehensive context and information to ensure our content meets all validation requirements for proper testing.",
            main_sections=sections,
            conclusion="This is the conclusion that meets the 100 character minimum requirement. It effectively summarizes the key points of our article.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.02,
            sources_used=["https://test.com"],
        )

        html = article.to_html()

        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html lang='en'>" in html
        assert f"<title>{article.title}</title>" in html
        assert f"<meta name='description' content='{article.meta_description}'>" in html
        assert f"<meta name='keywords' content='{article.focus_keyword}'>" in html
        assert f"<h1>{article.title}</h1>" in html
        assert "⏱️ 4 min read" in html
        assert "<h2>Introduction Section</h2>" in html
        assert "<h3>Subsection One</h3>" in html
        assert f"<div class='conclusion'>{article.conclusion}</div>" in html


class TestTavilyModels:
    """Test cases for Tavily API response models."""

    def test_tavily_search_result(self):
        """Test TavilySearchResult model."""
        # Valid result
        result = TavilySearchResult(
            title="Research Paper",
            url="https://example.edu/paper",
            content="This paper discusses...",
            score=0.95,
            credibility_score=0.85,
            domain=".edu",
        )

        assert result.title == "Research Paper"
        assert result.credibility_score == 0.85

        # Test URL validation
        with pytest.raises(ValueError, match="URL must start with http"):
            TavilySearchResult(
                title="Test", url="www.example.com", content="Test content"
            )

    def test_tavily_search_response(self):
        """Test TavilySearchResponse model."""
        results = [
            TavilySearchResult(
                title="Result 1",
                url="https://test.edu",
                content="Content 1",
                credibility_score=0.9,
                domain=".edu",
            ),
            TavilySearchResult(
                title="Result 2",
                url="https://test.com",
                content="Content 2",
                credibility_score=0.6,
                domain=".com",
            ),
        ]

        response = TavilySearchResponse(
            query="test query", results=results, answer="AI generated answer"
        )

        assert response.query == "test query"
        assert len(response.results) == 2

        # Test get_academic_results
        academic = response.get_academic_results()
        assert len(academic) == 1  # Only one result has credibility >= 0.7
        assert academic[0].title == "Result 1"

        # Test get_results_by_domain
        edu_results = response.get_results_by_domain(".edu")
        assert len(edu_results) == 1
        assert edu_results[0].domain == ".edu"

    def test_empty_tavily_response(self):
        """Test empty Tavily response."""
        response = TavilySearchResponse(query="test query", results=[])

        assert len(response.results) == 0
        assert response.answer is None
        assert len(response.get_academic_results()) == 0


# Additional edge case tests
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        source = AcademicSource(
            title="研究論文: Unicode Test",
            url="https://test.edu/unicode",
            excerpt="This contains émojis 🚀 and special chars: ñ, ü, ß",
            domain=".edu",
            credibility_score=0.8,
        )

        assert "研究論文" in source.title
        assert "🚀" in source.excerpt

    def test_very_long_content(self):
        """Test handling of very long content."""
        # Create section with exactly minimum content
        section = ArticleSection(
            heading="Test Section", content="a" * 200  # Exactly 200 chars
        )
        assert len(section.content) == 200

    def test_none_values_handling(self):
        """Test handling of None values in optional fields."""
        source = AcademicSource(
            title="Test",
            url="https://test.com",
            excerpt="Test",
            domain=".com",
            credibility_score=0.5,
            authors=None,
            publication_date=None,
            journal_name=None,
        )

        citation = source.to_citation()
        assert source.authors is None
        assert "et al." not in citation  # Should not appear for None authors

    def test_empty_lists(self):
        """Test handling of empty lists."""
        sources = [
            AcademicSource(
                title="Test",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            key_statistics=[],  # Empty list
            research_gaps=[],  # Empty list
            main_findings=["1", "2", "3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        assert len(findings.key_statistics) == 0
        assert len(findings.research_gaps) == 0

        # Check markdown summary handles empty lists
        markdown = findings.to_markdown_summary()
        assert "## Key Statistics" not in markdown  # Should not include empty section
