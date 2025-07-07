# Google Drive Integration Implementation Guide

*Last Updated: January 7, 2025*

## Overview

This guide provides a step-by-step implementation plan for integrating Google Drive functionality into our SEO Content Automation RAG system. We're following the patterns established in the Example RAG Pipeline, which has proven to be a robust and well-tested approach.

### Goals
- [ ] Enable automatic upload of generated articles to Google Drive
- [ ] Monitor Drive folders for new research documents
- [ ] Create embeddings for Drive documents to enhance RAG capabilities
- [ ] Implement bidirectional sync between local storage and Drive

### Reference Implementation
We're adapting patterns from: `/Example RAG Pipeline/RAG_Pipeline/Google_Drive/`

---

## Prerequisites

### Google Cloud Setup
- [✓] Create a Google Cloud Project
  - Go to https://console.cloud.google.com
  - Create new project or select existing
  - Note the project ID
- [✓] Enable Google Drive API
  - Navigate to APIs & Services > Library
  - Search for "Google Drive API"
  - Click Enable
- [✓] Create OAuth 2.0 Credentials
  - Go to APIs & Services > Credentials
  - Click "Create Credentials" > "OAuth client ID"
  - Choose "Desktop app" as application type
  - Download credentials as `credentials.json`
- [✓] Set up OAuth consent screen
  - Configure basic app information
  - Add test users if in development
  - Add required scopes

### Python Dependencies
Add to requirements.txt:
- [✓] `google-api-python-client`
- [✓] `google-auth-httplib2`
- [✓] `google-auth-oauthlib`

### Environment Variables
Add to .env:
- [✓] `GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json`
- [✓] `GOOGLE_DRIVE_TOKEN_PATH=token.json`
- [✓] `GOOGLE_DRIVE_FOLDER_ID=<your-folder-id>` (optional)
- [✓] `GOOGLE_DRIVE_UPLOAD_FOLDER_ID=<your-upload-folder-id>`

---

## Implementation Steps

### Phase 1: Authentication Module (rag/drive/auth.py)

#### 1.1 Basic Structure
- [✓] Create `rag/drive/` directory
- [✓] Create `rag/drive/__init__.py`
- [✓] Create `rag/drive/auth.py`

#### 1.2 OAuth Implementation
- [✓] Define SCOPES constant:
  ```python
  SCOPES = [
      'https://www.googleapis.com/auth/drive.metadata.readonly',
      'https://www.googleapis.com/auth/drive.readonly',
      'https://www.googleapis.com/auth/drive.file'
  ]
  ```
- [✓] Create `GoogleDriveAuth` class
- [✓] Implement `authenticate()` method:
  - [✓] Check for existing token.json
  - [✓] Validate token and refresh if needed
  - [✓] Run OAuth flow if no valid token
  - [✓] Save token for future use
- [ ] Add service account support (optional - deferred)
- [✓] Create `get_drive_service()` helper function

#### 1.3 Error Handling
- [✓] Handle `RefreshError` for expired tokens
- [✓] Add network error handling
- [ ] Implement retry logic with exponential backoff (will add in API calls)
- [ ] Create custom exceptions for auth errors (using standard exceptions for now)

### Phase 2: Configuration (rag/drive/config.py)

#### 2.1 Configuration Structure
- [ ] Create `rag/drive/config.py`
- [ ] Define configuration schema:
  ```python
  {
      "supported_mime_types": [...],
      "export_mime_types": {...},
      "watch_folder_id": "...",
      "sync_interval": 60,
      "max_retries": 3
  }
  ```

#### 2.2 Integration with Main Config
- [ ] Extend main `rag/config.py` with Drive settings
- [ ] Add validation for Drive-specific settings
- [ ] Create default configuration values
- [ ] Add config loading from JSON file option

### Phase 3: Article Uploader (rag/drive/uploader.py)

#### 3.1 Basic Uploader
- [✓] Create `ArticleUploader` class
- [✓] Implement `upload_html_as_doc()` method:
  - [✓] Convert HTML to Google Docs format
  - [✓] Set document title from article metadata
  - [✓] Handle special characters and formatting
- [✓] Add folder organization:
  - [✓] Create year/month folder structure
  - [✓] Check if folders exist before creating
  - [✓] Handle folder permissions

#### 3.2 Metadata Management
- [✓] Attach custom properties to uploaded files:
  - [✓] Keywords used
  - [✓] Generation timestamp
  - [✓] Research sources count
  - [✓] Local file path reference
- [✓] Implement `update_file_metadata()` method
- [ ] Add version tracking system (deferred to future phase)

#### 3.3 Batch Operations
- [ ] Implement batch upload functionality (basic support exists)
- [ ] Add progress tracking for multiple files
- [ ] Create upload queue management
- [ ] Handle partial upload failures

