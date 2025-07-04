# Research Cache Table Explanation

## Purpose
The `research_cache` table implements an intelligent caching layer for Tavily API responses, reducing API costs, improving response times, and enabling analytics on search patterns.

## Architecture Overview
This table provides:
- Exact-match caching for repeated searches
- TTL-based expiration management
- Access pattern tracking
- Cache performance analytics
- Automatic cleanup mechanisms

## Key Concepts

### 1. Table Structure

#### Core Cache Fields
```sql
keyword TEXT NOT NULL
tavily_response JSONB NOT NULL
response_hash TEXT NOT NULL
```
- **keyword**: Exact search term (case-sensitive for exact matches)
- **tavily_response**: Complete API response preserved
- **response_hash**: MD5 hash prevents storing duplicates

#### Time Management
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
expires_at TIMESTAMP WITH TIME ZONE NOT NULL
```
- **Three-tier timing**: Creation, access, and expiration
- **TTL enforcement**: Automatic expiration handling
- **Access tracking**: Identifies hot cache entries

#### Analytics Fields
```sql
access_count INTEGER DEFAULT 1
total_results INTEGER NOT NULL DEFAULT 0
academic_results INTEGER NOT NULL DEFAULT 0
```
- **access_count**: Cache hit frequency
- **result counts**: Quality metrics for analytics
- **Performance insights**: Identify valuable searches

### 2. Caching Strategy

#### Exact Match Approach
- **Why exact**: Ensures consistent results
- **Trade-off**: Less flexible than semantic matching
- **Complement**: Works alongside vector search

#### TTL Management
```sql
p_ttl_hours INTEGER DEFAULT 168  -- 7 days default
```
- **Default**: 7 days for most research
- **Maximum**: 30 days enforced by trigger
- **Rationale**: Balance freshness vs. efficiency

#### Deduplication
```sql
CONSTRAINT unique_keyword_response UNIQUE (keyword, response_hash)
```
- **Prevents**: Storing identical responses
- **Handles**: API returning same results
- **Efficiency**: Saves storage space

### 3. Smart Functions

#### Cache Retrieval
```sql
CREATE FUNCTION get_cached_research
```
**Features**:
- Automatic access count increment
- Last accessed timestamp update
- Expiration checking
- Optional max age parameter

**Usage pattern**:
```sql
-- Get cache if less than 24 hours old
SELECT * FROM get_cached_research('diabetes treatment', 24);
```

#### Cache Storage
```sql
CREATE FUNCTION store_research_cache
```
**Smart behaviors**:
- Calculates response hash automatically
- Extracts quality metrics
- Handles duplicates gracefully
- Returns whether entry was new

#### Cache Statistics
```sql
CREATE FUNCTION get_cache_statistics
```
**Provides insights on**:
- Total vs. active entries
- Most accessed keywords
- Cache hit rates
- Storage utilization

### 4. Performance Optimization

#### Strategic Indexes
```sql
-- Primary lookup
CREATE INDEX idx_research_cache_keyword

-- Expiration management
CREATE INDEX idx_research_cache_expires_at

-- Hot entry identification
CREATE INDEX idx_research_cache_access_count DESC

-- Active entries only
CREATE INDEX idx_research_cache_active ... WHERE expires_at > NOW()
```

#### Partial Index Strategy
- **Active entries index**: Skips expired rows
- **Performance boost**: Smaller index to search
- **Automatic**: Database maintains it

### 5. Cache Management

#### Cleanup Function
```sql
CREATE FUNCTION cleanup_expired_research_cache
```
- **Retention period**: Keep expired data for analytics
- **Space reclamation**: Reports freed space
- **Schedule**: Run daily via cron

#### Cache Warming
```sql
CREATE FUNCTION warm_cache_for_keyword
```
- **Pre-populate**: Common searches
- **Variations**: Check multiple forms
- **Efficiency**: Batch API calls

## Decision Rationale

### Why Exact Match Cache?
1. **Consistency**: Same keyword = same results
2. **Simplicity**: No fuzzy matching complexity
3. **Performance**: O(1) lookup with index
4. **Complement**: Vector search handles similarity

### Why JSONB for Responses?
1. **Flexibility**: API response structure may change
2. **Queryability**: Can extract specific fields
3. **Compression**: PostgreSQL compresses JSONB
4. **Native support**: No serialization needed

### Why Track Access Patterns?
1. **Optimization**: Identify hot keywords
2. **Analytics**: Understand user behavior
3. **Cleanup**: Remove unused entries
4. **Cost analysis**: Calculate cache value

## Learning Path

### Caching Fundamentals
1. **Cache hit**: Found in cache, no API call
2. **Cache miss**: Not found, must call API
3. **Cache invalidation**: When to refresh data
4. **TTL strategy**: Balancing freshness vs. efficiency

### PostgreSQL Features Used
1. **JSONB operations**: Storing and querying JSON
2. **ON CONFLICT**: Upsert pattern
3. **Partial indexes**: Conditional indexing
4. **Triggers**: Automatic validation

## Real-World Applications

### Similar Systems
1. **Redis**: In-memory caching with TTL
2. **CloudFlare**: CDN with edge caching
3. **Varnish**: HTTP accelerator
4. **API Gateway caches**: AWS, Azure, Google Cloud

### Cache Patterns
- **Cache-aside**: Check cache, then source
- **Write-through**: Update cache on writes
- **TTL-based**: Automatic expiration
- **LRU eviction**: Remove least recently used

## Common Pitfalls

1. **Case sensitivity**: "Diabetes" ≠ "diabetes"
2. **Stale data**: Too long TTL
3. **Cache stampede**: Many misses at once
4. **Storage bloat**: Not cleaning expired entries

## Best Practices Demonstrated

1. **Defensive validation**: Trigger checks data quality
2. **Graceful degradation**: Return expired if needed
3. **Analytics built-in**: Track usage patterns
4. **Maintenance tools**: Cleanup functions included

## Query Examples

### Check Cache Before API Call
```sql
-- In your application code
SELECT * FROM get_cached_research('ketogenic diet benefits');
-- If empty, call Tavily API
-- Then store the result
```

### Store API Response
```sql
SELECT * FROM store_research_cache(
    'ketogenic diet benefits',
    '{"results": [...]}',  -- Tavily response
    168,  -- 7 days TTL
    '{"api_version": "v1", "processing_time": 0.234}'
);
```

### Monitor Cache Performance
```sql
SELECT * FROM get_cache_statistics();
-- Shows hit rates, popular keywords, storage size
```

### Pre-warm Cache
```sql
SELECT * FROM warm_cache_for_keyword(
    'diabetes',
    ARRAY['diabetes treatment', 'diabetes symptoms', 'diabetes diet']
);
```

## Advanced Concepts

### Cache Invalidation Strategies
1. **Time-based**: Our current approach (TTL)
2. **Event-based**: Invalidate on data change
3. **Manual**: Admin can force refresh
4. **Hybrid**: Combine multiple strategies

### Performance Metrics
- **Hit rate**: (hits / (hits + misses)) * 100
- **Miss penalty**: Time saved by cache hit
- **Storage efficiency**: Value per MB stored
- **Cost savings**: API calls avoided * cost per call

What questions do you have about caching strategies, Finn?
Would you like me to explain cache invalidation in more detail?
Try this exercise: Calculate the cost savings if our cache has a 70% hit rate with 1000 daily searches at $0.01 per API call.