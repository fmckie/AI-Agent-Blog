-- Google Drive sync status tracking table
-- Tracks the synchronization status of files between local system and Google Drive

CREATE TABLE IF NOT EXISTS drive_sync_status (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Google Drive file ID (unique identifier)
    file_id TEXT UNIQUE NOT NULL,
    
    -- Local reference path (e.g., "article_uuid" or "drive_doc_uuid")
    local_path TEXT,
    
    -- Google Drive web view URL
    drive_url TEXT,
    
    -- Sync status: synced, pending, processing, error
    sync_status TEXT NOT NULL DEFAULT 'pending',
    
    -- Last successful sync timestamp
    last_synced TIMESTAMP WITH TIME ZONE,
    
    -- Error message if sync failed
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_drive_sync_status_file_id ON drive_sync_status(file_id);
CREATE INDEX IF NOT EXISTS idx_drive_sync_status_sync_status ON drive_sync_status(sync_status);
CREATE INDEX IF NOT EXISTS idx_drive_sync_status_last_synced ON drive_sync_status(last_synced DESC);

-- Add RLS (Row Level Security) policy
ALTER TABLE drive_sync_status ENABLE ROW LEVEL SECURITY;

-- Create policy for service role access
CREATE POLICY "Service role can manage drive sync status" ON drive_sync_status
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_drive_sync_status_updated_at 
    BEFORE UPDATE ON drive_sync_status 
    FOR EACH ROW 
    EXECUTE PROCEDURE update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE drive_sync_status IS 'Tracks synchronization status between local files and Google Drive';
COMMENT ON COLUMN drive_sync_status.file_id IS 'Google Drive file ID - unique identifier from Drive API';
COMMENT ON COLUMN drive_sync_status.local_path IS 'Local reference path for the file (e.g., article_uuid)';
COMMENT ON COLUMN drive_sync_status.sync_status IS 'Current sync status: synced, pending, processing, error';
COMMENT ON COLUMN drive_sync_status.last_synced IS 'Timestamp of last successful synchronization';
COMMENT ON COLUMN drive_sync_status.error_message IS 'Error details if sync failed';