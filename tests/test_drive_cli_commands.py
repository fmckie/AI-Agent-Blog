"""
Test suite for Google Drive CLI commands.

Tests the new drive commands: logout, upload-pending, retry-failed.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, call
import pytest
from click.testing import CliRunner

from main import cli
from rag.drive.config import DriveConfig
from rag.drive.auth import GoogleDriveAuth
from rag.drive.uploader import BatchUploader
from rag.drive.storage import DriveStorageHandler


class TestDriveLogoutCommand:
    """Test drive logout command."""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()
    
    def test_drive_logout_with_confirmation(self, runner):
        """Test logout with user confirmation."""
        with patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class:
            mock_auth = Mock()
            mock_auth.token_path = "token.json"
            mock_auth_class.return_value = mock_auth
            
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.unlink') as mock_unlink:
                
                # Simulate user confirming
                result = runner.invoke(cli, ['drive', 'logout'], input='y\n')
                
                assert result.exit_code == 0
                assert "Successfully logged out from Google Drive" in result.output
                mock_unlink.assert_called_once()
    
    def test_drive_logout_cancelled(self, runner):
        """Test logout cancelled by user."""
        with patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class:
            mock_auth = Mock()
            mock_auth_class.return_value = mock_auth
            
            # Simulate user declining
            result = runner.invoke(cli, ['drive', 'logout'], input='n\n')
            
            assert result.exit_code == 0
            assert "Logout cancelled" in result.output
    
    def test_drive_logout_force(self, runner):
        """Test force logout without confirmation."""
        with patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class:
            mock_auth = Mock()
            mock_auth.token_path = "token.json"
            mock_auth_class.return_value = mock_auth
            
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.unlink') as mock_unlink:
                
                result = runner.invoke(cli, ['drive', 'logout', '--force'])
                
                assert result.exit_code == 0
                assert "Successfully logged out from Google Drive" in result.output
                mock_unlink.assert_called_once()
    
    def test_drive_logout_no_session(self, runner):
        """Test logout when no active session exists."""
        with patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class:
            mock_auth = Mock()
            mock_auth.token_path = "token.json"
            mock_auth_class.return_value = mock_auth
            
            with patch('pathlib.Path.exists', return_value=False):
                result = runner.invoke(cli, ['drive', 'logout', '--force'])
                
                assert result.exit_code == 0
                assert "No active session found" in result.output
    
    def test_drive_logout_error(self, runner):
        """Test logout error handling."""
        with patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class:
            mock_auth_class.side_effect = Exception("Auth error")
            
            result = runner.invoke(cli, ['drive', 'logout', '--force'])
            
            assert result.exit_code == 1
            assert "Logout failed: Auth error" in result.output


class TestDriveUploadPendingCommand:
    """Test drive upload-pending command."""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for upload-pending."""
        with patch('rag.drive.storage.DriveStorageHandler') as mock_storage_class, \
             patch('config.get_config') as mock_get_config, \
             patch('rag.drive.config.get_drive_config') as mock_get_drive_config, \
             patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class, \
             patch('rag.drive.uploader.BatchUploader') as mock_uploader_class:
            
            # Mock storage
            mock_storage = Mock(spec=DriveStorageHandler)
            mock_storage_class.return_value = mock_storage
            
            # Mock config
            mock_config = Mock()
            mock_config.google_drive_upload_folder_id = "test_folder_id"
            mock_get_config.return_value = mock_config
            
            # Mock drive config
            mock_drive_config = Mock(spec=DriveConfig)
            mock_drive_config.batch_size = 10
            mock_get_drive_config.return_value = mock_drive_config
            
            # Mock auth
            mock_auth = Mock(spec=GoogleDriveAuth)
            mock_auth.authenticate.return_value = None
            mock_auth_class.return_value = mock_auth
            
            # Mock uploader
            mock_uploader = Mock(spec=BatchUploader)
            mock_uploader_class.return_value = mock_uploader
            
            yield {
                "storage": mock_storage,
                "config": mock_config,
                "drive_config": mock_drive_config,
                "auth": mock_auth,
                "uploader": mock_uploader,
                "storage_class": mock_storage_class,
                "uploader_class": mock_uploader_class
            }
    
    def test_upload_pending_no_articles(self, runner, mock_dependencies):
        """Test upload-pending with no pending articles."""
        mock_dependencies["storage"].get_pending_uploads.return_value = []
        
        result = runner.invoke(cli, ['drive', 'upload-pending'])
        
        assert result.exit_code == 0
        assert "No pending articles to upload" in result.output
    
    def test_upload_pending_dry_run(self, runner, mock_dependencies):
        """Test upload-pending in dry run mode."""
        # Mock pending articles
        pending = [
            {"id": "1", "title": "Article 1", "keyword": "test1"},
            {"id": "2", "title": "Article 2", "keyword": "test2"},
            {"id": "3", "title": "Article 3", "keyword": "test3"}
        ]
        mock_dependencies["storage"].get_pending_uploads.return_value = pending
        
        result = runner.invoke(cli, ['drive', 'upload-pending', '--dry-run'])
        
        assert result.exit_code == 0
        assert "Found 3 pending articles" in result.output
        assert "Articles that would be uploaded:" in result.output
        assert "Article 1 (test1)" in result.output
        assert "Article 2 (test2)" in result.output
        assert "Article 3 (test3)" in result.output
        
        # Verify no actual upload happened
        mock_dependencies["uploader"].upload_pending_articles.assert_not_called()
    
    def test_upload_pending_success(self, runner, mock_dependencies):
        """Test successful batch upload."""
        # Mock pending articles
        pending = [
            {"id": "1", "title": "Article 1", "keyword": "test1", "file_path": "/path/1"},
            {"id": "2", "title": "Article 2", "keyword": "test2", "file_path": "/path/2"}
        ]
        mock_dependencies["storage"].get_pending_uploads.return_value = pending
        
        # Mock upload result
        async def mock_upload(articles, progress_callback=None):
            return {
                "stats": {
                    "total": 2,
                    "successful": 2,
                    "failed": 0,
                    "skipped": 0,
                    "retried": 0
                },
                "results": [
                    {
                        "article_id": "1",
                        "success": True,
                        "drive_file_id": "file_1",
                        "drive_url": "https://docs.google.com/1",
                        "folder_path": "2025/01/08"
                    },
                    {
                        "article_id": "2",
                        "success": True,
                        "drive_file_id": "file_2",
                        "drive_url": "https://docs.google.com/2",
                        "folder_path": "2025/01/08"
                    }
                ],
                "failed_articles": []
            }
        
        mock_dependencies["uploader"].upload_pending_articles = mock_upload
        
        result = runner.invoke(cli, ['drive', 'upload-pending'])
        
        assert result.exit_code == 0
        assert "Found 2 pending articles" in result.output
        assert "Upload Summary:" in result.output
        assert "Total: 2" in result.output
        assert "Successful: 2" in result.output
        assert "Database updated" in result.output
        
        # Verify track_upload was called
        assert mock_dependencies["storage"].track_upload.call_count == 2
    
    def test_upload_pending_with_failures(self, runner, mock_dependencies):
        """Test batch upload with some failures."""
        pending = [
            {"id": "1", "title": "Success", "keyword": "test1"},
            {"id": "2", "title": "Failed", "keyword": "test2"},
            {"id": "3", "title": "Skipped", "keyword": "test3"}
        ]
        mock_dependencies["storage"].get_pending_uploads.return_value = pending
        
        async def mock_upload(articles, progress_callback=None):
            return {
                "stats": {
                    "total": 3,
                    "successful": 1,
                    "failed": 1,
                    "skipped": 1,
                    "retried": 2
                },
                "results": [
                    {
                        "article_id": "1",
                        "success": True,
                        "drive_file_id": "file_1",
                        "drive_url": "https://docs.google.com/1",
                        "folder_path": "2025/01/08"
                    },
                    {
                        "article_id": "2",
                        "success": False,
                        "error": "Network error"
                    },
                    {
                        "article_id": "3",
                        "success": False,
                        "error": "File not found"
                    }
                ],
                "failed_articles": [pending[1]]
            }
        
        mock_dependencies["uploader"].upload_pending_articles = mock_upload
        
        result = runner.invoke(cli, ['drive', 'upload-pending'])
        
        assert result.exit_code == 0
        assert "Upload Summary:" in result.output
        assert "Successful: 1" in result.output
        assert "Failed: 1" in result.output
        assert "Skipped: 1" in result.output
        assert "Retried: 2" in result.output
        
        # Only successful uploads tracked
        assert mock_dependencies["storage"].track_upload.call_count == 1
    
    def test_upload_pending_custom_batch_size(self, runner, mock_dependencies):
        """Test upload with custom batch size."""
        pending = [{"id": str(i), "title": f"Article {i}", "keyword": "test"} for i in range(5)]
        mock_dependencies["storage"].get_pending_uploads.return_value = pending
        
        async def mock_upload(articles, progress_callback=None):
            return {
                "stats": {"total": 5, "successful": 5, "failed": 0, "skipped": 0, "retried": 0},
                "results": [],
                "failed_articles": []
            }
        
        mock_dependencies["uploader"].upload_pending_articles = mock_upload
        
        result = runner.invoke(cli, ['drive', 'upload-pending', '--batch-size', '2'])
        
        assert result.exit_code == 0
        # Verify batch size was updated
        assert mock_dependencies["drive_config"].batch_size == 2
    
    def test_upload_pending_verbose(self, runner, mock_dependencies):
        """Test verbose output during upload."""
        pending = [{"id": "1", "title": "Test Article", "keyword": "test"}]
        mock_dependencies["storage"].get_pending_uploads.return_value = pending
        
        # Track if progress callback was provided
        callback_provided = False
        
        async def mock_upload(articles, progress_callback=None):
            nonlocal callback_provided
            callback_provided = progress_callback is not None
            if progress_callback:
                progress_callback(1, 1, "Uploaded: Test Article")
            return {
                "stats": {"total": 1, "successful": 1, "failed": 0, "skipped": 0, "retried": 0},
                "results": [{"article_id": "1", "success": True, "drive_file_id": "f1", 
                           "drive_url": "https://docs.google.com/1", "folder_path": "2025"}],
                "failed_articles": []
            }
        
        mock_dependencies["uploader"].upload_pending_articles = mock_upload
        
        result = runner.invoke(cli, ['drive', 'upload-pending', '--verbose'])
        
        assert result.exit_code == 0
        assert callback_provided  # Callback should be provided in verbose mode
    
    def test_upload_pending_error(self, runner, mock_dependencies):
        """Test error handling during upload."""
        mock_dependencies["storage"].get_pending_uploads.side_effect = Exception("Database error")
        
        result = runner.invoke(cli, ['drive', 'upload-pending'])
        
        assert result.exit_code == 1
        assert "Upload failed: Database error" in result.output


