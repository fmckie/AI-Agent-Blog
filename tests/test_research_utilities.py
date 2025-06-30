"""
Comprehensive tests for Research Agent utility functions.

This test file covers all utility functions in research_agent/utilities.py,
including citation formatting, theme extraction, and quality assessment.
"""

from datetime import datetime
from typing import Any, Dict, List

# Import testing utilities
import pytest

# Import models for test data
from models import AcademicSource, ResearchFindings

# Import utilities to test
from research_agent.utilities import (
    assess_research_quality,
    calculate_source_diversity,
    extract_research_themes,
    format_apa_citation,
    format_mla_citation,
    generate_research_questions,
    identify_conflicting_findings,
)


class TestCitationFormatting:
    """Test cases for citation formatting functions."""

    def test_apa_citation_full_metadata(self):
        """Test APA citation with complete metadata."""
        # Create source with all fields
        source = AcademicSource(
            title="The Impact of AI on Healthcare",
            url="https://journal.edu/article123",
            authors=["John Smith", "Jane Doe", "Bob Johnson"],
            publication_date="2024-03-15",
            journal_name="Journal of AI Research",
            excerpt="This study examines...",
            domain=".edu",
            credibility_score=0.9,
        )

        # Generate APA citation
        citation = format_apa_citation(source)

        # Verify citation components
        assert "Smith, J., Doe, J., Johnson, B." in citation
        assert "(2024)" in citation
        assert "The Impact of AI on Healthcare." in citation
        assert "*Journal of AI Research*." in citation
        assert "Retrieved from https://journal.edu/article123" in citation

    def test_apa_citation_many_authors(self):
        """Test APA citation with more than 3 authors."""
        # Create source with many authors
        source = AcademicSource(
            title="Collaborative Research Study",
            url="https://example.edu/study",
            authors=[
                "Author One",
                "Author Two",
                "Author Three",
                "Author Four",
                "Author Five",
            ],
            publication_date="2023-01-01",
            excerpt="Abstract",
            domain=".edu",
            credibility_score=0.8,
        )

        citation = format_apa_citation(source)

        # Should show first 3 authors then et al.
        assert "One, A., Two, A., Three, A., et al." in citation
        assert "Four" not in citation  # Fourth author not shown

    def test_apa_citation_no_authors(self):
        """Test APA citation without authors."""
        # Create source without authors
        source = AcademicSource(
            title="Anonymous Research Paper",
            url="https://example.com/paper",
            excerpt="Content",
            domain=".com",
            credibility_score=0.7,
        )

        citation = format_apa_citation(source)

        # Should use "Unknown Author"
        assert "Unknown Author" in citation
        assert "(n.d.)" in citation  # No date

    def test_apa_citation_author_name_parsing(self):
        """Test APA citation with various author name formats."""
        # Test single-word author name
        source = AcademicSource(
            title="Test Paper",
            url="https://test.edu",
            authors=["Einstein"],  # Single name
            excerpt="Test",
            domain=".edu",
            credibility_score=0.8,
        )

        citation = format_apa_citation(source)
        assert "Einstein" in citation  # Should include as-is

        # Test author with middle name
        source.authors = ["Albert B. Einstein"]
        citation = format_apa_citation(source)
        assert "Einstein, A." in citation  # Should format as Last, F.

    def test_apa_citation_date_extraction(self):
        """Test APA citation date handling."""
        source = AcademicSource(
            title="Test",
            url="https://test.edu",
            excerpt="Test",
            domain=".edu",
            credibility_score=0.8,
        )

        # Test various date formats
        date_tests = [
            ("2024-03-15", "(2024)"),
            ("March 15, 2024", "(2024)"),
            ("15/03/2024", "(2024)"),
            ("Published in 2023", "(2023)"),
            ("1999 study", "(1999)"),
            ("No year here", "(No year here)"),  # Can't extract year
        ]

        for date_input, expected in date_tests:
            source.publication_date = date_input
            citation = format_apa_citation(source)
            assert expected in citation

    def test_mla_citation_full_metadata(self):
        """Test MLA citation with complete metadata."""
        # Create source with all fields
        source = AcademicSource(
            title="Digital Humanities Research",
            url="https://journal.org/article",
            authors=["Sarah Johnson"],
            publication_date="15 Mar. 2024",
            journal_name="Digital Studies Quarterly",
            excerpt="Abstract text",
            domain=".org",
            credibility_score=0.85,
        )

        citation = format_mla_citation(source)

        # Verify MLA format
        assert "Sarah Johnson." in citation
        assert '"Digital Humanities Research."' in citation
        assert "*Digital Studies Quarterly*," in citation
        assert "15 Mar. 2024," in citation
        assert "https://journal.org/article." in citation

    def test_mla_citation_two_authors(self):
        """Test MLA citation with two authors."""
        source = AcademicSource(
            title="Collaborative Study",
            url="https://example.edu",
            authors=["John Smith", "Jane Doe"],
            excerpt="Test",
            domain=".edu",
            credibility_score=0.8,
        )

        citation = format_mla_citation(source)
        assert "John Smith, and Jane Doe." in citation

    def test_mla_citation_three_plus_authors(self):
        """Test MLA citation with three or more authors."""
        source = AcademicSource(
            title="Multi-Author Paper",
            url="https://example.edu",
            authors=["Author One", "Author Two", "Author Three"],
            excerpt="Test",
            domain=".edu",
            credibility_score=0.8,
        )

        citation = format_mla_citation(source)
        assert "Author One, et al." in citation
        assert "Author Two" not in citation  # Only first author shown