### Phase 4: Folder Watcher (rag/drive/watcher.py)

#### 4.1 Core Watcher Implementation
- [ ] Create `GoogleDriveWatcher` class (following Example pattern)
- [ ] Implement initialization:
  - [ ] Accept credentials and token paths
  - [ ] Support specific folder or full Drive watching
  - [ ] Load last check time from persistence
- [ ] Create `get_changes()` method:
  - [ ] Query for files modified since last check
  - [ ] Support recursive folder traversal
  - [ ] Update last check time after query

#### 4.2 File Processing Pipeline
- [ ] Implement `process_file()` method:
  - [ ] Check if file is supported type
  - [ ] Download file content
  - [ ] Extract text using existing processor
  - [ ] Generate embeddings
  - [ ] Store in database
- [ ] Add support for Google Workspace files:
  - [ ] Export Google Docs as plain text
  - [ ] Export Sheets as CSV
  - [ ] Export Slides as text

#### 4.3 Change Detection
- [ ] Implement `check_for_deleted_files()`:
  - [ ] Track known files in memory/database
  - [ ] Detect trashed or deleted files
  - [ ] Clean up database entries
- [ ] Add modification tracking:
  - [ ] Compare file versions
  - [ ] Update embeddings for modified files

#### 4.4 Continuous Monitoring
- [ ] Implement `watch_for_changes()` loop:
  - [ ] Configurable check interval
  - [ ] Graceful shutdown handling
  - [ ] Error recovery and logging
- [ ] Add state persistence:
  - [ ] Save watcher state to database
  - [ ] Resume from last position after restart

### Phase 5: Database Schema Updates

#### 5.1 New Tables
- [ ] Create migration for `drive_sync_status`:
  ```sql
  CREATE TABLE drive_sync_status (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      file_id TEXT UNIQUE NOT NULL,
      local_path TEXT,
      drive_url TEXT,
      last_synced TIMESTAMP WITH TIME ZONE,
      sync_status TEXT,
      error_message TEXT
  );
  ```

#### 5.2 Table Modifications
- [ ] Add to `generated_articles`:
  - [ ] `drive_file_id TEXT`
  - [ ] `drive_url TEXT`
  - [ ] `uploaded_at TIMESTAMP WITH TIME ZONE`
- [ ] Add to `research_documents`:
  - [ ] `source_type TEXT` (enum: 'api', 'file', 'drive')
  - [ ] `drive_file_id TEXT`

#### 5.3 Indexes
- [ ] Create index on `drive_file_id` columns
- [ ] Add composite index for sync queries
- [ ] Ensure foreign key constraints

### Phase 6: Storage Integration (rag/drive/storage.py)

#### 6.1 Database Operations
- [ ] Create `DriveStorageHandler` class
- [ ] Implement CRUD operations:
  - [ ] `save_drive_document()`
  - [ ] `get_drive_document()`
  - [ ] `update_sync_status()`
  - [ ] `delete_drive_document()`
- [ ] Add transaction support for atomic operations

#### 6.2 Sync Management
- [ ] Track sync status for each file
- [ ] Implement conflict resolution
- [ ] Add retry queue for failed syncs
- [ ] Create sync history logging

### Phase 7: Integration with Main Workflow

#### 7.1 Workflow Modifications
- [ ] Update `workflow.py`:
  - [ ] Add Drive upload after article generation
  - [ ] Make upload optional via configuration
  - [ ] Handle upload failures gracefully
- [ ] Create post-generation hook:
  - [ ] Trigger after successful local save
  - [ ] Queue for Drive upload
  - [ ] Update article metadata with Drive URL

#### 7.2 Research Agent Integration
- [ ] Modify research tools to check Drive documents
- [ ] Add Drive search capabilities
- [ ] Combine Drive and web research results
- [ ] Implement source attribution

### Phase 8: CLI Commands

#### 8.1 Authentication Commands
- [ ] `python main.py drive auth`
  - [ ] Initialize OAuth flow
  - [ ] Save credentials
  - [ ] Test connection
- [ ] `python main.py drive logout`
  - [ ] Remove stored token
  - [ ] Clear credentials

#### 8.2 Sync Commands
- [ ] `python main.py drive sync`
  - [ ] Manual sync trigger
  - [ ] Show sync progress
  - [ ] Report results
- [ ] `python main.py drive watch [--folder-id]`
  - [ ] Start folder watcher
  - [ ] Support daemon mode
  - [ ] Add stop command

#### 8.3 Management Commands
- [ ] `python main.py drive list`
  - [ ] List synced articles
  - [ ] Filter by date/status
  - [ ] Show sync statistics
