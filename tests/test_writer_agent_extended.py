"""
Extended tests for writer agent to improve coverage.

This module adds additional test cases for the writer agent,
focusing on article generation and formatting.
"""

import asyncio
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_ai import Agent

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from writer_agent import create_writer_agent
from writer_agent.agent import run_writer_agent


def create_valid_sections(count: int = 3) -> List[ArticleSection]:
    """Create valid article sections that meet validation requirements."""
    return [
        ArticleSection(
            heading=f"Section {i}: Important Information",
            content=f"This is section {i} with comprehensive content that provides valuable information to readers. "
            f"The content is detailed enough to meet the minimum length requirements while being informative. "
            f"We ensure each section has substantial content that adds value to the article.",
        )
        for i in range(1, count + 1)
    ]


class TestWriterAgentExtended:
    """Extended test cases for writer agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.llm_model = "gpt-4"
        config.max_retries = 3
        return config

    @pytest.fixture
    def sample_research_findings(self) -> ResearchFindings:
        """Create sample research findings."""
        sources = [
            AcademicSource(
                title="AI in Healthcare Study",
                url="https://journal.edu/ai-health",
                authors=["Smith, J."],
                publication_date="2024-01-15",
                excerpt="AI improves diagnostic accuracy...",
                domain=".edu",
                credibility_score=0.95,
            ),
        ]

        return ResearchFindings(
            keyword="AI healthcare",
            research_summary="AI is transforming healthcare through improved diagnostics.",
            academic_sources=sources,
            key_statistics=["diagnosis_improvement: 30%", "cost_reduction: 20%"],
            research_gaps=["Long-term studies needed"],
            main_findings=["AI diagnostics", "Healthcare efficiency"],
            total_sources_analyzed=1,
            search_query_used="AI healthcare",
        )

    @pytest.mark.asyncio
    async def test_create_writer_agent(self, mock_config):
        """Test writer agent creation."""
        with patch("writer_agent.agent.Agent") as mock_agent_class:
            agent = create_writer_agent(mock_config)

            # Verify agent was created with correct parameters
            mock_agent_class.assert_called_once()
            call_args = mock_agent_class.call_args

            assert call_args[1]["model"] == "openai:gpt-4"
            assert (
                "output_type" in call_args[1]
            )  # Changed from result_type to output_type

    @pytest.mark.asyncio
    async def test_run_writer_agent_success(
        self, mock_config, sample_research_findings
    ):
        """Test successful writer agent execution."""
        mock_agent = Mock()
        mock_result = Mock()

        # Create expected article output
        sections = [
            ArticleSection(
                heading="Introduction to AI in Healthcare",
                content="AI is revolutionizing healthcare by enabling more accurate diagnoses, personalized treatment plans, and efficient patient care. This technological advancement is transforming medical practices globally.",
            ),
            ArticleSection(
                heading="Current Applications",
                content="Modern AI applications include diagnostic imaging analysis, drug discovery, predictive analytics for patient outcomes, and automated administrative tasks. These innovations are improving healthcare delivery significantly.",
            ),
        ]

        # Add a third section to meet validation requirements
        sections.append(
            ArticleSection(
                heading="Future Directions and Research Opportunities",
                content="The future of AI in healthcare holds immense promise. Emerging areas include precision medicine, where AI analyzes genetic data to create personalized treatment plans. Additionally, AI-powered virtual health assistants are becoming more sophisticated, providing 24/7 patient support and monitoring.",
            )
        )

        mock_result.data = ArticleOutput(
            title="The Future of AI in Healthcare",
            meta_description="Discover how AI is transforming healthcare with improved diagnostics and personalized treatments for better patient outcomes.",
            focus_keyword="AI healthcare",
            introduction="Artificial intelligence is reshaping healthcare in unprecedented ways. From diagnostic imaging to personalized medicine, AI technologies are enabling medical professionals to provide more accurate, efficient, and patient-centered care. This article explores the current state and future potential of AI in healthcare.",
            main_sections=sections,
            conclusion="AI will continue to transform healthcare, bringing innovations that improve patient outcomes, reduce costs, and enhance the quality of care. As technology advances, we can expect even more groundbreaking applications in the medical field.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=["https://journal.edu/ai-health"],
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_writer_agent(
            mock_agent, "AI healthcare", sample_research_findings
        )

        assert isinstance(result, ArticleOutput)
        assert result.title == "The Future of AI in Healthcare"
        assert len(result.main_sections) == 3  # Updated to 3 sections
        assert result.focus_keyword == "AI healthcare"

    @pytest.mark.asyncio
    async def test_run_writer_agent_with_sources_validation(
        self, mock_config, sample_research_findings
    ):
        """Test writer agent validates sources are used."""
        mock_agent = Mock()
        mock_result = Mock()

        # Create output without sources
        mock_result.data = ArticleOutput(
            title="Test Article",
            meta_description="Test meta description providing comprehensive information about the topic with appropriate length for SEO optimization and search results.",
            focus_keyword="test",
            introduction="Test introduction that provides comprehensive context for the article. This introduction sets up the reader for what they will learn and engages them with relevant information about the topic at hand.",
            main_sections=create_valid_sections(3),
            conclusion="Test conclusion that summarizes the key points and provides actionable takeaways. This conclusion reinforces the main message and encourages readers to apply what they've learned.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.01,
            sources_used=[],  # No sources - should fail validation
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        # Should raise ValueError for missing sources
        with pytest.raises(ValueError) as exc_info:
            await run_writer_agent(mock_agent, "test", sample_research_findings)

        assert "Article must cite research sources" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_writer_agent_empty_research(self, mock_config):
        """Test writer agent with empty research findings."""
        mock_agent = Mock()
        mock_result = Mock()

        empty_findings = ResearchFindings(
            keyword="topic",
            research_summary="No research available.",
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=[],
            total_sources_analyzed=0,
            search_query_used="topic",
        )

        mock_result.data = ArticleOutput(
            title="Understanding the Topic",
            meta_description="An overview of the topic based on general knowledge, providing comprehensive insights and practical applications for readers.",
            focus_keyword="topic",
            introduction="This article explores the topic in detail, providing readers with a comprehensive understanding of the subject matter. We'll examine various aspects and implications, ensuring you gain valuable insights that can be applied in practical contexts.",
            main_sections=[
                ArticleSection(
                    heading="Overview",
                    content="General information about the topic provides a foundation for understanding its broader implications. This section covers the essential concepts, historical context, and current relevance in today's world.",
                ),
                ArticleSection(
                    heading="Key Concepts",
                    content="Understanding the core concepts is crucial for mastering this topic. We explore fundamental principles, theoretical frameworks, and practical applications that form the basis of this field of study.",
                ),
                ArticleSection(
                    heading="Applications",
                    content="Real-world applications demonstrate the practical value of this topic. From industry use cases to everyday scenarios, we examine how these concepts translate into tangible benefits and solutions.",
                ),
            ],
            conclusion="Further research is needed to fully explore all aspects of this topic. However, the foundations covered in this article provide a solid starting point for deeper investigation and practical application.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.01,
            sources_used=[
                "https://example.com/general-source"
            ],  # At least one source required
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_writer_agent(mock_agent, "topic", empty_findings)

        assert isinstance(result, ArticleOutput)
        assert len(result.sources_used) == 1  # We added one general source

    @pytest.mark.asyncio
    async def test_run_writer_agent_long_keyword(
        self, mock_config, sample_research_findings
    ):
        """Test writer agent with long keyword phrase."""
        mock_agent = Mock()
        mock_result = Mock()

        long_keyword = "artificial intelligence machine learning healthcare diagnostics"

        mock_result.data = ArticleOutput(
            title="AI and ML in Healthcare Diagnostics",
            meta_description="Exploring AI and ML applications in healthcare diagnostics with improved accuracy, predictive analytics, and personalized patient care.",
            focus_keyword=long_keyword,
            introduction="This comprehensive guide explores the revolutionary impact of artificial intelligence and machine learning in healthcare diagnostics. From improving accuracy to reducing costs, these technologies are transforming how medical professionals diagnose and treat patients worldwide.",
            main_sections=create_valid_sections(3),
            conclusion="The future is bright for AI and ML in healthcare diagnostics. As these technologies continue to evolve, we can expect even more accurate diagnoses, faster treatment decisions, and improved patient outcomes across all medical specialties.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.02,
            sources_used=["https://example.edu/ai-health"],
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_writer_agent(
            mock_agent, long_keyword, sample_research_findings
        )

        assert isinstance(result, ArticleOutput)
        assert long_keyword in result.focus_keyword

    @pytest.mark.asyncio
    async def test_run_writer_agent_unicode_keyword(
        self, mock_config, sample_research_findings
    ):
        """Test writer agent with unicode characters in keyword."""
        mock_agent = Mock()
        mock_result = Mock()

        unicode_keyword = "café société résumé"

        mock_result.data = ArticleOutput(
            title="Understanding Café Société",
            meta_description="A comprehensive guide to café société culture, exploring its rich history, social dynamics, and cultural significance in Europe.",
            focus_keyword=unicode_keyword,
            introduction="Exploring the concept of café société takes us on a journey through European cultural history. From the intellectual salons of Paris to the vibrant coffee houses of Vienna, café society has shaped literature, art, and political discourse for centuries.",
            main_sections=create_valid_sections(3),
            conclusion="In conclusion, café société remains a vital part of European culture, continuing to provide spaces for intellectual exchange, artistic expression, and social connection in our modern digital age.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.015,
            sources_used=["https://example.edu/cafe-culture"],
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_writer_agent(
            mock_agent, unicode_keyword, sample_research_findings
        )

        assert isinstance(result, ArticleOutput)
        assert unicode_keyword == result.focus_keyword

    @pytest.mark.asyncio
    async def test_run_writer_agent_max_retries_exceeded(
        self, mock_config, sample_research_findings
    ):
        """Test writer agent fails after max retries."""
        mock_agent = Mock()
        mock_agent.run = AsyncMock(side_effect=Exception("Persistent API Error"))

        with pytest.raises(Exception) as exc_info:
            await run_writer_agent(mock_agent, "test", sample_research_findings)

        assert "Persistent API Error" in str(exc_info.value)
        # The run_writer_agent doesn't have built-in retry logic, so it should only be called once
        assert mock_agent.run.call_count == 1

    @pytest.mark.asyncio
    async def test_writer_agent_with_extensive_research(self, mock_config):
        """Test writer agent with extensive research findings."""
        # Create extensive research with many sources
        sources = [
            AcademicSource(
                title=f"Study {i}: AI Applications",
                url=f"https://journal{i}.edu/paper",
                authors=[f"Author{i}, A."],
                publication_date=f"2024-0{min(i, 9)}-01",
                excerpt=f"Finding {i} about AI...",
                domain=".edu",
                credibility_score=0.9,
            )
            for i in range(1, 11)
        ]

        extensive_findings = ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive synthesis of all findings...",
            academic_sources=sources,
            key_statistics=["stat1: 50%", "stat2: 75%", "stat3: 90%"],
            research_gaps=["Gap 1", "Gap 2", "Gap 3"],
            main_findings=["AI", "ML", "Healthcare", "Ethics", "Future"],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence",
        )

        mock_agent = Mock()
        mock_result = Mock()

        # Expected output with multiple sections
        sections = [
            ArticleSection(
                heading=f"Section {i}: AI Applications",
                content=f"This section discusses important aspects of artificial intelligence. "
                f"Section {i} covers various applications and implementations of AI technology. "
                f"The content provides detailed insights into how AI is transforming different industries.",
            )
            for i in range(1, 6)
        ]

        mock_result.data = ArticleOutput(
            title="Comprehensive Guide to AI",
            meta_description="Everything you need to know about AI, from basic concepts to advanced applications. Learn how AI is revolutionizing industries.",
            focus_keyword="artificial intelligence",
            introduction="This comprehensive guide covers all aspects of artificial intelligence, from fundamental concepts to cutting-edge applications. Whether you're a student, professional, or enthusiast, this guide will provide valuable insights into the world of AI and its transformative impact.",
            main_sections=sections,
            conclusion="AI continues to evolve at a rapid pace, bringing new opportunities and challenges. As we've explored in this guide, artificial intelligence is not just a technology trend but a fundamental shift in how we solve problems and create value.",
            word_count=2000,
            reading_time_minutes=8,
            keyword_density=0.018,
            sources_used=[s.url for s in sources[:5]],  # Uses top 5 sources
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_writer_agent(
            mock_agent, "artificial intelligence", extensive_findings
        )

        assert isinstance(result, ArticleOutput)
        assert len(result.main_sections) == 5
        assert len(result.sources_used) == 5
        assert result.word_count == 2000

    @pytest.mark.asyncio
    async def test_writer_agent_context_handling(
        self, mock_config, sample_research_findings
    ):
        """Test writer agent properly uses context from research."""
        mock_agent = Mock()

        # Verify the agent receives proper context
        async def mock_run(keyword, deps):
            # Check that research findings are passed as dependency
            assert "research" in deps
            assert deps["research"] == sample_research_findings

            mock_result = Mock()
            mock_result.data = ArticleOutput(
                title="Context-Aware Article",
                meta_description="Article using research context to provide comprehensive insights and practical applications for readers seeking in-depth knowledge.",
                focus_keyword=keyword,
                introduction="Based on research findings, this article provides a comprehensive analysis of the topic. We explore various aspects and implications, drawing from academic sources to ensure accuracy and depth of coverage.",
                main_sections=create_valid_sections(3),
                conclusion="As research shows, this topic has significant implications for various fields. The insights presented here provide a foundation for further exploration and practical application.",
                word_count=1200,
                reading_time_minutes=5,
                keyword_density=0.012,
                sources_used=[
                    source.url for source in sample_research_findings.academic_sources
                ],
            )
            return mock_result

        mock_agent.run = mock_run

        result = await run_writer_agent(
            mock_agent, "test keyword", sample_research_findings
        )

        assert isinstance(result, ArticleOutput)
        assert len(result.sources_used) == len(
            sample_research_findings.academic_sources
        )
