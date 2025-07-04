-- Research cache table for storing complete Tavily API responses
-- This table provides exact-match caching to reduce API calls and costs

-- Create the research cache table
CREATE TABLE IF NOT EXISTS research_cache (
    -- Primary identifier
    id BIGSERIAL PRIMARY KEY,
    
    -- The exact keyword used for the search
    keyword TEXT NOT NULL,
    
    -- Complete Tavily API response stored as JSONB
    tavily_response JSONB NOT NULL,
    -- Expected structure:
    -- {
    --   "results": [...],
    --   "query": "original query",
    --   "response_time": 0.123,
    --   "sources_count": 10,
    --   "academic_sources": 5
    -- }
    
    -- Hash of the response for deduplication (MD5 of response JSON)
    response_hash TEXT NOT NULL,
    
    -- Number of times this cache entry has been accessed
    access_count INTEGER DEFAULT 1,
    
    -- Timestamps for cache management
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Cache metadata
    metadata JSONB DEFAULT '{}',
    -- Expected fields:
    -- - api_version: Tavily API version used
    -- - request_params: Additional parameters sent to API
    -- - processing_time: Time taken to get response
    -- - cache_source: 'api' or 'manual' (for pre-populated cache)
    
    -- Quality metrics extracted from response
    total_results INTEGER NOT NULL DEFAULT 0,
    academic_results INTEGER NOT NULL DEFAULT 0,
    avg_credibility_score FLOAT,
    
    -- Ensure we don't store empty responses
    CONSTRAINT response_not_empty CHECK (jsonb_array_length(tavily_response->'results') > 0),
    
    -- Unique constraint on keyword + response_hash to prevent duplicates
    CONSTRAINT unique_keyword_response UNIQUE (keyword, response_hash)
);

-- Create indexes for performance
-- Primary lookup index on keyword
CREATE INDEX idx_research_cache_keyword ON research_cache(keyword);

-- Index for cache expiration queries
CREATE INDEX idx_research_cache_expires_at ON research_cache(expires_at);

-- Index for finding frequently accessed entries
CREATE INDEX idx_research_cache_access_count ON research_cache(access_count DESC);

-- Index for last accessed (for LRU-style cleanup if needed)
CREATE INDEX idx_research_cache_last_accessed ON research_cache(last_accessed DESC);

-- Partial index for non-expired entries only
CREATE INDEX idx_research_cache_active ON research_cache(keyword, created_at DESC) 
WHERE expires_at > NOW();

-- Function to get cached research with automatic access tracking
CREATE OR REPLACE FUNCTION get_cached_research(
    p_keyword TEXT,
    p_max_age_hours INTEGER DEFAULT NULL
) RETURNS TABLE (
    id BIGINT,
    tavily_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER,
    is_expired BOOLEAN
) AS $$
DECLARE
    v_cutoff_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Calculate cutoff time if max age specified
    IF p_max_age_hours IS NOT NULL THEN
        v_cutoff_time := NOW() - (p_max_age_hours || ' hours')::INTERVAL;
    ELSE
        v_cutoff_time := TIMESTAMP '-infinity';
    END IF;
    
    -- Update access count and last accessed time for matching entries
    UPDATE research_cache rc
    SET 
        access_count = rc.access_count + 1,
        last_accessed = NOW()
    WHERE 
        rc.keyword = p_keyword 
        AND rc.expires_at > NOW()
        AND rc.created_at > v_cutoff_time;
    
    -- Return the most recent non-expired cache entry
    RETURN QUERY
    SELECT 
        rc.id,
        rc.tavily_response,
        rc.created_at,
        rc.expires_at,
        rc.access_count,
        (rc.expires_at <= NOW()) as is_expired
    FROM research_cache rc
    WHERE 
        rc.keyword = p_keyword
        AND rc.created_at > v_cutoff_time
    ORDER BY 
        (rc.expires_at > NOW()) DESC,  -- Non-expired first
        rc.created_at DESC              -- Most recent first
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to store new research in cache
CREATE OR REPLACE FUNCTION store_research_cache(
    p_keyword TEXT,
    p_tavily_response JSONB,
    p_ttl_hours INTEGER DEFAULT 168,  -- Default 7 days
    p_metadata JSONB DEFAULT '{}'
) RETURNS TABLE (
    id BIGINT,
    is_duplicate BOOLEAN,
    expires_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    v_response_hash TEXT;
    v_total_results INTEGER;
    v_academic_results INTEGER;
    v_avg_credibility FLOAT;
    v_expires_at TIMESTAMP WITH TIME ZONE;
    v_id BIGINT;
    v_is_duplicate BOOLEAN := FALSE;
BEGIN
    -- Calculate response hash
    v_response_hash := md5(p_tavily_response::TEXT);
    
    -- Calculate expiration time
    v_expires_at := NOW() + (p_ttl_hours || ' hours')::INTERVAL;
    
    -- Extract quality metrics from response
    v_total_results := jsonb_array_length(p_tavily_response->'results');
    
    -- Count academic results (simplified - you'd implement actual logic)
    SELECT 
        COUNT(*)::INTEGER,
        AVG((result->>'credibility_score')::FLOAT)
    INTO 
        v_academic_results,
        v_avg_credibility
    FROM jsonb_array_elements(p_tavily_response->'results') AS result
    WHERE result->>'url' SIMILAR TO '%\.(edu|gov|org|ac\.uk)%';
    
    -- Try to insert
    INSERT INTO research_cache (
        keyword,
        tavily_response,
        response_hash,
        expires_at,
        metadata,
        total_results,
        academic_results,
        avg_credibility_score
    ) VALUES (
        p_keyword,
        p_tavily_response,
        v_response_hash,
        v_expires_at,
        p_metadata,
        v_total_results,
        COALESCE(v_academic_results, 0),
        v_avg_credibility
    )
    ON CONFLICT (keyword, response_hash) DO UPDATE SET
        access_count = research_cache.access_count + 1,
        last_accessed = NOW()
    RETURNING research_cache.id, (xmax != 0) INTO v_id, v_is_duplicate;
    
    RETURN QUERY SELECT v_id, v_is_duplicate, v_expires_at;
END;
$$ LANGUAGE plpgsql;

-- Function to get cache statistics
CREATE OR REPLACE FUNCTION get_cache_statistics()
RETURNS TABLE (
    total_entries INTEGER,
    active_entries INTEGER,
    expired_entries INTEGER,
    total_keywords INTEGER,
    avg_access_count FLOAT,
    most_accessed_keywords JSONB,
    cache_hit_keywords JSONB,
    storage_size_mb FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH cache_stats AS (
        SELECT 
            COUNT(*) as total_entries,
            COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
            COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries,
            COUNT(DISTINCT keyword) as total_keywords,
            AVG(access_count) as avg_access_count
        FROM research_cache
    ),
    top_keywords AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'keyword', keyword,
                'access_count', access_count,
                'last_accessed', last_accessed
            ) ORDER BY access_count DESC
        ) as most_accessed
        FROM (
            SELECT keyword, MAX(access_count) as access_count, MAX(last_accessed) as last_accessed
            FROM research_cache
            GROUP BY keyword
            ORDER BY access_count DESC
            LIMIT 10
        ) top
    ),
    high_hit_keywords AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'keyword', keyword,
                'hit_rate', hit_rate
            ) ORDER BY hit_rate DESC
        ) as cache_hits
        FROM (
            SELECT 
                keyword,
                (SUM(access_count) - COUNT(*))::FLOAT / NULLIF(SUM(access_count), 0) as hit_rate
            FROM research_cache
            GROUP BY keyword
            HAVING SUM(access_count) > 1
            ORDER BY hit_rate DESC
            LIMIT 10
        ) hits
    ),
    storage_stats AS (
        SELECT 
            pg_total_relation_size('research_cache') / 1024.0 / 1024.0 as size_mb
    )
    SELECT 
        cs.total_entries::INTEGER,
        cs.active_entries::INTEGER,
        cs.expired_entries::INTEGER,
        cs.total_keywords::INTEGER,
        cs.avg_access_count,
        tk.most_accessed,
        hk.cache_hits,
        ss.size_mb
    FROM cache_stats cs
    CROSS JOIN top_keywords tk
    CROSS JOIN high_hit_keywords hk
    CROSS JOIN storage_stats ss;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_research_cache(
    p_retention_days INTEGER DEFAULT 30  -- Keep expired entries for analytics
) RETURNS TABLE (
    deleted_count INTEGER,
    freed_space_mb FLOAT
) AS $$
DECLARE
    v_deleted_count INTEGER;
    v_size_before FLOAT;
    v_size_after FLOAT;
