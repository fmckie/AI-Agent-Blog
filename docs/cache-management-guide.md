# Cache Management User Guide

This comprehensive guide explains how to use the RAG (Research Augmented Generation) cache system to optimize your SEO content generation workflow.

## Table of Contents
- [Overview](#overview)
- [Benefits](#benefits)
- [Cache Commands](#cache-commands)
  - [Search Cache](#search-cache)
  - [View Statistics](#view-statistics)
  - [Clear Cache](#clear-cache)
  - [Warm Cache](#warm-cache)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The RAG cache system intelligently stores research findings to reduce API costs and improve response times. It uses a three-tier approach:

1. **Exact Match**: Returns identical cached results for repeated queries
2. **Semantic Search**: Finds similar research using vector embeddings
3. **Fresh API Call**: Fetches new data only when necessary

## Benefits

- **Cost Reduction**: Save 40-60% on API costs
- **Faster Response**: <1 second for cached queries (vs 10-30 seconds for API calls)
- **Better Consistency**: Reuse high-quality research across related topics
- **Smart Deduplication**: Avoid storing duplicate information

## Cache Commands

### Search Cache

Find cached research similar to your query using semantic search.

#### Basic Search
```bash
python main.py cache search "blood sugar management"
```

#### Search with More Results
```bash
# Show top 20 results instead of default 10
python main.py cache search "insulin resistance" --limit 20
```

#### Adjust Similarity Threshold
```bash
# Stricter matching (0.9 instead of default 0.7)
python main.py cache search "diabetes" --threshold 0.9

# Looser matching for broader results
python main.py cache search "health" --threshold 0.5
```

#### Understanding Search Results
Each result shows:
- **Similarity Score**: 0.0-1.0 (higher = more similar)
- **Keyword**: Original search term used
- **Age**: How old the cached entry is
- **Sources**: Number of academic sources found
- **Preview**: First few lines of the research

Example output:
```
🔍 Searching cache for: "blood sugar control"

Found 3 similar cached entries:

1. [0.92] "blood sugar management" (2 days old)
   Sources: 5 academic papers
   Preview: Research on glycemic control strategies...

2. [0.85] "glucose regulation" (5 days old)
   Sources: 4 academic papers
   Preview: Studies on insulin sensitivity...

3. [0.78] "diabetes management" (1 week old)
   Sources: 6 academic papers
   Preview: Comprehensive diabetes care approaches...
```

### View Statistics

Monitor cache performance and usage metrics.

#### Basic Statistics
```bash
python main.py cache stats
```

#### Detailed Statistics
```bash
python main.py cache stats --detailed
```

#### Example Output
```
📊 Cache Statistics

Total cached entries: 156
Unique keywords: 42
Storage used: 12.45 MB
Average chunk size: 856 chars
Oldest entry: 2025-01-01 10:30:00
Newest entry: 2025-01-06 14:22:15

🎯 Cache Performance (Current Session):
Total requests: 45
Cache hits: 31 (Exact: 12, Semantic: 19)
Cache misses: 14
Hit rate: 68.9%
Avg response time: 0.245s
Estimated savings: $1.24

Detailed Breakdown:

Top 10 Cached Keywords:
  • diabetes management: 15 chunks
  • blood sugar control: 12 chunks
  • insulin resistance: 9 chunks
  • ketogenic diet: 8 chunks
  • intermittent fasting: 7 chunks
```

### Export Metrics

Export detailed metrics for monitoring and analysis.

#### Export as JSON
```bash
# To stdout
python main.py cache metrics

# To file
python main.py cache metrics -o metrics.json
```

#### Export as CSV
```bash
# For spreadsheet analysis
python main.py cache metrics --format csv -o cache_metrics.csv
```

#### Export for Prometheus
```bash
# For monitoring systems
python main.py cache metrics --format prometheus

# Example output:
# HELP cache_storage_entries Total number of cache entries
# TYPE cache_storage_entries gauge
cache_storage_entries 156
# HELP cache_hit_rate Cache hit rate ratio
# TYPE cache_hit_rate gauge
cache_hit_rate 0.689
```

#### Automated Monitoring
```bash
# Export metrics every hour for monitoring
while true; do
    python main.py cache metrics --format prometheus > /var/lib/prometheus/cache_metrics.prom
    sleep 3600
done
```

### Clear Cache

Remove old or unwanted cache entries to maintain optimal performance.

#### Clear by Age
```bash
# Remove entries older than 30 days
python main.py cache clear --older-than 30

# Preview what would be cleared (dry run)
python main.py cache clear --older-than 7 --dry-run
```

#### Clear by Keyword
```bash
# Remove all entries for specific keyword
python main.py cache clear --keyword "outdated topic"

# Clear entries matching pattern
python main.py cache clear --keyword-pattern "test*"
```

#### Clear by Size
```bash
# Keep only the 100 most recent entries
python main.py cache clear --keep-recent 100

# Clear to reduce cache to 10MB
python main.py cache clear --max-size 10
```

#### Clear All
```bash
# Clear entire cache (requires confirmation)
python main.py cache clear --all

# Force clear without confirmation
python main.py cache clear --all --force
```

### Warm Cache

Pre-populate the cache with anticipated searches to improve future performance.

#### Single Keyword
```bash
# Research and cache without generating article
python main.py cache warm "keto diet benefits"
```

#### Multiple Keywords
```bash
# Warm cache with multiple related topics
python main.py cache warm "diabetes" "insulin" "blood sugar" "glucose"
```

#### From File
```bash
# Read keywords from file (one per line)
python main.py cache warm --from-file keywords.txt
```

#### Batch Processing
```bash
# Process keywords in parallel for speed
python main.py cache warm --from-file keywords.txt --parallel 5
```

## Best Practices

### 1. Regular Maintenance
- Clear cache weekly: `python main.py cache clear --older-than 7`
- Monitor hit rate: `python main.py cache stats`
- Aim for >50% cache hit rate

### 2. Strategic Warming
- Warm cache before busy periods
- Pre-cache trending topics
- Use keyword variations for better coverage

### 3. Optimal Thresholds
- Default (0.7): Good for most use cases
- Higher (0.8-0.9): When accuracy is critical
- Lower (0.5-0.6): For exploratory research

### 4. Keyword Selection
- Use consistent terminology
- Include both specific and general terms
- Consider synonyms and related concepts

## Troubleshooting

### Low Cache Hit Rate
**Problem**: Cache hit rate below 30%

**Solutions**:
1. Review keyword consistency
2. Lower similarity threshold
3. Warm cache with common topics
4. Check if cache is too old

### Slow Search Performance
**Problem**: Cache searches taking >5 seconds

**Solutions**:
1. Clear old entries: `cache clear --older-than 30`
2. Reduce cache size
3. Check database connection
4. Verify index health

### Irrelevant Results
**Problem**: Search returns unrelated content

**Solutions**:
1. Increase similarity threshold
2. Use more specific keywords
3. Clear and rebuild cache
4. Check embedding model consistency

## Advanced Usage

### Analyze Cache Patterns
```bash
# Export cache metadata for analysis
python main.py cache export --format csv --output cache_analysis.csv

# Generate usage report
python main.py cache report --period 30 --output cache_report.html
```

### Integrate with Workflows
```bash
# Check cache before generating
if python main.py cache search "topic" --threshold 0.8 --quiet; then
    echo "Using cached research"
else
    python main.py generate "topic"
fi
```

### Monitor Performance
```bash
# Set up monitoring script
#!/bin/bash
while true; do
    python main.py cache stats --json >> cache_metrics.jsonl
    sleep 3600  # Check every hour
done
```

### Optimize for Specific Domains
```bash
# Healthcare content
python main.py cache warm --from-file healthcare_terms.txt --domain medical

# Technology content  
python main.py cache warm --from-file tech_terms.txt --domain technology
```

## Configuration

Add these settings to your `.env` file for customization:

```env
# Cache Behavior
CACHE_SIMILARITY_THRESHOLD=0.8    # Default similarity threshold
CACHE_TTL_DAYS=7                  # How long to keep cache entries
CACHE_MAX_SIZE_MB=1000           # Maximum cache size

# Performance
CACHE_SEARCH_TIMEOUT=5           # Search timeout in seconds
CACHE_BATCH_SIZE=10              # Batch size for warming

# Features
CACHE_ENABLE_ANALYTICS=true      # Track detailed metrics
CACHE_COMPRESSION=true           # Compress stored data
```

## Examples by Use Case

### Content Calendar Planning
```bash
# Warm cache for next month's topics
python main.py cache warm --from-file january_topics.txt

# Check what's already available
python main.py cache search "new year fitness" --limit 50
```

### Topic Research
```bash
# Explore related topics
python main.py cache search "intermittent fasting" --threshold 0.6 --limit 30
```

### Cost Optimization
```bash
# Find most expensive queries
python main.py cache stats --show-costs

# Pre-cache expensive topics
python main.py cache warm "complex medical procedures" --priority high
```

### Quality Assurance
```bash
# Verify cache quality
python main.py cache validate --check-embeddings --fix-issues
```

## Summary

The cache management system is a powerful tool for optimizing your content generation workflow. By understanding and utilizing these commands effectively, you can:

- Reduce API costs significantly
- Improve response times
- Maintain consistency across related content
- Build a valuable knowledge base over time

Remember to monitor your cache statistics regularly and adjust your strategy based on usage patterns. The cache is not just a performance optimization—it's a strategic asset for your content operation.

For more help, run:
```bash
python main.py cache --help
python main.py cache [command] --help
```