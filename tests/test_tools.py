"""
Tests for the tools module, focusing on Tavily API integration.

This test module covers:
- Successful API searches
- Error handling scenarios
- Rate limiting behavior
- Academic source filtering
- Credibility scoring
"""

# Import required libraries
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

# Import our modules
from tools import (
    TavilyClient,
    TavilyAPIError,
    TavilyAuthError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    search_academic_sources
)
from models import TavilySearchResponse, TavilySearchResult
from config import Config


# Mock response data
MOCK_TAVILY_RESPONSE = {
    "answer": "Academic research shows significant findings in this area.",
    "results": [
        {
            "title": "Academic Study on Machine Learning",
            "url": "https://university.edu/research/ml-study",
            "content": "This peer-reviewed study examines machine learning applications...",
            "score": 0.95
        },
        {
            "title": "Government Report on AI Ethics",
            "url": "https://agency.gov/reports/ai-ethics",
            "content": "Official government findings on ethical AI development...",
            "score": 0.90
        },
        {
            "title": "Blog Post About AI",
            "url": "https://techblog.com/ai-trends",
            "content": "Latest trends in artificial intelligence...",
            "score": 0.75
        },
        {
            "title": "Journal Article on Neural Networks",
            "url": "https://journal.org/papers/neural-nets",
            "content": "Peer-reviewed research on neural network architectures...",
            "score": 0.88
        }
    ]
}


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.tavily_api_key = "test-api-key"
    config.tavily_search_depth = "advanced"
    config.tavily_include_domains = [".edu", ".gov", ".org"]
    config.tavily_max_results = 10
    config.request_timeout = 30
    config.max_retries = 3
    return config


@pytest.fixture
async def tavily_client(mock_config):
    """Create a TavilyClient instance for testing."""
    async with TavilyClient(mock_config) as client:
        yield client


