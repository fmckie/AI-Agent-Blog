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
            assert "result_type" in call_args[1]

    @pytest.mark.asyncio
    async def test_run_writer_agent_success(self, mock_config, sample_research_findings):
        """Test successful writer agent execution."""
        mock_agent = Mock()
        mock_result = Mock()
        
        # Create expected article output
        sections = [
            ArticleSection(
                heading="Introduction to AI in Healthcare",
                content="AI is revolutionizing healthcare...",
            ),
            ArticleSection(
                heading="Current Applications",
                content="Modern AI applications include...",
            ),
        ]
        
        mock_result.data = ArticleOutput(
            title="The Future of AI in Healthcare",
            meta_description="Discover how AI is transforming healthcare with improved diagnostics.",
            focus_keyword="AI healthcare",
            introduction="Artificial intelligence is reshaping healthcare...",
            main_sections=sections,
            conclusion="AI will continue to transform healthcare...",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=["https://journal.edu/ai-health"],
        )
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        result = await run_writer_agent(mock_agent, "AI healthcare", sample_research_findings)
        
        assert isinstance(result, ArticleOutput)
        assert result.title == "The Future of AI in Healthcare"
        assert len(result.main_sections) == 2
        assert result.focus_keyword == "AI healthcare"

    @pytest.mark.asyncio
    async def test_run_writer_agent_with_retry(self, mock_config, sample_research_findings):
        """Test writer agent with retry on failure."""
        mock_agent = Mock()
        mock_result = Mock()
        
        mock_result.data = ArticleOutput(
            title="Test Article",
            meta_description="Test description",
            focus_keyword="test",
            introduction="Test intro",
            main_sections=[],
            conclusion="Test conclusion",
            word_count=500,
            reading_time_minutes=2,
            keyword_density=0.01,
            sources_used=[],
        )
        
        # First call fails, second succeeds
        mock_agent.run = AsyncMock(side_effect=[Exception("API Error"), mock_result])
        
        result = await run_writer_agent(mock_agent, "test", sample_research_findings)
        
        assert isinstance(result, ArticleOutput)
        assert mock_agent.run.call_count == 2

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
            meta_description="An overview of the topic based on general knowledge.",
            focus_keyword="topic",
            introduction="This article explores the topic...",
            main_sections=[
                ArticleSection(
                    heading="Overview",
                    content="General information about the topic...",
                )
            ],
            conclusion="Further research is needed...",
            word_count=500,
            reading_time_minutes=2,
            keyword_density=0.01,
            sources_used=[],
        )
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        result = await run_writer_agent(mock_agent, "topic", empty_findings)
        
        assert isinstance(result, ArticleOutput)
        assert len(result.sources_used) == 0

    @pytest.mark.asyncio
    async def test_run_writer_agent_long_keyword(self, mock_config, sample_research_findings):
        """Test writer agent with long keyword phrase."""
        mock_agent = Mock()
        mock_result = Mock()
        
        long_keyword = "artificial intelligence machine learning healthcare diagnostics"
        
        mock_result.data = ArticleOutput(
            title="AI and ML in Healthcare Diagnostics",
            meta_description="Exploring AI and ML applications in healthcare.",
            focus_keyword=long_keyword,
            introduction="This comprehensive guide...",
            main_sections=[],
            conclusion="The future is bright...",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.02,
            sources_used=[],
        )
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        result = await run_writer_agent(mock_agent, long_keyword, sample_research_findings)
        
        assert isinstance(result, ArticleOutput)
        assert long_keyword in result.focus_keyword

    @pytest.mark.asyncio
    async def test_run_writer_agent_unicode_keyword(self, mock_config, sample_research_findings):
        """Test writer agent with unicode characters in keyword."""
        mock_agent = Mock()
        mock_result = Mock()
        
        unicode_keyword = "café société résumé"
        
        mock_result.data = ArticleOutput(
            title="Understanding Café Société",
            meta_description="A guide to café société culture.",
            focus_keyword=unicode_keyword,
            introduction="Exploring the concept...",
            main_sections=[],
            conclusion="In conclusion...",
            word_count=800,
            reading_time_minutes=3,
            keyword_density=0.015,
            sources_used=[],
        )
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        result = await run_writer_agent(mock_agent, unicode_keyword, sample_research_findings)
        
        assert isinstance(result, ArticleOutput)
        assert unicode_keyword == result.focus_keyword

    @pytest.mark.asyncio
    async def test_run_writer_agent_max_retries_exceeded(self, mock_config, sample_research_findings):
        """Test writer agent fails after max retries."""
        mock_agent = Mock()
        mock_agent.run = AsyncMock(side_effect=Exception("Persistent API Error"))
        
        with pytest.raises(Exception) as exc_info:
            await run_writer_agent(mock_agent, "test", sample_research_findings)
        
        assert "Persistent API Error" in str(exc_info.value)
        assert mock_agent.run.call_count > 1

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
                heading=f"Section {i}",
                content=f"Content for section {i}...",
            )
            for i in range(1, 6)
        ]
        
        mock_result.data = ArticleOutput(
            title="Comprehensive Guide to AI",
            meta_description="Everything you need to know about AI.",
            focus_keyword="artificial intelligence",
            introduction="This comprehensive guide covers all aspects...",
            main_sections=sections,
            conclusion="AI continues to evolve...",
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
    async def test_writer_agent_context_handling(self, mock_config, sample_research_findings):
        """Test writer agent properly uses context from research."""
        mock_agent = Mock()
        
        # Verify the agent receives proper context
        async def mock_run(keyword, deps):
            # Check that research findings are passed as dependency
            assert "research_findings" in deps
            assert deps["research_findings"] == sample_research_findings
            
            mock_result = Mock()
            mock_result.data = ArticleOutput(
                title="Context-Aware Article",
                meta_description="Article using research context.",
                focus_keyword=keyword,
                introduction="Based on research findings...",
                main_sections=[],
                conclusion="As research shows...",
                word_count=600,
                reading_time_minutes=3,
                keyword_density=0.012,
                sources_used=[source.url for source in sample_research_findings.academic_sources],
            )
            return mock_result
        
        mock_agent.run = mock_run
        
        result = await run_writer_agent(
            mock_agent, "test keyword", sample_research_findings
        )
        
        assert isinstance(result, ArticleOutput)
        assert len(result.sources_used) == len(sample_research_findings.academic_sources)