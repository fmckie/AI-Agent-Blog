-- Initialize database for SEO Content Automation System
-- This script enables the pgvector extension for semantic search capabilities

-- Enable the pgvector extension to work with embedding vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema version tracking table
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

-- Insert initial version
INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial database setup with pgvector extension')
ON CONFLICT (version) DO NOTHING;

-- Create custom types for consistency
CREATE TYPE credibility_level AS ENUM ('low', 'medium', 'high', 'academic');
CREATE TYPE article_status AS ENUM ('draft', 'published', 'archived');

-- Helper function to calculate cosine similarity percentage
CREATE OR REPLACE FUNCTION cosine_similarity_percentage(
    embedding1 vector,
    embedding2 vector
) RETURNS FLOAT AS $$
BEGIN
    -- Convert cosine distance to similarity percentage
    -- 1 - cosine_distance = cosine_similarity
    RETURN (1 - (embedding1 <=> embedding2)) * 100;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Helper function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache() RETURNS void AS $$
BEGIN
    DELETE FROM research_cache 
    WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Create indexes for common queries (will be used after tables are created)
-- Note: These will be created in individual table SQL files

-- Grant necessary permissions (adjust based on your Supabase setup)
-- GRANT USAGE ON SCHEMA public TO authenticated;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;