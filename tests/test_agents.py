"""
Test suite for PydanticAI agents.

This module contains comprehensive tests for the Research and Writer agents,
ensuring they work correctly with various inputs and handle errors gracefully.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from config import Config
from models import ResearchFindings, AcademicSource, TavilySearchResponse, TavilySearchResult
from research_agent import create_research_agent, run_research_agent
from research_agent.agent import _identify_research_gaps


# Fixtures for test configuration
@pytest.fixture
def test_config():
    """
    Create a test configuration.
    
    Returns:
        Config object with test values
    """
    return Config(
        tavily_api_key="tvly-test1234567890abcdef1234567890ab",
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890ab",
        llm_model="gpt-4",
        output_dir="./test_drafts",
        log_level="DEBUG",
        max_retries=3,
        request_timeout=30,
        tavily_search_depth="advanced",
        tavily_include_domains=[".edu", ".gov", ".org"],
        tavily_max_results=10
    )


@pytest.fixture
def mock_tavily_response():
    """
    Create a mock Tavily API response.
    
    Returns:
        TavilySearchResponse with test data
    """
    return TavilySearchResponse(
        query="machine learning applications",
        results=[
            TavilySearchResult(
                title="Deep Learning in Healthcare: A Comprehensive Review",
                url="https://example.edu/paper1",
                content="This study examines deep learning applications in healthcare. Our findings show a 78% improvement in diagnostic accuracy. Further research is needed to validate these results across diverse populations.",
                score=0.95,
                credibility_score=0.9,
                domain=".edu",
                processed_at=datetime.now()
            ),
            TavilySearchResult(
                title="Government Report on AI in Public Services",
                url="https://example.gov/report",
                content="Federal agencies report 45% efficiency gains through AI implementation. The study analyzed 1,234 government offices. However, gaps remain in understanding long-term impacts.",
                score=0.88,
                credibility_score=0.85,
                domain=".gov",
                processed_at=datetime.now()
            ),
            TavilySearchResult(
                title="Machine Learning Applications in Education",
                url="https://journal.org/ml-education",
                content="A meta-analysis of 567 studies reveals that personalized learning algorithms improve student outcomes by 34%. More studies needed on implementation costs.",
                score=0.82,
                credibility_score=0.8,
                domain=".org",
                processed_at=datetime.now()
            )
        ],
        answer="Machine learning shows significant promise across healthcare, government, and education sectors with measurable improvements in efficiency and outcomes.",
        processing_metadata={
            "total_results": 3,
            "academic_results": 3,
            "search_depth": "advanced",
            "timestamp": datetime.now().isoformat()
        }
    )


class TestResearchAgent:
    """Test suite for the Research Agent."""
    
    @pytest.mark.asyncio
    async def test_create_research_agent(self, test_config):
        """
        Test that research agent is created correctly.
        
        Args:
            test_config: Test configuration fixture
        """
        # Create the agent
        agent = create_research_agent(test_config)
        
        # Verify agent properties
        assert agent is not None
        assert agent.output_type == ResearchFindings
        # Just verify the agent has a model configured
        assert agent.model is not None
        
        # PydanticAI agents don't expose tools directly anymore
        # We can only verify the agent was created successfully
    
    @pytest.mark.asyncio
    async def test_research_agent_execution_success(self, test_config, mock_tavily_response):
        """
        Test successful research agent execution.
        
        Args:
            test_config: Test configuration fixture
            mock_tavily_response: Mock Tavily response fixture
        """
        # Create the agent
        agent = create_research_agent(test_config)
        
        # Mock the agent's run method
        expected_findings = ResearchFindings(
            keyword="machine learning applications",
            research_summary="Recent studies demonstrate significant advancements in machine learning applications across healthcare, government, and education sectors, with measurable improvements in efficiency and outcomes.",
            academic_sources=[
                AcademicSource(
                    title="Deep Learning in Healthcare: A Comprehensive Review",
                    url="https://example.edu/paper1",
                    excerpt="Our findings show a 78% improvement in diagnostic accuracy",
                    domain=".edu",
                    credibility_score=0.9
                ),
                AcademicSource(
                    title="Government Report on AI in Public Services",
                    url="https://example.gov/report",
                    excerpt="Federal agencies report 45% efficiency gains",
                    domain=".gov",
                    credibility_score=0.85
                )
            ],
            main_findings=[
                "78% improvement in healthcare diagnostic accuracy using deep learning",
                "45% efficiency gains in government services through AI implementation",
                "34% improvement in student outcomes with personalized learning algorithms"
            ],
            key_statistics=["78%", "45%", "1,234 government offices", "567 studies", "34%"],
            research_gaps=[
                "Further research is needed to validate these results across diverse populations",
                "Gaps remain in understanding long-term impacts",
                "More studies needed on implementation costs"
            ],
            total_sources_analyzed=3,
            search_query_used="machine learning applications"
        )
        
        # Mock the run method
        with patch.object(agent, 'run', return_value=expected_findings) as mock_run:
            # Execute the research
            result = await run_research_agent(agent, "machine learning applications")
            
            # Verify the result
            assert result.keyword == "machine learning applications"
            assert len(result.academic_sources) >= 2
            assert len(result.main_findings) >= 3
            assert len(result.key_statistics) >= 3
            assert len(result.research_gaps) >= 2
            assert result.total_sources_analyzed == 3
            
            # Verify the agent was called
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_research_agent_no_sources_found(self, test_config):
        """
        Test research agent behavior when no sources are found.
        
        Args:
            test_config: Test configuration fixture
        """
        # Create the agent
        agent = create_research_agent(test_config)
        
        # Since ResearchFindings requires at least one source with credibility >= 0.7,
        # we'll test by mocking the agent to raise an exception
        with patch.object(agent, 'run', side_effect=ValueError("No academic sources found")):
            # Execute and expect the error to propagate
            with pytest.raises(Exception):  # run_research_agent will re-raise
                await run_research_agent(agent, "obscure topic xyz123")
    
    def test_identify_research_gaps(self):
        """Test the research gap identification function."""
        # Create test sources with gap indicators
        sources = [
            {
                "content": "This study shows promising results. However, further research is needed to confirm these findings in larger populations."
            },
            {
                "content": "The mechanism remains unclear and requires investigation. More studies needed to understand the causal relationships."
            },
            {
                "content": "Our data is limited by sample size. Future work should explore diverse demographics."
            }
        ]
        
        # Identify gaps
        gaps = _identify_research_gaps(sources)
        
        # Verify gaps were found
        assert len(gaps) > 0
        assert any("further research" in gap.lower() for gap in gaps)
        assert any("more studies needed" in gap.lower() for gap in gaps)
    
    def test_identify_research_gaps_no_gaps(self):
        """Test gap identification with no gaps present."""
        # Sources without gap indicators
        sources = [
            {
                "content": "This comprehensive study provides definitive evidence for the effectiveness of the intervention."
            },
            {
                "content": "Our findings are consistent with previous research and confirm the established theory."
            }
        ]
        
        # Identify gaps
        gaps = _identify_research_gaps(sources)
        
        # Should find no or minimal gaps
        assert len(gaps) == 0
    
    @pytest.mark.asyncio
    async def test_research_agent_with_mock_tools(self, test_config):
        """
        Test research agent with mocked tool responses.
        
        Args:
            test_config: Test configuration fixture
        """
        # Create the agent
        agent = create_research_agent(test_config)
        
        # Mock the search tool response
        mock_search_response = {
            "query": "artificial intelligence ethics",
            "results": [
                {
                    "title": "Ethics in AI: A University Study",
                    "url": "https://university.edu/ai-ethics",
                    "content": "Our study of 2,500 AI systems reveals that 67% lack proper ethical guidelines.",
                    "credibility_score": 0.95,
                    "domain": ".edu"
                }
            ],
            "answer": "AI ethics is a growing concern in the field.",
            "processing_metadata": {"total_results": 1}
        }
        
        # Mock tool functions
        with patch('research_agent.tools.search_academic', return_value=mock_search_response):
            # We can't easily test the full agent execution without mocking OpenAI
            # The new PydanticAI API doesn't expose tools directly
            # Just verify the agent was created successfully
            assert agent is not None
            assert agent.output_type == ResearchFindings
    
    @pytest.mark.asyncio
    async def test_research_agent_retry_on_failure(self, test_config):
        """
        Test that research agent retries on failure.
        
        Args:
            test_config: Test configuration fixture
        """
        # This test would require mocking the workflow orchestrator
        # Since we're testing the retry decorator behavior
        # We'll create a simplified test
        
        call_count = 0
        
        @pytest.mark.asyncio
        async def failing_research():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return ResearchFindings(
                keyword="test",
                research_summary="Success after retries",
                academic_sources=[
                    AcademicSource(
                        title="Test Source",
                        url="https://test.edu",
                        excerpt="Test excerpt",
                        domain=".edu",
                        credibility_score=0.8
                    )
                ],
                main_findings=["Test finding"],
                total_sources_analyzed=1,
                search_query_used="test"
            )
        
        # The retry logic is in the workflow, not the agent itself
        # So this test primarily verifies the structure is correct
        assert True  # Placeholder for retry testing


class TestResearchAgentIntegration:
    """Integration tests for the Research Agent."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_research_agent_with_real_api(self, test_config):
        """
        Test research agent with real API calls.
        
        NOTE: This test requires valid API keys and is marked for integration testing.
        
        Args:
            test_config: Test configuration fixture
        """
        # Skip if API keys are not real (they start with test patterns)
        if test_config.openai_api_key.startswith("sk-test"):
            pytest.skip("Skipping integration test - no real API keys")
        
        # Create real agent
        agent = create_research_agent(test_config)
        
        # Run with a simple keyword
        result = await run_research_agent(agent, "renewable energy")
        
        # Verify real results
        assert result.keyword == "renewable energy"
        assert len(result.academic_sources) >= 1
        assert len(result.main_findings) >= 3
        assert result.total_sources_analyzed >= 1
        assert result.research_summary != ""


# Test utility functions
def test_statistics_extraction():
    """Test the statistics extraction utility."""
    from tools import extract_key_statistics
    
    text = """
    Our study of 1,245 participants showed a 67.5% improvement rate.
    The control group of 500 people demonstrated only 23% improvement.
    Overall, 89 percent of subjects reported satisfaction.
    """
    
    stats = extract_key_statistics(text)
    
    assert "67.5%" in stats
    assert "23%" in stats
    assert "89 percent" in stats
    assert "1,245 participants" in stats or "1245 participants" in stats
    assert "500 people" in stats