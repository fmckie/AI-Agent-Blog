"""
Extended tests for tools.py focusing on edge cases and advanced scenarios.

This module complements test_tools_comprehensive.py by adding tests for
complex error scenarios, race conditions, and integration edge cases.
"""

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock

import aiohttp
import pytest

from config import Config
from models import TavilySearchResponse, TavilySearchResult
from tools import (
    TavilyAPIError,
    TavilyAuthError,
    TavilyClient,
    TavilyRateLimitError,
    TavilyTimeoutError,
    extract_key_statistics,
    search_academic_sources,
    extract_url_content,
    crawl_website,
    map_website,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.tavily_api_key = "test-api-key"
    config.tavily_search_depth = "advanced"
    config.tavily_include_domains = [".edu", ".gov", ".org"]
    config.tavily_max_results = 10
    config.request_timeout = 30
    config.max_retries = 3
    return config


class TestTavilyClientAdvanced:
    """Advanced tests for TavilyClient edge cases."""

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, mock_config):
        """Test rate limiting under concurrent requests."""
        async with TavilyClient(mock_config) as client:
            # Mock the session post method
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "title": "Test",
                            "url": "http://test.com",
                            "content": "Test content",
                        }
                    ]
                }
            )

            client.session.post = AsyncMock(return_value=mock_response)

            # Simulate filling up the rate limit window
            current_time = datetime.now()
            for i in range(58):  # Fill up most of the rate limit
                client._request_times.append(current_time - timedelta(seconds=i))

            # Launch multiple concurrent requests
            tasks = []
            for i in range(5):  # Try to make 5 concurrent requests
                task = asyncio.create_task(client.search("test query"))
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed but some might be delayed
            assert all(isinstance(r, TavilySearchResponse) for r in results)
            # Verify rate limit was respected
            assert len(client._request_times) <= client.rate_limit_calls

    @pytest.mark.asyncio
    async def test_session_recovery_after_network_error(self, mock_config):
        """Test client can recover from network errors."""
        async with TavilyClient(mock_config) as client:
            # First request fails with network error
            client.session.post = AsyncMock(
                side_effect=aiohttp.ClientError("Network error")
            )

            with pytest.raises(TavilyAPIError):
                await client.search("test query")

            # Subsequent request should work if network recovers
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"results": []})
            client.session.post = AsyncMock(return_value=mock_response)

            result = await client.search("test query 2")
            assert isinstance(result, TavilySearchResponse)

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, mock_config):
        """Test handling of malformed JSON responses."""
        async with TavilyClient(mock_config) as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                side_effect=json.JSONDecodeError("Invalid", "", 0)
            )
            mock_response.text = AsyncMock(return_value="<html>Error page</html>")

            client.session.post = AsyncMock(return_value=mock_response)

            with pytest.raises(TavilyAPIError) as exc_info:
                await client.search("test query")

            assert "Invalid JSON response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_partial_response_handling(self, mock_config):
        """Test handling of partial/incomplete responses."""
        async with TavilyClient(mock_config) as client:
            # Response missing required fields
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {"title": "Test"},  # Missing url and content
                        {"url": "http://test.com"},  # Missing title and content
                        {
                            "title": "Complete",
                            "url": "http://complete.com",
                            "content": "Content",
                        },
                    ]
                }
            )

            client.session.post = AsyncMock(return_value=mock_response)

            result = await client.search("test query")
            # Should handle partial results gracefully
            assert len(result.results) >= 1
            # Only complete results should be included
            assert all(r.title and r.url and r.content for r in result.results)

    @pytest.mark.asyncio
    async def test_timeout_during_different_stages(self, mock_config):
        """Test timeouts occurring at different stages of the request."""
        async with TavilyClient(mock_config) as client:
            # Timeout during connection
            client.session.post = AsyncMock(
                side_effect=asyncio.TimeoutError("Connection timeout")
            )

            with pytest.raises(TavilyTimeoutError):
                await client.search("test query")

            # Timeout during response read
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                side_effect=asyncio.TimeoutError("Read timeout")
            )

            client.session.post = AsyncMock(return_value=mock_response)

            with pytest.raises(TavilyTimeoutError):
                await client.search("test query")


