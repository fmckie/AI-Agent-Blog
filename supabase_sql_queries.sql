-- SQL Queries to Verify Vector Storage in Supabase
-- Copy and paste these into your Supabase SQL Editor

-- 1. View all test chunks with readable format
SELECT 
    substring(id, 1, 20) as id_preview,
    substring(content, 1, 60) || '...' as content_preview,
    keyword,
    metadata->>'source' as source,
    source_id,
    chunk_index,
    created_at
FROM research_chunks
WHERE source_id LIKE 'DEMO_%' OR keyword = 'AI healthcare'
ORDER BY created_at DESC;

-- 2. Check vector dimensions and first few values
SELECT 
    id,
    vector_dims(embedding) as dimensions,
    substring(embedding::text, 1, 50) || '...' as embedding_preview,
    keyword
FROM research_chunks
WHERE source_id LIKE 'DEMO_%'
LIMIT 5;

-- 3. View cache entries with hit counts
SELECT 
    keyword,
    keyword_normalized,
    substring(research_summary, 1, 80) || '...' as summary_preview,
    hit_count,
    array_length(chunk_ids, 1) as num_chunks,
    metadata,
    created_at,
    expires_at
FROM cache_entries
ORDER BY created_at DESC;

-- 4. Test similarity search between chunks
WITH first_chunk AS (
    SELECT id, embedding 
    FROM research_chunks 
    WHERE source_id LIKE 'DEMO_%' 
    LIMIT 1
)
SELECT 
    rc.id,
    substring(rc.content, 1, 50) || '...' as content,
    1 - (rc.embedding <=> fc.embedding) as similarity
FROM research_chunks rc, first_chunk fc
WHERE rc.id != fc.id
ORDER BY rc.embedding <=> fc.embedding
LIMIT 5;

-- 5. Summary statistics
SELECT 
    'Total Chunks' as metric,
    COUNT(*)::text as value
FROM research_chunks
UNION ALL
SELECT 
    'Total Cache Entries' as metric,
    COUNT(*)::text as value
FROM cache_entries
UNION ALL
SELECT 
    'Total Cache Hits' as metric,
    COALESCE(SUM(hit_count), 0)::text as value
FROM cache_entries
UNION ALL
SELECT 
    'Unique Keywords' as metric,
    COUNT(DISTINCT keyword)::text as value
FROM research_chunks;

-- 6. Check indexes are being used
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, content
FROM research_chunks
WHERE keyword = 'DEMO TEST';

-- 7. View most recent operations
SELECT 
    'research_chunks' as table_name,
    COUNT(*) as row_count,
    MAX(created_at) as last_insert
FROM research_chunks
UNION ALL
SELECT 
    'cache_entries' as table_name,
    COUNT(*) as row_count,
    MAX(created_at) as last_insert
FROM cache_entries;