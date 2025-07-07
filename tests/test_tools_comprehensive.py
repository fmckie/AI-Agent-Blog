"""
Comprehensive tests for tools.py to achieve 95%+ coverage.

This test module implements the testing plan to cover all untested code paths
in tools.py, including edge cases and error scenarios.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import ssl

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
    calculate_reading_time,
    clean_text_for_seo,
    generate_slug,
    search_academic_sources,
)


class TestUtilityFunctions:
    """Test utility functions that were previously untested."""

    def test_calculate_reading_time_minimum(self):
        """Test minimum reading time of 1 minute."""
        # Test with 0 words - should return 1 minute minimum
        assert calculate_reading_time(0) == 1
        
        # Test with very few words - should still return 1 minute
        assert calculate_reading_time(50) == 1
        assert calculate_reading_time(100) == 1
    
    def test_calculate_reading_time_exact(self):
        """Test reading time calculation at exact boundaries."""
        # 225 words = exactly 1 minute at 225 wpm
        assert calculate_reading_time(225) == 1
        
        # Just under 2 minutes worth
        assert calculate_reading_time(449) == 2
        
        # Just over 2 minutes worth
        assert calculate_reading_time(451) == 2
    
    def test_calculate_reading_time_longer(self):
        """Test reading time for longer content."""
        # 10 minutes worth
        assert calculate_reading_time(2250) == 10
        
        # 30 minutes worth
        assert calculate_reading_time(6750) == 30
    
    def test_clean_text_for_seo_basic(self):
        """Test basic SEO text cleaning."""
        # Remove extra whitespace
        text = "This  has   extra    whitespace"
        assert clean_text_for_seo(text) == "This has extra whitespace."
        
        # Already clean text with proper ending
        text = "This is already clean."
        assert clean_text_for_seo(text) == "This is already clean."
    
    def test_clean_text_for_seo_quotes(self):
        """Test quote replacement for SEO."""
        # Replace double quotes with single quotes
        text = 'He said "hello" to everyone'
        assert clean_text_for_seo(text) == "He said 'hello' to everyone."
    
    def test_clean_text_for_seo_html(self):
        """Test HTML character removal."""
        # Remove < and > characters
        text = "This <tag> should be removed"
        assert clean_text_for_seo(text) == "This tag should be removed."
        
        # Multiple HTML-like characters
        text = "Code: <div>content</div>"
        assert clean_text_for_seo(text) == "Code: divcontent/div."
    
    def test_clean_text_for_seo_sentence_ending(self):
        """Test proper sentence ending addition."""
        # Add period to text without ending punctuation
        text = "This needs a period"
        assert clean_text_for_seo(text) == "This needs a period."
        
        # Don't add period if already has ending punctuation
        text = "Is this a question?"
        assert clean_text_for_seo(text) == "Is this a question?"
        
        text = "What an exclamation!"
        assert clean_text_for_seo(text) == "What an exclamation!"
    
    def test_clean_text_for_seo_combined(self):
        """Test combined cleaning operations."""
        # Multiple issues in one text
        text = '  This   has "quotes" and <tags>  needs cleanup  '
        expected = "This has 'quotes' and tags needs cleanup."
        assert clean_text_for_seo(text) == expected
    
    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        # Simple title
        assert generate_slug("Hello World") == "hello-world"
        
        # Title with multiple words
        assert generate_slug("This Is A Test Title") == "this-is-a-test-title"
    
    def test_generate_slug_special_characters(self):
        """Test slug generation with special characters."""
        # Remove special characters
        assert generate_slug("Hello! World?") == "hello-world"
        
        # Numbers should be preserved
        assert generate_slug("Top 10 Tips") == "top-10-tips"
        
        # Remove all special characters
        assert generate_slug("Test@#$%^*()_+={}[]|\\:;\"'<>,.?/~`") == "test"
    
    def test_generate_slug_ampersand(self):
        """Test ampersand conversion to double hyphen."""
        # Single ampersand
        assert generate_slug("Tips & Tricks") == "tips--tricks"
        
        # Multiple ampersands
        assert generate_slug("A & B & C") == "a--b--c"
    
    def test_generate_slug_multiple_spaces(self):
        """Test handling of multiple spaces."""
        # Multiple spaces should become single hyphen
        assert generate_slug("Too    Many     Spaces") == "too-many-spaces"
        
        # Mixed whitespace
        assert generate_slug("Tab\there   and\nnewlines") == "tab-here-and-newlines"
    
    def test_generate_slug_hyphen_handling(self):
        """Test proper hyphen handling."""
        # Leading and trailing hyphens removed
        assert generate_slug("-Leading Hyphen") == "leading-hyphen"
        assert generate_slug("Trailing Hyphen-") == "trailing-hyphen"
        assert generate_slug("-Both Hyphens-") == "both-hyphens"
        
        # Multiple consecutive hyphens (except from &)
        assert generate_slug("Too---Many---Hyphens") == "too--many--hyphens"
    
    def test_generate_slug_edge_cases(self):
        """Test edge cases for slug generation."""
        # Empty string
        assert generate_slug("") == ""
        
        # Only special characters
        assert generate_slug("!!!@@@###") == ""
        
        # Very long title
        long_title = "This is a very long title " * 10
        slug = generate_slug(long_title)
        assert len(slug) > 0
        assert "--" not in slug  # No double hyphens except from &


class TestTavilyClientAdvanced:
    """Advanced tests for TavilyClient covering edge cases."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.tavily_api_key = "test-api-key"
        config.tavily_search_depth = "advanced"
        config.tavily_include_domains = [".edu", ".gov"]
        config.tavily_max_results = 10
        config.request_timeout = 30
        config.max_retries = 3
        return config
    
    @pytest.fixture
    def mock_datetime(self, monkeypatch):
        """Mock datetime for controlled time testing."""
        class MockDatetime:
            current_time = datetime(2024, 1, 1, 12, 0, 0)
            
            @classmethod
            def now(cls):
                return cls.current_time
            
            @classmethod
            def advance(cls, seconds):
                cls.current_time += timedelta(seconds=seconds)
        
        # Mock the datetime class in tools module
        monkeypatch.setattr('tools.datetime', MockDatetime)
        return MockDatetime
    
    @pytest.mark.asyncio
    async def test_rate_limit_window_cleanup(self, mock_config, mock_datetime):
        """Test that old requests are cleaned from rate limit tracking."""
        # Create client with short rate limit window for testing
        client = TavilyClient(mock_config)
        client.rate_limit_window = 60  # 60 second window
        
        # Add some old timestamps
        old_time = mock_datetime.now() - timedelta(seconds=120)  # 2 minutes ago
        recent_time = mock_datetime.now() - timedelta(seconds=30)  # 30 seconds ago
        
        client._request_times.append(old_time)
        client._request_times.append(old_time)
        client._request_times.append(recent_time)
        
        # Check rate limit - should clean old entries
        await client._check_rate_limit()
        
        # Only the recent timestamp should remain
        assert len(client._request_times) == 2  # Recent + new one added
        assert client._request_times[0] == recent_time
    
    @pytest.mark.asyncio
    async def test_rate_limit_wait_calculation(self, mock_config, mock_datetime):
        """Test wait time calculation when rate limited."""
        # Create client with very low rate limit for testing
        client = TavilyClient(mock_config)
        client.rate_limit_calls = 2
        client.rate_limit_window = 10  # 10 second window
        
        # Fill up the rate limit
        await client._check_rate_limit()  # Request 1
        await client._check_rate_limit()  # Request 2
        
        # Record the time before the third request
        start_time = mock_datetime.now()
        
        # Mock sleep to track if it was called with correct duration
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = None
            
            # Advance time by 5 seconds (halfway through window)
            mock_datetime.advance(5)
            
            # This should trigger rate limiting
            await client._check_rate_limit()
            
            # Check that sleep was called
            mock_sleep.assert_called_once()
            
            # The wait time should be approximately 5 seconds
            # (10 second window - 5 seconds elapsed)
            wait_time = mock_sleep.call_args[0][0]
            assert 4.9 <= wait_time <= 5.1  # Allow small margin
    
    @pytest.mark.asyncio
    async def test_search_with_domain_filtering(self, mock_config):
        """Test that domain filtering is included in API payload."""
        async with TavilyClient(mock_config) as client:
            # Mock the session.post to capture the payload
            captured_payload = None
            
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "results": [],
                "answer": None
            })
            
            # Create proper context manager for post
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            # Capture the payload when post is called
            def capture_post(url, json=None, **kwargs):
                nonlocal captured_payload
                captured_payload = json
                return mock_context
            
            with patch.object(client.session, 'post', side_effect=capture_post):
                await client.search("test query")
            
            # Verify domain filtering was included
            assert captured_payload is not None
            assert "include_domains" in captured_payload
            assert captured_payload["include_domains"] == [".edu", ".gov"]
    
    @pytest.mark.asyncio
    async def test_search_without_domain_filtering(self, mock_config):
        """Test search when include_domains is empty."""
        # Set include_domains to empty list
        mock_config.tavily_include_domains = []
        
        async with TavilyClient(mock_config) as client:
            captured_payload = None
            
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "results": [],
                "answer": None
            })
            
            # Create proper context manager
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            # Capture payload function
            def capture_post(url, json=None, **kwargs):
                nonlocal captured_payload
                captured_payload = json
                return mock_context
            
            with patch.object(client.session, 'post', side_effect=capture_post):
                await client.search("test query")
            
            # Verify domain filtering was NOT included
            assert captured_payload is not None
            assert "include_domains" not in captured_payload
    
    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_config):
        """Test handling of non-401/429 API errors."""
        async with TavilyClient(mock_config) as client:
            # Create mock 500 error response
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.message = "Internal Server Error"
            
            # Create the exception that raise_for_status would raise
            error = aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=500,
                message="Internal Server Error"
            )
            mock_response.raise_for_status = AsyncMock(side_effect=error)
            
            # Setup context manager
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(client.session, 'post', return_value=mock_context):
                with pytest.raises(TavilyAPIError) as exc_info:
                    await client.search("test query")
                
                assert "API request failed with status 500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_coroutine_response_handling(self, mock_config):
        """Test handling of coroutine responses (for test mocks)."""
        async with TavilyClient(mock_config) as client:
            # Create mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "results": [{
                    "title": "Test",
                    "url": "https://test.edu",
                    "content": "Content",
                    "score": 0.9
                }],
                "answer": "Test answer"
            })
            
            # Create a coroutine that returns the context manager
            async def mock_post_coroutine(*args, **kwargs):
                # Return a proper context manager
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_response)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                return mock_context
            
            # Make session.post return a coroutine
            # This tests the coroutine detection path
            client.session.post = mock_post_coroutine
            
            result = await client.search("test query")
            
            assert isinstance(result, TavilySearchResponse)
            assert len(result.results) == 1
    
    def test_credibility_journal_pubmed_urls(self, mock_config):
        """Test credibility scoring for journal and pubmed URLs."""
        client = TavilyClient(mock_config)
        
        # Test journal URL
        journal_result = {
            "url": "https://journal.nature.com/articles/12345",
            "title": "Research Paper",
            "content": "Scientific findings"
        }
        journal_score = client._calculate_credibility(journal_result)
        
        # Test pubmed URL
        pubmed_result = {
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345",
            "title": "Medical Study",
            "content": "Medical research"
        }
        pubmed_score = client._calculate_credibility(pubmed_result)
        
        # Test regular URL for comparison
        regular_result = {
            "url": "https://example.com/article",
            "title": "Regular Article",
            "content": "General content"
        }
        regular_score = client._calculate_credibility(regular_result)
        
        # Journal and pubmed should score higher
        assert journal_score > regular_score
        assert pubmed_score > regular_score
        
        # Both should get the 0.2 bonus for journal/pubmed
        assert journal_score >= 0.7  # Base 0.5 + 0.2
        assert pubmed_score >= 0.7   # Base 0.5 + 0.2
    
    def test_extract_domain_error_handling(self, mock_config):
        """Test domain extraction with malformed URLs."""
        client = TavilyClient(mock_config)
        
        # Test various malformed URLs
        test_cases = [
            ("not-a-url", ".com"),              # No protocol - defaults to .com
            ("http://", ".com"),                # No domain - defaults to .com
            ("ftp://[invalid", ".com"),         # Invalid URL - defaults to .com
            ("", ".com"),                       # Empty string - defaults to .com
            ("http://localhost", ".com"),       # No TLD - defaults to .com
            ("http://192.168.1.1", ".1"),       # IP address - takes last segment
        ]
        
        for url, expected in test_cases:
            result = client._extract_domain(url)
            assert result == expected, f"Failed for URL: {url}"
    
    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self, mock_config):
        """Test error when client is used without context manager."""
        client = TavilyClient(mock_config)
        
        # Try to search without entering context manager
        with pytest.raises(TavilyAPIError) as exc_info:
            await client.search("test query")
        
        assert "Client not initialized" in str(exc_info.value)
        assert "Use as context manager" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.tavily_api_key = "test-api-key"
        config.tavily_search_depth = "advanced"
        config.tavily_include_domains = [".edu", ".gov", ".org"]
        config.tavily_max_results = 5
        config.request_timeout = 30
        config.max_retries = 3
        return config
    
    @pytest.mark.asyncio
    async def test_full_search_flow_with_academic_results(self, mock_config):
        """Test complete search flow with realistic academic results."""
        async with TavilyClient(mock_config) as client:
            # Mock comprehensive response
            mock_response_data = {
                "answer": "Research shows significant improvements in machine learning accuracy.",
                "results": [
                    {
                        "title": "Deep Learning Study Published in Nature",
                        "url": "https://journal.nature.com/deep-learning-2024",
                        "content": "This peer-reviewed study presents findings on neural network architectures...",
                        "score": 0.98
                    },
                    {
                        "title": "Government AI Ethics Report",
                        "url": "https://nist.gov/ai-ethics-framework",
                        "content": "Official government publication on ethical AI development methodology...",
                        "score": 0.92
                    },
                    {
                        "title": "MIT Research on Transformer Models",
                        "url": "https://research.mit.edu/transformer-advances",
                        "content": "Academic research from MIT examining transformer model improvements...",
                        "score": 0.95
                    },
                    {
                        "title": "Medical AI Applications",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/medical-ai-2024",
                        "content": "Peer-reviewed medical journal article on AI in diagnostics...",
                        "score": 0.90
                    },
                    {
                        "title": "Tech Blog on AI Trends",
                        "url": "https://techblog.com/ai-trends-2024",
                        "content": "Industry perspective on current AI developments...",
                        "score": 0.75
                    }
                ]
            }
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value=mock_response_data)
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(client.session, 'post', return_value=mock_context):
                result = await client.search("machine learning advances 2024")
            
            # Verify response structure
            assert isinstance(result, TavilySearchResponse)
            assert result.query == "machine learning advances 2024"
            assert len(result.results) == 5
            
            # Verify results are sorted by credibility
            scores = [r.credibility_score for r in result.results]
            assert scores == sorted(scores, reverse=True)
            
            # Verify academic results have high credibility
            academic_results = result.get_academic_results()
            assert len(academic_results) >= 4  # All except the blog
            
            # Verify processing metadata
            assert result.processing_metadata["total_results"] == 5
            assert result.processing_metadata["academic_results"] >= 4
            
            # Verify specific domain scoring
            # Journal article should have high credibility (base 0.5 + domain bonus + keyword bonuses)
            journal_result = next(r for r in result.results if "journal.nature.com" in r.url)
            assert journal_result.credibility_score >= 0.8  # Should be high but may not reach 0.9
    
    @pytest.mark.asyncio
    async def test_error_recovery_with_retry(self, mock_config):
        """Test that transient errors are recovered through retry."""
        async with TavilyClient(mock_config) as client:
            call_count = 0
            
            async def mock_post_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count < 3:
                    # First two calls fail with transient error
                    raise aiohttp.ClientError("Network error")
                
                # Third call succeeds
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.raise_for_status = AsyncMock()
                mock_response.json = AsyncMock(return_value={
                    "results": [{
                        "title": "Success after retry",
                        "url": "https://example.edu/paper",
                        "content": "Content",
                        "score": 0.8
                    }],
                    "answer": "Recovered"
                })
                
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_response)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                return mock_context
            
            with patch.object(client.session, 'post', side_effect=mock_post_with_retry):
                result = await client.search("test with retry")
            
            # Should succeed after retries
            assert call_count == 3
            assert isinstance(result, TavilySearchResponse)
            assert len(result.results) == 1
            assert result.results[0].title == "Success after retry"


