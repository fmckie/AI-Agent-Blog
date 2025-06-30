"""
Comprehensive tests for Research Agent tools and Tavily API integration.

This test file covers the tool functions in research_agent/tools.py and
the Tavily API client in tools.py, including API mocking and error handling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp

# Import testing utilities
import pytest
from pydantic_ai import RunContext

from config import Config
from models import TavilySearchResponse, TavilySearchResult

# Import tools and utilities to test
from research_agent.tools import search_academic
from tools import (
    TavilyAPIError,
    TavilyAuthError,
    TavilyClient,
    TavilyRateLimitError,
    TavilyTimeoutError,
    calculate_reading_time,
    clean_text_for_seo,
    extract_key_statistics,
    generate_slug,
    search_academic_sources,
)


class TestResearchAgentTools:
    """Test cases for research agent tool functions."""

    @pytest.mark.asyncio
    async def test_search_academic_tool_success(self):
        """Test successful academic search through agent tool."""
        # Create mock config
        config = Mock(spec=Config)
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"

        # Create mock context
        ctx = Mock(spec=RunContext)

        # Mock the search_academic_sources function
        mock_response = TavilySearchResponse(
            query="machine learning",
            results=[
                TavilySearchResult(
                    title="ML Research Paper",
                    url="https://journal.edu/paper",
                    content="Research findings on ML",
                    credibility_score=0.85,
                    domain=".edu",
                )
            ],
            answer="Summary of ML research",
        )

        with patch(
            "research_agent.tools.search_academic_sources", return_value=mock_response
        ):
            # Call the tool function
            result = await search_academic(ctx, "machine learning", config)

            # Verify result structure
            assert isinstance(result, dict)
            assert result["query"] == "machine learning"
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "ML Research Paper"
            assert result["answer"] == "Summary of ML research"

    @pytest.mark.asyncio
    async def test_search_academic_tool_empty_results(self):
        """Test academic search with no results."""
        config = Mock(spec=Config)
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        ctx = Mock(spec=RunContext)

        # Mock empty response
        mock_response = TavilySearchResponse(
            query="obscure topic", results=[], answer=None
        )

        with patch(
            "research_agent.tools.search_academic_sources", return_value=mock_response
        ):
            result = await search_academic(ctx, "obscure topic", config)

            assert result["query"] == "obscure topic"
            assert len(result["results"]) == 0
            assert result["answer"] is None

    @pytest.mark.asyncio
    async def test_search_academic_tool_error_handling(self):
        """Test error handling in academic search tool."""
        config = Mock(spec=Config)
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        ctx = Mock(spec=RunContext)

        # Mock API error
        with patch(
            "research_agent.tools.search_academic_sources",
            side_effect=TavilyAPIError("API Error"),
        ):
            with pytest.raises(TavilyAPIError):
                await search_academic(ctx, "test query", config)


class TestTavilyClient:
    """Test cases for Tavily API client."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.tavily_search_depth = "basic"
        config.tavily_include_domains = [".edu", ".gov"]
        config.tavily_max_results = 10
        config.request_timeout = 30
        config.max_retries = 3
        return config

    @pytest.fixture
    def tavily_client(self, mock_config):
        """Create Tavily client instance."""
        return TavilyClient(mock_config)

    @pytest.mark.asyncio
    async def test_client_initialization(self, tavily_client, mock_config):
        """Test Tavily client initialization."""
        assert tavily_client.api_key == "sk-tavily1234567890abcdef1234567890"
        assert tavily_client.search_depth == "basic"
        assert tavily_client.include_domains == [".edu", ".gov"]
        assert tavily_client.max_results == 10
        assert tavily_client.timeout == 30
        assert tavily_client.max_retries == 3

    @pytest.mark.asyncio
    async def test_search_success(self, tavily_client):
        """Test successful API search."""
        # Mock API response
        mock_response_data = {
            "results": [
                {
                    "title": "Academic Paper",
                    "url": "https://university.edu/paper",
                    "content": "This study examines...",
                    "score": 0.9,
                }
            ],
            "answer": "Summary of findings",
        }

        # Create mock session
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_session.post.return_value.__aenter__.return_value = mock_response

        tavily_client.session = mock_session

        # Perform search
        result = await tavily_client.search("test query")

        # Verify results
        assert isinstance(result, TavilySearchResponse)
        assert result.query == "test query"
        assert len(result.results) == 1
        assert result.results[0].title == "Academic Paper"
        assert result.results[0].credibility_score > 0.5  # .edu domain

    @pytest.mark.asyncio
    async def test_search_auth_error(self, tavily_client):
        """Test authentication error handling."""
        # Mock 401 response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=401, message="Unauthorized"
        )
        mock_session.post.return_value.__aenter__.return_value = mock_response

        tavily_client.session = mock_session

        # Should raise TavilyAuthError
        with pytest.raises(TavilyAuthError, match="Invalid Tavily API key"):
            await tavily_client.search("test query")

    @pytest.mark.asyncio
    async def test_search_rate_limit_error(self, tavily_client):
        """Test rate limit error handling."""
        # Mock 429 response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=429, message="Too Many Requests"
        )
        mock_session.post.return_value.__aenter__.return_value = mock_response

        tavily_client.session = mock_session

        # Should raise TavilyRateLimitError
        with pytest.raises(TavilyRateLimitError, match="rate limit exceeded"):
            await tavily_client.search("test query")

    @pytest.mark.asyncio
    async def test_search_timeout_error(self, tavily_client):
        """Test timeout error handling."""
        # Mock timeout
        mock_session = AsyncMock()
        mock_session.post.side_effect = asyncio.TimeoutError()

        tavily_client.session = mock_session

        # Should raise TavilyTimeoutError
        with pytest.raises(TavilyTimeoutError, match="Request timed out"):
            await tavily_client.search("test query")

    @pytest.mark.asyncio
    async def test_rate_limiting(self, tavily_client):
        """Test rate limiting mechanism."""
        # Set up rate limit to 2 requests per second for testing
        tavily_client.rate_limit_calls = 2
        tavily_client.rate_limit_window = 1

        # Mock successful responses
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"results": [], "answer": None})
        mock_session.post.return_value.__aenter__.return_value = mock_response

        tavily_client.session = mock_session

        # Make rapid requests
        start_time = datetime.now()

        # First two requests should be immediate
        await tavily_client.search("query 1")
        await tavily_client.search("query 2")

        # Third request should be delayed
        await tavily_client.search("query 3")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Should have taken at least 1 second due to rate limiting
        assert duration >= 0.5  # Allow some margin for test execution

    def test_calculate_credibility(self, tavily_client):
        """Test credibility score calculation."""
        # Test .edu domain
        result_edu = {
            "url": "https://university.edu/research",
            "title": "Research Study on AI",
            "content": "This peer-reviewed study presents findings...",
        }
        score_edu = tavily_client._calculate_credibility(result_edu)
        assert score_edu > 0.8  # High score for .edu with academic keywords

        # Test .gov domain
        result_gov = {
            "url": "https://agency.gov/report",
            "title": "Government Report",
            "content": "Official findings and methodology",
        }
        score_gov = tavily_client._calculate_credibility(result_gov)
        assert score_gov > 0.7  # Good score for .gov

        # Test .com domain
        result_com = {
            "url": "https://blog.com/post",
            "title": "Blog Post",
            "content": "My thoughts on the topic",
        }
        score_com = tavily_client._calculate_credibility(result_com)
        assert score_com < 0.6  # Lower score for .com without academic keywords

        # Test journal URL
        result_journal = {
            "url": "https://journal.com/article",
            "title": "Journal Article",
            "content": "Abstract: This research examines...",
        }
        score_journal = tavily_client._calculate_credibility(result_journal)
        assert score_journal > 0.7  # Good score for journal

    def test_extract_domain(self, tavily_client):
        """Test domain extraction from URLs."""
        # Test various URL formats
        assert tavily_client._extract_domain("https://example.edu/page") == ".edu"
        assert tavily_client._extract_domain("http://site.gov") == ".gov"
        assert (
            tavily_client._extract_domain("https://www.journal.org/article") == ".org"
        )
        assert (
            tavily_client._extract_domain("https://subdomain.example.com/path")
            == ".com"
        )

        # Test edge cases
        assert tavily_client._extract_domain("invalid-url") == ".com"  # Default
        assert tavily_client._extract_domain("") == ".com"  # Default

    def test_process_results(self, tavily_client):
        """Test result processing and enhancement."""
        raw_data = {
            "results": [
                {
                    "title": "Low Credibility",
                    "url": "https://blog.com/post",
                    "content": "Blog content",
                    "score": 0.5,
                },
                {
                    "title": "High Credibility",
                    "url": "https://university.edu/research",
                    "content": "Peer-reviewed research study",
                    "score": 0.9,
                },
            ],
            "answer": "Summary",
        }

        response = tavily_client._process_results(raw_data, "test query")

        # Check response structure
        assert isinstance(response, TavilySearchResponse)
        assert response.query == "test query"
        assert len(response.results) == 2

        # Check sorting by credibility (high to low)
        assert response.results[0].title == "High Credibility"
        assert response.results[1].title == "Low Credibility"

        # Check metadata
        assert response.processing_metadata["total_results"] == 2
        assert response.processing_metadata["academic_results"] == 1  # Only .edu result


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_extract_key_statistics(self):
        """Test extracting statistics from text."""
        text = """
        The study found that 85% of participants showed improvement.
        Over 1,200 patients were involved in the trial.
        Results indicate a 2.5x increase in effectiveness.
        The success rate was 92.3 percent among the control group.
        """

        stats = extract_key_statistics(text)

        assert "85%" in stats
        assert "92.3%" in stats
        assert "1,200 patients" in stats
        assert len(stats) <= 10  # Limited to 10

    def test_extract_key_statistics_no_stats(self):
        """Test extracting statistics from text without numbers."""
        text = "This is a qualitative study with no numerical data."

        stats = extract_key_statistics(text)
        assert len(stats) == 0

    def test_extract_key_statistics_duplicates(self):
        """Test that duplicate statistics are removed."""
        text = "The rate is 50%. Half the subjects (50%) agreed. 50% was the median."

        stats = extract_key_statistics(text)
        # Should only have one "50%"
        assert stats.count("50%") == 1

    def test_calculate_reading_time(self):
        """Test reading time calculation."""
        # Test various word counts
        assert calculate_reading_time(225) == 1  # Exactly 1 minute
        assert calculate_reading_time(450) == 2  # Exactly 2 minutes
        assert calculate_reading_time(100) == 1  # Less than 1 minute rounds to 1
        assert calculate_reading_time(1000) == 4  # 4.44 minutes rounds to 4
        assert calculate_reading_time(1200) == 5  # 5.33 minutes rounds to 5
        assert calculate_reading_time(0) == 1  # Minimum 1 minute

    def test_clean_text_for_seo(self):
        """Test SEO text cleaning."""
        # Test removing extra whitespace
        text1 = "This   has    extra     spaces"
        assert clean_text_for_seo(text1) == "This has extra spaces."

        # Test removing special characters
        text2 = 'Text with "quotes" and <tags>'
        assert clean_text_for_seo(text2) == "Text with 'quotes' and tags."

        # Test adding period
        text3 = "No ending punctuation"
        assert clean_text_for_seo(text3) == "No ending punctuation."

        # Test preserving existing punctuation
        text4 = "Already has period."
        assert clean_text_for_seo(text4) == "Already has period."

        text5 = "Ends with question?"
        assert clean_text_for_seo(text5) == "Ends with question?"

    def test_generate_slug(self):
        """Test URL slug generation."""
        # Test basic slug generation
        assert generate_slug("The Future of AI") == "the-future-of-ai"

        # Test with special characters
        assert (
            generate_slug("AI & Machine Learning: A Guide")
            == "ai--machine-learning-a-guide"
        )

        # Test with numbers
        assert generate_slug("Top 10 AI Trends 2024") == "top-10-ai-trends-2024"

        # Test with multiple spaces
        assert generate_slug("Too    Many     Spaces") == "too-many-spaces"

        # Test with leading/trailing spaces
        assert generate_slug("  Trimmed Title  ") == "trimmed-title"

        # Test empty string
        assert generate_slug("") == ""


