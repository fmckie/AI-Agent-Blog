# RPC Functions Explanation

## Purpose
The `rpc_functions.sql` file provides a secure API layer for database access, replacing the dangerous `execute_custom_sql` approach with specific, safe functions that AI agents and application code can call.

## Architecture Overview
These Remote Procedure Call (RPC) functions:
- Provide controlled access to database operations
- Are transaction pooler compatible
- Include built-in security and validation
- Return structured, predictable results

## Key Concepts

### 1. Security Model

#### SECURITY DEFINER
```sql
CREATE FUNCTION ... SECURITY DEFINER
```
- Functions run with owner's privileges
- Allows controlled access to tables
- Users don't need direct table permissions

#### Permission Control
```sql
REVOKE EXECUTE ON FUNCTION ... FROM PUBLIC, anon
```
- Only service role can execute
- Prevents unauthorized access
- Supabase automatically grants to service role

### 2. Function Categories

#### Cache Management
```sql
rpc_check_cache_exists
rpc_get_cached_research
rpc_get_cache_metrics
```
- Quick cache lookups
- Automatic access tracking
- Performance monitoring

#### Research Search
```sql
rpc_search_research
rpc_find_similar_research
```
- Paginated results
- Credibility filtering
- Semantic similarity search

#### Analytics
```sql
rpc_get_keyword_stats
rpc_get_article_summary
rpc_get_top_sources
```
- Aggregated insights
- Performance metrics
- Quality tracking

### 3. Design Principles

#### Pooler Compatibility
All functions are designed to work with connection pooling:
- No session state dependencies
- Single transaction execution
- No prepared statements
- No temporary tables

#### Predictable Returns
```sql
RETURNS TABLE (
    field1 TYPE,
    field2 TYPE,
    ...
)
```
- Structured return types
- Consistent field names
- Type safety

#### Parameter Validation
```sql
p_limit INTEGER DEFAULT 10
p_min_credibility FLOAT DEFAULT 0.5
```
- Sensible defaults
- Input validation
- Prevents resource abuse

## Function Deep Dive

### 1. Cache Functions

#### rpc_check_cache_exists
```sql
rpc_check_cache_exists(keyword, max_age_hours)
```
**Purpose**: Quick check before expensive operations
**Use case**: Avoid unnecessary API calls
**Returns**: Simple boolean

#### rpc_get_cached_research
```sql
rpc_get_cached_research(keyword, max_age_hours)
```
**Purpose**: Retrieve full cache entry
**Features**: Auto-increments access count
**Returns**: Complete research data

### 2. Search Functions

#### rpc_search_research
```sql
rpc_search_research(keyword, limit, offset, min_credibility)
```
**Purpose**: Paginated research browsing
**Features**: 
- Credibility filtering
- Academic source priority
- Chronological ordering

#### rpc_find_similar_research
```sql
rpc_find_similar_research(keyword, content_sample, limit)
```
**Purpose**: Discover related research
**How it works**:
1. Finds sample embedding
2. Calculates vector similarity
3. Returns closest matches

### 3. Analytics Functions

#### rpc_get_keyword_stats
```sql
rpc_get_keyword_stats(keyword)
```
**Provides**:
- Document count
- Source diversity
- Quality metrics
- Cache status

#### rpc_get_article_summary
```sql
rpc_get_article_summary(days_back)
```
**Dashboard metrics**:
- Generation volume
- Quality trends
- Status distribution
- Keyword variety

### 4. Maintenance Functions

#### rpc_cleanup_old_data
```sql
rpc_cleanup_old_data(days_to_keep)
```
**Actions**:
- Removes old cache entries
- Cleans orphaned documents
- Reports space freed
**Schedule**: Run monthly

## Usage Examples

### From Python (with asyncpg)
```python
# Check cache before API call
async with pool.acquire() as conn:
    exists = await conn.fetchval(
        "SELECT rpc_check_cache_exists($1, $2)",
        keyword, 24  # max 24 hours old
    )
    
    if exists:
        # Get from cache
        result = await conn.fetchrow(
            "SELECT * FROM rpc_get_cached_research($1, $2)",
            keyword, 24
        )
    else:
        # Call Tavily API
        ...
```

### From JavaScript (with Supabase client)
```javascript
// Get top sources for research
const { data, error } = await supabase
  .rpc('rpc_get_top_sources', {
    p_keyword: 'machine learning',
    p_limit: 10
  });
```

### Direct SQL Usage
```sql
-- Get keyword statistics
SELECT * FROM rpc_get_keyword_stats('diabetes treatment');

-- Find similar research
SELECT * FROM rpc_find_similar_research(
    'ketogenic diet',
    'weight loss benefits',
    5
);
```

## Why Not execute_custom_sql?

### Security Risks
1. **SQL Injection**: Even with parameterization
2. **Data Exposure**: Access to any table
3. **Resource Abuse**: Expensive queries
4. **No Audit Trail**: Hard to track usage

### Our Approach Benefits
1. **Specific Functions**: Clear purpose
2. **Access Control**: Granular permissions
3. **Performance**: Optimized queries
4. **Monitoring**: Usage tracking built-in

## Best Practices

### 1. Function Naming
- Prefix with `rpc_` for clarity
- Descriptive action verbs
- Consistent parameter names

### 2. Error Handling
```sql
IF v_sample_embedding IS NULL THEN
    RETURN; -- Graceful empty result
END IF;
```

### 3. Performance
- Use indexes effectively
- Limit result sets
- Aggregate in database

### 4. Documentation
- Clear function comments
- Parameter descriptions
- Usage examples

## Common Patterns

### Pagination
```sql
LIMIT p_limit OFFSET p_offset
```
- Prevents large result sets
- Enables UI pagination
- Controls memory usage

### Optional Filtering
```sql
AND (p_min_quality IS NULL OR quality >= p_min_quality)
```
- Flexible query options
- Backwards compatible
- Clean API design

### JSON Aggregation
```sql
jsonb_object_agg(status, count)
```
- Structured results
- Reduces round trips
- Frontend-friendly

## Troubleshooting

### Permission Denied
- Ensure using service role key
- Check function exists
- Verify RPC prefix

### Empty Results
- Check parameter values
- Verify data exists
- Test with broader criteria

### Performance Issues
- Check indexes exist
- Monitor query plans
- Consider caching

What questions do you have about RPC functions and database security, Finn?
Would you like me to explain how SECURITY DEFINER works in detail?
Try this exercise: Design an RPC function to find articles that used specific sources.