class TestThemeExtraction:
    """Test cases for theme extraction functionality."""

    def test_extract_themes_from_findings(self):
        """Test extracting themes from research findings."""
        # Create research findings with theme-rich content
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
            keyword="climate change",
            research_summary="This research reveals significant trends in global warming patterns. The study demonstrates the critical impact of human activities.",
            academic_sources=sources,
            main_findings=[
                "Temperature increases show a clear upward trend",
                "The primary challenge is reducing carbon emissions",
                "Renewable energy presents a major opportunity for mitigation",
            ],
            total_sources_analyzed=5,
            search_query_used="climate change research",
        )

        themes = extract_research_themes(findings)

        # Should extract multiple themes
        assert len(themes) > 0
        assert len(themes) <= 10  # Limited to 10

        # Check for expected theme patterns
        theme_text = " ".join(themes)
        assert any(
            word in theme_text.lower()
            for word in ["trend", "impact", "challenge", "opportunity"]
        )

    def test_extract_themes_empty_findings(self):
        """Test theme extraction with minimal content."""
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
            research_summary="This is a longer research summary without many themes but with sufficient content to meet the minimum character requirement for proper validation.",
            academic_sources=sources,
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        themes = extract_research_themes(findings)

        # Should still work but return fewer themes
        assert isinstance(themes, list)
        assert len(themes) <= 10

    def test_extract_themes_deduplication(self):
        """Test that duplicate themes are removed."""
        sources = [
            AcademicSource(
                title="Test",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
        ]

        # Create findings with repetitive content
        findings = ResearchFindings(
            keyword="AI",
            research_summary="This trend shows a significant trend. The trend is important for understanding the overall patterns in the data and their implications for future research.",
            academic_sources=sources,
            main_findings=[
                "The significant trend continues",
                "Another significant trend emerges",
                "This trend is significant",
            ],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        themes = extract_research_themes(findings)

        # Should deduplicate similar themes
        assert len(themes) == len(set(themes))  # No duplicates


class TestSourceDiversity:
    """Test cases for source diversity calculation."""

    def test_calculate_diversity_comprehensive(self):
        """Test diversity calculation with varied sources."""
        # Create diverse sources
        sources = [
            AcademicSource(
                title="Recent Study",
                url="https://uni.edu/1",
                publication_date="2024-01-01",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="Government Report",
                url="https://agency.gov/2",
                publication_date="2023-06-15",
                excerpt="Test",
                domain=".gov",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Older Research",
                url="https://journal.org/3",
                publication_date="2018-03-20",
                excerpt="Test",
                domain=".org",
                credibility_score=0.7,
            ),
            AcademicSource(
                title="Commercial Study",
                url="https://research.com/4",
                publication_date="2022-11-30",
                excerpt="Test",
                domain=".com",
                credibility_score=0.5,
            ),
        ]

        diversity = calculate_source_diversity(sources)

        # Check structure
        assert "total_sources" in diversity
        assert diversity["total_sources"] == 4

        # Check domain distribution
        assert len(diversity["domain_distribution"]) == 4  # 4 different domains
        assert diversity["domain_distribution"][".edu"] == 1
        assert diversity["domain_distribution"][".gov"] == 1

        # Check year distribution
        assert "very_recent" in diversity["year_distribution"]  # 2024 source
        assert "recent" in diversity["year_distribution"]  # 2023, 2022 sources
        assert "older" in diversity["year_distribution"]  # 2018 source

        # Check credibility distribution
        assert diversity["credibility_distribution"]["high"] == 2  # 0.9, 0.85
        assert diversity["credibility_distribution"]["medium"] == 1  # 0.7
        assert diversity["credibility_distribution"]["low"] == 1  # 0.5

        # Check diversity score
        assert 0 <= diversity["diversity_score"] <= 1
        assert diversity["diversity_score"] > 0.5  # Should be relatively high

    def test_calculate_diversity_single_domain(self):
        """Test diversity with sources from single domain."""
        # All sources from .edu
        sources = [
            AcademicSource(
                title=f"Study {i}",
                url=f"https://uni{i}.edu/paper",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            )
            for i in range(3)
        ]

        diversity = calculate_source_diversity(sources)

        # Low domain diversity
        assert len(diversity["domain_distribution"]) == 1
        assert diversity["domain_distribution"][".edu"] == 3

        # Diversity score should be lower
        assert diversity["diversity_score"] < 0.7

    def test_calculate_diversity_no_dates(self):
        """Test diversity calculation when sources lack dates."""
        sources = [
            AcademicSource(
                title="Undated Source",
                url="https://example.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
                publication_date=None,  # No date
            )
        ]

        diversity = calculate_source_diversity(sources)

        # Should handle missing dates gracefully
        assert len(diversity["year_distribution"]) == 0
        assert diversity["diversity_score"] >= 0

    def test_calculate_diversity_empty_list(self):
        """Test diversity calculation with no sources."""
        diversity = calculate_source_diversity([])

        assert diversity["total_sources"] == 0
        assert diversity["diversity_score"] == 0.0
        assert len(diversity["domain_distribution"]) == 0


class TestConflictIdentification:
    """Test cases for identifying conflicts in findings."""

    def test_identify_conflicts_with_indicators(self):
        """Test identifying conflicts using indicator words."""
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
            keyword="treatment effectiveness",
            research_summary="Studies show mixed results across different populations and contexts, suggesting the need for more nuanced approaches to understanding these complex phenomena.",
            academic_sources=sources,
            main_findings=[
                "Treatment A shows 80% effectiveness in clinical trials.",
                "However, real-world studies indicate only 45% effectiveness.",
                "There is ongoing debate about the methodology used.",
                "Despite initial promise, long-term outcomes remain disputed.",
            ],
            total_sources_analyzed=10,
            search_query_used="treatment effectiveness",
        )

        conflicts = identify_conflicting_findings(findings)

        # Should identify multiple conflicts
        assert len(conflicts) > 0
        assert len(conflicts) <= 5  # Limited to 5

        # Check conflict structure
        for conflict in conflicts:
            assert "indicator" in conflict
            assert "description" in conflict
            assert conflict["indicator"] in ["however", "debate", "disputed", "despite"]

    def test_identify_conflicts_no_conflicts(self):
        """Test when no conflicts are present."""
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
            keyword="clear results",
            research_summary="All studies agree on the fundamental principles underlying this phenomenon, providing strong evidence for the theoretical framework proposed in recent literature.",
            academic_sources=sources,
            main_findings=[
                "Study A confirms the hypothesis.",
                "Study B supports these findings.",
                "Study C provides additional evidence.",
            ],
            total_sources_analyzed=3,
            search_query_used="clear results",
        )

        conflicts = identify_conflicting_findings(findings)

        # Should return empty list when no conflicts
        assert len(conflicts) == 0

    def test_identify_conflicts_sentence_length(self):
        """Test that very short sentences are ignored."""
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
            research_summary="This is a comprehensive test summary that provides adequate content for validation purposes while maintaining clarity and relevance to the research topic.",
            academic_sources=sources,
            main_findings=[
                "However short.",  # Too short, should be ignored
                "This is a longer sentence that mentions however the results vary significantly.",
            ],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        conflicts = identify_conflicting_findings(findings)

        # Should only include longer sentences
        if conflicts:
            for conflict in conflicts:
                assert len(conflict["description"]) > 20


