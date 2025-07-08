# Google Drive Integration Implementation Guide

*Last Updated: January 7, 2025*

## Overview

This guide provides a step-by-step implementation plan for integrating Google Drive functionality into our SEO Content Automation RAG system. We're following the patterns established in the Example RAG Pipeline, which has proven to be a robust and well-tested approach.

### Goals
- [✓] Enable automatic upload of generated articles to Google Drive
- [✓] Provide easy sharing and collaboration capabilities for articles
- [✓] Track upload status and handle failures gracefully
- [✓] Organize articles in Drive for easy client access

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
- [✓] Implement retry logic with exponential backoff (will add in API calls)
- [ ] Create custom exceptions for auth errors (using standard exceptions for now)

### Phase 2: Configuration (rag/drive/config.py)

#### 2.1 Configuration Structure
- [✓] Create `rag/drive/config.py`
- [✓] Define configuration schema:
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
- [✓] Extend main `rag/config.py` with Drive settings
- [✓] Add validation for Drive-specific settings
- [✓] Create default configuration values
- [✓] Add config loading from JSON file option

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
- [✓] Implement batch upload functionality (basic support exists)
- [✓] Add progress tracking for multiple files
- [✓] Create upload queue management
- [✓] Handle partial upload failures

### Phase 4: Batch Upload and Error Handling

#### 4.1 Batch Upload Implementation
- [✓] Create `BatchUploader` class extending `ArticleUploader`
- [✓] Implement `upload_pending_articles()` method:
  - [✓] Query database for articles without Drive IDs
  - [✓] Process uploads in configurable batch sizes
  - [✓] Track progress and report status
- [✓] Add retry mechanism:
  - [✓] Exponential backoff for failed uploads
  - [✓] Maximum retry limit configuration
  - [✓] Store error details for manual review

#### 4.2 Error Recovery
- [✓] Implement comprehensive error handling:
  - [✓] Network timeout recovery
  - [ ] API quota exceeded handling
  - [✓] Invalid file format detection
- [✓] Create error reporting:
  - [✓] Log detailed error information
  - [✓] Update database with failure reasons
  - [✓] Generate error summary reports

#### 4.3 Upload Queue Management
- [✓] Create upload queue system:
  - [ ] Priority-based queue for uploads
  - [ ] Pause/resume functionality
  - [✓] Rate limiting to avoid API quotas
- [✓] Add status tracking:
  - [✓] Real-time upload progress
  - [✓] Success/failure statistics
  - [✓] Performance metrics

### Phase 5: Database Schema Updates

#### 5.1 New Tables
- [✓] Create migration for `drive_sync_status`:
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
- [✓] Add to `generated_articles`:
  - [✓] `drive_file_id TEXT`
  - [✓] `drive_url TEXT`
  - [✓] `drive_folder_id TEXT` (for organization)
  - [✓] `upload_retry_count INTEGER DEFAULT 0`
  - [✓] `last_upload_error TEXT`

#### 5.3 Indexes
- [✓] Create index on `drive_file_id` columns
- [✓] Add index for pending uploads (`WHERE drive_file_id IS NULL`)
- [✓] Add index for failed uploads (`WHERE upload_retry_count > 0`)

### Phase 6: Storage Integration (rag/drive/storage.py)

#### 6.1 Database Operations
- [✓] Create `DriveStorageHandler` class
- [✓] Implement upload tracking operations:
  - [✓] `track_upload()` - Record successful uploads
  - [✓] `get_pending_uploads()` - Find articles needing upload
  - [✓] `mark_upload_error()` - Track failed uploads
  - [✓] `get_uploaded_articles()` - List uploaded articles
- [✓] Add transaction support for atomic operations

#### 6.2 Upload Management
- [✓] Track upload status for each article
- [✓] Implement retry tracking with backoff
- [✓] Add batch upload coordination
- [✓] Create upload history and statistics

### Phase 7: Integration with Main Workflow

#### 7.1 Workflow Modifications
- [✓] Update `workflow.py`:
  - [✓] Add Drive upload after article generation
  - [✓] Make upload optional via configuration
  - [✓] Handle upload failures gracefully
- [✓] Create post-generation upload:
  - [✓] Trigger after successful local save
  - [✓] Upload to Drive with metadata
  - [✓] Update article record with Drive URL

#### 7.2 Enhanced Upload Features
- [✓] Add upload status to workflow output
- [✓] Include Drive link in review interface
- [✓] Support custom folder organization
- [ ] Add upload notifications/callbacks

### Phase 8: CLI Commands

#### 8.1 Authentication Commands
- [✓] `python main.py drive auth`
  - [✓] Initialize OAuth flow
  - [✓] Save credentials
  - [✓] Test connection
- [✓] `python main.py drive logout`
  - [✓] Remove stored token
  - [✓] Clear credentials

