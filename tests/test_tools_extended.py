"""
Extended tests for tools module to improve coverage.

This module adds additional test cases for tool utilities like
statistics extraction and Tavily client functionality.
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from config import Config
from models import TavilySearchResponse, TavilySearchResult
from tools import (
    TavilyAPIError,
    TavilyClient,
    extract_key_statistics,
    search_academic_sources,
)


class TestToolsExtended:
    """Extended test cases for tools functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.tavily_api_key = "tvly-" + "x" * 40
        config.tavily_search_depth = "advanced"
        config.tavily_include_domains = [".edu", ".gov", ".org"]
        config.tavily_max_results = 10
        config.request_timeout = 30
        config.max_retries = 3
        return config

    def test_extract_key_statistics_basic(self):
        """Test basic statistics extraction."""
        text = (
            "The study showed a 45% improvement in accuracy and 30% reduction in costs."
        )
        stats = extract_key_statistics(text)

        assert isinstance(stats, list)
        assert "45%" in stats
        assert "30%" in stats

    def test_extract_key_statistics_percent_word(self):
        """Test extraction of 'X percent' format."""
        text = "Results show 85 percent success rate and 15 percent failure rate."
        stats = extract_key_statistics(text)

        assert "85%" in stats
        assert "15%" in stats

    def test_extract_key_statistics_with_context(self):
        """Test extraction of numbers with context."""
        text = """
        The study included 1,200 patients and 350 participants.
        Total of 50 cases were reviewed.
        """
        stats = extract_key_statistics(text)

        assert "1,200 patients" in stats
        assert "350 participants" in stats
        assert "50 cases" in stats

    def test_extract_key_statistics_no_stats(self):
        """Test extraction from text without statistics."""
        text = "This is a qualitative study with no numerical data."
        stats = extract_key_statistics(text)

        assert stats == []

    def test_extract_key_statistics_limit(self):
        """Test that extraction is limited to 10 statistics."""
        # Generate text with many statistics
        text = " ".join([f"{i}% improvement" for i in range(20)])
        stats = extract_key_statistics(text)

        assert len(stats) <= 10

    @pytest.mark.asyncio
    async def test_tavily_client_initialization(self, mock_config):
        """Test TavilyClient initialization."""
        client = TavilyClient(mock_config)

        assert client.api_key == mock_config.tavily_api_key
        assert client.search_depth == "advanced"
        assert client.include_domains == [".edu", ".gov", ".org"]
        assert client.max_results == 10
        assert client.timeout == 30

    @pytest.mark.asyncio
    async def test_tavily_client_search_success(self, mock_config):
        """Test successful search with TavilyClient."""
        with patch("tools.aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "title": "Test Paper",
                        "url": "https://test.edu/paper",
                        "content": "Test content with findings.",
                        "score": 0.85,
                    }
                ],
                "answer": "Summary of findings",
            }
            mock_session.post.return_value.__aenter__.return_value = mock_response

            async with TavilyClient(mock_config) as client:
                result = await client.search("test query")

            assert isinstance(result, TavilySearchResponse)
            assert result.query == "test query"
            assert len(result.results) == 1
            assert result.results[0].title == "Test Paper"
            assert result.results[0].domain == ".edu"

    @pytest.mark.asyncio
    async def test_tavily_client_calculate_credibility(self, mock_config):
        """Test credibility score calculation."""
        client = TavilyClient(mock_config)

        # High credibility - .edu domain with high score
        result1 = {
            "url": "https://journal.edu/paper",
            "score": 0.9,
            "content": "Peer-reviewed academic research",
        }
        cred1 = client._calculate_credibility(result1)
        assert cred1 > 0.8

        # Lower credibility - .com domain
        result2 = {
            "url": "https://blog.com/post",
            "score": 0.8,
            "content": "Blog post about research",
        }
        cred2 = client._calculate_credibility(result2)
        assert cred2 < cred1

    @pytest.mark.asyncio
    async def test_tavily_client_api_error_handling(self, mock_config):
        """Test API error handling."""
        with patch("tools.aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock 429 rate limit error
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.text.return_value = "Rate limit exceeded"
            mock_response.raise_for_status.side_effect = Exception("429 Client Error")
            mock_session.post.return_value.__aenter__.return_value = mock_response

            client = TavilyClient(mock_config)
            with pytest.raises(TavilyAPIError):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_search_academic_sources_wrapper(self, mock_config):
        """Test the search_academic_sources convenience function."""
        with patch("tools.TavilyClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock search result
            mock_result = TavilySearchResponse(
                query="test",
                results=[
                    TavilySearchResult(
                        title="Test",
                        url="https://test.edu",
                        content="Content",
                        score=0.9,
                        credibility_score=0.85,
                        domain=".edu",
                        processed_at=datetime.now(),
                    )
                ],
                answer=None,
                processing_metadata={},
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.search.return_value = mock_result

            result = await search_academic_sources("test", mock_config)

            assert isinstance(result, TavilySearchResponse)
            assert len(result.results) == 1

    def test_tavily_client_extract_domain(self, mock_config):
        """Test domain extraction from URLs."""
        client = TavilyClient(mock_config)

        test_cases = [
            ("https://journal.edu/paper", ".edu"),
            ("https://research.gov/study", ".gov"),
            ("https://blog.com/post", ".com"),
            ("https://university.ac.uk/research", ".uk"),
            ("invalid-url", ".com"),  # Default
        ]

        for url, expected_domain in test_cases:
            domain = client._extract_domain(url)
            assert domain == expected_domain

    @pytest.mark.asyncio
    async def test_tavily_client_timeout_handling(self, mock_config):
        """Test timeout handling."""
        mock_config.request_timeout = 0.1  # Very short timeout

        with patch("tools.aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Simulate timeout
            mock_session.post.side_effect = asyncio.TimeoutError()

            client = TavilyClient(mock_config)
            with pytest.raises(TavilyAPIError) as exc_info:
                await client.search("test")

            assert "timed out" in str(exc_info.value).lower()

    def test_extract_key_statistics_decimal_percentages(self):
        """Test extraction of decimal percentages."""
        text = "Accuracy improved by 99.97% with only 0.03% error rate."
        stats = extract_key_statistics(text)

        assert "99.97%" in stats
        assert "0.03%" in stats

    def test_extract_key_statistics_large_numbers(self):
        """Test extraction with large numbers."""
        text = "The study analyzed 1,234,567 users across 50 cases."
        stats = extract_key_statistics(text)

        assert "1,234,567 users" in stats
        assert "50 cases" in stats
