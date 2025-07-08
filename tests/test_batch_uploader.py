"""
Test suite specifically for BatchUploader functionality.

Tests batch processing, retry logic, statistics tracking, and error handling.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, call
from concurrent.futures import Future
import pytest

from rag.drive.uploader import BatchUploader
from rag.drive.config import DriveConfig
from rag.drive.auth import GoogleDriveAuth


class TestBatchUploaderInit:
    """Test BatchUploader initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with patch('rag.drive.config.get_drive_config') as mock_get_config:
            mock_config = Mock(spec=DriveConfig)
            mock_get_config.return_value = mock_config
            
            mock_auth = Mock(spec=GoogleDriveAuth)
            uploader = BatchUploader(auth=mock_auth)
            
            assert uploader.auth == mock_auth
            assert uploader.drive_config == mock_config
            assert uploader.stats["total"] == 0
            assert uploader.stats["successful"] == 0
            assert uploader.stats["failed"] == 0
            assert uploader.stats["retried"] == 0
            assert uploader.stats["skipped"] == 0
            assert uploader.failed_uploads == []
    
    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        mock_auth = Mock(spec=GoogleDriveAuth)
        mock_config = Mock(spec=DriveConfig)
        mock_config.batch_size = 20
        mock_config.concurrent_uploads = 5
        
        with patch('rag.drive.config.get_drive_config'):
            uploader = BatchUploader(
                auth=mock_auth,
                upload_folder_id="custom_folder",
                drive_config=mock_config
            )
            
            assert uploader.upload_folder_id == "custom_folder"
            assert uploader.drive_config == mock_config