class TestTavilyClient:
    """Test cases for TavilyClient class."""
    
    @pytest.mark.asyncio
    async def test_successful_search(self, mock_config):
        """Test successful academic search with good results."""
        # Create client
        async with TavilyClient(mock_config) as client:
            # Mock the session.post method
            with patch.object(client.session, 'post') as mock_post:
                # Create mock response
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value=MOCK_TAVILY_RESPONSE)
                
                # Configure the context manager
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Perform search
                result = await client.search("machine learning research")
                
                # Verify the result
                assert isinstance(result, TavilySearchResponse)
                assert result.query == "machine learning research"
                assert len(result.results) == 4
                assert result.answer == "Academic research shows significant findings in this area."
                
                # Check that results are sorted by credibility
                credibility_scores = [r.credibility_score for r in result.results if r.credibility_score]
                assert credibility_scores == sorted(credibility_scores, reverse=True)
                
                # Verify academic results
                academic_results = result.get_academic_results()
                assert len(academic_results) >= 2  # Should have at least .edu and .gov results
    
    @pytest.mark.asyncio
    async def test_auth_error(self, mock_config):
        """Test handling of authentication errors (401)."""
        async with TavilyClient(mock_config) as client:
            with patch.object(client.session, 'post') as mock_post:
                # Create mock 401 response
                mock_response = MagicMock()
                mock_response.status = 401
                mock_response.message = "Unauthorized"
                mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=401,
                    message="Unauthorized"
                ))
                
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Should raise TavilyAuthError
                with pytest.raises(TavilyAuthError) as exc_info:
                    await client.search("test query")
                
                assert "Invalid Tavily API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_config):
        """Test handling of rate limit errors (429)."""
        async with TavilyClient(mock_config) as client:
            with patch.object(client.session, 'post') as mock_post:
                # Create mock 429 response
                mock_response = MagicMock()
                mock_response.status = 429
                mock_response.message = "Rate limit exceeded"
                mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429,
                    message="Rate limit exceeded"
                ))
                
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Should raise TavilyRateLimitError
                with pytest.raises(TavilyRateLimitError) as exc_info:
                    await client.search("test query")
                
                assert "rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_config):
        """Test handling of timeout errors."""
        async with TavilyClient(mock_config) as client:
            with patch.object(client.session, 'post') as mock_post:
                # Simulate timeout
                mock_post.side_effect = asyncio.TimeoutError()
                
                # Should raise TavilyTimeoutError
                with pytest.raises(TavilyTimeoutError) as exc_info:
                    await client.search("test query")
                
                assert "Request timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, mock_config):
        """Test that retry logic works with backoff."""
        async with TavilyClient(mock_config) as client:
            with patch.object(client.session, 'post') as mock_post:
                # First two calls fail, third succeeds
                mock_response_success = MagicMock()
                mock_response_success.status = 200
                mock_response_success.raise_for_status = MagicMock()
                mock_response_success.json = AsyncMock(return_value=MOCK_TAVILY_RESPONSE)
                
                # Create context managers for each attempt
                mock_context_fail1 = MagicMock()
                mock_context_fail1.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
                mock_context_fail1.__aexit__ = AsyncMock(return_value=None)
                
                mock_context_fail2 = MagicMock()
                mock_context_fail2.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
                mock_context_fail2.__aexit__ = AsyncMock(return_value=None)
                
                mock_context_success = MagicMock()
                mock_context_success.__aenter__ = AsyncMock(return_value=mock_response_success)
                mock_context_success.__aexit__ = AsyncMock(return_value=None)
                
                mock_post.side_effect = [
                    mock_context_fail1,
                    mock_context_fail2,
                    mock_context_success
                ]
                
                # Should succeed after retries
                result = await client.search("test query")
                assert isinstance(result, TavilySearchResponse)
                assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_credibility_scoring(self, mock_config):
        """Test credibility scoring for different domains."""
        async with TavilyClient(mock_config) as client:
            # Test individual credibility calculation
            edu_result = {"url": "https://university.edu/paper", "content": "research study findings"}
            gov_result = {"url": "https://agency.gov/report", "content": "official report"}
            com_result = {"url": "https://blog.com/post", "content": "blog post"}
            
            edu_score = client._calculate_credibility(edu_result)
            gov_score = client._calculate_credibility(gov_result)
            com_score = client._calculate_credibility(com_result)
            
            # Academic sources should score higher
            assert edu_score > com_score
            assert gov_score > com_score
            assert 0 <= edu_score <= 1
            assert 0 <= gov_score <= 1
            assert 0 <= com_score <= 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_config):
        """Test rate limiting functionality."""
        # Set a low rate limit for testing
        mock_config.rate_limit_calls = 2
        mock_config.rate_limit_window = 1  # 1 second window
        
        async with TavilyClient(mock_config) as client:
            client.rate_limit_calls = 2
            client.rate_limit_window = 1
            
            # Mock successful responses
            with patch.object(client.session, 'post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.raise_for_status = AsyncMock()
                mock_response.json = AsyncMock(return_value=MOCK_TAVILY_RESPONSE)
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Make rapid requests
                start_time = datetime.now()
                
                # First two should be immediate
                await client.search("query 1")
                await client.search("query 2")
                
                # Third should be delayed
                await client.search("query 3")
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Should have taken at least 1 second due to rate limiting
                assert duration >= 0.9  # Allow small margin
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, mock_config):
        """Test handling of malformed API responses."""
        async with TavilyClient(mock_config) as client:
            with patch.object(client.session, 'post') as mock_post:
                # Mock response with missing fields
                malformed_response = {
                    "results": [
                        {
                            # Missing some fields, but has required ones
                            "title": "Test Result",
                            "url": "https://example.com/test",  # Add valid URL
                            "content": "Test content"  # Add content
                            # Missing optional fields like score
                        }
                    ]
                }
                
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value=malformed_response)
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Should handle gracefully
                result = await client.search("test query")
                assert isinstance(result, TavilySearchResponse)
                # Results with missing fields should still be processed
                assert len(result.results) == 1


class TestSearchAcademicSources:
    """Test the convenience function."""
    
    @pytest.mark.asyncio
    async def test_search_academic_sources(self, mock_config):
        """Test the convenience function works correctly."""
        with patch('tools.TavilyClient') as MockClient:
            # Create mock client instance
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=TavilySearchResponse(
                query="test",
                results=[],
                answer=None
            ))
            
            # Configure mock
            MockClient.return_value.__aenter__.return_value = mock_client
            
            # Call convenience function
            result = await search_academic_sources("test query", mock_config)
            
            # Verify
            assert isinstance(result, TavilySearchResponse)
            mock_client.search.assert_called_once_with("test query")


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])