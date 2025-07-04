-- Drive documents table for future Google Drive integration
-- This table will store embeddings and metadata for documents from Google Drive

-- Create the drive documents table (placeholder for Phase 7.4)
CREATE TABLE IF NOT EXISTS drive_documents (
    -- Primary identifier
    id BIGSERIAL PRIMARY KEY,
    
    -- Google Drive identifiers
    drive_file_id TEXT NOT NULL UNIQUE,
    drive_folder_id TEXT,
    
    -- File metadata
    file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT,
    
    -- Document metadata
    title TEXT,
    description TEXT,
    
    -- Content for embedding
    content TEXT,
    content_hash TEXT,  -- MD5 hash to detect changes
    
    -- Embedding vector (1536 dimensions for text-embedding-3-small)
    embedding vector(1536),
    
    -- Processing metadata
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status TEXT CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    processing_error TEXT,
    
    -- Version tracking
    version INTEGER DEFAULT 1,
    previous_version_id BIGINT REFERENCES drive_documents(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    modified_at TIMESTAMP WITH TIME ZONE,  -- From Drive metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Integration tracking
    source_type TEXT DEFAULT 'drive' CHECK (source_type IN ('drive', 'manual_upload', 'api')),
    
    -- Usage tracking
    times_referenced INTEGER DEFAULT 0,
    last_referenced_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata storage for additional Drive properties
    drive_metadata JSONB DEFAULT '{}',
    -- Expected fields:
    -- - owners: [{"emailAddress": "...", "displayName": "..."}]
    -- - permissions: [...]
    -- - webViewLink: "https://docs.google.com/..."
    -- - iconLink: "https://drive-thirdparty.googleusercontent.com/..."
    -- - capabilities: {"canEdit": true, "canComment": true}
    
    -- Content metadata
    content_metadata JSONB DEFAULT '{}',
    -- Expected fields:
    -- - word_count: 1500
    -- - language: "en"
    -- - topics: ["diabetes", "nutrition"]
    -- - document_type: "research_paper"
    -- - has_citations: true
    
    -- Constraints
    CONSTRAINT file_size_positive CHECK (file_size_bytes >= 0),
    CONSTRAINT version_positive CHECK (version > 0)
);

-- Create indexes for performance
-- Index for Drive file ID lookups
CREATE INDEX idx_drive_documents_file_id ON drive_documents(drive_file_id);

-- Index for folder-based queries
CREATE INDEX idx_drive_documents_folder_id ON drive_documents(drive_folder_id) 
WHERE drive_folder_id IS NOT NULL;

-- Index for processing status
CREATE INDEX idx_drive_documents_processing_status ON drive_documents(processing_status);

-- Index for content changes
CREATE INDEX idx_drive_documents_content_hash ON drive_documents(content_hash);

-- Index for last sync time (for incremental updates)
CREATE INDEX idx_drive_documents_last_synced ON drive_documents(last_synced_at);

-- Vector index for similarity search (when implemented)
-- CREATE INDEX idx_drive_documents_embedding ON drive_documents 
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- Function to search Drive documents (placeholder)
CREATE OR REPLACE FUNCTION search_drive_documents(
    query_embedding vector(1536),
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
) RETURNS TABLE (
    id BIGINT,
    drive_file_id TEXT,
    file_name TEXT,
    title TEXT,
    similarity FLOAT,
    last_synced_at TIMESTAMP WITH TIME ZONE
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Placeholder for future implementation
    -- Will implement semantic search across Drive documents
    RAISE NOTICE 'Drive document search not yet implemented';
    RETURN;
END;
$$;

-- Function to track document changes (placeholder)
CREATE OR REPLACE FUNCTION track_drive_document_change(
    p_drive_file_id TEXT,
    p_new_content_hash TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_current_hash TEXT;
    v_has_changed BOOLEAN;
BEGIN
    -- Check if content has changed
    SELECT content_hash INTO v_current_hash
    FROM drive_documents
    WHERE drive_file_id = p_drive_file_id
    ORDER BY version DESC
    LIMIT 1;
    
    v_has_changed := v_current_hash IS DISTINCT FROM p_new_content_hash;
    
    RETURN v_has_changed;
END;
$$ LANGUAGE plpgsql;

-- Function to get folder statistics (placeholder)
CREATE OR REPLACE FUNCTION get_drive_folder_stats(p_folder_id TEXT)
RETURNS TABLE (
    total_documents INTEGER,
    processed_documents INTEGER,
    failed_documents INTEGER,
    total_size_mb FLOAT,
    last_sync_time TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_documents,
        COUNT(*) FILTER (WHERE processing_status = 'completed')::INTEGER as processed_documents,
        COUNT(*) FILTER (WHERE processing_status = 'failed')::INTEGER as failed_documents,
        SUM(file_size_bytes) / 1024.0 / 1024.0 as total_size_mb,
        MAX(last_synced_at) as last_sync_time
    FROM drive_documents
    WHERE drive_folder_id = p_folder_id;
END;
$$ LANGUAGE plpgsql;

-- Add update trigger for last_synced_at
CREATE OR REPLACE FUNCTION update_drive_document_sync_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_synced_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_drive_document_sync_time_trigger
BEFORE UPDATE ON drive_documents
FOR EACH ROW
WHEN (OLD.content_hash IS DISTINCT FROM NEW.content_hash)
EXECUTE FUNCTION update_drive_document_sync_time();

-- Add comments for documentation
COMMENT ON TABLE drive_documents IS 'Stores embeddings and metadata for Google Drive documents (Phase 7.4 - Future Implementation)';
COMMENT ON COLUMN drive_documents.embedding IS 'OpenAI text-embedding-3-small vector for semantic search';
COMMENT ON COLUMN drive_documents.processing_status IS 'Current state of document processing pipeline';
COMMENT ON COLUMN drive_documents.version IS 'Version number for tracking document changes over time';

-- Note: This table is a placeholder for Phase 7.4 implementation
-- Additional features to implement:
-- 1. OAuth token storage and refresh
-- 2. Folder watching configuration
-- 3. Processing queue management
-- 4. Batch embedding generation
-- 5. Change detection and incremental updates