# Tavily Enhancement Implementation Guide

## Overview

This guide explains how to use the enhanced Tavily capabilities that have been integrated into the SEO Content Automation System. The enhancements provide advanced web research capabilities including content extraction, website crawling, and domain analysis.

## What's New

### 1. **Enhanced TavilyClient** (`tools.py`)
- **extract()**: Extract full content from specific URLs
- **crawl()**: Crawl websites to discover related content
- **map()**: Quickly map website structure

### 2. **Specialized Research Tools** (`research_agent/tools.py`)
- **extract_full_content()**: Get complete article content for deep analysis
- **crawl_domain()**: Comprehensively explore academic websites
- **analyze_domain_structure()**: Understand website organization
- **multi_step_research()**: Automated workflow combining all tools

### 3. **Enhanced Data Models** (`models.py`)
- **ExtractedContent**: Store full article content
- **CrawledPage**: Track discovered pages
- **DomainAnalysis**: Website structure insights
- **EnhancedResearchFindings**: Comprehensive research results

### 4. **Configuration Options** (`config.py`)
- Extract depth and URL limits
- Crawl depth and breadth settings
- Research strategy selection
- Credibility thresholds

## Usage Examples

### Basic Usage: Enhanced Search

```python
from research_agent.agent import create_research_agent, run_research_agent
from config import get_config

# Create agent with enhanced capabilities
config = get_config()
agent = create_research_agent(config)

# Run basic research (uses search + statistics)
findings = await run_research_agent(agent, "artificial intelligence ethics")
```

### Advanced Usage: Multi-Step Research

```python
# The agent now has access to comprehensive research tools
prompt = """
Research 'quantum computing applications' comprehensively:
1. Use search_academic_tool to find top sources
2. Use extract_content_tool to get full papers from .edu domains
3. Use crawl_website_tool on MIT or Stanford domains for latest research
4. Use analyze_website_tool to map research sections
5. Synthesize findings using all available data
"""

result = await agent.run(prompt)
```

### Using Specific Tools

#### Extract Full Content
```python
# In your agent prompt
"""
First search for sources on 'climate change impacts'.
Then extract full content from the top 3 .edu sources using extract_content_tool.
Analyze the complete methodology sections.
"""
```

#### Crawl Academic Domains
```python
# In your agent prompt
"""
Find the best .edu domain about 'renewable energy'.
Use crawl_website_tool with instructions: 
'Find all research papers, studies, and publications about solar panel efficiency'
Summarize the latest findings from crawled pages.
"""
```

#### Analyze Website Structure
```python
# In your agent prompt
"""
Use analyze_website_tool on 'https://ai.stanford.edu' 
with focus_area='machine learning research'.
Identify the most valuable sections for our research.
"""
```

## Configuration

### Environment Variables (.env)

```bash
# Existing
TAVILY_API_KEY=your_api_key
OPENAI_API_KEY=your_openai_key

# New options (optional - defaults are set)
TAVILY_EXTRACT_DEPTH=advanced
TAVILY_CRAWL_MAX_DEPTH=2
RESEARCH_STRATEGY=comprehensive
```

### Programmatic Configuration

```python
from config import Config

config = Config(
    # Enhanced settings
    tavily_extract_depth="advanced",
    tavily_crawl_max_depth=3,
    research_strategy="comprehensive",
    min_credibility_threshold=0.8
)
```

## Research Strategies

### 1. Basic Strategy
- Simple search with statistics extraction
- Suitable for quick research tasks
- Uses: search_academic_tool, extract_statistics_tool

### 2. Standard Strategy (Default)
- Search + selective content extraction
- Balances depth with efficiency
- Uses: search, extract top 3 sources, identify gaps

### 3. Comprehensive Strategy
- Full multi-step research workflow
- Maximum depth and coverage
- Uses: search, extract, crawl, analyze, synthesize

## Best Practices

### 1. Tool Selection
- Start with search for discovery
- Use extract for detailed analysis of known sources
- Use crawl for comprehensive domain exploration
- Use analyze before crawling to optimize efforts

### 2. Performance Optimization
- Extract content from high-credibility sources only
- Limit crawl depth to 2-3 for most cases
- Use focused instructions for crawling
- Cache results using the RAG system

### 3. Quality Assurance
- Verify extracted content matches search snippets
- Cross-reference findings across multiple tools
- Check publication dates in full content
- Validate statistics in original context

## API Rate Limits

The enhanced client includes intelligent rate limiting:
- 60 requests per minute (adjustable)
- Automatic retry with exponential backoff
- Graceful handling of 429 errors

## Error Handling

All new methods include comprehensive error handling:
- `TavilyAuthError`: Invalid API key
- `TavilyRateLimitError`: Rate limit exceeded
- `TavilyTimeoutError`: Request timeout
- `TavilyAPIError`: General API errors

## Example Workflow

Here's a complete example using all enhancements:

```python
async def comprehensive_research(keyword: str):
    config = get_config()
    agent = create_research_agent(config)
    
    prompt = f"""
    Conduct comprehensive research on '{keyword}':
    
    1. Start with search_academic_tool to find relevant sources
    2. Identify the top 3 .edu sources with credibility > 0.8
    3. Use extract_content_tool to get full content from these sources
    4. Find the most authoritative .edu domain from results
    5. Use analyze_website_tool to map its research sections
    6. Use crawl_website_tool on research sections with instructions:
       'Find recent studies, papers, and findings about {keyword}'
    7. Synthesize all findings into a comprehensive report
    8. Include methodology comparisons from full content
    9. Note any conflicting findings between sources
    10. Identify specific research gaps from all data
    """
    
    result = await agent.run(prompt)
    return result.data  # Returns ResearchFindings or EnhancedResearchFindings
```

## Monitoring and Debugging

### Logging
Enhanced logging is included for all operations:
```python
import logging
logging.getLogger("research_agent.tools").setLevel(logging.DEBUG)
```

### Tool Usage Tracking
The EnhancedResearchFindings model tracks which tools were used:
```python
findings = await run_research_agent(agent, "topic")
print(f"Tools used: {findings.tools_used}")
print(f"Research depth: {findings.research_depth}")
print(f"Confidence score: {findings.confidence_score}")
```

## Migration Guide

### Updating Existing Code
1. No breaking changes - existing code continues to work
2. To use enhancements, update agent prompts to mention new tools
3. Consider using EnhancedResearchFindings for richer output
4. Update configuration for optimal performance

### Gradual Adoption
1. Start by adding extract_content_tool to existing workflows
2. Test crawling on known good domains
3. Implement comprehensive research for high-value topics
4. Monitor API usage and adjust rate limits

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - Reduce concurrent requests
   - Increase rate limit window in config
   - Use caching more aggressively

2. **Timeout Errors**
   - Increase timeout in config
   - Reduce crawl depth
   - Use more specific crawl instructions

3. **Memory Issues with Large Extractions**
   - Process content in chunks
   - Limit number of simultaneous extractions
   - Use basic extraction depth for large sets

## Future Enhancements

Planned improvements include:
- Parallel extraction and crawling
- Smart crawl path optimization
- Automatic source quality scoring
- Integration with citation networks
- Real-time research monitoring

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify API key permissions
3. Test with simple examples first
4. Review rate limit settings

What questions do you have about using these new capabilities, Finn?