class TestConcurrentOperations:
    """Test concurrent request handling and rate limiting."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.tavily_api_key = "test-api-key"
        config.tavily_search_depth = "basic"
        config.tavily_include_domains = []
        config.tavily_max_results = 5
        config.request_timeout = 30
        config.max_retries = 3
        return config
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, mock_config):
        """Test multiple concurrent searches."""
        async with TavilyClient(mock_config) as client:
            # Mock successful responses
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "results": [{
                    "title": "Concurrent result",
                    "url": "https://example.com",
                    "content": "Content",
                    "score": 0.8
                }],
                "answer": None
            })
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(client.session, 'post', return_value=mock_context):
                # Launch multiple concurrent searches
                searches = [
                    client.search(f"query {i}")
                    for i in range(5)
                ]
                
                results = await asyncio.gather(*searches)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert isinstance(result, TavilySearchResponse)
                assert len(result.results) == 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_with_concurrent_requests(self, mock_config):
        """Test rate limiting with concurrent requests."""
        client = TavilyClient(mock_config)
        client.rate_limit_calls = 3
        client.rate_limit_window = 2  # 2 second window
        
        async with client:
            sleep_called = []
            
            async def mock_sleep(duration):
                sleep_called.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                # Mock successful responses
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.raise_for_status = AsyncMock()
                mock_response.json = AsyncMock(return_value={"results": [], "answer": None})
                
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_response)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                
                with patch.object(client.session, 'post', return_value=mock_context):
                    # Launch more requests than rate limit allows
                    searches = [client.search(f"query {i}") for i in range(5)]
                    
                    # Execute them
                    results = await asyncio.gather(*searches)
            
            # Should have triggered rate limiting
            assert len(sleep_called) > 0  # Some requests should have been delayed
            
            # All requests should still complete
            assert len(results) == 5
            for result in results:
                assert isinstance(result, TavilySearchResponse)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=tools", "--cov-report=term-missing"])