class TestResearchQuestions:
    """Test cases for research question generation."""

    def test_generate_questions_from_gaps(self):
        """Test generating questions based on research gaps."""
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
            keyword="machine learning ethics",
            research_summary="Current research on ML ethics reveals complex challenges in bias mitigation, transparency, and accountability that require interdisciplinary collaboration.",
            academic_sources=sources,
            research_gaps=[
                "Further research is needed on bias mitigation",
                "Long-term impacts remain unclear",
                "Limited data on cross-cultural applications",
            ],
            main_findings=[
                "AI bias is prevalent",
                "Transparency is crucial",
                "Regulation is emerging",
            ],
            total_sources_analyzed=5,
            search_query_used="ML ethics",
        )

        questions = generate_research_questions(findings)

        # Should generate multiple questions
        assert len(questions) > 0
        assert len(questions) <= 8  # Limited to 8

        # All should be questions
        for q in questions:
            assert q.endswith("?")

        # Should address gaps
        question_text = " ".join(questions)
        assert (
            "bias" in question_text
            or "unclear" in question_text
            or "limited" in question_text.lower()
        )

    def test_generate_questions_minimal_data(self):
        """Test question generation with minimal findings."""
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
            keyword="test topic",
            research_summary="This basic research summary provides foundational insights into the topic while meeting all validation requirements for content length and comprehensiveness.",
            academic_sources=sources,
            research_gaps=[],  # No gaps
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        questions = generate_research_questions(findings)

        # Should still generate general questions
        assert len(questions) > 0

        # Check for general question patterns
        question_text = " ".join(questions)
        assert any(
            term in question_text
            for term in ["ethical", "implications", "future", "apply"]
        )

    def test_generate_questions_deduplication(self):
        """Test that duplicate questions are removed."""
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
            keyword="AI",
            research_summary="AI research demonstrates transformative potential across multiple domains, with significant implications for technological advancement and societal impact.",
            academic_sources=sources,
            research_gaps=[
                "Further research is needed on ethics",
                "Further research is needed on ethics",  # Duplicate
            ],
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=1,
            search_query_used="AI",
        )

        questions = generate_research_questions(findings)

        # Should have no duplicate questions
        assert len(questions) == len(set(questions))


