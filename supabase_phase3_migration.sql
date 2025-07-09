-- Phase 3: Advanced Supabase Storage Migration Script
-- Purpose: Create tables for storing research content with vector embeddings
-- Database: SEO Automation (qlizuiolutwgpjzulpij)

-- ============================================
-- STEP 1: Enable pgvector Extension
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- STEP 2: Create Research Sources Table
-- ============================================
-- Stores scraped article metadata and content
CREATE TABLE research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    full_content TEXT,
    excerpt TEXT,
    credibility_score FLOAT,
    source_type TEXT,
    authors JSONB,
    publication_date TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for research_sources
CREATE INDEX idx_sources_domain ON research_sources(domain);
CREATE INDEX idx_sources_credibility ON research_sources(credibility_score DESC);
CREATE INDEX idx_sources_created ON research_sources(created_at DESC);
CREATE INDEX idx_sources_metadata ON research_sources USING GIN(metadata);

-- ============================================
-- STEP 3: Create Research Findings Table
-- ============================================
-- Stores aggregated findings from research sessions
CREATE TABLE research_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    research_summary TEXT,
    main_findings JSONB,
    key_statistics JSONB,
    research_gaps JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for research_findings
CREATE INDEX idx_findings_keyword ON research_findings(keyword);
CREATE INDEX idx_findings_created ON research_findings(created_at DESC);

-- ============================================
-- STEP 4: Create Source Relationships Table
-- ============================================
-- Tracks relationships between sources (citations, references, etc.)
CREATE TABLE source_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_sources(id) ON DELETE CASCADE,
    related_source_id UUID REFERENCES research_sources(id) ON DELETE CASCADE,
    relationship_type TEXT,
    similarity_score FLOAT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_id, related_source_id)
);

-- Create indexes for source_relationships
CREATE INDEX idx_relationships_source ON source_relationships(source_id);
CREATE INDEX idx_relationships_related ON source_relationships(related_source_id);
CREATE INDEX idx_relationships_similarity ON source_relationships(similarity_score DESC);

-- ============================================
-- STEP 5: Create Content Chunks Table
-- ============================================
-- Stores article content in chunks with embeddings for vector search
CREATE TABLE content_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_sources(id) ON DELETE CASCADE,
    chunk_text TEXT,
    chunk_embedding vector(1536),  -- For OpenAI text-embedding-ada-002
    chunk_number INTEGER,
    chunk_overlap INTEGER DEFAULT 50,
    chunk_metadata JSONB,
    chunk_type TEXT,
    embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create vector index for similarity search (cosine distance)
CREATE INDEX idx_chunks_embedding_cosine 
ON content_chunks 
USING ivfflat (chunk_embedding vector_cosine_ops)
WITH (lists = 100);  -- Will adjust based on row count

-- Create additional indexes
CREATE INDEX idx_chunks_source_id ON content_chunks(source_id);
CREATE INDEX idx_chunks_metadata ON content_chunks USING GIN(chunk_metadata);