class TestIntegration:
    """Integration tests for the complete flow."""

    @pytest.mark.asyncio
    async def test_search_academic_sources_integration(self):
        """Test the complete search flow with mocked client."""
        # Create config
        config = Mock(spec=Config)
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.tavily_search_depth = "basic"
        config.tavily_include_domains = None
        config.tavily_max_results = 5
        config.request_timeout = 30
        config.max_retries = 3

        # Mock the client's search method
        mock_response = TavilySearchResponse(
            query="climate change",
            results=[
                TavilySearchResult(
                    title="Climate Research",
                    url="https://journal.edu/climate",
                    content="Research on climate patterns",
                    credibility_score=0.9,
                    domain=".edu",
                )
            ],
            answer="Climate change research summary",
        )

        with patch.object(TavilyClient, "search", return_value=mock_response):
            # Call the convenience function
            result = await search_academic_sources("climate change", config)

            # Verify result
            assert isinstance(result, TavilySearchResponse)
            assert result.query == "climate change"
            assert len(result.results) == 1
            assert result.results[0].title == "Climate Research"


# Test context manager functionality
class TestContextManager:
    """Test async context manager for TavilyClient."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self, mock_config):
        """Test that client properly opens and closes session."""
        async with TavilyClient(mock_config) as client:
            # Session should be created
            assert hasattr(client, "session")
            assert isinstance(client.session, aiohttp.ClientSession)

        # After context, session should be closed
        assert client.session.closed


# Edge case tests
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, tavily_client):
        """Test search with empty query."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"results": [], "answer": None})
        mock_session.post.return_value.__aenter__.return_value = mock_response

        tavily_client.session = mock_session

        result = await tavily_client.search("")
        assert result.query == ""
        assert len(result.results) == 0

    def test_credibility_score_bounds(self, tavily_client):
        """Test that credibility scores stay within bounds."""
        # Test maximum possible score
        result_max = {
            "url": "https://university.edu/journal/research",
            "title": "Peer-Reviewed Research Study Analysis",
            "content": " ".join(
                [
                    "study research journal peer-reviewed publication "
                    "findings methodology results conclusion abstract doi citation"
                ]
                * 5
            ),
        }
        score_max = tavily_client._calculate_credibility(result_max)
        assert 0 <= score_max <= 1

        # Test minimum score
        result_min = {
            "url": "https://random.xyz",
            "title": "Random",
            "content": "No academic content",
        }
        score_min = tavily_client._calculate_credibility(result_min)
        assert 0 <= score_min <= 1

    def test_special_characters_in_processing(self):
        """Test handling of special characters in various functions."""
        # Test statistics extraction with special characters
        text = "The rate is 85% (±5%). Cost: $1,200.50"
        stats = extract_key_statistics(text)
        assert "85%" in stats

        # Test slug generation with unicode
        slug = generate_slug("AI Research: Émergent Technologíes")
        assert slug == "ai-research-mergent-technologes"  # Unicode stripped

        # Test SEO cleaning with various quotes
        text = "Text with \"smart quotes\" and 'apostrophes'"
        cleaned = clean_text_for_seo(text)
        assert '"' not in cleaned  # Double quotes converted to single