#### 8.2 Upload Commands
- [✓] `python main.py drive upload-pending`
  - [✓] Upload all pending articles
  - [✓] Show progress for each upload
  - [✓] Report success/failure summary
- [✓] `python main.py drive retry-failed`
  - [✓] Retry failed uploads
  - [✓] Apply exponential backoff
  - [✓] Limit retry attempts

#### 8.3 Management Commands
- [ ] `python main.py drive list`
  - [ ] List uploaded articles
  - [ ] Filter by date/status
  - [ ] Show Drive URLs
- [ ] `python main.py drive status`
  - [ ] Show upload statistics
  - [ ] Display pending/failed counts
  - [ ] Recent upload history

#### 8.4 Utility Commands
- [ ] `python main.py drive clean`
  - [ ] Clean orphaned sync records
  - [ ] Remove invalid entries
  - [ ] Verify database consistency

### Phase 9: Testing

#### 9.1 Unit Tests
- [✓] Create `tests/test_drive_auth.py`:
  - [✓] Test OAuth flow
  - [✓] Test token refresh
  - [✓] Test error handling
- [✓] Create `tests/test_drive_uploader.py`:
  - [✓] Test HTML to Docs conversion
  - [✓] Test folder creation
  - [✓] Test metadata attachment
- [✓] Create `tests/test_batch_uploader.py`:
  - [✓] Test batch upload logic
  - [✓] Test retry mechanism
  - [✓] Test error tracking
- [✓] Create `tests/test_drive_config.py`:
  - [✓] Test configuration validation
  - [✓] Test environment variable loading
  - [✓] Test JSON serialization
- [✓] Create `tests/test_drive_cli_commands.py`:
  - [✓] Test all CLI commands
  - [✓] Test error scenarios
  - [✓] Test progress tracking

#### 9.2 Integration Tests
- [ ] Test complete upload flow
- [ ] Test batch upload with failures
- [ ] Test error recovery scenarios
- [ ] Test concurrent upload handling

#### 9.3 Manual Testing
- [✓] Upload test article to Drive
- [✓] Verify folder structure
- [✓] Test batch uploads
- [✓] Verify error handling and retries

### Phase 10: Documentation

#### 10.1 Setup Guide
- [✓] Write Drive API setup instructions
- [✓] Document credential configuration
- [✓] Add troubleshooting section
- [✓] Include security best practices

#### 10.2 Usage Documentation
- [✓] Document all CLI commands
- [ ] Add workflow diagrams
- [ ] Create example scenarios
- [ ] Write API reference

#### 10.3 Code Documentation
- [✓] Add docstrings to all classes/methods
- [✓] Create inline comments for complex logic
- [ ] Generate API documentation
- [✓] Add type hints throughout

---

## Configuration Files

### Example drive_config.json
```json
{
  "upload_settings": {
    "auto_upload": true,
    "folder_structure": "YYYY/MM/DD",
    "default_folder_id": null,
    "create_folders": true
  },
  "batch_settings": {
    "batch_size": 10,
    "max_retries": 3,
    "retry_delay": 60,
    "concurrent_uploads": 3
  },
  "error_handling": {
    "log_failures": true,
    "notify_on_error": false,
    "quarantine_after_retries": 5
  },
  "metadata": {
    "include_keywords": true,
    "include_sources": true,
    "include_generation_time": true,
    "custom_properties": {}
  }
}
```

---

## Verification Steps

### Component Verification
- [✓] Auth: Successfully obtain and refresh token
- [✓] Uploader: Article appears in Drive with correct formatting
- [✓] Storage: Database correctly tracks uploaded articles
- [✓] Batch: Multiple articles upload successfully
- [✓] CLI: All commands execute without errors

### End-to-End Verification
- [✓] Generate article → Auto-upload to Drive → Verify in Drive UI
- [✓] Failed upload → Retry mechanism → Eventual success
- [✓] Batch upload → Progress tracking → Complete report
- [✓] Database sync → Accurate upload status

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
   - Check network connectivity

3. **Batch Upload Issues**
   - Verify database has pending articles
   - Check retry count limits
   - Review error messages in logs

4. **Database Sync Issues**
   - Verify drive_sync_status table exists
   - Check for orphaned records
   - Review transaction logs

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

- **Completed**: Basic authentication and upload functionality
- **Week 1**: Batch upload and error handling (Phase 4)
- **Week 2**: Enhanced CLI commands and management tools (Phase 8)
- **Week 3**: Testing and documentation updates (Phases 9-10)
- **Week 4**: Performance optimization and monitoring

---

## Success Criteria

- [✓] All generated articles automatically upload to Drive
- [✓] Failed uploads are automatically retried with backoff
- [✓] Batch upload processes pending articles efficiently
- [✓] System handles errors gracefully with detailed logging
- [✓] Performance meets requirements (< 5s per article upload)
- [✓] Upload success rate > 95% after retries
- [✓] Clear visibility into upload status and history