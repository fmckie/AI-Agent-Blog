-- Research documents table for storing chunked research content with embeddings
-- This table enables semantic search across all research gathered by the system

-- Create the main research documents table
CREATE TABLE IF NOT EXISTS research_documents (
    -- Primary identifier
    id BIGSERIAL PRIMARY KEY,
    
    -- The keyword that triggered this research
    keyword TEXT NOT NULL,
    
    -- The actual content chunk (research finding, fact, or insight)
    content TEXT NOT NULL,
    
    -- Metadata about this chunk stored as JSON
    metadata JSONB NOT NULL DEFAULT '{}',
    -- Expected metadata fields:
    -- - source_url: Original URL of the research
    -- - source_title: Title of the source article/paper
    -- - chunk_index: Position of this chunk in the original document
    -- - credibility_score: 0.0 to 1.0 score
    -- - is_academic: Boolean for .edu/.gov/journal sources
    -- - extraction_date: When this was extracted
    -- - key_topics: Array of main topics in this chunk
    
    -- The embedding vector (1536 dimensions for text-embedding-3-small)
    embedding vector(1536) NOT NULL,
    
    -- Timestamp for when this research was stored
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Link to the research metadata table (for source tracking)
    source_metadata_id BIGINT,
    
    -- Ensure content is not empty
    CONSTRAINT content_not_empty CHECK (char_length(content) > 0)
);

-- Create indexes for performance
-- Index for fast keyword lookups
CREATE INDEX idx_research_documents_keyword ON research_documents(keyword);

-- Index for timestamp-based queries (finding recent research)
CREATE INDEX idx_research_documents_created_at ON research_documents(created_at DESC);

-- GIN index for JSONB metadata queries
CREATE INDEX idx_research_documents_metadata ON research_documents USING gin(metadata);

-- Create vector index for similarity searches
-- Using ivfflat index for better performance on large datasets
CREATE INDEX idx_research_documents_embedding ON research_documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Function to search for similar research documents
CREATE OR REPLACE FUNCTION search_similar_research(
    query_embedding vector(1536),
    search_keyword TEXT DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
) RETURNS TABLE (
    id BIGINT,
    keyword TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rd.id,
        rd.keyword,
        rd.content,
        rd.metadata,
        1 - (rd.embedding <=> query_embedding) as similarity,
        rd.created_at
    FROM research_documents rd
    WHERE 
        -- Filter by keyword if provided
        (search_keyword IS NULL OR rd.keyword = search_keyword)
        -- Only return results above similarity threshold
        AND (1 - (rd.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY rd.embedding <=> query_embedding
    LIMIT max_results;
END;
$$;

-- Function to find research by academic sources
CREATE OR REPLACE FUNCTION find_academic_research(
    search_keyword TEXT,
    limit_results INT DEFAULT 20
) RETURNS TABLE (
    id BIGINT,
    keyword TEXT,
    content TEXT,
    source_url TEXT,
    credibility_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rd.id,
        rd.keyword,
        rd.content,
        rd.metadata->>'source_url' as source_url,
        (rd.metadata->>'credibility_score')::FLOAT as credibility_score,
        rd.created_at
    FROM research_documents rd
    WHERE 
        rd.keyword = search_keyword
        AND (rd.metadata->>'is_academic')::BOOLEAN = true
    ORDER BY 
        (rd.metadata->>'credibility_score')::FLOAT DESC,
        rd.created_at DESC
    LIMIT limit_results;
END;
$$;

-- Function to get research statistics by keyword
CREATE OR REPLACE FUNCTION get_research_stats(search_keyword TEXT)
RETURNS TABLE (
    total_chunks INT,
    academic_sources INT,
    avg_credibility FLOAT,
    date_range JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INT as total_chunks,
        COUNT(*) FILTER (WHERE (metadata->>'is_academic')::BOOLEAN = true)::INT as academic_sources,
        AVG((metadata->>'credibility_score')::FLOAT) as avg_credibility,
        jsonb_build_object(
            'earliest', MIN(created_at),
            'latest', MAX(created_at)
        ) as date_range
    FROM research_documents
    WHERE keyword = search_keyword;
END;
$$;

-- Trigger to validate metadata before insert
CREATE OR REPLACE FUNCTION validate_research_metadata()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure required metadata fields exist
    IF NOT (NEW.metadata ? 'source_url') THEN
        RAISE EXCEPTION 'metadata must contain source_url';
    END IF;
    
    IF NOT (NEW.metadata ? 'credibility_score') THEN
        RAISE EXCEPTION 'metadata must contain credibility_score';
    END IF;
    
    -- Validate credibility score range
    IF (NEW.metadata->>'credibility_score')::FLOAT < 0 OR 
       (NEW.metadata->>'credibility_score')::FLOAT > 1 THEN
        RAISE EXCEPTION 'credibility_score must be between 0 and 1';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_research_metadata_trigger
BEFORE INSERT OR UPDATE ON research_documents
FOR EACH ROW
EXECUTE FUNCTION validate_research_metadata();

-- Add comments for documentation
COMMENT ON TABLE research_documents IS 'Stores chunked research content with vector embeddings for semantic search';
COMMENT ON COLUMN research_documents.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';
COMMENT ON COLUMN research_documents.metadata IS 'JSONB containing source_url, credibility_score, is_academic, and other metadata';