class TestDriveRetryFailedCommand:
    """Test drive retry-failed command."""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for retry-failed."""
        with patch('config.get_config') as mock_get_config, \
             patch('rag.drive.auth.GoogleDriveAuth') as mock_auth_class, \
             patch('rag.drive.uploader.BatchUploader') as mock_uploader_class, \
             patch('rag.drive.storage.DriveStorageHandler') as mock_storage_class:
            
            # Mock config
            mock_config = Mock()
            mock_config.google_drive_upload_folder_id = "test_folder_id"
            mock_get_config.return_value = mock_config
            
            # Mock auth
            mock_auth = Mock()
            mock_auth.authenticate.return_value = None
            mock_auth_class.return_value = mock_auth
            
            # Mock uploader
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            
            # Mock storage
            mock_storage = Mock()
            mock_storage_class.return_value = mock_storage
            
            yield {
                "config": mock_config,
                "auth": mock_auth,
                "uploader": mock_uploader,
                "storage": mock_storage
            }
    
    def test_retry_failed_no_failures(self, runner, mock_dependencies):
        """Test retry when no failed uploads exist."""
        mock_dependencies["uploader"].failed_uploads = []
        
        result = runner.invoke(cli, ['drive', 'retry-failed'])
        
        assert result.exit_code == 0
        assert "No failed uploads to retry" in result.output
        assert "Failed uploads are tracked within a session" in result.output
    
    def test_retry_failed_success(self, runner, mock_dependencies):
        """Test successful retry of failed uploads."""
        # Mock failed uploads
        mock_dependencies["uploader"].failed_uploads = [
            {"id": "1", "title": "Failed Article 1"},
            {"id": "2", "title": "Failed Article 2"}
        ]
        
        # Mock retry result
        mock_dependencies["uploader"].retry_failed_uploads.return_value = {
            "stats": {
                "total": 2,
                "successful": 2,
                "failed": 0
            },
            "results": [
                {
                    "article_id": "1",
                    "success": True,
                    "drive_file_id": "retry_1",
                    "drive_url": "https://docs.google.com/r1",
                    "folder_path": "2025/01/08"
                },
                {
                    "article_id": "2",
                    "success": True,
                    "drive_file_id": "retry_2",
                    "drive_url": "https://docs.google.com/r2",
                    "folder_path": "2025/01/08"
                }
            ]
        }
        
        result = runner.invoke(cli, ['drive', 'retry-failed'])
        
        assert result.exit_code == 0
        assert "Retrying 2 failed uploads" in result.output
        assert "Retry Summary:" in result.output
        assert "Successful: 2" in result.output
        assert "Database updated" in result.output
        
        # Verify track_upload called
        assert mock_dependencies["storage"].track_upload.call_count == 2
    
    def test_retry_failed_partial_success(self, runner, mock_dependencies):
        """Test retry with partial success."""
        mock_dependencies["uploader"].failed_uploads = [
            {"id": "1", "title": "Will Succeed"},
            {"id": "2", "title": "Will Fail Again"}
        ]
        
        mock_dependencies["uploader"].retry_failed_uploads.return_value = {
            "stats": {
                "total": 2,
                "successful": 1,
                "failed": 1
            },
            "results": [
                {
                    "article_id": "1",
                    "success": True,
                    "drive_file_id": "retry_1",
                    "drive_url": "https://docs.google.com/r1",
                    "folder_path": "2025/01/08"
                },
                {
                    "article_id": "2",
                    "success": False,
                    "error": "Persistent error"
                }
            ]
        }
        
        result = runner.invoke(cli, ['drive', 'retry-failed'])
        
        assert result.exit_code == 0
        assert "Retry Summary:" in result.output
        assert "Successful: 1" in result.output
        assert "Failed: 1" in result.output
        
        # Only successful retries tracked
        assert mock_dependencies["storage"].track_upload.call_count == 1
    
    def test_retry_failed_verbose(self, runner, mock_dependencies):
        """Test verbose retry output."""
        mock_dependencies["uploader"].failed_uploads = [{"id": "1", "title": "Test"}]
        
        # Check if callback provided
        callback_provided = False
        def mock_retry(progress_callback=None):
            nonlocal callback_provided
            callback_provided = progress_callback is not None
            return {"stats": {"total": 1, "successful": 1, "failed": 0}, "results": []}
        
        mock_dependencies["uploader"].retry_failed_uploads = mock_retry
        
        result = runner.invoke(cli, ['drive', 'retry-failed', '--verbose'])
        
        assert result.exit_code == 0
        assert callback_provided  # Callback should be provided in verbose mode
    
    def test_retry_failed_error(self, runner, mock_dependencies):
        """Test error handling during retry."""
        mock_dependencies["uploader"].failed_uploads = [{"id": "1"}]
        mock_dependencies["uploader"].retry_failed_uploads.side_effect = Exception("Retry error")
        
        result = runner.invoke(cli, ['drive', 'retry-failed'])
        
        assert result.exit_code == 1
        assert "Retry failed: Retry error" in result.output