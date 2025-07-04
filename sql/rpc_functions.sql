-- RPC (Remote Procedure Call) functions for safe database access
-- These functions provide a secure API for AI agents and application code
-- All functions are designed to be transaction pooler compatible

-- =====================================================
-- Research Cache Functions
-- =====================================================

-- Check if research exists in cache for a keyword
CREATE OR REPLACE FUNCTION rpc_check_cache_exists(
    p_keyword TEXT,
    p_max_age_hours INTEGER DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    -- Check if valid cache entry exists
    SELECT EXISTS (
        SELECT 1 
        FROM research_cache 
        WHERE keyword = p_keyword 
        AND expires_at > NOW()
        AND (p_max_age_hours IS NULL OR 
             created_at > NOW() - (p_max_age_hours || ' hours')::INTERVAL)
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$;

-- Get cached research with automatic access tracking
CREATE OR REPLACE FUNCTION rpc_get_cached_research(
    p_keyword TEXT,
    p_max_age_hours INTEGER DEFAULT NULL
) RETURNS TABLE (
    id BIGINT,
    tavily_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER,
    total_results INTEGER,
    academic_results INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Use the existing function
    RETURN QUERY
    SELECT 
        cr.id,
        cr.tavily_response,
        cr.created_at,
        cr.expires_at,
        cr.access_count,
        cr.total_results,
        cr.academic_results
    FROM get_cached_research(p_keyword, p_max_age_hours) cr
    WHERE NOT cr.is_expired;
END;
$$;

-- =====================================================
-- Research Search Functions
-- =====================================================

-- Search research documents by keyword with pagination
CREATE OR REPLACE FUNCTION rpc_search_research(
    p_keyword TEXT,
    p_limit INTEGER DEFAULT 10,
    p_offset INTEGER DEFAULT 0,
    p_min_credibility FLOAT DEFAULT 0.5
) RETURNS TABLE (
    id BIGINT,
    content TEXT,
    source_url TEXT,
    credibility_score FLOAT,
    is_academic BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rd.id,
        rd.content,
        rd.metadata->>'source_url' as source_url,
        (rd.metadata->>'credibility_score')::FLOAT as credibility_score,
        (rd.metadata->>'is_academic')::BOOLEAN as is_academic,
        rd.created_at
    FROM research_documents rd
    WHERE 
        rd.keyword = p_keyword
        AND (rd.metadata->>'credibility_score')::FLOAT >= p_min_credibility
    ORDER BY 
        (rd.metadata->>'credibility_score')::FLOAT DESC,
        rd.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Get similar research using semantic search
CREATE OR REPLACE FUNCTION rpc_find_similar_research(
    p_keyword TEXT,
    p_content_sample TEXT,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (
    id BIGINT,
    keyword TEXT,
    content TEXT,
    similarity FLOAT,
    source_url TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_sample_embedding vector(1536);
BEGIN
    -- Get embedding of a sample document
    SELECT embedding INTO v_sample_embedding
    FROM research_documents
    WHERE keyword = p_keyword
    AND content ILIKE '%' || p_content_sample || '%'
    LIMIT 1;
    
    IF v_sample_embedding IS NULL THEN
        RETURN; -- No matching sample found
    END IF;
    
    -- Find similar documents
    RETURN QUERY
    SELECT 
        rd.id,
        rd.keyword,
        rd.content,
        1 - (rd.embedding <=> v_sample_embedding) as similarity,
        rd.metadata->>'source_url' as source_url
    FROM research_documents rd
    WHERE rd.keyword != p_keyword
    ORDER BY rd.embedding <=> v_sample_embedding
    LIMIT p_limit;
END;
$$;

-- =====================================================
-- Source Quality Functions
-- =====================================================

-- Get top sources for a keyword
CREATE OR REPLACE FUNCTION rpc_get_top_sources(
    p_keyword TEXT,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (
    source_url TEXT,
    domain TEXT,
    credibility_score FLOAT,
    source_type TEXT,
    times_used INTEGER,
    is_academic BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM get_top_sources_for_research(p_keyword, p_limit);
END;
$$;

-- Get keyword statistics
CREATE OR REPLACE FUNCTION rpc_get_keyword_stats(
    p_keyword TEXT
) RETURNS TABLE (
    total_documents INTEGER,
    unique_sources INTEGER,
    academic_sources INTEGER,
    avg_credibility FLOAT,
    cache_entries INTEGER,
    latest_research TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH doc_stats AS (
        SELECT 
            COUNT(*) as total_docs,
            COUNT(DISTINCT metadata->>'source_url') as unique_sources,
            COUNT(*) FILTER (WHERE (metadata->>'is_academic')::BOOLEAN) as academic_sources,
            AVG((metadata->>'credibility_score')::FLOAT) as avg_cred,
            MAX(created_at) as latest
        FROM research_documents
        WHERE keyword = p_keyword
    ),
    cache_stats AS (
        SELECT COUNT(*) as cache_count
        FROM research_cache
        WHERE keyword = p_keyword AND expires_at > NOW()
    )
    SELECT 
        doc_stats.total_docs::INTEGER,
        doc_stats.unique_sources::INTEGER,
        doc_stats.academic_sources::INTEGER,
        doc_stats.avg_cred,
        cache_stats.cache_count::INTEGER,
        doc_stats.latest
    FROM doc_stats, cache_stats;
END;
$$;

-- =====================================================
-- Article Analytics Functions
-- =====================================================

-- Get recent articles with quality metrics
CREATE OR REPLACE FUNCTION rpc_get_recent_articles(
    p_days_back INTEGER DEFAULT 7,
    p_limit INTEGER DEFAULT 10,
    p_min_quality FLOAT DEFAULT NULL
) RETURNS TABLE (
    id BIGINT,
    keyword TEXT,
    title TEXT,
    quality_score FLOAT,
    seo_score FLOAT,
    word_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    status article_status
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ga.id,
        ga.keyword,
        ga.title,
        ga.quality_score,
        ga.seo_score,
        ga.word_count,
        ga.created_at,
        ga.status
    FROM generated_articles ga
    WHERE 
        ga.created_at >= NOW() - (p_days_back || ' days')::INTERVAL
        AND (p_min_quality IS NULL OR ga.quality_score >= p_min_quality)
    ORDER BY ga.created_at DESC
    LIMIT p_limit;
END;
$$;

-- Get article performance summary
CREATE OR REPLACE FUNCTION rpc_get_article_summary(
    p_days_back INTEGER DEFAULT 30
) RETURNS TABLE (
    total_articles INTEGER,
    avg_quality_score FLOAT,
    avg_word_count INTEGER,
    total_keywords INTEGER,
    articles_by_status JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH article_stats AS (
        SELECT 
            COUNT(*) as total,
            AVG(quality_score) as avg_quality,
            AVG(word_count)::INTEGER as avg_words,
            COUNT(DISTINCT keyword) as total_keywords
        FROM generated_articles
        WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    ),
    status_breakdown AS (
        SELECT jsonb_object_agg(status, count) as by_status
        FROM (
            SELECT status, COUNT(*) as count
            FROM generated_articles
            WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
            GROUP BY status
        ) s
    )
    SELECT 
        article_stats.total::INTEGER,
        article_stats.avg_quality,
        article_stats.avg_words,
        article_stats.total_keywords::INTEGER,
        status_breakdown.by_status
    FROM article_stats, status_breakdown;
END;
$$;

-- =====================================================
-- Cache Management Functions
-- =====================================================

-- Get cache performance metrics
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
            AVG(CASE WHEN access_count > 1 THEN 
                (access_count - 1.0) / access_count 
                ELSE 0 END) as hit_rate
        FROM research_cache
    ),
    size_data AS (
        SELECT pg_total_relation_size('research_cache') / 1024.0 / 1024.0 as size_mb
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
        cache_data.hit_rate,
        size_data.size_mb,
        top_keywords.top_5
    FROM cache_data, size_data, top_keywords;
END;
$$;

-- Clean up old data (maintenance function)
CREATE OR REPLACE FUNCTION rpc_cleanup_old_data(
    p_days_to_keep INTEGER DEFAULT 90
) RETURNS TABLE (
    deleted_cache_entries INTEGER,
    deleted_documents INTEGER,
    freed_space_mb FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_cache_deleted INTEGER;
    v_docs_deleted INTEGER;
    v_space_before FLOAT;
    v_space_after FLOAT;
BEGIN
    -- Get current space usage
    SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 INTO v_space_before;
    
    -- Clean old cache entries
    DELETE FROM research_cache
    WHERE created_at < NOW() - (p_days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS v_cache_deleted = ROW_COUNT;
    
    -- Clean orphaned research documents
    DELETE FROM research_documents rd
    WHERE created_at < NOW() - (p_days_to_keep || ' days')::INTERVAL
    AND NOT EXISTS (
        SELECT 1 FROM generated_articles ga 
        WHERE ga.keyword = rd.keyword 
        AND ga.created_at >= NOW() - (p_days_to_keep || ' days')::INTERVAL
    );
    GET DIAGNOSTICS v_docs_deleted = ROW_COUNT;
    
    -- Get space after cleanup
    SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 INTO v_space_after;
    
    RETURN QUERY SELECT 
        v_cache_deleted,
        v_docs_deleted,
        (v_space_before - v_space_after);
END;
$$;

-- =====================================================
-- Security and Permissions
-- =====================================================

-- Grant execute permissions to service role only
-- Revoke from public and anon roles for security
DO $$
DECLARE
    func_name TEXT;
BEGIN
    FOR func_name IN 
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name LIKE 'rpc_%'
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %I FROM PUBLIC, anon', func_name);
        -- Note: GRANT to service role is automatic in Supabase
    END LOOP;
END $$;

-- Add comments for documentation
COMMENT ON FUNCTION rpc_check_cache_exists IS 'Check if valid cache exists for a keyword';
COMMENT ON FUNCTION rpc_get_cached_research IS 'Retrieve cached research with access tracking';
COMMENT ON FUNCTION rpc_search_research IS 'Search research documents with pagination';
COMMENT ON FUNCTION rpc_find_similar_research IS 'Find semantically similar research';
COMMENT ON FUNCTION rpc_get_top_sources IS 'Get highest quality sources for a keyword';
COMMENT ON FUNCTION rpc_get_keyword_stats IS 'Get comprehensive statistics for a keyword';
COMMENT ON FUNCTION rpc_get_recent_articles IS 'Get recently generated articles with metrics';
COMMENT ON FUNCTION rpc_get_article_summary IS 'Get article generation summary statistics';
COMMENT ON FUNCTION rpc_get_cache_metrics IS 'Get cache performance metrics';
COMMENT ON FUNCTION rpc_cleanup_old_data IS 'Clean up old data for maintenance';