-- Generated articles table for tracking all articles created by the system
-- This table links research to output and provides analytics on content generation

-- Create the generated articles table
CREATE TABLE IF NOT EXISTS generated_articles (
    -- Primary identifier
    id BIGSERIAL PRIMARY KEY,
    
    -- The keyword that triggered article generation
    keyword TEXT NOT NULL,
    
    -- Article metadata
    title TEXT NOT NULL,
    meta_description TEXT NOT NULL CHECK (char_length(meta_description) BETWEEN 120 AND 160),
    
    -- Content metrics
    word_count INTEGER NOT NULL CHECK (word_count > 0),
    reading_time_minutes INTEGER GENERATED ALWAYS AS (CEIL(word_count / 200.0)) STORED,
    
    -- SEO metrics
    seo_score FLOAT CHECK (seo_score >= 0 AND seo_score <= 100),
    keyword_density FLOAT CHECK (keyword_density >= 0 AND keyword_density <= 10),
    
    -- Content structure metrics stored as JSONB
    content_metrics JSONB DEFAULT '{}',
    -- Expected fields:
    -- - headings_count: {"h1": 1, "h2": 4, "h3": 6}
    -- - internal_links: 5
    -- - external_links: 10
    -- - images_count: 3
    -- - readability_score: 65.5 (Flesch Reading Ease)
    -- - sections: ["introduction", "main_content", "conclusion"]
    
    -- File storage information
    file_path TEXT NOT NULL,
    file_size_kb INTEGER,
    
    -- Google Drive integration (for Phase 7.4)
    drive_file_id TEXT,
    drive_url TEXT,
    drive_folder_id TEXT,
    
    -- Link to research used
    research_cache_id BIGINT REFERENCES research_cache(id),
    
    -- Performance tracking
    generation_time_seconds FLOAT,
    total_api_calls INTEGER DEFAULT 0,
    
    -- Status tracking
    status article_status DEFAULT 'draft',
    
    -- Quality metrics
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 100),
    reviewed BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Article configuration used
    generation_config JSONB DEFAULT '{}',
    -- Expected fields:
    -- - model_version: "gpt-4"
    -- - temperature: 0.7
    -- - prompts_version: "v1.2"
    -- - target_length: 1500
    
    -- Ensure title is unique per keyword
    CONSTRAINT unique_title_per_keyword UNIQUE (keyword, title)
);

-- Create indexes for performance
-- Index for keyword-based queries
CREATE INDEX idx_generated_articles_keyword ON generated_articles(keyword);

-- Index for status filtering
CREATE INDEX idx_generated_articles_status ON generated_articles(status);

-- Index for chronological queries
CREATE INDEX idx_generated_articles_created_at ON generated_articles(created_at DESC);

-- Index for quality-based sorting
CREATE INDEX idx_generated_articles_quality ON generated_articles(quality_score DESC) 
WHERE quality_score IS NOT NULL;

-- Index for finding articles needing review
CREATE INDEX idx_generated_articles_pending_review ON generated_articles(created_at) 
WHERE reviewed = FALSE AND status = 'draft';

-- Partial index for published articles
CREATE INDEX idx_generated_articles_published ON generated_articles(published_at DESC) 
WHERE status = 'published';

-- Function to calculate article quality score
CREATE OR REPLACE FUNCTION calculate_article_quality_score(
    p_word_count INTEGER,
    p_seo_score FLOAT,
    p_keyword_density FLOAT,
    p_readability_score FLOAT,
    p_has_all_sections BOOLEAN,
    p_internal_links INTEGER,
    p_external_links INTEGER
) RETURNS FLOAT AS $$
DECLARE
    quality_score FLOAT := 0;