-- ============================================
-- STEP 6: Create Embedding Queue Table
-- ============================================
-- Tracks embedding generation status
CREATE TABLE embedding_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_sources(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- Create indexes for embedding_queue
CREATE INDEX idx_queue_status ON embedding_queue(status);
CREATE INDEX idx_queue_created ON embedding_queue(created_at);

-- ============================================
-- STEP 7: Create Search History Table
-- ============================================
-- Tracks vector searches for performance monitoring
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT,
    query_embedding vector(1536),
    result_count INTEGER,
    avg_similarity FLOAT,
    execution_time_ms INTEGER,
    filters_applied JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for search history
CREATE INDEX idx_search_history_created ON search_history(created_at DESC);

-- ============================================
-- STEP 8: Create Helper Functions
-- ============================================

-- Function to calculate optimal index lists based on row count
CREATE OR REPLACE FUNCTION calculate_optimal_lists(table_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    row_count BIGINT;
    optimal_lists INTEGER;
BEGIN
    EXECUTE format('SELECT COUNT(*) FROM %I', table_name) INTO row_count;
    -- Formula: lists = 4 * sqrt(rows)
    optimal_lists := GREATEST(10, LEAST(1000, 4 * SQRT(row_count)::INTEGER));
    RETURN optimal_lists;
END;
$$ LANGUAGE plpgsql;

-- Function for semantic search with metadata filtering
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    domain_filter TEXT DEFAULT NULL,
    source_type_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    source_id UUID,
    chunk_text TEXT,
    source_title TEXT,
    source_url TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id as chunk_id,
        c.source_id,
        c.chunk_text,
        s.title as source_title,
        s.url as source_url,
        1 - (c.chunk_embedding <=> query_embedding) as similarity
    FROM content_chunks c
    JOIN research_sources s ON s.id = c.source_id
    WHERE 
        1 - (c.chunk_embedding <=> query_embedding) > match_threshold
        AND (domain_filter IS NULL OR s.domain = domain_filter)
        AND (source_type_filter IS NULL OR s.source_type = source_type_filter)
    ORDER BY c.chunk_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to find related sources based on content similarity
CREATE OR REPLACE FUNCTION find_related_sources(
    source_id_input UUID,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
)
RETURNS TABLE (
    related_source_id UUID,
    title TEXT,
    url TEXT,
    avg_similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH source_embeddings AS (
        SELECT 
            chunk_embedding
        FROM content_chunks
        WHERE source_id = source_id_input
    ),
    similarities AS (
        SELECT 
            c2.source_id,
            AVG(1 - (se.chunk_embedding <=> c2.chunk_embedding)) as avg_similarity
        FROM source_embeddings se
        CROSS JOIN content_chunks c2
        WHERE c2.source_id != source_id_input
        GROUP BY c2.source_id
        HAVING AVG(1 - (se.chunk_embedding <=> c2.chunk_embedding)) > similarity_threshold
    )
    SELECT 
        s.id as related_source_id,
        s.title,
        s.url,
        sim.avg_similarity
    FROM similarities sim
    JOIN research_sources s ON s.id = sim.source_id
    ORDER BY sim.avg_similarity DESC
    LIMIT max_results;
END;
$$;

-- ============================================
-- STEP 9: Create Update Triggers
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_research_sources_updated_at 
BEFORE UPDATE ON research_sources
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- STEP 10: Create Views for Common Queries
-- ============================================

-- View for sources with embedding status
CREATE VIEW v_sources_with_embedding_status AS
SELECT 
    s.id,
    s.url,
    s.title,
    s.domain,
    s.credibility_score,
    s.created_at,
    COALESCE(eq.status, 'not_queued') as embedding_status,
    COUNT(c.id) as chunk_count
FROM research_sources s
LEFT JOIN embedding_queue eq ON eq.source_id = s.id
LEFT JOIN content_chunks c ON c.source_id = s.id
GROUP BY s.id, s.url, s.title, s.domain, s.credibility_score, s.created_at, eq.status;

-- View for research statistics
CREATE VIEW v_research_statistics AS
SELECT 
    COUNT(DISTINCT rs.id) as total_sources,
    COUNT(DISTINCT rs.domain) as unique_domains,
    COUNT(cc.id) as total_chunks,
    COUNT(DISTINCT rf.id) as total_findings,
    AVG(rs.credibility_score) as avg_credibility_score,
    MAX(rs.created_at) as latest_source_added
FROM research_sources rs
LEFT JOIN content_chunks cc ON cc.source_id = rs.id
LEFT JOIN research_findings rf ON rf.keyword IN (
    SELECT DISTINCT keyword FROM research_findings
);

-- ============================================
-- STEP 11: Add Comments for Documentation
-- ============================================

COMMENT ON TABLE research_sources IS 'Stores metadata and content from scraped research articles';
COMMENT ON TABLE research_findings IS 'Aggregated findings from research sessions by keyword';
COMMENT ON TABLE source_relationships IS 'Tracks relationships between research sources';
COMMENT ON TABLE content_chunks IS 'Stores article content chunks with vector embeddings for semantic search';
COMMENT ON TABLE embedding_queue IS 'Queue for tracking embedding generation status';
COMMENT ON TABLE search_history IS 'Logs vector searches for performance monitoring';

COMMENT ON COLUMN content_chunks.chunk_embedding IS 'Vector embedding using OpenAI text-embedding-ada-002 (1536 dimensions)';
COMMENT ON COLUMN content_chunks.chunk_overlap IS 'Number of tokens overlapping with adjacent chunks for context preservation';
COMMENT ON COLUMN source_relationships.similarity_score IS 'Cosine similarity between source embeddings (0-1)';

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- Next steps:
-- 1. Run this migration script
-- 2. Verify all tables and functions created successfully
-- 3. Start populating research_sources with scraped content
-- 4. Generate embeddings for content_chunks
-- 5. Monitor performance and adjust index parameters as needed