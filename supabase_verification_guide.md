# How to Verify Vector Storage in Supabase Dashboard

## Step 1: Access Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Log in to your account
3. Select your project (quprtbkdpujtjadpathz)

## Step 2: Navigate to Table Editor

1. In the left sidebar, click on **"Table Editor"**
2. You should see two tables:
   - `research_chunks`
   - `cache_entries`

## Step 3: View Research Chunks

Click on the `research_chunks` table to see:

- **id**: Unique identifier (e.g., "health_ai_001_0_434824c8")
- **content**: The actual text content
- **embedding**: Vector data (will show as an array of 1536 numbers)
- **metadata**: JSON data with source information
- **keyword**: "AI healthcare"
- **chunk_index**: 0, 1, 2, etc.
- **source_id**: "health_ai_001" or "health_ai_002"
- **created_at**: Timestamp when created

## Step 4: View Cache Entries

Click on the `cache_entries` table to see:

- **id**: SHA256 hash of normalized keyword
- **keyword**: "AI healthcare"
- **keyword_normalized**: "ai healthcare"
- **research_summary**: The cached summary
- **chunk_ids**: Array of chunk IDs
- **hit_count**: Number of times accessed
- **expires_at**: When the cache expires

## Step 5: Run SQL Queries

For more detailed verification, click on **"SQL Editor"** in the sidebar and try these queries:

### Check Vector Dimensions
```sql
-- Verify vector dimensions
SELECT 
    id,
    vector_dims(embedding) as dimensions,
    substring(content, 1, 50) as content_preview
FROM research_chunks
LIMIT 5;
```

### Test Similarity Search
```sql
-- Find similar chunks (replace with actual vector from a chunk)
SELECT 
    id,
    content,
    1 - (embedding <=> (SELECT embedding FROM research_chunks LIMIT 1)) as similarity
FROM research_chunks
WHERE id != (SELECT id FROM research_chunks LIMIT 1)
ORDER BY embedding <=> (SELECT embedding FROM research_chunks LIMIT 1)
LIMIT 5;
```

### View Cache Statistics
```sql
-- Cache statistics
SELECT 
    COUNT(*) as total_entries,
    SUM(hit_count) as total_hits,
    AVG(hit_count) as avg_hits_per_entry,
    MAX(hit_count) as max_hits
FROM cache_entries;
```

### Check Table Sizes
```sql
-- Table sizes and row counts
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_stat_user_tables
WHERE tablename IN ('research_chunks', 'cache_entries')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Step 6: Real-time Monitoring

1. Click on **"Realtime"** in the sidebar
2. Select either `research_chunks` or `cache_entries`
3. You'll see real-time updates when new data is inserted

## Step 7: API Logs

To see the actual API calls:

1. Click on **"Logs"** in the sidebar
2. Select **"API Edge"**
3. You'll see all Supabase client operations
4. Look for INSERT and SELECT operations on your tables

## Visual Indicators of Success

When everything is working correctly, you should see:

✅ **In research_chunks table:**
- Multiple rows with healthcare-related content
- Each row has a 1536-dimensional embedding vector
- Metadata contains source information
- Timestamps show recent creation

✅ **In cache_entries table:**
- At least one entry for "AI healthcare"
- hit_count increases when cache is accessed
- chunk_ids array contains references to research_chunks

✅ **In SQL queries:**
- Vector dimensions show 1536
- Similarity scores between 0 and 1
- Proper row counts and table sizes

## Quick Verification Script

Here's a SQL script that checks everything at once:

```sql
-- Comprehensive RAG system check
DO $$ 
BEGIN
    RAISE NOTICE '=== RAG System Verification ===';
    
    -- Check research chunks
    RAISE NOTICE 'Research Chunks: % rows', (SELECT COUNT(*) FROM research_chunks);
    
    -- Check cache entries
    RAISE NOTICE 'Cache Entries: % rows', (SELECT COUNT(*) FROM cache_entries);
    
    -- Check vector dimensions
    RAISE NOTICE 'Vector Dimensions: %', (
        SELECT vector_dims(embedding) 
        FROM research_chunks 
        LIMIT 1
    );
    
    -- Check total cache hits
    RAISE NOTICE 'Total Cache Hits: %', (
        SELECT COALESCE(SUM(hit_count), 0) 
        FROM cache_entries
    );
    
    RAISE NOTICE '=== All checks complete ===';
END $$;
```

## Troubleshooting

If you don't see any data:

1. **Check Filters**: Make sure no filters are applied in the table view
2. **Refresh**: Click the refresh button in the table editor
3. **Check Logs**: Look for any errors in the API logs
4. **Run Test Again**: Execute `python test_vector_storage_integration.py` and choose 'n' to keep data

## Pro Tips

1. **Export Data**: You can export table data as CSV for analysis
2. **RLS Policies**: We're using service role key, so RLS is bypassed
3. **Performance**: Check the "Database" section for query performance metrics
4. **Indexes**: Verify indexes exist in "Database" → "Indexes" section

Would you like me to create a script that generates some test data you can view in Supabase?