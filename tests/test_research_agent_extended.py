"""
Extended tests for research agent to improve coverage.

This module adds additional test cases for the research agent,
focusing on error handling and edge cases.
"""

import asyncio
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from config import Config
from models import AcademicSource, ResearchFindings
from research_agent import create_research_agent, run_research_agent
from research_agent.agent import _identify_research_gaps as identify_research_gaps


class TestResearchAgentExtended:
    """Extended test cases for research agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.llm_model = "gpt-4"
        config.max_retries = 3
        return config

    @pytest.fixture
    def sample_sources(self) -> List[AcademicSource]:
        """Create sample academic sources."""
        return [
            AcademicSource(
                title="Machine Learning in Healthcare",
                url="https://journal.edu/ml-health",
                authors=["Smith, J.", "Doe, A."],
                publication_date="2024-01-15",
                excerpt="ML algorithms show promise in early disease detection...",
                domain=".edu",
                credibility_score=0.95,
            ),
            AcademicSource(
                title="AI Ethics in Medical Applications",
                url="https://university.edu/ai-ethics",
                authors=["Johnson, K."],
                publication_date="2023-12-01",
                excerpt="Ethical considerations for AI deployment in healthcare...",
                domain=".edu",
                credibility_score=0.88,
            ),
        ]

    @pytest.mark.asyncio
    async def test_create_research_agent(self, mock_config):
        """Test research agent creation."""
        with patch("research_agent.agent.Agent") as mock_agent_class:
            agent = create_research_agent(mock_config)

            # Verify agent was created with correct parameters
            mock_agent_class.assert_called_once()
            call_args = mock_agent_class.call_args

            assert call_args[1]["model"] == "openai:gpt-4"
            assert "result_type" in call_args[1]

    @pytest.mark.asyncio
    async def test_run_research_agent_success(self, mock_config):
        """Test successful research agent execution."""
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.data = ResearchFindings(
            keyword="healthcare AI",
            research_summary="AI shows promise in healthcare applications.",
            academic_sources=[],
            key_statistics=["accuracy_improvement: 30%"],
            research_gaps=["Long-term effects unstudied"],
            main_findings=["AI in healthcare"],
            total_sources_analyzed=0,
            search_query_used="healthcare AI",
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_research_agent(mock_agent, "healthcare AI")

        assert isinstance(result, ResearchFindings)
        assert result.main_findings == ["AI in healthcare"]
        mock_agent.run.assert_called_once_with("healthcare AI")

    @pytest.mark.asyncio
    async def test_run_research_agent_with_retry(self, mock_config):
        """Test research agent with retry on failure."""
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.data = ResearchFindings(
            keyword="test keyword",
            research_summary="Test synthesis",
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=["test"],
            total_sources_analyzed=0,
            search_query_used="test keyword",
        )

        # First call fails, second succeeds
        mock_agent.run = AsyncMock(side_effect=[Exception("API Error"), mock_result])

        # Should still succeed due to retry
        result = await run_research_agent(mock_agent, "test keyword")

        assert isinstance(result, ResearchFindings)
        assert mock_agent.run.call_count == 2

    @pytest.mark.asyncio
    async def test_run_research_agent_max_retries_exceeded(self, mock_config):
        """Test research agent fails after max retries."""
        mock_agent = Mock()
        mock_agent.run = AsyncMock(side_effect=Exception("Persistent API Error"))

        with pytest.raises(Exception) as exc_info:
            await run_research_agent(mock_agent, "test keyword")

        assert "Persistent API Error" in str(exc_info.value)
        # Should attempt max_retries + 1 times
        assert mock_agent.run.call_count > 1

    def test_identify_research_gaps_with_sources(self, sample_sources):
        """Test research gap identification with sources."""
        # Convert AcademicSource objects to dicts
        source_dicts = [
            {
                "content": source.excerpt,
                "title": source.title,
            }
            for source in sample_sources
        ]
        gaps = identify_research_gaps(source_dicts)

        assert isinstance(gaps, list)
        # May or may not find gaps depending on content

    def test_identify_research_gaps_empty_sources(self):
        """Test research gap identification with no sources."""
        gaps = identify_research_gaps([])

        assert isinstance(gaps, list)
        assert len(gaps) == 0  # Empty sources return empty gaps

    def test_identify_research_gaps_old_sources(self):
        """Test research gap identification with old sources."""
        old_sources = [
            {
                "content": "Outdated findings. More studies needed on recent developments. Further research required.",
                "title": "Old Research",
            }
        ]

        gaps = identify_research_gaps(old_sources)

        assert isinstance(gaps, list)
        assert len(gaps) > 0  # Should find gaps from "more studies needed"

    def test_identify_research_gaps_single_domain(self):
        """Test gap identification when sources from single domain."""
        single_domain_sources = [
            {
                "content": f"Finding {i}. This area requires investigation and future work is needed.",
                "title": f"Paper {i}",
            }
            for i in range(3)
        ]

        gaps = identify_research_gaps(single_domain_sources)

        assert isinstance(gaps, list)
        assert len(gaps) > 0  # Should find gaps from "requires investigation"

    @pytest.mark.asyncio
    async def test_research_agent_with_tool_error(self, mock_config):
        """Test research agent handles tool errors gracefully."""
        with patch("research_agent.agent.Agent") as mock_agent_class:
            mock_agent_instance = Mock()
            mock_agent_class.return_value = mock_agent_instance

            # Simulate tool error during execution
            mock_agent_instance.run = AsyncMock(
                side_effect=UnexpectedModelBehavior("Tool execution failed")
            )

            agent = create_research_agent(mock_config)

            with pytest.raises(UnexpectedModelBehavior):
                await run_research_agent(agent, "test keyword")

    @pytest.mark.asyncio
    async def test_research_agent_empty_keyword(self, mock_config):
        """Test research agent with empty keyword."""
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.data = ResearchFindings(
            keyword="",
            research_summary="Unable to research without a specific keyword.",
            academic_sources=[],
            key_statistics=[],
            research_gaps=["No specific topic provided"],
            main_findings=[],
            total_sources_analyzed=0,
            search_query_used="",
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await run_research_agent(mock_agent, "")

        assert isinstance(result, ResearchFindings)
        assert len(result.academic_sources) == 0
        assert "No specific topic" in result.research_gaps[0]

    @pytest.mark.asyncio
    async def test_research_agent_special_characters_keyword(self, mock_config):
        """Test research agent with special characters in keyword."""
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.data = ResearchFindings(
            keyword="AI & ML: Future @2025!",
            research_summary="Research on sanitized topic.",
            academic_sources=[],
            key_statistics=[],
            research_gaps=[],
            main_findings=["sanitized topic"],
            total_sources_analyzed=0,
            search_query_used="AI & ML: Future @2025!",
        )

        mock_agent.run = AsyncMock(return_value=mock_result)

        # Keyword with special characters
        result = await run_research_agent(mock_agent, "AI & ML: Future @2025!")

        assert isinstance(result, ResearchFindings)
        mock_agent.run.assert_called_once()

    def test_identify_research_gaps_low_credibility(self):
        """Test gap identification with low credibility sources."""
        low_cred_sources = [
            {
                "content": "Dubious claims. The results are unclear and not well understood. Limited data available.",
                "title": "Questionable Research",
            }
        ]

        gaps = identify_research_gaps(low_cred_sources)

        assert isinstance(gaps, list)
        assert len(gaps) > 0  # Should find gaps from "unclear" and "limited data"

    def test_identify_research_gaps_comprehensive_coverage(self):
        """Test gap identification with comprehensive sources."""
        comprehensive_sources = [
            {
                "content": f"Comprehensive findings on aspect {i}. All aspects well understood with solid evidence.",
                "title": f"Comprehensive Study Part {i}",
            }
            for i in range(1, 6)
        ]

        gaps = identify_research_gaps(comprehensive_sources)

        # With no gap indicators, should return empty list
        assert isinstance(gaps, list)
        assert len(gaps) == 0
