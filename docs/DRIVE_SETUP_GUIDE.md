# Google Drive Integration Setup Guide

*Last Updated: January 8, 2025*

This guide walks you through setting up Google Drive integration for the SEO Content Automation System, enabling automatic upload of generated articles to Google Drive.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Google Cloud Project Setup](#google-cloud-project-setup)
3. [OAuth Credentials Configuration](#oauth-credentials-configuration)
4. [Local Environment Setup](#local-environment-setup)
5. [Authentication](#authentication)
6. [Configuration Options](#configuration-options)
7. [Testing the Integration](#testing-the-integration)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

## Prerequisites

Before starting, ensure you have:
- A Google account
- Python 3.11+ installed
- The SEO Content Automation System set up
- Administrative access to create Google Cloud projects

## Google Cloud Project Setup

### Step 1: Create a New Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Enter project details:
   - **Project name**: `seo-content-automation`
   - **Organization**: Select your organization or "No organization"
4. Click "Create" and wait for the project to be created
5. Note your Project ID (you'll need this later)

### Step 2: Enable Google Drive API

1. In the Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on "Google Drive API" from the results
4. Click "Enable"
5. Wait for the API to be enabled (usually takes a few seconds)

### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless using Google Workspace)
3. Click "Create"
4. Fill in the required fields:
   - **App name**: SEO Content Automation
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click "Save and Continue"
6. On the Scopes page:
   - Click "Add or Remove Scopes"
   - Add these scopes:
     - `https://www.googleapis.com/auth/drive.file`
     - `https://www.googleapis.com/auth/drive.metadata.readonly`
   - Click "Update" and "Save and Continue"
7. Add test users (your email) if in testing mode
8. Review and click "Back to Dashboard"

## OAuth Credentials Configuration

### Step 1: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select application type: "Desktop app"
4. Name: `SEO Content CLI`
5. Click "Create"
6. Download the credentials:
   - Click "Download JSON"
   - Save as `credentials.json` in your project root

### Step 2: Verify Credentials File

The `credentials.json` should look like:
```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "seo-content-automation",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Local Environment Setup

### Step 1: Install Dependencies

Ensure all required packages are installed:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 2: Configure Environment Variables

Add to your `.env` file:
```bash
# Google Drive Configuration
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_TOKEN_PATH=token.json
GOOGLE_DRIVE_UPLOAD_FOLDER_ID=  # Optional: specific folder ID
GOOGLE_DRIVE_SYNC_INTERVAL=300  # 5 minutes

# RAG System Drive Settings
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_AUTO_UPLOAD=true
```

### Step 3: Create Upload Folder (Optional)

1. Open [Google Drive](https://drive.google.com)
2. Create a new folder named "SEO Articles" or similar
3. Right-click the folder → "Get link"
4. Copy the folder ID from the URL:
   - URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Copy: `FOLDER_ID_HERE`
5. Add to `.env`:
   ```bash
   GOOGLE_DRIVE_UPLOAD_FOLDER_ID=FOLDER_ID_HERE
   ```

## Authentication

### Initial Authentication

Run the authentication command:
```bash
python main.py drive auth
```

This will:
1. Open your default web browser
2. Ask you to sign in to Google
3. Request permissions for the app
4. Show a success message
5. Save credentials to `token.json`

### Verify Authentication

Check authentication status:
```bash
python main.py drive status
```

Expected output:
```
Google Drive Status

Configuration:
  Drive Enabled: ✅
  Auto-upload: ✅
  Upload Folder: configured

Authentication:
  Status: ✅ Authenticated
  Connection: ✅ Active

Statistics:
  Total Uploaded: 0 articles
  Pending Upload: 0 articles
```

## Configuration Options

### Drive Configuration File

Create `drive_config.json` for advanced settings:
```json
{
  "upload_settings": {
    "auto_upload": true,
    "folder_structure": "YYYY/MM/DD",
    "create_folders": true
  },
  "batch_settings": {
    "batch_size": 10,
    "max_retries": 3,
    "retry_delay": 60,
    "concurrent_uploads": 3
  },
  "metadata": {
    "include_keywords": true,
    "include_sources": true,
    "include_generation_time": true
  }
}
```

### Folder Structure Options

Configure how articles are organized:
- `YYYY/MM/DD` - Date-based (2025/01/07)
- `YYYY/MM/keyword` - Year/Month/Keyword
- `keyword/YYYY-MM` - Keyword/Date
- `flat` - No subfolders

## Testing the Integration

### Test 1: Manual Upload

Upload a single HTML file:
```bash
# Create test file
echo "<html><body><h1>Test Article</h1></body></html>" > test.html

# Upload to Drive
python main.py drive upload test.html

# Expected output:
# ✅ Upload successful!
# File: Test Article
# Drive URL: https://docs.google.com/document/d/...
```

### Test 2: Generate and Auto-Upload

Generate an article with auto-upload:
```bash
python main.py generate "diabetes management tips"

# Check upload status
python main.py drive list

# Expected output:
# Uploaded Articles:
# 1. Effective Diabetes Management Tips for Better Health
#    Keyword: diabetes management tips
#    Uploaded: 2025-01-07 15:30:00
#    URL: https://docs.google.com/document/d/...
```

### Test 3: Batch Upload

Upload pending articles:
```bash
# Check pending
python main.py drive upload-pending --dry-run

# Upload all pending
python main.py drive upload-pending --verbose
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors

**Error**: "The credentials file does not exist"
```bash
# Solution: Ensure credentials.json is in the project root
ls -la credentials.json
```

**Error**: "Access blocked: Authorization Error"
- Ensure OAuth consent screen is configured
- Add your email as a test user
- Check app is not in production mode

#### 2. Permission Errors

**Error**: "403 Forbidden"
- Verify the folder ID is correct
- Ensure you have write access to the folder
- Check API quotas haven't been exceeded

#### 3. Upload Failures

**Error**: "Network timeout"
```bash
# Increase timeout in drive_config.json
{
  "upload_timeout": 600  # 10 minutes
}
```

**Error**: "Quota exceeded"
- Wait 24 hours for quota reset
- Reduce batch size and concurrent uploads
- Check [API quotas](https://console.cloud.google.com/apis/api/drive.googleapis.com/quotas)

#### 4. Token Issues

**Error**: "Token has been expired or revoked"
```bash
# Re-authenticate
python main.py drive logout
python main.py drive auth
```

### Debug Mode

Enable detailed logging:
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Run with verbose output
python main.py drive upload-pending --verbose
```

## Security Best Practices

### 1. Credential Management
- **Never commit** `credentials.json` or `token.json` to version control
- Add to `.gitignore`:
  ```
  credentials.json
  token.json
  ```
- Use environment variables for production

### 2. Folder Permissions
- Create a dedicated folder for uploads
- Limit sharing to necessary users only
- Regularly review access permissions

### 3. API Key Security
- Restrict API key to specific IPs (if possible)
- Set up usage alerts
- Rotate credentials periodically

### 4. Token Storage
- Store tokens encrypted in production
- Use secure key management services
- Implement token refresh logic

### 5. Monitoring
- Set up quota alerts
- Monitor unusual activity
- Log all upload operations

## Advanced Configuration

### Service Account Setup (Production)

For production deployments, use a service account:

1. Create service account:
   ```bash
   gcloud iam service-accounts create seo-content-automation \
     --display-name="SEO Content Automation"
   ```

2. Grant permissions:
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:seo-content-automation@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/drive.file"
   ```

3. Create key:
   ```bash
   gcloud iam service-accounts keys create credentials.json \
     --iam-account=seo-content-automation@PROJECT_ID.iam.gserviceaccount.com
   ```

### Custom Metadata

Add custom properties to uploaded files:
```python
# In drive_config.json
{
  "metadata": {
    "custom_properties": {
      "department": "content-marketing",
      "project": "seo-automation",
      "version": "1.0"
    }
  }
}
```

### Rate Limiting

Configure rate limits to avoid quota issues:
```python
# In drive_config.json
{
  "rate_limiting": {
    "requests_per_minute": 30,
    "burst_size": 10,
    "cooldown_seconds": 60
  }
}
```

## Next Steps

1. **Set up monitoring**: Configure alerts for failed uploads
2. **Automate uploads**: Schedule batch uploads with cron
3. **Organize content**: Create folder templates for different content types
4. **Track metrics**: Monitor upload success rates and performance

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting)
- Review [Google Drive API documentation](https://developers.google.com/drive/api/v3/about-sdk)
- Open an issue on the project repository

---

**Note**: This guide assumes you're using the OAuth 2.0 flow for desktop applications. For web applications or automated systems, consider using service accounts instead.