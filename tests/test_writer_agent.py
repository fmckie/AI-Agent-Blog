"""
Test suite for the Writer Agent.

This module contains comprehensive tests for the Writer Agent,
including tool functions, agent execution, and SEO validation.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from tests.helpers import MockAgentRunResult, create_valid_article_output
from writer_agent import create_writer_agent, run_writer_agent
from writer_agent.tools import (
    calculate_keyword_density,
    check_seo_requirements,
    format_sources_for_citation,
    generate_keyword_variations,
)
from writer_agent.utilities import (
    analyze_keyword_placement,
    calculate_content_score,
    calculate_readability_score,
    extract_headers_structure,
    find_transition_words,
    validate_header_hierarchy,
)


# Fixtures
@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        tavily_api_key="tvly-test1234567890abcdef1234567890ab",
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890ab",
        llm_model="gpt-4",
        output_dir="./test_drafts",
        log_level="DEBUG",
    )


@pytest.fixture
def mock_research_findings():
    """Create mock research findings for testing."""
    return ResearchFindings(
        keyword="artificial intelligence",
        research_summary="AI is transforming various industries with significant improvements in efficiency and accuracy. This comprehensive research explores the latest developments in artificial intelligence and its wide-ranging applications.",
        academic_sources=[
            AcademicSource(
                title="Deep Learning in Healthcare",
                url="https://example.edu/ai-healthcare",
                excerpt="AI shows 78% improvement in diagnostic accuracy",
                domain=".edu",
                credibility_score=0.95,
            ),
            AcademicSource(
                title="AI in Business Automation",
                url="https://journal.org/ai-business",
                excerpt="Companies report 45% efficiency gains with AI implementation",
                domain=".org",
                credibility_score=0.88,
            ),
            AcademicSource(
                title="Ethical Considerations in AI",
                url="https://ethics.edu/ai-ethics",
                excerpt="67% of AI systems lack proper ethical guidelines",
                domain=".edu",
                credibility_score=0.92,
            ),
        ],
        main_findings=[
            "AI improves diagnostic accuracy by 78% in healthcare",
            "45% efficiency gains reported in business automation",
            "67% of AI systems lack ethical guidelines",
        ],
        key_statistics=["78%", "45%", "67%"],
        research_gaps=[
            "Long-term impact studies needed",
            "More research on AI bias required",
        ],
        total_sources_analyzed=5,
        search_query_used="artificial intelligence academic research",
    )


@pytest.fixture
def sample_article_content():
    """Create sample article content for testing."""
    return """
    <h1>Artificial Intelligence: Transforming Our Digital Future</h1>
    
    <p>Artificial intelligence is revolutionizing the way we live and work. 
    This comprehensive guide explores the latest developments in AI technology
    and its impact across various industries.</p>
    
    <h2>Understanding Artificial Intelligence</h2>
    <p>At its core, artificial intelligence refers to computer systems that
    can perform tasks typically requiring human intelligence. These systems
    use machine learning algorithms to process data and make decisions.</p>
    
    <h2>Applications in Healthcare</h2>
    <p>The healthcare industry has seen remarkable improvements through AI
    implementation. Recent studies show a 78% improvement in diagnostic
    accuracy when AI assists medical professionals.</p>
    
    <h3>Diagnostic Tools</h3>
    <p>AI-powered diagnostic tools analyze medical images with unprecedented
    precision. Furthermore, these systems continuously learn from new data.</p>
    
    <h2>Business Automation</h2>
    <p>Companies implementing AI report 45% efficiency gains. Moreover,
    automation reduces human error and improves consistency.</p>
    
    <h2>Ethical Considerations</h2>
    <p>However, ethical concerns remain paramount. Research indicates that
    67% of AI systems lack proper ethical guidelines.</p>
    
    <p>In conclusion, artificial intelligence offers tremendous potential
    while requiring careful consideration of ethical implications.</p>
    """


class TestWriterTools:
    """Test suite for writer agent tools."""

    def test_calculate_keyword_density(self):
        """Test keyword density calculation."""
        # Create mock context
        ctx = Mock()
        ctx.deps = {"research": Mock()}

        # Test with simple content
        content = "Artificial intelligence is amazing. AI transforms industries."
        keyword = "artificial intelligence"

        density = calculate_keyword_density(ctx, content, keyword)

        # Should find "artificial intelligence" once in 8 words
        assert density > 0
        assert density < 50  # Reasonable upper bound

    def test_calculate_keyword_density_multi_word(self):
        """Test keyword density with multi-word keywords."""
        ctx = Mock()
        ctx.deps = {"research": Mock()}

        content = "Machine learning is part of artificial intelligence. Machine learning has many applications."
        keyword = "machine learning"

        density = calculate_keyword_density(ctx, content, keyword)

        # Should find "machine learning" twice
        assert density > 0

    def test_format_sources_for_citation(self, mock_research_findings):
        """Test source formatting for citations."""
        ctx = Mock()
        ctx.deps = {"research": mock_research_findings}

        source_urls = [
            "https://example.edu/ai-healthcare",
            "https://journal.org/ai-business",
        ]

        citations = format_sources_for_citation(ctx, source_urls)

        assert len(citations) == 2
        assert "Deep Learning in Healthcare" in citations[0]
        assert "https://example.edu/ai-healthcare" in citations[0]

    def test_check_seo_requirements(self, sample_article_content):
        """Test SEO requirements checking."""
        ctx = Mock()
        ctx.deps = {"research": Mock()}

        title = "Artificial Intelligence: Transforming Our Digital Future"
        meta = "Discover how artificial intelligence is revolutionizing industries with 78% improvements in healthcare diagnostics and 45% efficiency gains."
        keyword = "artificial intelligence"

        results = check_seo_requirements(
            ctx, title, meta, sample_article_content, keyword
        )

        assert "passes_all" in results
        assert "checks" in results

        # Check individual validations
        assert results["checks"]["keyword_in_title"]["value"] is True
        assert results["checks"]["keyword_in_meta"]["value"] is True
        assert 50 <= results["checks"]["title_length"]["value"] <= 60
        assert 120 <= results["checks"]["meta_length"]["value"] <= 160

    def test_generate_keyword_variations(self):
        """Test keyword variation generation."""
        ctx = Mock()

        # Test single word
        variations = generate_keyword_variations(ctx, "marketing")
        assert "marketing" in variations
        assert "marketings" in variations or "marketing" in variations
        assert any("guide" in v for v in variations)

        # Test multi-word
        variations = generate_keyword_variations(ctx, "content marketing")
        assert "content marketing" in variations
        assert "content-marketing" in variations
        assert any("marketing content" in v for v in variations)


class TestWriterUtilities:
    """Test suite for writer utility functions."""

    def test_calculate_readability_score(self, sample_article_content):
        """Test readability score calculation."""
        score_data = calculate_readability_score(sample_article_content)

        assert "score" in score_data
        assert "level" in score_data
        assert 0 <= score_data["score"] <= 100
        assert score_data["word_count"] > 0
        assert score_data["sentence_count"] > 0

    def test_extract_headers_structure(self, sample_article_content):
        """Test header extraction."""
        headers = extract_headers_structure(sample_article_content)

        assert len(headers) > 0
        assert any(h["level"] == 1 for h in headers)
        assert any(
            h["text"] == "Artificial Intelligence: Transforming Our Digital Future"
            for h in headers
        )
        assert any(h["level"] == 2 for h in headers)
        assert any(h["level"] == 3 for h in headers)

    def test_validate_header_hierarchy(self):
        """Test header hierarchy validation."""
        # Good hierarchy
        good_headers = [
            {"level": 1, "text": "Main Title"},
            {"level": 2, "text": "Section 1"},
            {"level": 3, "text": "Subsection 1.1"},
            {"level": 2, "text": "Section 2"},
        ]

        result = validate_header_hierarchy(good_headers)
        assert result["valid"] is True
        assert result["h1_count"] == 1

        # Bad hierarchy - multiple H1s
        bad_headers = [
            {"level": 1, "text": "Title 1"},
            {"level": 1, "text": "Title 2"},
            {"level": 2, "text": "Section"},
        ]

        result = validate_header_hierarchy(bad_headers)
        assert result["valid"] is False
        assert "Multiple H1" in str(result["issues"])

    def test_find_transition_words(self, sample_article_content):
        """Test transition word detection."""
        transitions = find_transition_words(sample_article_content)

        assert "found" in transitions
        assert "total_count" in transitions
        assert "percentage" in transitions

        # Should find "furthermore", "moreover", "however"
        assert transitions["total_count"] > 0
        assert any(t["word"] == "furthermore" for t in transitions["found"])

    def test_analyze_keyword_placement(self, sample_article_content):
        """Test keyword placement analysis."""
        analysis = analyze_keyword_placement(
            sample_article_content, "artificial intelligence"
        )

        assert analysis["in_title"] is True
        assert analysis["in_first_paragraph"] is True
        assert analysis["total_occurrences"] > 0
        assert len(analysis["positions"]) > 0
        assert len(analysis["in_headers"]) > 0

    def test_calculate_content_score(self, sample_article_content):
        """Test content scoring."""
        score_data = calculate_content_score(
            sample_article_content,
            "artificial intelligence",
            word_count=250,
            sources_count=3,
        )

        assert "total_score" in score_data
        assert "grade" in score_data
        assert "breakdown" in score_data
        assert 0 <= score_data["total_score"] <= 100

        # Check individual scores
        assert "word_count" in score_data["breakdown"]
        assert "readability" in score_data["breakdown"]
        assert "keyword_optimization" in score_data["breakdown"]


class TestWriterAgent:
    """Test suite for the Writer Agent."""

    @pytest.mark.asyncio
    async def test_create_writer_agent(self, test_config):
        """Test writer agent creation."""
        agent = create_writer_agent(test_config)

        assert agent is not None
        assert agent.output_type == ArticleOutput
        assert agent.model is not None

    @pytest.mark.asyncio
    async def test_run_writer_agent_success(self, test_config, mock_research_findings):
        """Test successful writer agent execution."""
        agent = create_writer_agent(test_config)

        # Use helper to create valid article output
        expected_article = create_valid_article_output(
            keyword="artificial intelligence",
            title="Artificial Intelligence: The Future is Now",
            sources_count=3,
        )

        # Mock the agent's run method to return a proper AgentRunResult
        mock_result = MockAgentRunResult(expected_article)

        with patch.object(agent, "run", new=AsyncMock(return_value=mock_result)):
            result = await run_writer_agent(
                agent, "artificial intelligence", mock_research_findings
            )

            assert result.title == expected_article.title
            assert result.word_count >= 1000
            assert len(result.main_sections) >= 3
            assert len(result.sources_used) > 0
            assert 0.005 <= result.keyword_density <= 0.03

    @pytest.mark.asyncio
    async def test_run_writer_agent_no_sources(
        self, test_config, mock_research_findings
    ):
        """Test writer agent with no sources cited."""
        agent = create_writer_agent(test_config)

        # Create article without sources using helper
        bad_article = create_valid_article_output(
            keyword="test", sources_count=0  # No sources!
        )

        # Mock the agent's run method to return a proper AgentRunResult
        mock_result = MockAgentRunResult(bad_article)

        with patch.object(agent, "run", new=AsyncMock(return_value=mock_result)):
            with pytest.raises(ValueError, match="must cite research sources"):
                await run_writer_agent(agent, "test", mock_research_findings)

    def test_article_html_generation(self):
        """Test HTML generation from article."""
        article = ArticleOutput(
            title="Test Article",
            meta_description="Test meta description that is long enough to meet the 120-160 character requirement for proper SEO validation and testing purposes.",
            focus_keyword="test",
            introduction="Test introduction that meets the minimum 150 character requirement. This comprehensive introduction provides the necessary context for our test article and ensures all validation rules are satisfied.",
            main_sections=[
                ArticleSection(
                    heading="Section One Title",
                    content="Content for section one that meets the 200 character minimum requirement. This section contains detailed information and comprehensive content to ensure proper validation. We need sufficient content here."
                    * 2,
                ),
                ArticleSection(
                    heading="Section Two Title",
                    content="Content for section two that also meets the 200 character minimum requirement. This section provides additional information and maintains the quality standards required for proper content validation."
                    * 2,
                ),
                ArticleSection(
                    heading="Section Three Title",
                    content="Content for section three to meet the minimum three sections requirement. This final section also contains at least 200 characters of meaningful content to satisfy all validation requirements."
                    * 2,
                ),
            ],
            conclusion="Test conclusion that meets the 100 character minimum requirement. This conclusion effectively summarizes the article content.",
            word_count=1000,
            reading_time_minutes=5,
            keyword_density=0.01,
            sources_used=["https://example.com"],
        )

        html = article.to_html()

        assert "<h1>Test Article</h1>" in html
        assert "<h2>Section One Title</h2>" in html
        assert "<h2>Section Two Title</h2>" in html
        assert "Test introduction" in html
        assert "Test conclusion" in html
        assert "5 min read" in html


class TestWriterAgentIntegration:
    """Integration tests for the Writer Agent."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_writer_agent_with_real_api(
        self, test_config, mock_research_findings
    ):
        """Test writer agent with real API calls."""
        # Skip if API keys are not real
        if test_config.openai_api_key.startswith("sk-test"):
            pytest.skip("Skipping integration test - no real API keys")

        agent = create_writer_agent(test_config)

        # Run with mock research findings
        result = await run_writer_agent(
            agent, "artificial intelligence", mock_research_findings
        )

        # Verify real results
        assert result.title != ""
        assert len(result.title) <= 70
        assert result.meta_description != ""
        assert 120 <= len(result.meta_description) <= 160
        assert result.word_count >= 1000
        assert len(result.main_sections) >= 3
        assert result.keyword_density > 0
        assert len(result.sources_used) >= 3