class TestBatchUploaderProcessing:
    """Test batch upload processing."""
    
    @pytest.fixture
    def mock_uploader(self):
        """Create BatchUploader with mocked dependencies."""
        with patch('rag.drive.config.get_drive_config') as mock_get_config:
            mock_config = Mock(spec=DriveConfig)
            mock_config.batch_size = 3
            mock_config.concurrent_uploads = 2
            mock_config.max_retries = 2
            mock_config.retry_delay = 1
            mock_config.upload_timeout = 30
            mock_get_config.return_value = mock_config
            
            mock_auth = Mock(spec=GoogleDriveAuth)
            uploader = BatchUploader(auth=mock_auth)
            
            # Mock parent class method
            uploader.upload_html_as_doc = Mock(return_value={
                "file_id": "test_file_id",
                "name": "Test Article",
                "web_link": "https://docs.google.com/doc",
                "folder_path": "2025/01/08"
            })
            
            return uploader
    
    @pytest.mark.asyncio
    async def test_upload_pending_articles_empty_list(self, mock_uploader):
        """Test uploading empty article list."""
        result = await mock_uploader.upload_pending_articles([])
        
        assert result["stats"]["total"] == 0
        assert result["stats"]["successful"] == 0
        assert result["stats"]["failed"] == 0
        assert result["results"] == []
        assert result["failed_articles"] == []
    
    @pytest.mark.asyncio
    async def test_upload_pending_articles_single_success(self, mock_uploader, tmp_path):
        """Test uploading single article successfully."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test Article</body></html>")
        
        articles = [{
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test",
            "created_at": "2025-01-08T10:00:00Z"
        }]
        
        # Mock the retry method to use the mocked upload
        mock_uploader._upload_article_with_retry = Mock(return_value={
            "article_id": "123",
            "success": True,
            "drive_file_id": "test_file_id",
            "drive_url": "https://docs.google.com/doc",
            "folder_path": "2025/01/08",
            "attempts": 1
        })
        
        result = await mock_uploader.upload_pending_articles(articles)
        
        assert result["stats"]["total"] == 1
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True
    
    @pytest.mark.asyncio
    async def test_upload_pending_articles_mixed_results(self, mock_uploader, tmp_path):
        """Test uploading with mixed success/failure results."""
        # Create test files
        success_file = tmp_path / "success.html"
        success_file.write_text("<html><body>Success</body></html>")
        
        articles = [
            {
                "id": "1",
                "title": "Success Article",
                "file_path": str(success_file),
                "keyword": "success"
            },
            {
                "id": "2",
                "title": "Missing File Article",
                "file_path": "/nonexistent/file.html",
                "keyword": "missing"
            },
            {
                "id": "3",
                "title": "No Path Article",
                "keyword": "nopath"
                # Missing file_path
            }
        ]
        
        # Don't mock _upload_article_with_retry, let it run naturally
        # This will properly update the skipped stats
        
        result = await mock_uploader.upload_pending_articles(articles)
        
        assert result["stats"]["total"] == 3
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 0  # Skipped files don't count as failed
        assert result["stats"]["skipped"] == 2
    
    @pytest.mark.asyncio
    async def test_upload_pending_with_progress_callback(self, mock_uploader, tmp_path):
        """Test progress callback is called correctly."""
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        articles = [{
            "id": "123",
            "title": "Test Article with Very Long Title That Should Be Truncated",
            "file_path": str(test_file),
            "keyword": "test"
        }]
        
        # Track progress calls
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append({
                "current": current,
                "total": total,
                "message": message
            })
        
        mock_uploader._upload_article_with_retry = Mock(return_value={
            "article_id": "123",
            "success": True,
            "drive_file_id": "test_id",
            "drive_url": "https://docs.google.com/doc",
            "folder_path": "2025/01/08",
            "attempts": 1
        })
        
        await mock_uploader.upload_pending_articles(articles, progress_callback)
        
        # Verify callback was called
        assert len(progress_calls) > 0
        assert progress_calls[0]["total"] == 1
        assert "Uploaded:" in progress_calls[0]["message"]
        assert "Test Article with Very Long Title That Should Be T..." in progress_calls[0]["message"]
    
    @pytest.mark.asyncio
    async def test_upload_respects_batch_size(self, mock_uploader, tmp_path):
        """Test that batch size limits are respected."""
        # Create many articles
        articles = []
        for i in range(10):
            test_file = tmp_path / f"article{i}.html"
            test_file.write_text(f"<html><body>Article {i}</body></html>")
            articles.append({
                "id": str(i),
                "title": f"Article {i}",
                "file_path": str(test_file),
                "keyword": "test"
            })
        
        # Mock all as successful
        mock_uploader._upload_article_with_retry = Mock(side_effect=lambda a: {
            "article_id": a["id"],
            "success": True,
            "drive_file_id": f"file_{a['id']}",
            "drive_url": f"https://docs.google.com/{a['id']}",
            "folder_path": "2025/01/08",
            "attempts": 1
        })
        
        # Set batch size to 3
        mock_uploader.drive_config.batch_size = 3
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await mock_uploader.upload_pending_articles(articles)
            
            # Should have slept between batches (10 articles, batch size 3 = 3 sleeps)
            assert mock_sleep.call_count >= 3
        
        assert result["stats"]["successful"] == 10


class TestBatchUploaderRetryLogic:
    """Test retry logic and error handling."""
    
    @pytest.fixture
    def uploader_with_retry(self, tmp_path):
        """Create uploader setup for retry testing."""
        with patch('rag.drive.config.get_drive_config') as mock_get_config:
            mock_config = Mock(spec=DriveConfig)
            mock_config.batch_size = 5
            mock_config.concurrent_uploads = 2
            mock_config.max_retries = 3
            mock_config.retry_delay = 0.1  # Short delay for tests
            mock_config.upload_timeout = 30
            mock_get_config.return_value = mock_config
            
            mock_auth = Mock(spec=GoogleDriveAuth)
            uploader = BatchUploader(auth=mock_auth)
            
            return uploader
    
    def test_upload_article_with_retry_success_first_try(self, uploader_with_retry, tmp_path):
        """Test successful upload on first attempt."""
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Mock successful upload
        uploader_with_retry.upload_html_as_doc = Mock(return_value={
            "file_id": "success_id",
            "name": "Test Article",
            "web_link": "https://docs.google.com/doc",
            "folder_path": "2025/01/08"
        })
        
        result = uploader_with_retry._upload_article_with_retry(article)
        
        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["drive_file_id"] == "success_id"
        assert uploader_with_retry.stats["retried"] == 0
    
    def test_upload_article_with_retry_success_after_retry(self, uploader_with_retry, tmp_path):
        """Test successful upload after retries."""
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Mock to fail twice then succeed
        call_count = 0
        def upload_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Network error {call_count}")
            return {
                "file_id": "success_after_retry",
                "name": "Test Article",
                "web_link": "https://docs.google.com/doc",
                "folder_path": "2025/01/08"
            }
        
        uploader_with_retry.upload_html_as_doc = Mock(side_effect=upload_side_effect)
        
        with patch('time.sleep'):  # Speed up test
            result = uploader_with_retry._upload_article_with_retry(article)
        
        assert result["success"] is True
        assert result["attempts"] == 3
        assert result["drive_file_id"] == "success_after_retry"
        assert uploader_with_retry.stats["retried"] == 1
    
    def test_upload_article_max_retries_exceeded(self, uploader_with_retry, tmp_path):
        """Test failure after exceeding max retries."""
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Mock to always fail
        uploader_with_retry.upload_html_as_doc = Mock(
            side_effect=Exception("Persistent network error")
        )
        
        with patch('time.sleep'):  # Speed up test
            result = uploader_with_retry._upload_article_with_retry(article)
        
        assert result["success"] is False
        assert result["attempts"] == 4  # Initial + 3 retries
        assert "Persistent network error" in result["error"]
    
    def test_upload_article_missing_file(self, uploader_with_retry):
        """Test handling of missing file."""
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": "/nonexistent/file.html",
            "keyword": "test"
        }
        
        result = uploader_with_retry._upload_article_with_retry(article)
        
        assert result["success"] is False
        assert "File not found" in result["error"]
        assert uploader_with_retry.stats["skipped"] == 1
    
    def test_upload_article_no_file_path(self, uploader_with_retry):
        """Test handling of missing file_path field."""
        article = {
            "id": "123",
            "title": "Test Article",
            "keyword": "test"
            # Missing file_path
        }
        
        result = uploader_with_retry._upload_article_with_retry(article)
        
        assert result["success"] is False
        assert result["error"] == "Missing file_path"
        assert uploader_with_retry.stats["skipped"] == 1
    
    def test_exponential_backoff(self, uploader_with_retry, tmp_path):
        """Test exponential backoff timing."""
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Always fail
        uploader_with_retry.upload_html_as_doc = Mock(
            side_effect=Exception("Network error")
        )
        
        sleep_calls = []
        def mock_sleep(seconds):
            sleep_calls.append(seconds)
        
        with patch('time.sleep', side_effect=mock_sleep):
            uploader_with_retry._upload_article_with_retry(article)
        
        # Verify exponential backoff
        expected_delays = [
            0.1,      # retry_delay
            0.2,      # retry_delay * 2^1
            0.4       # retry_delay * 2^2
        ]
        
        assert len(sleep_calls) == 3
        for i, (actual, expected) in enumerate(zip(sleep_calls, expected_delays)):
            assert actual == expected, f"Retry {i+1}: expected {expected}s, got {actual}s"


class TestBatchUploaderFailedUploads:
    """Test failed upload tracking and retry."""
    
    @pytest.fixture
    def uploader(self):
        """Create uploader for testing."""
        with patch('rag.drive.config.get_drive_config') as mock_get_config:
            mock_config = Mock(spec=DriveConfig)
            mock_config.batch_size = 5
            mock_config.concurrent_uploads = 2
            mock_get_config.return_value = mock_config
            
            return BatchUploader()
    
    def test_retry_failed_uploads_empty(self, uploader):
        """Test retry with no failed uploads."""
        result = uploader.retry_failed_uploads()
        
        assert result["stats"]["total"] == 0
        assert result["stats"]["successful"] == 0
        assert result["stats"]["failed"] == 0
        assert result["results"] == []
    
    def test_retry_failed_uploads_success(self, uploader, tmp_path):
        """Test successful retry of failed uploads."""
        # Create test file
        test_file = tmp_path / "failed.html"
        test_file.write_text("<html><body>Failed Article</body></html>")
        
        # Add failed upload
        uploader.failed_uploads = [{
            "id": "456",
            "title": "Previously Failed Article",
            "file_path": str(test_file),
            "keyword": "retry"
        }]
        
        # Mock successful retry
        async def mock_upload_pending(articles, progress_callback=None):
            return {
                "stats": {
                    "total": 1,
                    "successful": 1,
                    "failed": 0,
                    "retried": 0,
                    "skipped": 0
                },
                "results": [{
                    "article_id": "456",
                    "success": True,
                    "drive_file_id": "retry_success",
                    "drive_url": "https://docs.google.com/retry",
                    "folder_path": "2025/01/08",
                    "attempts": 1
                }],
                "failed_articles": []
            }
        
        uploader.upload_pending_articles = mock_upload_pending
        
        result = uploader.retry_failed_uploads()
        
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 0
        assert len(uploader.failed_uploads) == 0  # Cleared after retry
    
    def test_retry_failed_uploads_with_callback(self, uploader, tmp_path):
        """Test retry with progress callback."""
        test_file = tmp_path / "failed.html"
        test_file.write_text("<html><body>Failed</body></html>")
        
        uploader.failed_uploads = [{
            "id": "789",
            "title": "Failed Article",
            "file_path": str(test_file),
            "keyword": "test"
        }]
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        async def mock_upload_pending(articles, progress_callback=None):
            if progress_callback:
                progress_callback(1, 1, "Retrying: Failed Article")
            return {
                "stats": {"total": 1, "successful": 1, "failed": 0, "retried": 0, "skipped": 0},
                "results": [{"article_id": "789", "success": True}],
                "failed_articles": []
            }
        
        uploader.upload_pending_articles = mock_upload_pending
        
        result = uploader.retry_failed_uploads(progress_callback)
        
        assert len(progress_calls) > 0
        assert "Retrying: Failed Article" in progress_calls[0][2]


class TestBatchUploaderStatistics:
    """Test statistics tracking."""
    
    def test_get_upload_stats(self):
        """Test getting upload statistics."""
        with patch('rag.drive.config.get_drive_config'):
            uploader = BatchUploader()
            
            # Set some stats
            uploader.stats = {
                "total": 10,
                "successful": 7,
                "failed": 2,
                "retried": 3,
                "skipped": 1
            }
            
            stats = uploader.get_upload_stats()
            
            # Verify copy returned
            assert stats == uploader.stats
            assert stats is not uploader.stats  # Different object
            
            # Modify returned stats shouldn't affect original
            stats["total"] = 20
            assert uploader.stats["total"] == 10
    
    def test_clear_stats(self):
        """Test clearing statistics and failed uploads."""
        with patch('rag.drive.config.get_drive_config'):
            uploader = BatchUploader()
            
            # Set some values
            uploader.stats = {
                "total": 5,
                "successful": 3,
                "failed": 2,
                "retried": 1,
                "skipped": 0
            }
            uploader.failed_uploads = [{"id": "1"}, {"id": "2"}]
            
            # Clear stats
            uploader.clear_stats()
            
            # Verify reset
            assert uploader.stats["total"] == 0
            assert uploader.stats["successful"] == 0
            assert uploader.stats["failed"] == 0
            assert uploader.stats["retried"] == 0
            assert uploader.stats["skipped"] == 0
            assert len(uploader.failed_uploads) == 0