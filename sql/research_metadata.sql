-- Research metadata table for tracking and scoring research sources
-- This table maintains a registry of all sources used in research with credibility metrics

-- Create the research metadata table
CREATE TABLE IF NOT EXISTS research_metadata (
    -- Primary identifier
    id BIGSERIAL PRIMARY KEY,
    
    -- The source URL (unique constraint ensures one entry per source)
    source_url TEXT NOT NULL UNIQUE,
    
    -- Extracted domain for credibility assessment
    domain TEXT NOT NULL,
    
    -- Credibility score from 0.0 to 1.0
    -- 0.0-0.3: Low credibility (blogs, forums)
    -- 0.3-0.6: Medium credibility (news sites, established blogs)
    -- 0.6-0.8: High credibility (research institutions, government)
    -- 0.8-1.0: Academic credibility (peer-reviewed journals, .edu)
    credibility_score FLOAT NOT NULL CHECK (credibility_score >= 0 AND credibility_score <= 1),
    
    -- Quick flag for academic sources
    is_academic BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Source categorization
    source_type TEXT CHECK (source_type IN ('journal', 'government', 'education', 'organization', 'news', 'blog', 'other')),
    
    -- Additional metadata about the source
    metadata JSONB DEFAULT '{}',
    -- Expected fields:
    -- - publication_name: Name of journal/publication if applicable
    -- - author_credentials: Known author qualifications
    -- - peer_reviewed: Boolean for academic papers
    -- - impact_factor: Journal impact factor if known
    -- - last_verified: When the source was last checked
    
    -- Tracking timestamps
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Usage statistics
    times_referenced INTEGER DEFAULT 1,
    
    -- Quality indicators
    has_citations BOOLEAN DEFAULT FALSE,
    has_methodology BOOLEAN DEFAULT FALSE,
    
    -- Domain-based constraints
    CONSTRAINT academic_domain_check CHECK (
        (is_academic = true AND domain SIMILAR TO '%\.(edu|gov|org|ac\.uk|edu\.au|edu\.ca)$') OR
        is_academic = false
    )
);

-- Create indexes for performance
-- Index for domain-based queries
CREATE INDEX idx_research_metadata_domain ON research_metadata(domain);

-- Index for credibility-based sorting
CREATE INDEX idx_research_metadata_credibility ON research_metadata(credibility_score DESC);

-- Index for academic source filtering
CREATE INDEX idx_research_metadata_academic ON research_metadata(is_academic) WHERE is_academic = true;

-- Index for source type filtering
CREATE INDEX idx_research_metadata_source_type ON research_metadata(source_type);

-- Function to calculate credibility score based on domain and indicators
CREATE OR REPLACE FUNCTION calculate_credibility_score(
    p_domain TEXT,
    p_has_citations BOOLEAN DEFAULT FALSE,
    p_has_methodology BOOLEAN DEFAULT FALSE,
    p_source_type TEXT DEFAULT 'other'
) RETURNS FLOAT AS $$
DECLARE
    base_score FLOAT := 0.3;  -- Default score for unknown sources
