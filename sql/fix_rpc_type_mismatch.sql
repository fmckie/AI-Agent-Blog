-- Fix type mismatch in rpc_get_cache_metrics function
-- The issue is that AVG() returns numeric but the function expects FLOAT (double precision)

-- Drop the existing function first
DROP FUNCTION IF EXISTS rpc_get_cache_metrics();

-- Recreate with proper type casting
CREATE OR REPLACE FUNCTION rpc_get_cache_metrics() 
RETURNS TABLE (
    total_entries INTEGER,
    active_entries INTEGER,
    avg_hit_rate FLOAT,
    cache_size_mb FLOAT,
    top_cached_keywords JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH cache_data AS (
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE expires_at > NOW()) as active,
            -- Cast the AVG result to FLOAT explicitly
            AVG(CASE WHEN access_count > 1 THEN 
                (access_count - 1.0) / access_count 
                ELSE 0 END)::FLOAT as hit_rate  -- Added ::FLOAT cast here
        FROM research_cache
    ),
    size_data AS (
        SELECT pg_total_relation_size('research_cache')::FLOAT / 1024.0 / 1024.0 as size_mb
    ),
    top_keywords AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'keyword', keyword,
                'access_count', access_count
            ) ORDER BY access_count DESC
        ) as top_5
        FROM (
            SELECT keyword, MAX(access_count) as access_count
            FROM research_cache
            WHERE expires_at > NOW()
            GROUP BY keyword
            ORDER BY access_count DESC
            LIMIT 5
        ) t
    )
    SELECT 
        cache_data.total::INTEGER,
        cache_data.active::INTEGER,
        cache_data.hit_rate,  -- Now properly typed as FLOAT
        size_data.size_mb,
        top_keywords.top_5
    FROM cache_data, size_data, top_keywords;
END;
$$;

-- Add comment for documentation
COMMENT ON FUNCTION rpc_get_cache_metrics IS 'Get cache performance metrics (fixed type mismatch)';

-- Test the fixed function
SELECT * FROM rpc_get_cache_metrics();