BEGIN
    -- Word count score (optimal: 1200-2000 words)
    IF p_word_count BETWEEN 1200 AND 2000 THEN
        quality_score := quality_score + 20;
    ELSIF p_word_count BETWEEN 800 AND 1200 OR p_word_count BETWEEN 2000 AND 2500 THEN
        quality_score := quality_score + 15;
    ELSIF p_word_count BETWEEN 500 AND 800 THEN
        quality_score := quality_score + 10;
    ELSE
        quality_score := quality_score + 5;
    END IF;
    
    -- SEO score contribution (max 30 points)
    quality_score := quality_score + (COALESCE(p_seo_score, 0) * 0.3);
    
    -- Keyword density score (optimal: 1-2%)
    IF p_keyword_density BETWEEN 1 AND 2 THEN
        quality_score := quality_score + 15;
    ELSIF p_keyword_density BETWEEN 0.5 AND 1 OR p_keyword_density BETWEEN 2 AND 3 THEN
        quality_score := quality_score + 10;
    ELSE
        quality_score := quality_score + 5;
    END IF;
    
    -- Readability score (optimal: 60-70 Flesch Reading Ease)
    IF p_readability_score BETWEEN 60 AND 70 THEN
        quality_score := quality_score + 15;
    ELSIF p_readability_score BETWEEN 50 AND 60 OR p_readability_score BETWEEN 70 AND 80 THEN
        quality_score := quality_score + 10;
    ELSE
        quality_score := quality_score + 5;
    END IF;
    
    -- Structure completeness
    IF p_has_all_sections THEN
        quality_score := quality_score + 10;
    END IF;
    
    -- Link quality (internal and external)
    IF p_internal_links >= 3 THEN
        quality_score := quality_score + 5;
    END IF;
    
    IF p_external_links BETWEEN 5 AND 15 THEN
        quality_score := quality_score + 5;
    END IF;
    
    -- Cap at 100
    RETURN LEAST(quality_score, 100);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to record new article generation
CREATE OR REPLACE FUNCTION record_article_generation(
    p_keyword TEXT,
    p_title TEXT,
    p_meta_description TEXT,
    p_word_count INTEGER,
    p_file_path TEXT,
    p_content_metrics JSONB,
    p_seo_score FLOAT DEFAULT NULL,
    p_keyword_density FLOAT DEFAULT NULL,
    p_generation_time FLOAT DEFAULT NULL,
    p_research_cache_id BIGINT DEFAULT NULL,
    p_generation_config JSONB DEFAULT '{}'
) RETURNS TABLE (
    article_id BIGINT,
    quality_score FLOAT,
    reading_time INTEGER
) AS $$
DECLARE
    v_article_id BIGINT;
    v_quality_score FLOAT;
    v_reading_time INTEGER;
    v_readability_score FLOAT;
    v_has_all_sections BOOLEAN;
    v_internal_links INTEGER;
    v_external_links INTEGER;
BEGIN
    -- Extract metrics for quality calculation
    v_readability_score := (p_content_metrics->>'readability_score')::FLOAT;
    v_has_all_sections := jsonb_array_length(p_content_metrics->'sections') >= 3;
    v_internal_links := COALESCE((p_content_metrics->>'internal_links')::INTEGER, 0);
    v_external_links := COALESCE((p_content_metrics->>'external_links')::INTEGER, 0);
    
    -- Calculate quality score
    v_quality_score := calculate_article_quality_score(
        p_word_count,
        p_seo_score,
        p_keyword_density,
        v_readability_score,
        v_has_all_sections,
        v_internal_links,
        v_external_links
    );
    
    -- Insert article record
    INSERT INTO generated_articles (
        keyword,
        title,
        meta_description,
        word_count,
        file_path,
        content_metrics,
        seo_score,
        keyword_density,
        quality_score,
        generation_time_seconds,
        research_cache_id,
        generation_config
    ) VALUES (
        p_keyword,
        p_title,
        p_meta_description,
        p_word_count,
        p_file_path,
        p_content_metrics,
        p_seo_score,
        p_keyword_density,
        v_quality_score,
        p_generation_time,
        p_research_cache_id,
        p_generation_config
    )
    RETURNING id, quality_score, reading_time_minutes 
    INTO v_article_id, v_quality_score, v_reading_time;
    
    RETURN QUERY SELECT v_article_id, v_quality_score, v_reading_time;
END;
$$ LANGUAGE plpgsql;

