# Performance Tuning Guide

This guide helps you optimize the SEO Content Automation System for maximum performance, efficiency, and cost-effectiveness.

## Table of Contents
- [Overview](#overview)
- [Performance Metrics](#performance-metrics)
- [Optimization Areas](#optimization-areas)
  - [API Performance](#api-performance)
  - [Cache Optimization](#cache-optimization)
  - [Database Tuning](#database-tuning)
  - [Parallel Processing](#parallel-processing)
  - [Memory Management](#memory-management)
- [Configuration Tuning](#configuration-tuning)
- [Monitoring & Diagnostics](#monitoring--diagnostics)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The system's performance depends on several factors:
- API response times (Tavily, OpenAI)
- Cache hit rates
- Database query efficiency
- Network latency
- Resource utilization

Target performance goals:
- Cache hit rate: >70%
- Average response time: <2s for cached, <30s for fresh
- Cost per article: <$0.20
- Memory usage: <500MB per process

## Performance Metrics

### Key Performance Indicators (KPIs)

1. **Response Times**
   - Cache hit response: Target <1s
   - API response: Target <30s
   - End-to-end generation: Target <45s

2. **Cache Efficiency**
   - Hit rate: Target >70%
   - Storage efficiency: <100MB per 1000 entries
   - Retrieval accuracy: >90% relevance

3. **Resource Usage**
   - CPU: <50% average
   - Memory: <500MB per instance
   - Network: <10MB per article

4. **Cost Metrics**
   - API calls per article: Target <5
   - Cost per article: Target <$0.20
   - Monthly savings: Track via metrics

## Optimization Areas

### API Performance

#### 1. Reduce API Calls
```python
# Configure to maximize cache usage
CACHE_SIMILARITY_THRESHOLD=0.75  # Lower for more cache hits
CACHE_TTL_DAYS=14               # Longer TTL for stable content
```

#### 2. Optimize Request Parameters
```python
# Tavily configuration
TAVILY_MAX_RESULTS=10           # Balance quality vs cost
TAVILY_SEARCH_DEPTH=basic       # Use 'advanced' only when needed
TAVILY_INCLUDE_DOMAINS=.edu,.gov,.org  # Focus on quality sources
```

#### 3. Implement Request Batching
```bash
# Use batch processing for multiple keywords
python main.py batch "keyword1" "keyword2" "keyword3" --parallel 3
```

### Cache Optimization

#### 1. Tune Similarity Threshold
```python
# Lower threshold = more cache hits
CACHE_SIMILARITY_THRESHOLD=0.7   # Default: 0.8

# Monitor impact
python main.py cache stats --detailed
```

#### 2. Optimize Cache Size
```python
# Balance storage vs performance
CACHE_MAX_ENTRIES=10000         # Limit total entries
CHUNK_SIZE=1000                 # Optimal chunk size
CHUNK_OVERLAP=200               # Preserve context
```

#### 3. Strategic Cache Warming
```bash
# Pre-populate high-value keywords
python main.py cache warm --from-file trending_keywords.txt

# Schedule regular warming
0 6 * * * python main.py cache warm "evergreen topic"
```

### Database Tuning

#### 1. Connection Pool Optimization
```python
# Supabase connection settings
CONNECTION_POOL_MIN=2           # Minimum idle connections
CONNECTION_POOL_MAX=10          # Maximum connections
CONNECTION_TIMEOUT=30           # Timeout in seconds
```

#### 2. Query Optimization
```sql
-- Ensure indexes exist for vector search
CREATE INDEX idx_embeddings_vector 
ON research_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM research_chunks
WHERE embedding <=> $1 < 0.3
ORDER BY embedding <=> $1
LIMIT 10;
```

#### 3. Maintenance Tasks
```bash
# Regular vacuum for optimal performance
psql -c "VACUUM ANALYZE research_chunks;"

# Monitor table sizes
psql -c "SELECT pg_size_pretty(pg_relation_size('research_chunks'));"
```

### Parallel Processing

#### 1. Optimal Parallel Settings
```python
# CPU-bound tasks (text processing)
PARALLEL_WORKERS = min(cpu_count() - 1, 4)

# I/O-bound tasks (API calls)
PARALLEL_API_CALLS = 3  # Respect rate limits
```

#### 2. Batch Processing Configuration
```bash
# Optimal batch sizes by resource
# High memory system (>16GB)
python main.py batch keywords.txt --parallel 4

# Limited memory (<8GB)
python main.py batch keywords.txt --parallel 2

# Rate-limited APIs
python main.py batch keywords.txt --parallel 1 --continue-on-error
```

### Memory Management

#### 1. Embedding Batch Sizes
```python
# Adjust based on available memory
EMBEDDING_BATCH_SIZE=50         # Default: 100
EMBEDDING_CACHE_SIZE=1000       # In-memory cache limit
```

#### 2. Text Processing Limits
```python
# Prevent memory spikes
MAX_ARTICLE_LENGTH=10000        # Characters
MAX_CHUNK_SIZE=2000            # Per chunk
MAX_SOURCES_PER_KEYWORD=20     # Limit processing
```

## Configuration Tuning

### Development Environment
```env
# .env.development
LOG_LEVEL=DEBUG
CACHE_SIMILARITY_THRESHOLD=0.9
MAX_RETRIES=1
REQUEST_TIMEOUT=60
CONNECTION_POOL_MAX=5
```

### Production Environment
```env
# .env.production
LOG_LEVEL=WARNING
CACHE_SIMILARITY_THRESHOLD=0.75
MAX_RETRIES=3
REQUEST_TIMEOUT=30
CONNECTION_POOL_MAX=20
EMBEDDING_BATCH_SIZE=100
```

### High-Volume Environment
```env
# .env.highvolume
CACHE_TTL_DAYS=30
CACHE_SIMILARITY_THRESHOLD=0.7
CONNECTION_POOL_MIN=5
CONNECTION_POOL_MAX=50
PARALLEL_WORKERS=8
EMBEDDING_BATCH_SIZE=200
```

## Monitoring & Diagnostics

### 1. Real-time Monitoring
```bash
# Monitor cache performance
watch -n 60 'python main.py cache stats'

# Track resource usage
htop -p $(pgrep -f "python main.py")

# Monitor API calls
tail -f logs/api_calls.log | grep "TAVILY\|OPENAI"
```

### 2. Performance Profiling
```python
# Enable profiling
import cProfile
import pstats

# Profile specific operations
cProfile.run('asyncio.run(generate_article("keyword"))', 'profile_stats')

# Analyze results
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(20)
```

### 3. Metrics Collection
```bash
# Export metrics for analysis
python main.py cache metrics --format csv -o daily_metrics.csv

# Set up automated collection
*/15 * * * * python main.py cache metrics --format prometheus >> /var/log/cache_metrics.log
```

## Best Practices

### 1. Cache Management
- **Regular Maintenance**: Clean cache weekly
- **Monitor Hit Rate**: Aim for >70%
- **Warm Strategic Keywords**: Pre-cache high-value topics
- **Adjust Thresholds**: Based on content type

### 2. Resource Optimization
- **Batch Similar Requests**: Group related keywords
- **Use Appropriate Parallelism**: Based on system resources
- **Monitor Rate Limits**: Avoid API throttling
- **Implement Circuit Breakers**: Fail fast on errors

### 3. Cost Optimization
- **Track API Usage**: Monitor costs daily
- **Maximize Cache Usage**: Lower similarity thresholds
- **Use Basic Search**: When advanced isn't needed
- **Batch Process**: During off-peak hours

### 4. System Health
- **Regular Backups**: Export cache periodically
- **Monitor Disk Space**: Cache can grow large
- **Update Dependencies**: Keep libraries current
- **Test Performance**: Regular benchmarking

## Troubleshooting

### High Memory Usage
```bash
# Check memory consumption
ps aux | grep python | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Solutions:
1. Reduce EMBEDDING_BATCH_SIZE
2. Lower CONNECTION_POOL_MAX
3. Implement memory limits
4. Use cache cleanup more frequently
```

### Slow Response Times
```bash
# Diagnose bottlenecks
python main.py generate "test keyword" --verbose

# Common causes:
1. Low cache hit rate
2. Network latency
3. Database connection issues
4. API rate limiting
```

### Low Cache Hit Rate
```bash
# Analyze cache patterns
python main.py cache stats --detailed

# Solutions:
1. Lower CACHE_SIMILARITY_THRESHOLD
2. Increase cache warming
3. Use consistent keywords
4. Extend CACHE_TTL_DAYS
```

### Database Performance Issues
```sql
-- Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC;

-- Solutions:
1. Add missing indexes
2. Increase connection pool
3. Optimize query patterns
4. Regular VACUUM ANALYZE
```

## Performance Benchmarks

### Baseline Performance (Single Keyword)
- Research phase: 15-20s
- Writing phase: 10-15s
- Total time: 25-35s
- Memory usage: 200-300MB
- API cost: $0.15-0.20

### Optimized Performance (With Cache)
- Cache hit: <1s
- Partial cache hit: 5-10s
- Memory usage: 150-200MB
- API cost: $0.00-0.10

### Batch Performance (10 Keywords)
- Sequential: 250-350s
- Parallel (3): 100-150s
- Parallel (5): 70-100s
- Memory usage: 400-600MB
- Average cost: $0.10 per keyword

## Summary

Effective performance tuning requires:
1. **Monitoring**: Regular metrics collection
2. **Analysis**: Identify bottlenecks
3. **Optimization**: Apply targeted improvements
4. **Validation**: Measure impact

Key areas for maximum impact:
- Cache hit rate optimization
- Connection pool tuning
- Batch processing implementation
- API call reduction

Remember: Measure before and after each change to validate improvements.