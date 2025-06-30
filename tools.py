"""
External API integrations and utility tools.

This module provides integrations with external services like Tavily API
and other utility functions used throughout the system.
"""

# Import required libraries
import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import backoff
from collections import deque

# Import our modules
from config import Config
from models import TavilySearchResult, TavilySearchResponse

# Set up logging
logger = logging.getLogger(__name__)


# Custom exceptions for Tavily API
class TavilyAPIError(Exception):
    """Base exception for Tavily API errors."""
    pass


class TavilyAuthError(TavilyAPIError):
    """Raised when authentication fails (401 status)."""
    pass


class TavilyRateLimitError(TavilyAPIError):
    """Raised when API rate limit is exceeded (429 status)."""
    pass


class TavilyTimeoutError(TavilyAPIError):
    """Raised when API request times out."""
    pass


class TavilyClient:
    """
    Async client for Tavily API integration.
    
    Provides methods for searching academic sources with
    proper error handling and retry logic.
    """
    
    def __init__(self, config: Config):
        """
        Initialize Tavily client with configuration.
        
        Args:
            config: System configuration with API keys
        """
        self.api_key = config.tavily_api_key
        self.base_url = "https://api.tavily.com"
        self.search_depth = config.tavily_search_depth
        self.include_domains = config.tavily_include_domains
        self.max_results = config.tavily_max_results
        self.timeout = config.request_timeout
        self.max_retries = config.max_retries
        
        # Create session with timeout
        self.timeout_config = aiohttp.ClientTimeout(total=self.timeout)
        
        # Rate limiting configuration
        self.rate_limit_calls = 60  # Max calls per minute (adjust based on API limits)
        self.rate_limit_window = 60  # Window in seconds
        self._request_times: deque[datetime] = deque(maxlen=self.rate_limit_calls)
        self._rate_limit_lock = asyncio.Lock()
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Create SSL context that doesn't verify certificates (for development)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout_config,
            connector=connector
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.session.close()
        
    async def _check_rate_limit(self):
        """
        Check and enforce rate limiting.
        
        This method ensures we don't exceed the API rate limit by
        tracking request times and delaying if necessary.
        """
        async with self._rate_limit_lock:
            now = datetime.now()
            
            # Remove old requests outside the window
            cutoff_time = now - timedelta(seconds=self.rate_limit_window)
            while self._request_times and self._request_times[0] < cutoff_time:
                self._request_times.popleft()
            
            # Check if we're at the limit
            if len(self._request_times) >= self.rate_limit_calls:
                # Calculate how long to wait
                oldest_request = self._request_times[0]
                wait_time = (oldest_request + timedelta(seconds=self.rate_limit_window) - now).total_seconds()
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                    
                    # Remove the oldest request after waiting
                    self._request_times.popleft()
            
            # Record this request
            self._request_times.append(now)
        
    @backoff.on_exception(
        backoff.expo,
        (TavilyAPIError, TavilyTimeoutError),  # Retry on our custom exceptions
        max_tries=3,
        max_time=60,
        giveup=lambda e: isinstance(e, (TavilyAuthError, TavilyRateLimitError))
    )
    async def search(self, query: str) -> TavilySearchResponse:
        """
        Search for academic sources using Tavily API.
        
        Args:
            query: Search query string
            
        Returns:
            TavilySearchResponse containing search results
            
        Raises:
            TavilyAuthError: On authentication failure
            TavilyRateLimitError: On rate limit exceeded
            TavilyTimeoutError: On timeout
            TavilyAPIError: On other API errors
        """
        logger.info(f"Searching Tavily for: {query}")
        
        # Check rate limit before making request
        await self._check_rate_limit()
        
        # Prepare request payload
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": self.search_depth,
            "max_results": self.max_results,
            "include_answer": True,
            "include_raw_content": False,
            "include_images": False,
        }
        
        # Add domain filtering if configured
        if self.include_domains:
            payload["include_domains"] = self.include_domains
            
        try:
            # Make API request
            async with self.session.post(
                f"{self.base_url}/search",
                json=payload
            ) as response:
                # Check response status
                response.raise_for_status()
                
                # Parse JSON response
                data = await response.json()
                
                # Log results
                results_count = len(data.get("results", []))
                logger.info(f"Tavily returned {results_count} results")
                
                # Process and enhance results
                return self._process_results(data, query)
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"Tavily API error: {e.status} - {e.message}")
            
            # Handle specific error codes
            if e.status == 401:
                raise TavilyAuthError("Invalid Tavily API key") from e
            elif e.status == 429:
                raise TavilyRateLimitError("Tavily API rate limit exceeded") from e
            else:
                raise TavilyAPIError(f"API request failed with status {e.status}") from e
                
        except asyncio.TimeoutError as e:
            logger.error(f"Tavily API timeout after {self.timeout}s")
            raise TavilyTimeoutError(f"Request timed out after {self.timeout}s") from e
            
        except Exception as e:
            logger.error(f"Unexpected error calling Tavily API: {e}")
            raise TavilyAPIError(f"Unexpected error: {str(e)}") from e
            
    def _process_results(self, data: Dict[str, Any], query: str) -> TavilySearchResponse:
        """
        Process and enhance Tavily search results.
        
        Args:
            data: Raw response from Tavily
            query: Original search query
            
        Returns:
            TavilySearchResponse with processed results
        """
        # Extract raw results
        raw_results = data.get("results", [])
        
        # Convert to Pydantic models with enhanced data
        processed_results = []
        for result in raw_results:
            # Calculate credibility score
            credibility = self._calculate_credibility(result)
            
            # Create TavilySearchResult model
            search_result = TavilySearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=result.get("score"),
                credibility_score=credibility,
                domain=self._extract_domain(result.get("url", "")),
                processed_at=datetime.now()
            )
            processed_results.append(search_result)
            
        # Sort by credibility score
        processed_results.sort(key=lambda x: x.credibility_score or 0, reverse=True)
        
        # Create processing metadata
        processing_metadata = {
            "total_results": len(processed_results),
            "academic_results": len([r for r in processed_results if (r.credibility_score or 0) >= 0.7]),
            "search_depth": self.search_depth,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create and return response model
        return TavilySearchResponse(
            query=query,
            results=processed_results,
            answer=data.get("answer"),
            processing_metadata=processing_metadata
        )
        
    def _calculate_credibility(self, result: Dict[str, Any]) -> float:
        """
        Calculate credibility score for a search result.
        
        Args:
            result: Single search result
            
        Returns:
            Credibility score between 0 and 1
        """
        score = 0.5  # Base score
        
        url = result.get("url", "").lower()
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()
        
        # Domain scoring
        if ".edu" in url:
            score += 0.3
        elif ".gov" in url:
            score += 0.25
        elif ".org" in url:
            score += 0.15
        elif "journal" in url or "pubmed" in url:
            score += 0.2
            
        # Content indicators
        academic_keywords = [
            "study", "research", "journal", "peer-reviewed",
            "publication", "findings", "methodology", "results",
            "conclusion", "abstract", "doi", "citation"
        ]
        
        keyword_count = sum(1 for keyword in academic_keywords if keyword in content)
        score += min(keyword_count * 0.02, 0.2)  # Max 0.2 bonus
        
        # Title indicators
        if any(word in title for word in ["study", "research", "analysis", "journal"]):
            score += 0.1
            
        # Ensure score is between 0 and 1
        return min(max(score, 0.0), 1.0)
        
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain extension from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain extension (e.g., ".edu")
        """
        try:
            # Simple domain extraction
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain_parts = parsed.netloc.split('.')
            
            if len(domain_parts) >= 2:
                return f".{domain_parts[-1]}"
            return ".com"  # Default
            
        except Exception:
            return ".com"  # Default on error


# Convenience function for use in agents
async def search_academic_sources(query: str, config: Config) -> TavilySearchResponse:
    """
    Search for academic sources using Tavily API.
    
    This is a convenience function that handles client lifecycle
    and is easily callable from PydanticAI agents.
    
    Args:
        query: Search query
        config: System configuration
        
    Returns:
        TavilySearchResponse with academic search results
    """
    async with TavilyClient(config) as client:
        return await client.search(query)


# Utility functions for content processing
def extract_key_statistics(text: str) -> List[str]:
    """
    Extract statistical information from text.
    
    Args:
        text: Source text to analyze
        
    Returns:
        List of extracted statistics
    """
    import re
    
    statistics = []
    
    # Pattern for percentages
    percent_pattern = r'\b\d+(?:\.\d+)?%'
    percentages = re.findall(percent_pattern, text)
    statistics.extend(percentages)
    
    # Pattern for numerical data with context
    number_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)\s+(\w+)'
    numbers = re.findall(number_pattern, text)
    
    for number, unit in numbers:
        if unit.lower() in ['percent', 'people', 'patients', 'subjects', 'participants']:
            statistics.append(f"{number} {unit}")
            
    # Remove duplicates while preserving order
    seen = set()
    unique_stats = []
    for stat in statistics:
        if stat not in seen:
            seen.add(stat)
            unique_stats.append(stat)
            
    return unique_stats[:10]  # Return top 10 statistics


def calculate_reading_time(word_count: int) -> int:
    """
    Calculate estimated reading time.
    
    Args:
        word_count: Number of words in content
        
    Returns:
        Reading time in minutes
    """
    # Average reading speed is 200-250 words per minute
    # We'll use 225 as a middle ground
    minutes = word_count / 225
    
    # Round up to nearest minute, minimum 1 minute
    return max(1, int(minutes + 0.5))


def clean_text_for_seo(text: str) -> str:
    """
    Clean text for SEO optimization.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text suitable for SEO
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters that might break meta tags
    text = text.replace('"', "'")
    text = text.replace('<', '')
    text = text.replace('>', '')
    
    # Ensure proper sentence ending
    if text and not text[-1] in '.!?':
        text += '.'
        
    return text


def generate_slug(title: str) -> str:
    """
    Generate URL-friendly slug from title.
    
    Args:
        title: Article title
        
    Returns:
        URL-friendly slug
    """
    import re
    
    # Convert to lowercase
    slug = title.lower()
    
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    
    # Remove special characters
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


# Export commonly used functions and exceptions
__all__ = [
    # Exceptions
    'TavilyAPIError',
    'TavilyAuthError',
    'TavilyRateLimitError',
    'TavilyTimeoutError',
    # Classes
    'TavilyClient',
    # Models (re-exported for convenience)
    'TavilySearchResult',
    'TavilySearchResponse',
    # Functions
    'search_academic_sources',
    'extract_key_statistics',
    'calculate_reading_time',
    'clean_text_for_seo',
    'generate_slug'
]