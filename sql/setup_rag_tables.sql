-- RAG System Database Setup for Supabase
-- Run this script in your Supabase SQL editor

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables if needed (be careful in production!)
-- DROP TABLE IF EXISTS cache_entries CASCADE;
-- DROP TABLE IF EXISTS research_chunks CASCADE;

-- Create the research_chunks table for storing text chunks with embeddings
CREATE TABLE IF NOT EXISTS research_chunks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small dimensions
    metadata JSONB DEFAULT '{}',
    keyword TEXT,
    chunk_index INTEGER NOT NULL,
    source_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the cache_entries table for quick keyword lookups
CREATE TABLE IF NOT EXISTS cache_entries (
    id TEXT PRIMARY KEY,
    keyword TEXT NOT NULL,
    keyword_normalized TEXT NOT NULL,
    research_summary TEXT NOT NULL,
    chunk_ids TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Create indexes for better performance
-- Vector similarity search index (using IVFFlat for balance of speed/accuracy)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
    ON research_chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust 'lists' based on your data size

-- Text search indexes
CREATE INDEX IF NOT EXISTS idx_chunks_keyword 
    ON research_chunks (keyword);
    
CREATE INDEX IF NOT EXISTS idx_chunks_source 
    ON research_chunks (source_id);
    
CREATE INDEX IF NOT EXISTS idx_chunks_created 
    ON research_chunks (created_at DESC);

-- Cache lookup indexes
CREATE INDEX IF NOT EXISTS idx_cache_keyword 
    ON cache_entries (keyword_normalized);
    
CREATE INDEX IF NOT EXISTS idx_cache_expires 
    ON cache_entries (expires_at);
    
CREATE INDEX IF NOT EXISTS idx_cache_hits 
    ON cache_entries (hit_count DESC);

-- Create updated_at trigger for research_chunks
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_research_chunks_updated_at 
    BEFORE UPDATE ON research_chunks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add Row Level Security (RLS) policies if needed
-- Note: For service role key, RLS is bypassed

-- Enable RLS on tables (optional, depends on your security model)
-- ALTER TABLE research_chunks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cache_entries ENABLE ROW LEVEL SECURITY;

-- Create policies for service role (full access)
-- CREATE POLICY "Service role has full access to research_chunks" 
--     ON research_chunks 
--     FOR ALL 
--     USING (auth.role() = 'service_role');

-- CREATE POLICY "Service role has full access to cache_entries" 
--     ON cache_entries 
--     FOR ALL 
--     USING (auth.role() = 'service_role');

-- Verify setup
DO $$ 
BEGIN
    -- Check if pgvector is installed
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE 'WARNING: pgvector extension is not installed!';
    ELSE
        RAISE NOTICE 'SUCCESS: pgvector extension is installed';
    END IF;
    
    -- Check tables
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'research_chunks') THEN
        RAISE NOTICE 'SUCCESS: research_chunks table exists';
    ELSE
        RAISE NOTICE 'ERROR: research_chunks table does not exist';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cache_entries') THEN
        RAISE NOTICE 'SUCCESS: cache_entries table exists';
    ELSE
        RAISE NOTICE 'ERROR: cache_entries table does not exist';
    END IF;
END $$;

-- Sample queries to test the setup

-- Test vector storage (you'll need actual embeddings)
-- INSERT INTO research_chunks (id, content, embedding, keyword, chunk_index, source_id)
-- VALUES (
--     'test_chunk_1',
--     'This is a test chunk for vector storage',
--     '[0.1, 0.2, 0.3, ...]'::vector(1536),  -- Replace with actual 1536-dim vector
--     'test',
--     0,
--     'test_source_1'
-- );

-- Test similarity search
-- SELECT id, content, 1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) as similarity
-- FROM research_chunks
-- WHERE 1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) > 0.7
-- ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
-- LIMIT 10;

-- View table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('research_chunks', 'cache_entries')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;