class TestResearchQualityAssessment:
    """Test cases for research quality assessment."""

    def test_assess_high_quality_research(self):
        """Test assessment of high-quality research."""
        # Create high-quality sources
        sources = [
            AcademicSource(
                title=f"High Quality Study {i}",
                url=f"https://journal{i}.edu/paper",
                publication_date=f"2024-0{i+1}-01",
                excerpt="Peer-reviewed research",
                domain=".edu" if i % 2 == 0 else ".gov",
                credibility_score=0.85 + (i * 0.03),
            )
            for i in range(5)
        ]

        findings = ResearchFindings(
            keyword="quantum computing",
            research_summary="Comprehensive analysis of quantum computing advances reveals breakthroughs in error correction, qubit stability, and algorithmic efficiency that promise to revolutionize computational capabilities.",
            academic_sources=sources,
            key_statistics=[
                "99.9% accuracy",
                "1000x speedup",
                "50 qubit milestone",
                "Error rate < 0.1%",
            ],
            research_gaps=["Scalability challenges"],
            main_findings=[
                "Major breakthrough",
                "Commercial viability",
                "Technical advances",
            ],
            total_sources_analyzed=10,
            search_query_used="quantum computing research",
        )

        assessment = assess_research_quality(findings)

        # Check overall high quality
        assert assessment["overall_score"] > 0.7
        assert len(assessment["strengths"]) > len(assessment["weaknesses"])

        # Check specific metrics
        assert assessment["metrics"]["source_quality"] > 0.8
        assert assessment["metrics"]["source_quantity"] == 1.0  # 5 sources
        assert assessment["metrics"]["content_depth"] > 0.7  # Has statistics
        assert assessment["metrics"]["recency"] > 0.8  # All 2024

        # Should have positive assessment
        assert any(
            "High-quality" in s or "Excellent" in s for s in assessment["strengths"]
        )

    def test_assess_low_quality_research(self):
        """Test assessment of low-quality research."""
        # Create low-quality sources
        sources = [
            AcademicSource(
                title="Old Study",
                url="https://site.com/page",
                publication_date="2015-01-01",
                excerpt="Outdated research",
                domain=".com",
                credibility_score=0.5,
            ),
            AcademicSource(
                title="Another Old Study",
                url="https://blog.net/post",
                publication_date="2010-01-01",
                excerpt="Very old findings",
                domain=".net",
                credibility_score=0.4,
            ),
        ]

        findings = ResearchFindings(
            keyword="outdated topic",
            research_summary="Limited research available on this topic.",
            academic_sources=sources,
            key_statistics=[],  # No statistics
            research_gaps=["Many unknowns"],
            main_findings=[
                "Limited data",
                "Inconclusive results",
                "More research needed",
            ],
            total_sources_analyzed=2,
            search_query_used="outdated topic",
        )

        assessment = assess_research_quality(findings)

        # Check overall low quality
        assert assessment["overall_score"] < 0.6
        assert len(assessment["weaknesses"]) > 0
        assert len(assessment["recommendations"]) > 0

        # Check specific weaknesses
        assert assessment["metrics"]["source_quality"] < 0.6
        assert assessment["metrics"]["source_quantity"] < 0.5
        assert assessment["metrics"]["recency"] < 0.3

        # Should recommend improvements
        assert any("additional research" in r for r in assessment["recommendations"])

    def test_assess_mixed_quality_research(self):
        """Test assessment of mixed quality research."""
        sources = [
            AcademicSource(
                title="Recent High Quality",
                url="https://journal.edu",
                publication_date="2024-01-01",
                excerpt="Excellent research",
                domain=".edu",
                credibility_score=0.95,
            ),
            AcademicSource(
                title="Old Low Quality",
                url="https://blog.com",
                publication_date="2015-01-01",  # Older date to trigger outdated warning
                excerpt="Blog post",
                domain=".com",
                credibility_score=0.3,
            ),
            AcademicSource(
                title="Medium Quality",
                url="https://org.org",
                publication_date="2022-01-01",
                excerpt="Organization report",
                domain=".org",
                credibility_score=0.7,
            ),
        ]

        findings = ResearchFindings(
            keyword="mixed topic",
            research_summary="Research with varying quality across different sources demonstrates the complexity of this topic and highlights the need for careful evaluation.",
            academic_sources=sources,
            key_statistics=["Some data"],  # Less than 3 to trigger weakness
            research_gaps=["Gaps exist"],
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=3,
            search_query_used="mixed",
        )

        assessment = assess_research_quality(findings)

        # Should have mixed assessment with overall score in middle range
        assert 0.4 < assessment["overall_score"] < 0.8
        # With current test data, we get recommendations but not necessarily strengths/weaknesses
        assert len(assessment["recommendations"]) > 0
        # Check that metrics are populated correctly
        assert assessment["metrics"]["source_quality"] == 0.65
        assert assessment["metrics"]["source_quantity"] == 0.7
        assert assessment["metrics"]["content_depth"] == 0.5

    def test_assess_empty_sources(self):
        """Test assessment with minimal sources."""
        sources = [
            AcademicSource(
                title="Single Source",
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

        assessment = assess_research_quality(findings)

        # Should identify lack of sources as weakness
        assert assessment["metrics"]["source_quantity"] < 0.5
        assert any("Limited number of sources" in w for w in assessment["weaknesses"])


# Edge case tests
class TestUtilitiesEdgeCases:
    """Test edge cases and error handling."""

    def test_format_citations_special_characters(self):
        """Test citation formatting with special characters."""
        source = AcademicSource(
            title="Research on COVID-19 & Machine Learning: A Multi-disciplinary Study",
            url="https://journal.edu/article?id=12345&lang=en",
            authors=["O'Brien, Patrick", "José García-López", "Anne-Marie Smith"],
            excerpt="Test",
            domain=".edu",
            credibility_score=0.8,
        )

        # Test both citation formats
        apa = format_apa_citation(source)
        mla = format_mla_citation(source)

        # Should handle special characters
        assert "COVID-19 & Machine Learning" in apa
        assert "COVID-19 & Machine Learning" in mla
        assert "O'Brien" in apa
        assert "García-López" in apa

    def test_theme_extraction_no_matches(self):
        """Test theme extraction when no patterns match."""
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
            keyword="abc",
            research_summary="XYZ ABC DEF GHI JKL MNO PQR.",  # No theme indicators, but long enough
            academic_sources=sources,
            main_findings=["A", "B", "C"],  # Too short
            total_sources_analyzed=1,
            search_query_used="test",
        )

        themes = extract_research_themes(findings)

        # Should return empty list or very few themes
        assert isinstance(themes, list)
        assert len(themes) <= 2

    def test_quality_assessment_edge_values(self):
        """Test quality assessment with edge case values."""
        # Test with exactly threshold values
        sources = [
            AcademicSource(
                title="Threshold Study",
                url="https://test.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.6,  # Exactly at medium threshold
            )
            for _ in range(3)  # Exactly 3 sources
        ]

        findings = ResearchFindings(
            keyword="test",
            research_summary="a" * 100,
            academic_sources=sources,
            key_statistics=["Stat 1", "Stat 2"],  # Just under 3
            main_findings=["1", "2", "3"],
            total_sources_analyzed=3,
            search_query_used="test",
        )

        assessment = assess_research_quality(findings)

        # Check edge case handling
        assert assessment["metrics"]["source_quantity"] == 0.7  # 3 sources = 0.7
        assert assessment["metrics"]["content_depth"] < 0.8  # Less than 3 stats
