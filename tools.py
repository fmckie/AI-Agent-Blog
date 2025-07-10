"""
External API integrations and utility tools.

This module provides integrations with external services like Tavily API
and other utility functions used throughout the system.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Import required libraries
import aiohttp
import backoff

# Import our modules
from config import Config
from models import TavilySearchResponse, TavilySearchResult

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
            timeout=self.timeout_config, connector=connector
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
                wait_time = (
                    oldest_request + timedelta(seconds=self.rate_limit_window) - now
                ).total_seconds()

                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached. Waiting {wait_time:.2f} seconds..."
                    )
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
        giveup=lambda e: isinstance(e, (TavilyAuthError, TavilyRateLimitError)),
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

        # Prepare request headers with Bearer token
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Prepare request payload (no API key in body)
        payload = {
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
            if not hasattr(self, "session"):
                raise TavilyAPIError(
                    "Client not initialized. Use as context manager: async with TavilyClient(config) as client:"
                )

            # Get the response context manager with headers
            # This handles both real aiohttp and mocked sessions
            response_cm = self.session.post(
                f"{self.base_url}/search", json=payload, headers=headers
            )

            # If it's a coroutine (from AsyncMock), await it first
            if asyncio.iscoroutine(response_cm):
                # This shouldn't happen in production, but handles test mocks
                response_cm = await response_cm

            async with response_cm as response:
                # Check response status
                # Handle both sync and async mocks
                raise_result = response.raise_for_status()
                if asyncio.iscoroutine(raise_result):
                    await raise_result

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
                raise TavilyAPIError(
                    f"API request failed with status {e.status}"
                ) from e

        except asyncio.TimeoutError as e:
            logger.error(f"Tavily API timeout after {self.timeout}s")
            raise TavilyTimeoutError(f"Request timed out after {self.timeout}s") from e

        except Exception as e:
            logger.error(f"Unexpected error calling Tavily API: {e}")
            raise TavilyAPIError(f"Unexpected error: {str(e)}") from e

    def _process_results(
        self, data: Dict[str, Any], query: str
    ) -> TavilySearchResponse:
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
                processed_at=datetime.now(),
            )
            processed_results.append(search_result)

        # Sort by credibility score
        processed_results.sort(key=lambda x: x.credibility_score or 0, reverse=True)

        # Create processing metadata
        processing_metadata = {
            "total_results": len(processed_results),
            "academic_results": len(
                [r for r in processed_results if (r.credibility_score or 0) >= 0.7]
            ),
            "search_depth": self.search_depth,
            "timestamp": datetime.now().isoformat(),
        }

        # Create and return response model
        return TavilySearchResponse(
            query=query,
            results=processed_results,
            answer=data.get("answer"),
            processing_metadata=processing_metadata,
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
            "study",
            "research",
            "journal",
            "peer-reviewed",
            "publication",
            "findings",
            "methodology",
            "results",
            "conclusion",
            "abstract",
            "doi",
            "citation",
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
            domain_parts = parsed.netloc.split(".")

            if len(domain_parts) >= 2:
                return f".{domain_parts[-1]}"
            return ".com"  # Default

        except Exception:
            return ".com"  # Default on error

    @backoff.on_exception(
        backoff.expo,
        (TavilyAPIError, TavilyTimeoutError),
        max_tries=3,
        max_time=60,
        giveup=lambda e: isinstance(e, (TavilyAuthError, TavilyRateLimitError)),
    )
    async def extract(
        self, urls: List[str], extract_depth: str = "advanced"
    ) -> Dict[str, Any]:
        """
        Extract full content from specific URLs.

        Args:
            urls: List of URLs to extract content from (max 20)
            extract_depth: Extraction depth - "basic" or "advanced"

        Returns:
            Dictionary containing extracted content for each URL

        Raises:
            TavilyAPIError: On API errors
        """
        logger.info(f"Extracting content from {len(urls)} URLs")

        # Validate inputs
        if not urls:
            raise ValueError("URLs list cannot be empty")
        if len(urls) > 20:
            logger.warning(f"Too many URLs ({len(urls)}), limiting to first 20")
            urls = urls[:20]

        # Check rate limit
        await self._check_rate_limit()

        # Prepare request headers with Bearer token
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Prepare request payload (no API key in body)
        payload = {
            "urls": urls,
            "extract_depth": extract_depth,
        }

        try:
            if not hasattr(self, "session"):
                raise TavilyAPIError("Client not initialized. Use as context manager")

            response_cm = self.session.post(
                f"{self.base_url}/extract", json=payload, headers=headers
            )

            if asyncio.iscoroutine(response_cm):
                response_cm = await response_cm

            async with response_cm as response:
                raise_result = response.raise_for_status()
                if asyncio.iscoroutine(raise_result):
                    await raise_result

                data = await response.json()

                # Process extracted results
                extracted_count = len(data.get("results", []))
                logger.info(
                    f"Successfully extracted content from {extracted_count} URLs"
                )

                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"Tavily Extract API error: {e.status}")
            if e.status == 401:
                raise TavilyAuthError("Invalid API key") from e
            elif e.status == 429:
                raise TavilyRateLimitError("Rate limit exceeded") from e
            else:
                raise TavilyAPIError(f"Extract failed: {e.status}") from e

        except Exception as e:
            logger.error(f"Extract error: {e}")
            raise TavilyAPIError(f"Extract failed: {str(e)}") from e

    @backoff.on_exception(
        backoff.expo,
        (TavilyAPIError, TavilyTimeoutError),
        max_tries=3,
        max_time=60,
        giveup=lambda e: isinstance(e, (TavilyAuthError, TavilyRateLimitError)),
    )
    async def crawl(
        self,
        url: str,
        max_depth: int = 2,
        max_breadth: int = 10,
        instructions: Optional[str] = None,
        extract_depth: str = "advanced",
    ) -> Dict[str, Any]:
        """
        Crawl a website to gather comprehensive content.

        Args:
            url: Base URL to crawl
            max_depth: Maximum crawl depth (default 2)
            max_breadth: Maximum pages per level (default 10)
            instructions: Natural language instructions for crawling
            extract_depth: Content extraction depth

        Returns:
            Dictionary containing crawled pages and content

        Raises:
            TavilyAPIError: On API errors
        """
        logger.info(f"Crawling website: {url} (depth={max_depth})")

        # Check rate limit
        await self._check_rate_limit()

        # Prepare request headers with Bearer token
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Prepare request payload (no API key in body)
        payload = {
            "url": url,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "extract_depth": extract_depth,
        }

        # Add optional instructions
        if instructions:
            payload["instructions"] = instructions

        try:
            if not hasattr(self, "session"):
                raise TavilyAPIError("Client not initialized. Use as context manager")

            response_cm = self.session.post(
                f"{self.base_url}/crawl", json=payload, headers=headers
            )

            if asyncio.iscoroutine(response_cm):
                response_cm = await response_cm

            async with response_cm as response:
                raise_result = response.raise_for_status()
                if asyncio.iscoroutine(raise_result):
                    await raise_result

                data = await response.json()

                # Process crawl results
                pages_crawled = len(data.get("results", []))
                logger.info(f"Successfully crawled {pages_crawled} pages")

                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"Tavily Crawl API error: {e.status}")
            if e.status == 401:
                raise TavilyAuthError("Invalid API key") from e
            elif e.status == 429:
                raise TavilyRateLimitError("Rate limit exceeded") from e
            else:
                raise TavilyAPIError(f"Crawl failed: {e.status}") from e

        except Exception as e:
            logger.error(f"Crawl error: {e}")
            raise TavilyAPIError(f"Crawl failed: {str(e)}") from e

    @backoff.on_exception(
        backoff.expo,
        (TavilyAPIError, TavilyTimeoutError),
        max_tries=3,
        max_time=60,
        giveup=lambda e: isinstance(e, (TavilyAuthError, TavilyRateLimitError)),
    )
    async def map(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Map a website structure quickly without full content extraction.

        Args:
            url: Base URL to map
            instructions: Natural language instructions for mapping

        Returns:
            Dictionary containing site structure and links

        Raises:
            TavilyAPIError: On API errors
        """
        logger.info(f"Mapping website structure: {url}")

        # Check rate limit
        await self._check_rate_limit()

        # Prepare request headers with Bearer token
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Prepare request payload (no API key in body)
        payload = {
            "url": url,
        }

        # Add optional instructions
        if instructions:
            payload["instructions"] = instructions

        try:
            if not hasattr(self, "session"):
                raise TavilyAPIError("Client not initialized. Use as context manager")

            response_cm = self.session.post(
                f"{self.base_url}/map", json=payload, headers=headers
            )

            if asyncio.iscoroutine(response_cm):
                response_cm = await response_cm

            async with response_cm as response:
                raise_result = response.raise_for_status()
                if asyncio.iscoroutine(raise_result):
                    await raise_result

                data = await response.json()

                # Process map results - API returns 'results' not 'links'
                results_found = len(data.get("results", []))
                logger.info(f"Found {results_found} URLs in site map")

                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"Tavily Map API error: {e.status}")
            if e.status == 401:
                raise TavilyAuthError("Invalid API key") from e
            elif e.status == 429:
                raise TavilyRateLimitError("Rate limit exceeded") from e
            else:
                raise TavilyAPIError(f"Map failed: {e.status}") from e

        except Exception as e:
            logger.error(f"Map error: {e}")
            raise TavilyAPIError(f"Map failed: {str(e)}") from e


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


