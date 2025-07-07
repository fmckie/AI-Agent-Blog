"""
Extended tests for models.py to improve coverage.

This module adds additional test cases for Pydantic models,
focusing on methods, validation, and edge cases.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from models import (
    AcademicSource,
    ArticleOutput,
    ArticleSection,
    ArticleSubsection,
    ResearchFindings,
    TavilySearchResponse,
    TavilySearchResult,
)


class TestAcademicSourceExtended:
    """Extended tests for AcademicSource model."""

    def test_to_citation_full_details(self):
        """Test citation generation with all fields."""
        source = AcademicSource(
            title="Advances in AI Healthcare Applications",
            url="https://journal.edu/ai-health",
            authors=["Smith, J.", "Doe, A.", "Johnson, K."],
            publication_date="2024-01-15",
            journal_name="Journal of AI Research",
            excerpt="This study examines AI applications...",
            domain=".edu",
            credibility_score=0.95,
        )

        citation = source.to_citation()

        assert "Smith, J., Doe, A., Johnson, K." in citation
        assert '"Advances in AI Healthcare Applications"' in citation
        assert "Journal of AI Research" in citation
        assert "(2024-01-15)" in citation
        assert "Available at: https://journal.edu/ai-health" in citation

    def test_to_citation_many_authors(self):
        """Test citation with more than 3 authors."""
        source = AcademicSource(
            title="Collaborative AI Study",
            url="https://example.edu/study",
            authors=["Author1", "Author2", "Author3", "Author4", "Author5"],
            excerpt="Study excerpt",
            domain=".edu",
            credibility_score=0.8,
        )

        citation = source.to_citation()

        assert "Author1, Author2, Author3 et al." in citation
        assert "Author4" not in citation
        assert "Author5" not in citation

    def test_to_citation_minimal_fields(self):
        """Test citation with minimal required fields."""
        source = AcademicSource(
            title="Basic Study",
            url="https://example.com/study",
            excerpt="Excerpt",
            domain=".com",
            credibility_score=0.5,
        )

        citation = source.to_citation()

        assert '"Basic Study"' in citation
        assert "Available at: https://example.com/study" in citation
        # Should not have authors, journal, or date sections

    def test_url_validation_edge_cases(self):
        """Test URL validation with edge cases."""
        # Valid URLs
        valid_source = AcademicSource(
            title="Test",
            url="https://example.com/page",
            excerpt="Test",
            domain=".com",
            credibility_score=0.5,
        )
        assert valid_source.url == "https://example.com/page"

        # Invalid URLs
        with pytest.raises(ValidationError):
            AcademicSource(
                title="Test",
                url="not-a-url",
                excerpt="Test",
                domain=".com",
                credibility_score=0.5,
            )

        with pytest.raises(ValidationError):
            AcademicSource(
                title="Test",
                url="ftp://example.com",  # Not http/https
                excerpt="Test",
                domain=".com",
                credibility_score=0.5,
            )

    def test_domain_extraction_variations(self):
        """Test domain extraction with various inputs."""
        # With dot
        source = AcademicSource(
            title="Test",
            url="https://example.edu",
            excerpt="Test",
            domain=".edu",
            credibility_score=0.5,
        )
        assert source.domain == ".edu"

        # Without dot (should add it)
        source = AcademicSource(
            title="Test",
            url="https://example.gov",
            excerpt="Test",
            domain="gov",
            credibility_score=0.5,
        )
        assert source.domain == ".gov"

        # Non-academic domain
        source = AcademicSource(
            title="Test",
            url="https://example.xyz",
            excerpt="Test",
            domain="xyz",
            credibility_score=0.5,
        )
        assert source.domain == ".xyz"

    def test_excerpt_length_limit(self):
        """Test excerpt max length validation."""
        # At limit
        long_excerpt = "x" * 500
        source = AcademicSource(
            title="Test",
            url="https://example.com",
            excerpt=long_excerpt,
            domain=".com",
            credibility_score=0.5,
        )
        assert len(source.excerpt) == 500

        # Over limit
        with pytest.raises(ValidationError):
            AcademicSource(
                title="Test",
                url="https://example.com",
                excerpt="x" * 501,
                domain=".com",
                credibility_score=0.5,
            )


class TestResearchFindingsExtended:
    """Extended tests for ResearchFindings model."""

    def test_get_top_sources_various_counts(self):
        """Test getting top sources with different counts."""
        sources = [
            AcademicSource(
                title=f"Source {i}",
                url=f"https://example{i}.edu",
                excerpt=f"Excerpt {i}",
                domain=".edu",
                credibility_score=0.9 - (i * 0.1),
            )
            for i in range(7)
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="Summary of test research findings with sufficient length",
            academic_sources=sources,
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=7,
            search_query_used="test",
        )

        # Default (5 sources)
        top_5 = findings.get_top_sources()
        assert len(top_5) == 5
        assert top_5[0].credibility_score == 0.9
        assert top_5[4].credibility_score == 0.5

        # Custom count
        top_3 = findings.get_top_sources(3)
        assert len(top_3) == 3

        # More than available
        top_10 = findings.get_top_sources(10)
        assert len(top_10) == 7

    def test_to_markdown_summary_complete(self):
        """Test markdown summary generation with all fields."""
        sources = [
            AcademicSource(
                title="AI Study 1",
                url="https://journal1.edu/ai",
                excerpt="First study about AI applications in healthcare.",
                domain=".edu",
                credibility_score=0.95,
            ),
            AcademicSource(
                title="AI Study 2",
                url="https://journal2.edu/ai",
                excerpt="Second study on machine learning diagnostics.",
                domain=".edu",
                credibility_score=0.90,
            ),
        ]

        findings = ResearchFindings(
            keyword="AI healthcare",
            research_summary="Comprehensive AI healthcare research summary.",
            academic_sources=sources,
            key_statistics=["95% accuracy", "30% cost reduction"],
            research_gaps=["Long-term studies needed"],
            main_findings=["AI improves diagnostics", "Reduces healthcare costs"],
            total_sources_analyzed=10,
            search_query_used="AI healthcare applications",
        )

        markdown = findings.to_markdown_summary()

        # Check structure
        assert "# Research Findings: AI healthcare" in markdown
        assert "## Summary" in markdown
        assert "Comprehensive AI healthcare research summary." in markdown
        assert "## Main Findings" in markdown
        assert "1. AI improves diagnostics" in markdown
        assert "2. Reduces healthcare costs" in markdown
        assert "## Key Statistics" in markdown
        assert "- 95% accuracy" in markdown
        assert "- 30% cost reduction" in markdown
        assert "## Top Academic Sources" in markdown
        assert "### AI Study 1" in markdown
        assert "**Credibility**: 0.95" in markdown
        assert "**Excerpt**: First study about AI applications" in markdown

    def test_to_markdown_summary_minimal(self):
        """Test markdown summary with minimal data."""
        findings = ResearchFindings(
            keyword="test topic",
            research_summary="Basic summary with sufficient content for validation",
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=0,
            search_query_used="test",
        )

        markdown = findings.to_markdown_summary()

        assert "# Research Findings: test topic" in markdown
        assert "## Summary" in markdown
        assert "Basic summary" in markdown
        assert "## Main Findings" in markdown
        # Should not have statistics section if empty
        assert "## Key Statistics" not in markdown

    def test_source_credibility_sorting(self):
        """Test automatic sorting of sources by credibility."""
        # Create unsorted sources
        sources = [
            AcademicSource(
                title="Low credibility",
                url="https://example.com/1",
                excerpt="Test",
                domain=".com",
                credibility_score=0.3,
            ),
            AcademicSource(
                title="High credibility",
                url="https://example.edu/2",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="Medium credibility",
                url="https://example.org/3",
                excerpt="Test",
                domain=".org",
                credibility_score=0.6,
            ),
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="Summary of research about credibility testing and validation",
            academic_sources=sources,
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=3,
            search_query_used="test",
        )

        # Sources should be sorted by credibility
        assert findings.academic_sources[0].credibility_score == 0.9
        assert findings.academic_sources[1].credibility_score == 0.6
        assert findings.academic_sources[2].credibility_score == 0.3

    def test_research_summary_length_validation(self):
        """Test research summary length constraints."""
        # Too short
        with pytest.raises(ValidationError):
            ResearchFindings(
                keyword="test",
                research_summary="Too short",
                academic_sources=[],
                key_statistics=[],
                research_gaps=[],
                main_findings=[],
                total_sources_analyzed=0,
                search_query_used="test",
            )

        # At minimum
        findings = ResearchFindings(
            keyword="test",
            research_summary="x" * 20,
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=0,
            search_query_used="test",
        )
        assert len(findings.research_summary) == 20

        # At maximum
        findings = ResearchFindings(
            keyword="test",
            research_summary="x" * 2000,
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=0,
            search_query_used="test",
        )
        assert len(findings.research_summary) == 2000

        # Too long
        with pytest.raises(ValidationError):
            ResearchFindings(
                keyword="test",
                research_summary="x" * 2001,
                academic_sources=[],
                key_statistics=[],
                research_gaps=[],
                main_findings=[],
                total_sources_analyzed=0,
                search_query_used="test",
            )


class TestArticleOutputExtended:
    """Extended tests for ArticleOutput model."""

    def test_to_html_complete(self):
        """Test HTML generation with complete article."""
        sections = [
            ArticleSection(
                heading="Introduction to AI",
                content="AI is transforming technology. This section provides an overview of artificial intelligence and its applications in modern society.",
                subsections=[
                    ArticleSubsection(
                        heading="What is AI?",
                        content="Artificial Intelligence refers to computer systems that can perform tasks requiring human intelligence.",
                    ),
                    ArticleSubsection(
                        heading="History of AI",
                        content="AI research began in the 1950s with pioneers like Alan Turing and John McCarthy.",
                    ),
                ],
            ),
            ArticleSection(
                heading="Applications",
                content="AI has numerous applications across industries. From healthcare to finance, AI is revolutionizing how we work and live.",
            ),
            ArticleSection(
                heading="Future Developments",
                content="The future of AI holds immense potential. Emerging technologies like quantum computing and neuromorphic chips will enable even more sophisticated AI systems.",
            ),
        ]

        article = ArticleOutput(
            title="The Future of Artificial Intelligence",
            meta_description="Explore the future of AI technology, its applications, and impact on society. Learn about the latest developments and trends.",
            focus_keyword="artificial intelligence",
            introduction="Artificial Intelligence is rapidly evolving and transforming our world. This article explores the current state and future potential of AI technology.",
            main_sections=sections,
            conclusion="AI will continue to shape our future. As technology advances, we must ensure responsible development and deployment of AI systems.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.02,
            sources_used=["https://example.edu/ai"],
        )

        html = article.to_html()

        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html lang='en'>" in html
        assert f"<title>{article.title}</title>" in html
        assert f"<meta name='description' content='{article.meta_description}'>" in html
        assert f"<meta name='keywords' content='{article.focus_keyword}'>" in html
        assert "<meta charset='UTF-8'>" in html
        assert (
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            in html
        )

        # Check content
        assert f"<h1>{article.title}</h1>" in html
        assert "⏱️ 6 min read" in html
        assert f"<div class='introduction'>{article.introduction}</div>" in html
        assert "<h2>Introduction to AI</h2>" in html
        assert "<h3>What is AI?</h3>" in html
        assert "<h3>History of AI</h3>" in html
        assert "<h2>Applications</h2>" in html
        assert f"<div class='conclusion'>{article.conclusion}</div>" in html
        assert "</body>" in html
        assert "</html>" in html

    def test_to_html_no_subsections(self):
        """Test HTML generation without subsections."""
        sections = [
            ArticleSection(
                heading="Section 1",
                content="Content for section 1 that meets the minimum length requirement for proper validation. This content includes additional details to ensure it passes all validation checks.",
            ),
            ArticleSection(
                heading="Section 2",
                content="Content for section 2 with sufficient detail to pass validation requirements. The content here is comprehensive and provides valuable information to readers.",
            ),
            ArticleSection(
                heading="Section 3",
                content="Content for section 3 providing comprehensive information for readers. This section contains detailed explanations and examples to help readers understand the topic.",
            ),
        ]

        article = ArticleOutput(
            title="Simple Article",
            meta_description="A simple article without subsections to test basic HTML generation and ensure proper formatting of content.",
            focus_keyword="simple test",
            introduction="This is a simple article introduction that provides context for the content that follows in the main sections.",
            main_sections=sections,
            conclusion="In conclusion, this simple article demonstrates basic HTML generation without the complexity of subsections.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.01,
            sources_used=["https://example.com"],
        )

        html = article.to_html()

        # Should have sections but no subsections
        assert "<h2>Section 1</h2>" in html
        assert "<h2>Section 2</h2>" in html
        assert "<h3>" not in html

    def test_article_validation_constraints(self):
        """Test ArticleOutput validation constraints."""
        valid_sections = [
            ArticleSection(
                heading=f"Section {i}",
                content=f"Content that is long enough to meet validation requirements. "
                f"This section provides detailed information about topic {i}.",
            )
            for i in range(1, 4)
        ]

        # Test title length
        with pytest.raises(ValidationError):
            ArticleOutput(
                title="Short",  # Too short
                meta_description="x" * 130,
                focus_keyword="test",
                introduction="x" * 150,
                main_sections=valid_sections,
                conclusion="x" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.01,
                sources_used=["url"],
            )

        # Test meta description length
        with pytest.raises(ValidationError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="Too short",  # Less than 120 chars
                focus_keyword="test",
                introduction="x" * 150,
                main_sections=valid_sections,
                conclusion="x" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.01,
                sources_used=["url"],
            )

        # Test word count minimum
        with pytest.raises(ValidationError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="x" * 130,
                focus_keyword="test",
                introduction="x" * 150,
                main_sections=valid_sections,
                conclusion="x" * 100,
                word_count=999,  # Below 1000
                reading_time_minutes=4,
                keyword_density=0.01,
                sources_used=["url"],
            )

        # Test keyword density range
        with pytest.raises(ValidationError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="x" * 130,
                focus_keyword="test",
                introduction="x" * 150,
                main_sections=valid_sections,
                conclusion="x" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.04,  # Above 3%
                sources_used=["url"],
            )

    def test_minimum_sections_requirement(self):
        """Test minimum 3 sections requirement."""
        # Less than 3 sections
        with pytest.raises(ValidationError):
            ArticleOutput(
                title="Valid Title Here",
                meta_description="x" * 130,
                focus_keyword="test",
                introduction="x" * 150,
                main_sections=[
                    ArticleSection(heading="Section 1", content="x" * 100),
                    ArticleSection(heading="Section 2", content="x" * 100),
                ],  # Only 2 sections
                conclusion="x" * 100,
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.01,
                sources_used=["url"],
            )


class TestArticleSectionExtended:
    """Extended tests for ArticleSection model."""

    def test_heading_validation_formatting(self):
        """Test heading formatting validation."""
        # Test markdown removal
        section = ArticleSection(
            heading="## This Is A Heading ##",
            content="x" * 100,
        )
        assert section.heading == "This Is A Heading"

        # Test capitalization
        section = ArticleSection(
            heading="all lowercase heading",
            content="x" * 100,
        )
        assert section.heading == "All Lowercase Heading"

        # Test mixed case preservation
        section = ArticleSection(
            heading="AI and ML Applications",
            content="x" * 100,
        )
        assert section.heading == "AI and ML Applications"

    def test_heading_length_constraints(self):
        """Test heading length validation."""
        # Too short
        with pytest.raises(ValidationError):
            ArticleSection(
                heading="Hi",  # Less than 5 chars
                content="x" * 100,
            )

        # At limit
        section = ArticleSection(
            heading="x" * 100,  # Exactly 100 chars
            content="x" * 100,
        )
        assert len(section.heading) == 100

        # Too long
        with pytest.raises(ValidationError):
            ArticleSection(
                heading="x" * 101,  # More than 100 chars
                content="x" * 100,
            )

    def test_content_length_validation(self):
        """Test content minimum length."""
        # Too short
        with pytest.raises(ValidationError):
            ArticleSection(
                heading="Valid Heading",
                content="x" * 99,  # Less than 100
            )

        # At minimum
        section = ArticleSection(
            heading="Valid Heading",
            content="x" * 100,
        )
        assert len(section.content) == 100

    def test_section_with_subsections(self):
        """Test section with subsections."""
        subsections = [
            ArticleSubsection(
                heading="Subsection 1",
                content="Content for subsection 1 with sufficient length to meet the minimum requirement of 50 characters.",
            ),
            ArticleSubsection(
                heading="Subsection 2",
                content="Content for subsection 2 with sufficient length to meet the minimum requirement of 50 characters.",
            ),
        ]

        section = ArticleSection(
            heading="Main Section",
            content="Main section content that meets length requirements.",
            subsections=subsections,
        )

        assert len(section.subsections) == 2
        assert section.subsections[0].heading == "Subsection 1"


class TestTavilyModelsExtended:
    """Extended tests for Tavily search models."""

    def test_tavily_search_result_validation(self):
        """Test TavilySearchResult validation."""
        # Valid result
        result = TavilySearchResult(
            title="Search Result",
            url="https://example.com/page",
            content="Result content",
            score=0.95,
            credibility_score=0.8,
            domain=".com",
            processed_at=datetime.now(),
        )

        assert result.title == "Search Result"
        assert result.score == 0.95
        assert result.credibility_score == 0.8

        # Invalid URL
        with pytest.raises(ValidationError):
            TavilySearchResult(
                title="Test",
                url="invalid-url",
                content="Content",
            )

        # Invalid credibility score
        with pytest.raises(ValidationError):
            TavilySearchResult(
                title="Test",
                url="https://example.com",
                content="Content",
                credibility_score=1.5,  # Above 1.0
            )

    def test_tavily_search_response_methods(self):
        """Test TavilySearchResponse filtering methods."""
        results = [
            TavilySearchResult(
                title="Academic Result 1",
                url="https://university.edu/paper1",
                content="Academic content",
                credibility_score=0.9,
                domain=".edu",
            ),
            TavilySearchResult(
                title="Academic Result 2",
                url="https://journal.edu/paper2",
                content="Journal content",
                credibility_score=0.85,
                domain=".edu",
            ),
            TavilySearchResult(
                title="Government Report",
                url="https://agency.gov/report",
                content="Government content",
                credibility_score=0.88,
                domain=".gov",
            ),
            TavilySearchResult(
                title="Low Quality Result",
                url="https://blog.com/post",
                content="Blog content",
                credibility_score=0.5,
                domain=".com",
            ),
        ]

        response = TavilySearchResponse(
            query="academic research",
            results=results,
            answer="Summary of findings",
            processing_metadata={"timestamp": "2024-01-01"},
        )

        # Test get_academic_results
        academic = response.get_academic_results(min_credibility=0.7)
        assert len(academic) == 3  # All except the .com result

        academic_high = response.get_academic_results(min_credibility=0.87)
        assert len(academic_high) == 2  # Only .edu and .gov with high scores

        # Test get_results_by_domain
        edu_results = response.get_results_by_domain(".edu")
        assert len(edu_results) == 2
        assert all(r.domain == ".edu" for r in edu_results)

        gov_results = response.get_results_by_domain(".gov")
        assert len(gov_results) == 1
        assert gov_results[0].domain == ".gov"

        org_results = response.get_results_by_domain(".org")
        assert len(org_results) == 0

    def test_model_forward_references(self):
        """Test that forward references are properly resolved."""
        # This should not raise any errors
        article = ArticleOutput(
            title="Test Article",
            meta_description="x" * 130,
            focus_keyword="test",
            introduction="x" * 150,
            main_sections=[
                ArticleSection(
                    heading="Section with Subsections",
                    content="x" * 100,
                    subsections=[
                        ArticleSubsection(
                            heading="Subsection",
                            content="x" * 50,
                        ),
                    ],
                ),
                ArticleSection(heading="Section 2", content="x" * 100),
                ArticleSection(heading="Section 3", content="x" * 100),
            ],
            conclusion="x" * 100,
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.01,
            sources_used=["url"],
        )

        # Access nested models
        assert article.main_sections[0].subsections[0].heading == "Subsection"