- [ ] `python main.py drive upload <file>`
  - [ ] Upload specific file
  - [ ] Support batch upload
  - [ ] Show upload URL

#### 8.4 Search Commands
- [ ] `python main.py drive search <query>`
  - [ ] Search Drive documents
  - [ ] Show relevance scores
  - [ ] Include in RAG results

### Phase 9: Testing

#### 9.1 Unit Tests
- [ ] Create `tests/test_drive_auth.py`:
  - [ ] Test OAuth flow
  - [ ] Test token refresh
  - [ ] Test error handling
- [ ] Create `tests/test_drive_uploader.py`:
  - [ ] Test HTML to Docs conversion
  - [ ] Test folder creation
  - [ ] Test metadata attachment
- [ ] Create `tests/test_drive_watcher.py`:
  - [ ] Test change detection
  - [ ] Test file processing
  - [ ] Test deletion handling

#### 9.2 Integration Tests
- [ ] Test complete upload flow
- [ ] Test watcher with real Drive changes
- [ ] Test error recovery scenarios
- [ ] Test concurrent operations

#### 9.3 Manual Testing
- [ ] Upload test article to Drive
- [ ] Verify folder structure
- [ ] Test watcher with various file types
- [ ] Verify database synchronization

### Phase 10: Documentation

#### 10.1 Setup Guide
- [ ] Write Drive API setup instructions
- [ ] Document credential configuration
- [ ] Add troubleshooting section
- [ ] Include security best practices

#### 10.2 Usage Documentation
- [ ] Document all CLI commands
- [ ] Add workflow diagrams
- [ ] Create example scenarios
- [ ] Write API reference

#### 10.3 Code Documentation
- [ ] Add docstrings to all classes/methods
- [ ] Create inline comments for complex logic
- [ ] Generate API documentation
- [ ] Add type hints throughout

---

## Configuration Files

### Example drive_config.json
```json
{
  "supported_mime_types": [
    "application/pdf",
    "text/plain",
    "text/html",
    "text/csv",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "image/png",
    "image/jpeg"
  ],
  "export_mime_types": {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain"
  },
  "text_processing": {
    "chunk_size": 1000,
    "chunk_overlap": 200
  },
  "sync_settings": {
    "check_interval": 300,
    "max_retries": 3,
    "batch_size": 10
  }
}
```

---

## Verification Steps

### Component Verification
- [ ] Auth: Successfully obtain and refresh token
- [ ] Uploader: Article appears in Drive with correct formatting
- [ ] Watcher: Detects new files within configured interval
- [ ] Storage: Database correctly tracks all Drive files
- [ ] CLI: All commands execute without errors

### End-to-End Verification
- [ ] Generate article → Auto-upload to Drive → Verify in Drive UI
- [ ] Add document to Drive → Watcher detects → Embeddings created
- [ ] Modify Drive document → Changes reflected in database
- [ ] Delete Drive document → Cleanup in database

---

## Troubleshooting

### Common Issues
1. **Authentication Errors**
   - Check credentials.json is valid
   - Ensure OAuth consent screen is configured
   - Verify scopes match requirements

2. **Upload Failures**
   - Check Drive storage quota
   - Verify folder permissions
   - Review API rate limits

3. **Watcher Not Detecting Changes**
   - Verify folder ID is correct
   - Check last_check_time persistence
   - Review API query filters

4. **Database Sync Issues**
   - Check foreign key constraints
   - Verify transaction handling
   - Review error logs

---

## Notes and Best Practices

1. **Security**
   - Never commit credentials.json or token.json
   - Use service accounts for production
   - Implement proper access controls

2. **Performance**
   - Batch API requests when possible
   - Implement caching for frequently accessed files
   - Use async operations for better throughput

3. **Reliability**
   - Always implement retry logic
   - Use transactions for database operations
   - Log all operations for debugging

4. **Monitoring**
   - Track API usage and quotas
   - Monitor sync lag times
   - Alert on repeated failures

---

## Implementation Timeline

- **Week 1**: Authentication and Configuration (Phases 1-2)
- **Week 2**: Uploader and Database Schema (Phases 3, 5)
- **Week 3**: Watcher Implementation (Phase 4)
- **Week 4**: Integration and CLI (Phases 6-8)
- **Week 5**: Testing and Documentation (Phases 9-10)

---

## Success Criteria

- [ ] All generated articles automatically upload to Drive
- [ ] Drive documents are searchable through RAG system
- [ ] Bidirectional sync maintains consistency
- [ ] System handles errors gracefully
- [ ] Performance meets requirements (< 5s upload time)
- [ ] All tests pass with > 90% coverage
- [ ] Documentation is complete and accurate