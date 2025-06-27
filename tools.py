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
from datetime import datetime
import backoff

# Import our modules
from config import Config

# Set up logging
logger = logging.getLogger(__name__)


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
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout_config)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.session.close()
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search for academic sources using Tavily API.
        
        Args:
            query: Search query string
            
        Returns:
            Dict containing search results
            
        Raises:
            aiohttp.ClientError: On API errors
            asyncio.TimeoutError: On timeout
        """
        logger.info(f"Searching Tavily for: {query}")
        
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
                raise ValueError("Invalid Tavily API key")
            elif e.status == 429:
                raise ValueError("Tavily API rate limit exceeded")
            else:
                raise
                
        except asyncio.TimeoutError:
            logger.error(f"Tavily API timeout after {self.timeout}s")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error calling Tavily API: {e}")
            raise
            
    def _process_results(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Process and enhance Tavily search results.
        
        Args:
            data: Raw response from Tavily
            query: Original search query
            
        Returns:
            Processed results with credibility scores
        """
        # Extract results
        results = data.get("results", [])
        
        # Enhance each result with credibility scoring
        for result in results:
            # Calculate credibility score
            result["credibility_score"] = self._calculate_credibility(result)
            
            # Extract domain
            url = result.get("url", "")
            result["domain"] = self._extract_domain(url)
            
            # Add processing timestamp
            result["processed_at"] = datetime.now().isoformat()
            
        # Sort by credibility score
        results.sort(key=lambda x: x["credibility_score"], reverse=True)
        
        # Add metadata
        data["query"] = query
        data["processing_metadata"] = {
            "total_results": len(results),
            "academic_results": len([r for r in results if r["credibility_score"] >= 0.7]),
            "search_depth": self.search_depth,
            "timestamp": datetime.now().isoformat()
        }
        
        return data
        
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
async def search_academic_sources(query: str, config: Config) -> Dict[str, Any]:
    """
    Search for academic sources using Tavily API.
    
    This is a convenience function that handles client lifecycle
    and is easily callable from PydanticAI agents.
    
    Args:
        query: Search query
        config: System configuration
        
    Returns:
        Search results with credibility scores
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


# Export commonly used functions
__all__ = [
    'TavilyClient',
    'search_academic_sources',
    'extract_key_statistics',
    'calculate_reading_time',
    'clean_text_for_seo',
    'generate_slug'
]