BEGIN
    -- Academic domains get high base score
    IF p_domain SIMILAR TO '%\.(edu|ac\.uk|edu\.au|edu\.ca)$' THEN
        base_score := 0.8;
    -- Government domains are highly credible
    ELSIF p_domain SIMILAR TO '%\.gov$' THEN
        base_score := 0.75;
    -- Organization domains (WHO, UN, etc.)
    ELSIF p_domain SIMILAR TO '%\.org$' THEN
        base_score := 0.6;
    -- Known journal publishers
    ELSIF p_domain SIMILAR TO '%(nature\.com|science\.org|nejm\.org|bmj\.com|thelancet\.com|cell\.com|springer\.com|wiley\.com|elsevier\.com)$' THEN
        base_score := 0.85;
    -- Preprint servers (slightly lower than peer-reviewed)
    ELSIF p_domain SIMILAR TO '%(arxiv\.org|biorxiv\.org|medrxiv\.org|ssrn\.com)$' THEN
        base_score := 0.7;
    -- Reputable news organizations
    ELSIF p_domain SIMILAR TO '%(reuters\.com|apnews\.com|bbc\.com|npr\.org|wsj\.com|nytimes\.com|washingtonpost\.com)$' THEN
        base_score := 0.5;
    END IF;
    
    -- Boost score for quality indicators
    IF p_has_citations THEN
        base_score := base_score + 0.1;
    END IF;
    
    IF p_has_methodology THEN
        base_score := base_score + 0.05;
    END IF;
    
    -- Boost for specific source types
    IF p_source_type = 'journal' THEN
        base_score := base_score + 0.1;
    ELSIF p_source_type = 'government' THEN
        base_score := base_score + 0.05;
    END IF;
    
    -- Cap at 1.0
    RETURN LEAST(base_score, 1.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get or create metadata for a source
CREATE OR REPLACE FUNCTION upsert_research_metadata(
    p_source_url TEXT,
    p_domain TEXT,
    p_source_type TEXT DEFAULT 'other',
    p_has_citations BOOLEAN DEFAULT FALSE,
    p_has_methodology BOOLEAN DEFAULT FALSE,
    p_additional_metadata JSONB DEFAULT '{}'
) RETURNS TABLE (
    id BIGINT,
    credibility_score FLOAT,
    is_academic BOOLEAN,
    is_new BOOLEAN
) AS $$
DECLARE
    v_credibility_score FLOAT;
    v_is_academic BOOLEAN;
    v_id BIGINT;
    v_is_new BOOLEAN := FALSE;
BEGIN
    -- Calculate credibility score
    v_credibility_score := calculate_credibility_score(
        p_domain, 
        p_has_citations, 
        p_has_methodology, 
        p_source_type
    );
    
    -- Determine if academic
    v_is_academic := p_domain SIMILAR TO '%\.(edu|gov|ac\.uk|edu\.au|edu\.ca)$' OR 
                     p_source_type IN ('journal', 'education');
    
    -- Try to insert or update
    INSERT INTO research_metadata (
        source_url, 
        domain, 
        credibility_score, 
        is_academic,
        source_type,
        has_citations,
        has_methodology,
        metadata
    ) VALUES (
        p_source_url,
        p_domain,
        v_credibility_score,
        v_is_academic,
        p_source_type,
        p_has_citations,
        p_has_methodology,
        p_additional_metadata
    )
    ON CONFLICT (source_url) DO UPDATE SET
        times_referenced = research_metadata.times_referenced + 1,
        last_updated = NOW(),
        metadata = research_metadata.metadata || p_additional_metadata
    RETURNING research_metadata.id, research_metadata.credibility_score, research_metadata.is_academic, 
              (xmax = 0) INTO v_id, v_credibility_score, v_is_academic, v_is_new;
    
    RETURN QUERY SELECT v_id, v_credibility_score, v_is_academic, v_is_new;
END;
$$ LANGUAGE plpgsql;

-- Function to get top sources by credibility for a keyword
CREATE OR REPLACE FUNCTION get_top_sources_for_research(
    p_keyword TEXT,
    p_limit INT DEFAULT 10
) RETURNS TABLE (
    source_url TEXT,
    domain TEXT,
    credibility_score FLOAT,
    source_type TEXT,
    times_used INT,
    avg_chunk_quality FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        rm.source_url,
        rm.domain,
        rm.credibility_score,
        rm.source_type,
        rm.times_referenced as times_used,
        AVG((rd.metadata->>'credibility_score')::FLOAT) as avg_chunk_quality
    FROM research_metadata rm
    JOIN research_documents rd ON rd.metadata->>'source_url' = rm.source_url
    WHERE rd.keyword = p_keyword
    GROUP BY rm.id, rm.source_url, rm.domain, rm.credibility_score, rm.source_type, rm.times_referenced
    ORDER BY rm.credibility_score DESC, rm.times_referenced DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to analyze source diversity for a keyword
CREATE OR REPLACE FUNCTION analyze_source_diversity(p_keyword TEXT)
RETURNS TABLE (
    total_sources INT,
    academic_sources INT,
    government_sources INT,
    source_types JSONB,
    credibility_distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH source_stats AS (
        SELECT DISTINCT
            rm.*
        FROM research_metadata rm
        JOIN research_documents rd ON rd.metadata->>'source_url' = rm.source_url
        WHERE rd.keyword = p_keyword
    )
    SELECT
        COUNT(*)::INT as total_sources,
        COUNT(*) FILTER (WHERE is_academic)::INT as academic_sources,
        COUNT(*) FILTER (WHERE source_type = 'government')::INT as government_sources,
        jsonb_object_agg(source_type, count) as source_types,
        jsonb_build_object(
            'low', COUNT(*) FILTER (WHERE credibility_score < 0.3),
            'medium', COUNT(*) FILTER (WHERE credibility_score >= 0.3 AND credibility_score < 0.6),
            'high', COUNT(*) FILTER (WHERE credibility_score >= 0.6 AND credibility_score < 0.8),
            'academic', COUNT(*) FILTER (WHERE credibility_score >= 0.8)
        ) as credibility_distribution
    FROM (
        SELECT source_type, COUNT(*) as count
        FROM source_stats
        GROUP BY source_type
    ) type_counts
    CROSS JOIN (SELECT COUNT(*) FROM source_stats) total;
END;
$$ LANGUAGE plpgsql;

-- Add update trigger for last_updated
CREATE OR REPLACE FUNCTION update_research_metadata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_research_metadata_timestamp_trigger
BEFORE UPDATE ON research_metadata
FOR EACH ROW
EXECUTE FUNCTION update_research_metadata_timestamp();

-- Add comments for documentation
COMMENT ON TABLE research_metadata IS 'Registry of all research sources with credibility scoring and usage tracking';
COMMENT ON COLUMN research_metadata.credibility_score IS 'Score from 0.0-1.0 based on domain, type, and quality indicators';
COMMENT ON COLUMN research_metadata.is_academic IS 'True for .edu, .gov, and peer-reviewed journal sources';
COMMENT ON FUNCTION calculate_credibility_score IS 'Calculates credibility score based on domain and quality indicators';