async def extract_url_content(
    urls: List[str], config: Config, extract_depth: str = "advanced"
) -> Dict[str, Any]:
    """
    Extract full content from URLs using Tavily API.

    Args:
        urls: List of URLs to extract content from
        config: System configuration
        extract_depth: Extraction depth ("basic" or "advanced")

    Returns:
        Dictionary with extracted content for each URL
    """
    async with TavilyClient(config) as client:
        return await client.extract(urls, extract_depth)


async def crawl_website(
    url: str,
    config: Config,
    max_depth: int = 2,
    instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crawl a website using Tavily API.

    Args:
        url: Base URL to crawl
        config: System configuration
        max_depth: Maximum crawl depth
        instructions: Natural language crawling instructions

    Returns:
        Dictionary with crawled pages and content
    """
    async with TavilyClient(config) as client:
        return await client.crawl(url, max_depth=max_depth, instructions=instructions)


async def map_website(
    url: str, config: Config, instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Map website structure using Tavily API.

    Args:
        url: Base URL to map
        config: System configuration
        instructions: Natural language mapping instructions

    Returns:
        Dictionary with site structure and links
    """
    async with TavilyClient(config) as client:
        return await client.map(url, instructions=instructions)


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

    # Pattern for percentages (including "X percent" format)
    percent_pattern = r"\b\d+(?:\.\d+)?%"
    percentages = re.findall(percent_pattern, text)
    statistics.extend(percentages)

    # Also find "X percent" format and convert to "X%"
    percent_word_pattern = r"\b(\d+(?:\.\d+)?)\s+percent\b"
    percent_words = re.findall(percent_word_pattern, text)
    for pw in percent_words:
        statistics.append(f"{pw}%")

    # Pattern for numerical data with context
    number_pattern = r"(\d+(?:,\d+)*(?:\.\d+)?)\s+(\w+)"
    numbers = re.findall(number_pattern, text)

    for number, unit in numbers:
        if unit.lower() in [
            "people",
            "patients",
            "subjects",
            "participants",
            "users",
            "cases",
        ]:
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

    # Round to nearest minute, minimum 1 minute
    return max(1, round(minutes))


def clean_text_for_seo(text: str) -> str:
    """
    Clean text for SEO optimization.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text suitable for SEO
    """
    # Remove extra whitespace
    text = " ".join(text.split())

    # Remove special characters that might break meta tags
    text = text.replace('"', "'")
    text = text.replace("<", "")
    text = text.replace(">", "")

    # Ensure proper sentence ending
    if text and not text[-1] in ".!?":
        text += "."

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

    # First, collapse multiple spaces to single space
    slug = re.sub(r"\s+", " ", slug)

    # Replace & with a special marker to preserve double hyphen
    slug = slug.replace(" & ", "---AMPERSAND---")

    # Replace spaces with hyphens
    slug = slug.replace(" ", "-")

    # Remove special characters (including our marker text but keeping the hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Replace our marker with double hyphen
    slug = slug.replace("---AMPERSAND---", "--")

    # Remove multiple hyphens (except our intentional double hyphens)
    # This is tricky - we need to preserve exactly 2 hyphens from & but collapse others
    # First collapse 3+ hyphens to 2
    slug = re.sub(r"-{3,}", "--", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug


# Export commonly used functions and exceptions
__all__ = [
    # Exceptions
    "TavilyAPIError",
    "TavilyAuthError",
    "TavilyRateLimitError",
    "TavilyTimeoutError",
    # Classes
    "TavilyClient",
    # Models (re-exported for convenience)
    "TavilySearchResult",
    "TavilySearchResponse",
    # Functions
    "search_academic_sources",
    "extract_url_content",
    "crawl_website",
    "map_website",
    "extract_key_statistics",
    "calculate_reading_time",
    "clean_text_for_seo",
    "generate_slug",
]