class TestSearchAcademicSourcesAdvanced:
    """Advanced tests for search_academic_sources function."""

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, mock_config):
        """Test searching with special characters in query."""
        queries = [
            "COVID-19 & mental health",
            "type 2 diabetes (T2D)",
            "omega-3/omega-6 ratio",
            "vitamin D3 + K2",
            "5-HTP supplementation",
            "mTOR/AMPK pathway",
        ]

        with patch("tools.TavilyClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Mock successful responses
            mock_client.search.return_value = TavilySearchResponse(
                results=[
                    TavilySearchResult(
                        title="Test Result",
                        url="http://test.edu/paper",
                        content="Test content",
                        score=0.9,
                    )
                ]
            )

            for query in queries:
                result = await search_academic_sources(query, mock_config)
                assert len(result.results) > 0
                # Verify query was passed correctly
                mock_client.search.assert_called_with(query)

    @pytest.mark.asyncio
    async def test_search_empty_results_handling(self, mock_config):
        """Test handling of empty search results."""
        with patch("tools.TavilyClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Mock empty results
            mock_client.search.return_value = TavilySearchResponse(results=[])

            result = await search_academic_sources("very obscure topic", mock_config)
            assert len(result.results) == 0
            assert isinstance(result, TavilySearchResponse)

    @pytest.mark.asyncio
    async def test_search_client_initialization_failure(self, mock_config):
        """Test handling of client initialization failures."""
        with patch("tools.TavilyClient") as mock_client_class:
            # Make client creation fail
            mock_client_class.side_effect = Exception("Failed to create client")

            with pytest.raises(Exception) as exc_info:
                await search_academic_sources("test", mock_config)

            assert "Failed to create client" in str(exc_info.value)


class TestExtractKeyStatisticsAdvanced:
    """Advanced tests for extract_key_statistics function."""

    def test_statistics_with_various_formats(self):
        """Test extraction of statistics in various formats."""
        test_cases = [
            # Percentages with different formats
            ("The success rate was 87.5%.", ["87.5%"]),
            ("Improvement of 23 percent was observed.", ["23 percent"]),
            ("A 45% reduction in symptoms.", ["45%"]),
            # Numbers with units
            ("Average weight loss: 5.2kg", ["5.2kg"]),
            ("Temperature increased by 2.3°C", ["2.3°C"]),
            ("Dosage: 500mg twice daily", ["500mg"]),
            # Ratios and ranges
            ("The ratio was 3:1", ["3:1"]),
            ("Results ranged from 10-25%", ["10-25%"]),
            ("P-value < 0.001", ["< 0.001"]),
            # Scientific notation
            ("Concentration: 1.5×10^6 cells/ml", ["1.5×10^6"]),
            ("Effect size: 2.3e-4", ["2.3e-4"]),
            # Mixed statistics
            (
                "Study showed 78% efficacy (p<0.05) with 3.2mg dosage over 12 weeks.",
                ["78%", "p<0.05", "3.2mg", "12 weeks"],
            ),
        ]

        for text, expected_stats in test_cases:
            stats = extract_key_statistics(text)
            for expected in expected_stats:
                assert any(
                    expected in stat for stat in stats
                ), f"Expected {expected} in {stats}"

    def test_statistics_edge_cases(self):
        """Test edge cases for statistics extraction."""
        # Empty text
        assert extract_key_statistics("") == []

        # Text with no statistics
        assert extract_key_statistics("This is a text without any numbers.") == []

        # Very long text with many statistics
        long_text = " ".join([f"Result {i}: {i*10}%" for i in range(100)])
        stats = extract_key_statistics(long_text)
        assert len(stats) <= 20  # Should limit results

        # Text with false positives (e.g., dates, IDs)
        text = "Study ID: 12345, published in 2023, DOI: 10.1234/journal.2023.567"
        stats = extract_key_statistics(text)
        # Should filter out non-statistical numbers
        assert len(stats) < 5


class TestURLContentExtraction:
    """Tests for URL content extraction functions."""

    @pytest.mark.asyncio
    async def test_extract_url_content_with_redirects(self):
        """Test content extraction with multiple redirects."""
        mock_session = AsyncMock()

        # Mock redirect chain
        redirect_response = AsyncMock()
        redirect_response.status = 301
        redirect_response.headers = {"Location": "http://final.url"}

        final_response = AsyncMock()
        final_response.status = 200
        final_response.text = AsyncMock(
            return_value="<html><body>Content</body></html>"
        )

        mock_session.get.side_effect = [redirect_response, final_response]

        result = await extract_url_content("http://start.url", mock_session)
        assert "Content" in result
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_url_content_encoding_issues(self):
        """Test handling of various content encodings."""
        mock_session = AsyncMock()

        # Test different encodings
        encodings = [
            ("utf-8", "Test content with émojis 🎉"),
            ("latin-1", "Test content with accents: café"),
            ("iso-8859-1", "Test content with special chars: ñ"),
        ]

        for encoding, content in encodings:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=content)
            mock_response.encoding = encoding

            mock_session.get.return_value = mock_response

            result = await extract_url_content("http://test.url", mock_session)
            assert len(result) > 0  # Should handle encoding without error

    @pytest.mark.asyncio
    async def test_crawl_website_depth_limiting(self):
        """Test website crawling respects depth limits."""
        mock_session = AsyncMock()

        # Mock responses for different pages
        pages = {
            "http://site.com": "<html><a href='/page1'>Link1</a><a href='/page2'>Link2</a></html>",
            "http://site.com/page1": "<html><a href='/deep1'>Deep1</a></html>",
            "http://site.com/page2": "<html><a href='/deep2'>Deep2</a></html>",
            "http://site.com/deep1": "<html>Deep content 1</html>",
            "http://site.com/deep2": "<html>Deep content 2</html>",
        }

        async def mock_get(url, **kwargs):
            response = AsyncMock()
            response.status = 200
            response.text = AsyncMock(
                return_value=pages.get(url, "<html>Not found</html>")
            )
            return response

        mock_session.get = mock_get

        # Test with max_depth=1 (should only get main page and direct links)
        results = await crawl_website("http://site.com", mock_session, max_depth=1)
        assert len(results) <= 3  # Main + 2 direct links

        # Test with max_depth=2 (should get all pages)
        results = await crawl_website("http://site.com", mock_session, max_depth=2)
        assert len(results) <= 5  # All pages

    @pytest.mark.asyncio
    async def test_map_website_circular_references(self):
        """Test website mapping handles circular references."""
        mock_session = AsyncMock()

        # Create circular reference: A -> B -> C -> A
        pages = {
            "http://site.com": "<html><a href='/pageB'>B</a></html>",
            "http://site.com/pageB": "<html><a href='/pageC'>C</a></html>",
            "http://site.com/pageC": "<html><a href='/'>Home</a></html>",
        }

        async def mock_get(url, **kwargs):
            response = AsyncMock()
            response.status = 200
            response.text = AsyncMock(
                return_value=pages.get(url, "<html>Not found</html>")
            )
            return response

        mock_session.get = mock_get

        # Should handle circular refs without infinite loop
        sitemap = await map_website("http://site.com", mock_session)
        assert len(sitemap) == 3  # Should find all 3 unique pages
        assert all(url in sitemap for url in pages.keys())


class TestErrorPropagation:
    """Test error propagation through the tools module."""

    @pytest.mark.asyncio
    async def test_nested_error_handling(self, mock_config):
        """Test that errors are properly propagated through nested calls."""
        with patch("tools.TavilyClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Test different error types
            errors = [
                (TavilyAuthError("Invalid API key"), TavilyAuthError),
                (TavilyRateLimitError("Rate limit exceeded"), TavilyRateLimitError),
                (TavilyTimeoutError("Request timeout"), TavilyTimeoutError),
                (TavilyAPIError("Generic error"), TavilyAPIError),
            ]

            for error, expected_type in errors:
                mock_client.search.side_effect = error

                with pytest.raises(expected_type):
                    await search_academic_sources("test", mock_config)


class TestPerformanceOptimizations:
    """Test performance-related aspects of the tools module."""

    @pytest.mark.asyncio
    async def test_connection_pooling(self, mock_config):
        """Test that connection pooling is used efficiently."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with TavilyClient(mock_config) as client:
                # Make multiple requests
                for _ in range(5):
                    mock_response = AsyncMock()
                    mock_response.status = 200
                    mock_response.json = AsyncMock(return_value={"results": []})
                    client.session.post = AsyncMock(return_value=mock_response)

                    await client.search("test")

            # Session should be created once and reused
            assert mock_session_class.call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, mock_config):
        """Test handling of concurrent requests."""
        async with TavilyClient(mock_config) as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"results": []})

            # Add delay to simulate network latency
            async def delayed_post(*args, **kwargs):
                await asyncio.sleep(0.1)
                return mock_response

            client.session.post = delayed_post

            # Launch concurrent requests
            start_time = asyncio.get_event_loop().time()
            tasks = [client.search(f"query {i}") for i in range(5)]
            results = await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()

            # Should complete faster than sequential (5 * 0.1 = 0.5s)
            assert (end_time - start_time) < 0.3  # Allow some overhead
            assert len(results) == 5


# Integration tests
class TestToolsIntegration:
    """Integration tests for tools module components."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, mock_config):
        """Test complete search workflow from query to results."""
        with patch("tools.TavilyClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Mock comprehensive response
            mock_client.search.return_value = TavilySearchResponse(
                results=[
                    TavilySearchResult(
                        title="Diabetes Management Study",
                        url="http://medical.edu/diabetes-study",
                        content="A comprehensive study showing 78% improvement in glycemic control...",
                        score=0.95,
                    ),
                    TavilySearchResult(
                        title="Insulin Resistance Research",
                        url="http://research.org/insulin",
                        content="New findings indicate 45% reduction in insulin resistance...",
                        score=0.87,
                    ),
                ]
            )

            # Perform search
            results = await search_academic_sources("diabetes management", mock_config)

            # Verify results
            assert len(results.results) == 2
            assert (
                results.results[0].score > results.results[1].score
            )  # Sorted by score

            # Extract statistics from results
            all_content = " ".join(r.content for r in results.results)
            stats = extract_key_statistics(all_content)
            assert "78%" in " ".join(stats)
            assert "45%" in " ".join(stats)


# Fixtures for advanced testing
@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session with common configurations."""
    session = AsyncMock()
    session.closed = False
    return session


@pytest.fixture
def sample_html_responses():
    """Provide sample HTML responses for testing."""
    return {
        "academic_article": """
        <html>
            <head><title>Research Article</title></head>
            <body>
                <h1>Effects of Exercise on Type 2 Diabetes</h1>
                <p>Our study of 500 participants showed a 67% improvement in glucose control.</p>
                <p>Average HbA1c reduction: 1.2% over 6 months.</p>
            </body>
        </html>
        """,
        "complex_layout": """
        <html>
            <body>
                <nav>Navigation menu</nav>
                <aside>Sidebar content</aside>
                <main>
                    <article>
                        <h2>Main findings</h2>
                        <p>Primary outcome: 89% success rate (p<0.001)</p>
                    </article>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """,
    }


# What questions do you have about these extended tests, Finn?
# Would you like me to explain any specific testing pattern in more detail?
# Try this exercise: Add tests for websocket connections if the API supports them!