BEGIN
    -- Get size before cleanup
    SELECT pg_total_relation_size('research_cache') / 1024.0 / 1024.0 INTO v_size_before;
    
    -- Delete old expired entries
    DELETE FROM research_cache
    WHERE expires_at < NOW() - (p_retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    -- Get size after cleanup
    SELECT pg_total_relation_size('research_cache') / 1024.0 / 1024.0 INTO v_size_after;
    
    -- Vacuum to reclaim space
    -- Note: In production, this would be handled by autovacuum
    
    RETURN QUERY SELECT v_deleted_count, (v_size_before - v_size_after);
END;
$$ LANGUAGE plpgsql;

-- Function for cache warming (pre-populate common searches)
CREATE OR REPLACE FUNCTION warm_cache_for_keyword(
    p_keyword TEXT,
    p_variations TEXT[] DEFAULT NULL
) RETURNS TABLE (
    keyword TEXT,
    should_fetch BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH keywords_to_check AS (
        SELECT UNNEST(ARRAY[p_keyword] || COALESCE(p_variations, ARRAY[]::TEXT[])) as keyword
    )
    SELECT 
        k.keyword,
        NOT EXISTS (
            SELECT 1 
            FROM research_cache rc 
            WHERE rc.keyword = k.keyword 
            AND rc.expires_at > NOW()
        ) as should_fetch
    FROM keywords_to_check k;
END;
$$ LANGUAGE plpgsql;

-- Trigger to validate cache entries before insert
CREATE OR REPLACE FUNCTION validate_cache_entry()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure tavily_response has required structure
    IF NOT (NEW.tavily_response ? 'results') THEN
        RAISE EXCEPTION 'tavily_response must contain results array';
    END IF;
    
    -- Ensure expiration is in the future for new entries
    IF TG_OP = 'INSERT' AND NEW.expires_at <= NOW() THEN
        RAISE EXCEPTION 'expires_at must be in the future for new entries';
    END IF;
    
    -- Ensure TTL is reasonable (max 30 days)
    IF NEW.expires_at > NOW() + INTERVAL '30 days' THEN
        NEW.expires_at := NOW() + INTERVAL '30 days';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_cache_entry_trigger
BEFORE INSERT OR UPDATE ON research_cache
FOR EACH ROW
EXECUTE FUNCTION validate_cache_entry();

-- Add comments for documentation
COMMENT ON TABLE research_cache IS 'Exact-match cache for Tavily API responses to reduce API calls and improve performance';
COMMENT ON COLUMN research_cache.response_hash IS 'MD5 hash of tavily_response for deduplication';
COMMENT ON COLUMN research_cache.expires_at IS 'When this cache entry expires and should be refreshed';
COMMENT ON FUNCTION get_cached_research IS 'Retrieves cached research with automatic access tracking and freshness check';