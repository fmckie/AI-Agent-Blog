# Tavily API Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [API Reference](#api-reference)
   - [Search Endpoint](#search-endpoint)
   - [Extract Endpoint](#extract-endpoint)
   - [Crawl Endpoint](#crawl-endpoint)
   - [Map Endpoint](#map-endpoint)
3. [Best Practices](#best-practices)
   - [Search Best Practices](#search-best-practices)
   - [Extract Best Practices](#extract-best-practices)
   - [Crawl Best Practices](#crawl-best-practices)

## Introduction

### Base URL
The base URL for all Tavily API requests is:
```
https://api.tavily.com
```

### Authentication
- All Tavily endpoints require API key authentication
- You can [get a free API key](https://app.tavily.com)
- Authentication format: Bearer token in Authorization header

Authentication Example:
```bash
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -d '{"query": "Who is Leo Messi?"}'
```

### Available Endpoints
Tavily offers several key API endpoints:

1. `/search` - Tavily's powerful web search API for executing web search queries
2. `/extract` - Tavily's powerful content extraction API for extracting content from web pages
3. `/crawl` - Tavily's intelligent sitegraph navigation and extraction tool
4. `/map` - Website traversal tool for generating comprehensive site maps

## API Reference

### Search Endpoint

**Endpoint Details:**
- Method: `POST`
- Path: `/search`
- Base URL: `https://api.tavily.com/`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query string (max 400 characters recommended) |
| `auto_parameters` | boolean | No | Automatically configure search settings |
| `topic` | string | No | Choose between "general" or "news" |
| `search_depth` | string | No | "basic" (1 credit) or "advanced" (2 credits) |
| `max_results` | integer | No | 0-20 results (default 5) |
| `include_answer` | boolean | No | Generate an AI-powered answer |
| `include_raw_content` | boolean | No | Return full webpage content |
| `include_images` | boolean | No | Perform image search |
| `time_range` | string | No | Filter results by date |
| `include_domains` | array | No | Include specific domains |
| `exclude_domains` | array | No | Exclude specific domains |

**Example Python SDK Usage:**
```python
from tavily import TavilyClient

tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")
response = tavily_client.search("Who is Leo Messi?")
```

**Response Structure:**
```json
{
  "query": "original search query",
  "answer": "AI-generated response (optional)",
  "results": [
    {
      "title": "Page title",
      "url": "https://example.com",
      "content": "Content snippet",
      "relevance_score": 0.95
    }
  ],
  "response_time": 1.23
}
```

### Extract Endpoint

**Endpoint Details:**
- Method: `POST`
- Path: `/extract`
- Purpose: Extract web page content from one or more specified URLs

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `urls` | string/array | Yes | Single URL or array of URLs to extract |
| `include_images` | boolean | No | Include image URLs |
| `include_favicon` | boolean | No | Include favicon |
| `extract_depth` | string | No | "basic" (1 credit/5 URLs) or "advanced" (2 credits/5 URLs) |
| `format` | string | No | "markdown" (default) or "text" |

**Example Python SDK Usage:**
```python
from tavily import TavilyClient

tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")
response = tavily_client.extract("https://en.wikipedia.org/wiki/Artificial_intelligence")
```

**Response Structure:**
```json
{
  "results": [
    {
      "url": "https://example.com",
      "content": "Extracted content in requested format"
    }
  ],
  "failed_results": [],
  "response_time": 2.34
}
```

**Response Codes:**
- 200: Successful extraction
- 400: Bad Request
- 401: Unauthorized (check API key)
- 429: Rate limit exceeded
- 432: Plan limit exceeded
- 500: Server error

### Crawl Endpoint (BETA)

**Endpoint Details:**
- Name: Tavily Crawl (BETA)
- Description: Graph-based website traversal tool with parallel exploration and intelligent discovery

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Starting URL to crawl |
| `max_depth` | integer | No | Maximum crawl depth (default 1) |
| `max_breadth` | integer | No | Maximum links per page (default 20) |
| `limit` | integer | No | Total links to process (default 50) |
| `instructions` | string | No | Natural language guidance for crawler |
| `select_paths` | array | No | Regex patterns for URL path selection |
| `exclude_paths` | array | No | Regex patterns to exclude URLs |
| `allow_external` | boolean | No | Whether to follow external domain links |
| `extract_depth` | string | No | "basic" or "advanced" extraction |
| `format` | string | No | "markdown" or "text" |

**Example Python SDK Usage:**
```python
from tavily import TavilyClient

tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")
response = tavily_client.crawl("https://docs.tavily.com", 
                                instructions="Find all pages on the Python SDK")
```

**Pricing:**
- Basic mapping: 1 API credit per 10 pages
- Instructed mapping: 2 API credits per 10 pages

### Map Endpoint

**Endpoint Details:**
- Method: `POST`
- Path: `/map`
- Description: Traverses websites like a graph to generate comprehensive site maps

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Base URL to start mapping |
| `max_depth` | integer | No | How far from base URL to explore (default 1) |
| `max_breadth` | integer | No | Links to follow per page level (default 20) |
| `limit` | integer | No | Total links to process (default 50) |
| `instructions` | string | No | Custom crawler guidance |
| `select_paths` | array | No | URL path regex filters |
| `select_domains` | array | No | Domain regex filters |
| `exclude_paths` | array | No | URL exclusion patterns |
| `exclude_domains` | array | No | Domain exclusion patterns |
| `allow_external` | boolean | No | Permit external domain links |
| `categories` | array | No | URL category filters |

**Example Request:**
```python
from tavily import TavilyClient

tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")
response = tavily_client.map("https://docs.tavily.com")
```

**Example Response:**
```json
{
  "base_url": "docs.tavily.com",
  "results": [
    "https://docs.tavily.com/welcome",
    "https://docs.tavily.com/documentation/api-credits",
    "https://docs.tavily.com/documentation/about"
  ],
  "response_time": 1.23
}
```

**Pricing Note:** Custom instructions increase cost to 2 credits per 10 pages.

## Best Practices

### Search Best Practices

**Query Optimization:**
1. Keep queries under 400 characters
2. Break complex queries into smaller, focused sub-queries
3. Use specific, targeted language

**Request Parameter Strategies:**
- `max_results`: Limit search results (default is 5)
- `search_depth`: Use "advanced" for higher relevance
- `time_range`: Filter results by date
- `topic=news`: Get recent news updates
- `include_domains`/`exclude_domains`: Refine search sources

**Advanced Techniques:**
- Use asynchronous API calls
- Leverage metadata for post-processing
- Apply regex for precise data extraction
- Combine keyword filtering with LLM analysis

**Key Recommendation:** Break your query into smaller, more focused sub-queries and send them as separate requests to improve search precision and relevance.

### Extract Best Practices

**Two Main Extraction Approaches:**

1. **One-Step Extraction**
   - Enable `include_raw_content = true` in search
   - Retrieve search results and content simultaneously
   - Potential drawback: may extract content from irrelevant sources

2. **Two-Step Process (Recommended)**
   - First, use Search API to get URLs
   - Then, use Extract API to fetch content from most relevant sources
   - Benefits:
     - More control over source selection
     - Higher accuracy
     - Advanced extraction capabilities

**Advanced Extraction Recommendations:**
- Use `extract_depth = "advanced"` for:
  - Complex web pages with dynamic content
  - Pages with tables and structured information
  - Achieving higher success rates

**Key Filtering Strategy:**
- Filter URLs by relevance score (e.g., > 0.5)
- Alternative methods:
  - Use re-ranking models
  - Employ LLM for source identification
  - Cluster documents and extract from most relevant cluster

### Crawl Best Practices

**Key Use Cases:**
1. **Deep Content Extraction**
   - Explore deeply nested pages
   - Access paginated or search-only content
   - Use selective path patterns

2. **Performance Optimization**
   - Start with `max_depth: 1`
   - Control breadth with `max_breadth`
   - Set appropriate `limit`

3. **Extraction Strategies**
   - Use `basic` extract_depth for simple content
   - Use `advanced` extract_depth for complex analysis
   - Leverage `select_paths` and `exclude_paths`

**Best Practice Recommendations:**
- Start small and gradually increase crawl complexity
- Be specific with URL patterns
- Optimize resource usage
- Respect site's robots.txt
- Handle errors gracefully
- Monitor API usage and performance

**Example Configuration:**
```json
{
  "url": "example.com",
  "max_depth": 2,
  "max_breadth": 50,
  "select_paths": ["/docs/.*", "/blog/.*"],
  "extract_depth": "advanced"
}
```

**Ideal for:**
- RAG systems
- Semantic search
- Content analysis
- Knowledge base building

## Additional Notes

- SDKs are available for Python and JavaScript
- All endpoints support asynchronous operations
- Rate limits apply based on your subscription plan
- Always handle errors gracefully and implement retry logic
- Monitor your API credit usage to avoid unexpected charges