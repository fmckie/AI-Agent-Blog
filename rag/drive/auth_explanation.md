# Google Drive Authentication Module - Detailed Explanation

## Purpose
The `auth.py` module handles all authentication-related tasks for Google Drive integration, managing OAuth 2.0 flow, token persistence, and providing authenticated service instances.

## Architecture

### Core Components

1. **SCOPES** - Defines API permissions:
   - `drive.metadata.readonly` - Read file metadata
   - `drive.readonly` - Download and read files
   - `drive.file` - Create/modify files created by our app

2. **GoogleDriveAuth Class** - Main authentication handler:
   - Manages OAuth 2.0 flow
   - Handles token persistence
   - Provides service instances
   - Supports token refresh and revocation

### Key Methods

#### `__init__()`
- Initializes with credentials and token paths
- Falls back to environment variables if not provided
- Validates credentials file exists

#### `authenticate()`
- Core authentication logic with three-step process:
  1. Check for existing valid token
  2. Try to refresh expired token
  3. Run OAuth flow if needed
- Saves token for future use

#### `get_service()`
- Returns authenticated Google Drive API service
- Caches service instance for reuse
- Supports different Google services and versions

#### `test_connection()`
- Verifies authentication works
- Retrieves user information
- Useful for debugging

## Authentication Flow

```
Start
  ↓
Token exists? → Yes → Token valid? → Yes → Use token
  ↓ No              ↓ No
  ↓                 ↓
  ↓            Can refresh? → Yes → Refresh token
  ↓                 ↓ No
  ↓                 ↓
  ←─────────────────┘
  ↓
Run OAuth flow
  ↓
Save token
  ↓
Return credentials
```

## Security Considerations

1. **Token Storage**:
   - Saved with 0o600 permissions (owner read/write only)
   - Never commit token files to version control
   - Token contains access credentials

2. **Scope Limitations**:
   - Only request necessary permissions
   - `drive.file` only affects files we create
   - Cannot delete or modify user's existing files

3. **Error Handling**:
   - Graceful fallback for expired tokens
   - Clear error messages for missing credentials
   - Network error resilience

## Usage Examples

### Basic Authentication
```python
from rag.drive.auth import GoogleDriveAuth

# Create auth instance
auth = GoogleDriveAuth()

# Authenticate (will open browser if needed)
auth.authenticate()

# Get service
service = auth.get_service()
```

### Test Connection
```python
# Verify authentication works
if auth.test_connection():
    print("Connected successfully!")
else:
    print("Connection failed")
```

### Convenience Function
```python
from rag.drive.auth import get_drive_service

# Quick way to get authenticated service
service = get_drive_service()
```

## Common Issues and Solutions

1. **"Credentials file not found"**
   - Ensure credentials.json is in project root
   - Check GOOGLE_DRIVE_CREDENTIALS_PATH in .env

2. **"Token refresh failed"**
   - Token may be revoked or too old
   - Delete token.json and re-authenticate

3. **"Cannot open browser"**
   - OAuth flow requires browser access
   - Can modify to use console flow if needed

4. **"Permission denied"**
   - Check OAuth consent screen configuration
   - Ensure all required scopes are approved

## Integration Points

- **config.py**: Reads environment variables
- **CLI commands**: Will use this for `drive auth` command
- **Uploader/Watcher**: Will use `get_service()` for API calls

## Best Practices

1. Always use try/except when calling API methods
2. Check `is_authenticated` before operations
3. Log authentication events for debugging
4. Implement exponential backoff for API calls
5. Handle token expiration gracefully

## Next Steps

With authentication in place, we can:
1. Create CLI command for authentication
2. Build the uploader module
3. Implement the folder watcher
4. Add batch operations support