-- Function to get article generation statistics
CREATE OR REPLACE FUNCTION get_article_statistics(
    p_days_back INTEGER DEFAULT 30
) RETURNS TABLE (
    total_articles INTEGER,
    avg_word_count INTEGER,
    avg_quality_score FLOAT,
    avg_seo_score FLOAT,
    avg_generation_time FLOAT,
    articles_by_status JSONB,
    quality_distribution JSONB,
    top_keywords JSONB,
    daily_generation JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH date_range AS (
        SELECT NOW() - (p_days_back || ' days')::INTERVAL as start_date
    ),
    article_stats AS (
        SELECT 
            COUNT(*) as total_articles,
            AVG(word_count)::INTEGER as avg_word_count,
            AVG(quality_score) as avg_quality_score,
            AVG(seo_score) as avg_seo_score,
            AVG(generation_time_seconds) as avg_generation_time
        FROM generated_articles
        WHERE created_at >= (SELECT start_date FROM date_range)
    ),
    status_counts AS (
        SELECT jsonb_object_agg(status, count) as articles_by_status
        FROM (
            SELECT status, COUNT(*) as count
            FROM generated_articles
            WHERE created_at >= (SELECT start_date FROM date_range)
            GROUP BY status
        ) s
    ),
    quality_dist AS (
        SELECT jsonb_build_object(
            'excellent', COUNT(*) FILTER (WHERE quality_score >= 80),
            'good', COUNT(*) FILTER (WHERE quality_score >= 60 AND quality_score < 80),
            'fair', COUNT(*) FILTER (WHERE quality_score >= 40 AND quality_score < 60),
            'poor', COUNT(*) FILTER (WHERE quality_score < 40)
        ) as quality_distribution
        FROM generated_articles
        WHERE created_at >= (SELECT start_date FROM date_range)
    ),
    keyword_stats AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'keyword', keyword,
                'count', article_count,
                'avg_quality', avg_quality
            ) ORDER BY article_count DESC
        ) as top_keywords
        FROM (
            SELECT 
                keyword,
                COUNT(*) as article_count,
                AVG(quality_score) as avg_quality
            FROM generated_articles
            WHERE created_at >= (SELECT start_date FROM date_range)
            GROUP BY keyword
            ORDER BY article_count DESC
            LIMIT 10
        ) k
    ),
    daily_stats AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'date', generation_date,
                'count', article_count
            ) ORDER BY generation_date
        ) as daily_generation
        FROM (
            SELECT 
                DATE(created_at) as generation_date,
                COUNT(*) as article_count
            FROM generated_articles
            WHERE created_at >= (SELECT start_date FROM date_range)
            GROUP BY DATE(created_at)
        ) d
    )
    SELECT 
        a.total_articles::INTEGER,
        a.avg_word_count,
        a.avg_quality_score,
        a.avg_seo_score,
        a.avg_generation_time,
        s.articles_by_status,
        q.quality_distribution,
        k.top_keywords,
        d.daily_generation
    FROM article_stats a
    CROSS JOIN status_counts s
    CROSS JOIN quality_dist q
    CROSS JOIN keyword_stats k
    CROSS JOIN daily_stats d;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar articles (for avoiding duplicates)
CREATE OR REPLACE FUNCTION find_similar_articles(
    p_keyword TEXT,
    p_title TEXT,
    p_similarity_threshold FLOAT DEFAULT 0.8
) RETURNS TABLE (
    id BIGINT,
    title TEXT,
    keyword TEXT,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ga.id,
        ga.title,
        ga.keyword,
        similarity(ga.title, p_title) as similarity,
        ga.created_at
    FROM generated_articles ga
    WHERE 
        ga.keyword = p_keyword
        AND similarity(ga.title, p_title) >= p_similarity_threshold
    ORDER BY similarity DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to update article status
CREATE OR REPLACE FUNCTION update_article_status(
    p_article_id BIGINT,
    p_new_status article_status,
    p_drive_file_id TEXT DEFAULT NULL,
    p_drive_url TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_updated BOOLEAN;
BEGIN
    UPDATE generated_articles
    SET 
        status = p_new_status,
        published_at = CASE 
            WHEN p_new_status = 'published' THEN NOW()
            ELSE published_at
        END,
        drive_file_id = COALESCE(p_drive_file_id, drive_file_id),
        drive_url = COALESCE(p_drive_url, drive_url),
        updated_at = NOW()
    WHERE id = p_article_id;
    
    GET DIAGNOSTICS v_updated = FOUND;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION update_article_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_article_timestamp_trigger
BEFORE UPDATE ON generated_articles
FOR EACH ROW
WHEN (OLD.* IS DISTINCT FROM NEW.*)
EXECUTE FUNCTION update_article_timestamp();

-- Add comments for documentation
COMMENT ON TABLE generated_articles IS 'Tracks all articles generated by the SEO content automation system with quality metrics and performance data';
COMMENT ON COLUMN generated_articles.quality_score IS 'Calculated score 0-100 based on word count, SEO, readability, and structure';
COMMENT ON COLUMN generated_articles.reading_time_minutes IS 'Estimated reading time calculated as word_count / 200';
COMMENT ON FUNCTION calculate_article_quality_score IS 'Calculates comprehensive quality score based on multiple content metrics';