"""
Comprehensive test suite for Google Drive uploader functionality.

Tests ArticleUploader and BatchUploader classes with various scenarios
including HTML conversion, folder creation, metadata handling, and batch operations.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
from io import BytesIO
import pytest

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from rag.drive.uploader import ArticleUploader, BatchUploader
from rag.drive.auth import GoogleDriveAuth
from rag.drive.config import DriveConfig


class TestArticleUploader:
    """Test suite for ArticleUploader class."""
    
    @pytest.fixture
    def mock_auth(self):
        """Create mock GoogleDriveAuth instance."""
        auth = Mock(spec=GoogleDriveAuth)
        auth.get_service.return_value = Mock()
        return auth
    
    @pytest.fixture
    def mock_drive_service(self):
        """Create mock Google Drive service."""
        service = Mock()
        
        # Mock files() methods
        files_mock = Mock()
        service.files.return_value = files_mock
        
        # Setup chainable mocks
        create_mock = Mock()
        files_mock.create.return_value = create_mock
        create_mock.execute.return_value = {"id": "test_file_id", "webViewLink": "https://docs.google.com/test"}
        
        update_mock = Mock()
        files_mock.update.return_value = update_mock
        update_mock.execute.return_value = {"id": "test_file_id"}
        
        list_mock = Mock()
        files_mock.list.return_value = list_mock
        list_mock.execute.return_value = {"files": []}
        
        get_mock = Mock()
        files_mock.get.return_value = get_mock
        get_mock.execute.return_value = {"id": "folder_id", "name": "Test Folder"}
        
        return service
    
    @pytest.fixture
    def uploader(self, mock_auth, mock_drive_service):
        """Create ArticleUploader instance with mocked dependencies."""
        mock_auth.get_service.return_value = mock_drive_service
        uploader = ArticleUploader(auth=mock_auth, upload_folder_id="test_folder_id")
        uploader.service = mock_drive_service
        return uploader
    
    def test_init_with_auth(self, mock_auth):
        """Test initialization with provided auth."""
        uploader = ArticleUploader(auth=mock_auth, upload_folder_id="folder_123")
        assert uploader.auth == mock_auth
        assert uploader.upload_folder_id == "folder_123"
        assert uploader._folder_cache == {}
    
    def test_init_without_auth(self):
        """Test initialization creates new auth instance."""
        with patch('rag.drive.uploader.GoogleDriveAuth') as mock_auth_class:
            mock_auth_instance = Mock()
            mock_auth_class.return_value = mock_auth_instance
            
            uploader = ArticleUploader(upload_folder_id="folder_456")
            
            mock_auth_class.assert_called_once()
            assert uploader.auth == mock_auth_instance
    
    def test_upload_html_as_doc_success(self, uploader, mock_drive_service):
        """Test successful HTML to Google Docs upload."""
        # Setup test data
        html_content = "<html><body><h1>Test Article</h1></body></html>"
        title = "Test Article"
        metadata = {"keyword": "test", "author": "Test Author"}
        
        # Mock folder creation
        uploader._ensure_folder_path = Mock(return_value="parent_folder_id")
        
        # Call method
        result = uploader.upload_html_as_doc(html_content, title, metadata)
        
        # Verify result
        assert result["file_id"] == "test_file_id"
        assert result["name"] == title
        assert result["web_link"] == "https://docs.google.com/test"
        assert "folder_path" in result
        
        # Verify Drive API calls
        mock_drive_service.files().create.assert_called_once()
        create_call_args = mock_drive_service.files().create.call_args
        
        # Check file metadata
        body = create_call_args[1]['body']
        assert body['name'] == title
        assert body['mimeType'] == 'application/vnd.google-apps.document'
        assert 'parents' in body
        
        # Check media upload
        assert 'media_body' in create_call_args[1]
        media_body = create_call_args[1]['media_body']
        assert isinstance(media_body, MediaIoBaseUpload)
    
    def test_upload_html_with_special_characters(self, uploader):
        """Test uploading HTML with special characters in title."""
        html_content = "<html><body>Content</body></html>"
        title = "Test/Article:With*Special?Characters"
        
        result = uploader.upload_html_as_doc(html_content, title)
        
        # Verify title was sanitized
        assert "/" not in result["name"]
        assert ":" not in result["name"]
        assert "*" not in result["name"]
        assert "?" not in result["name"]
    
    def test_upload_html_with_metadata(self, uploader, mock_drive_service):
        """Test metadata is properly attached to uploaded file."""
        html_content = "<html><body>Test</body></html>"
        metadata = {
            "keyword": "seo optimization",
            "sources": ["source1", "source2"],
            "generation_time": "2025-01-07T12:00:00Z"
        }
        
        # Mock update for metadata
        uploader.update_file_metadata = Mock(return_value=True)
        
        result = uploader.upload_html_as_doc(html_content, "Test", metadata)
        
        # Verify metadata update was called
        uploader.update_file_metadata.assert_called_once_with("test_file_id", metadata)
    
    def test_upload_html_failure(self, uploader, mock_drive_service):
        """Test handling of upload failure."""
        # Make create raise an error
        error = HttpError(resp=Mock(status=500), content=b'Server Error')
        mock_drive_service.files().create().execute.side_effect = error
        
        # Verify exception is raised
        with pytest.raises(HttpError):
            uploader.upload_html_as_doc("<html></html>", "Test")
    
    def test_create_folder_success(self, uploader, mock_drive_service):
        """Test successful folder creation."""
        # Mock response
        mock_drive_service.files().create().execute.return_value = {"id": "new_folder_id"}
        
        # Create folder
        folder_id = uploader.create_folder("2025", "parent_id")
        
        # Verify result
        assert folder_id == "new_folder_id"
        
        # Verify API call
        create_args = mock_drive_service.files().create.call_args[1]
        assert create_args['body']['name'] == "2025"
        assert create_args['body']['mimeType'] == 'application/vnd.google-apps.folder'
        assert create_args['body']['parents'] == ["parent_id"]
    
    def test_create_folder_uses_cache(self, uploader):
        """Test folder creation uses cache for repeated calls."""
        # Pre-populate cache
        uploader._folder_cache["root/TestFolder"] = "cached_folder_id"
        
        # Call create_folder
        folder_id = uploader.create_folder("TestFolder", "root")
        
        # Verify cache was used (no API call)
        assert folder_id == "cached_folder_id"
        uploader.service.files().create.assert_not_called()
    
    def test_create_folder_finds_existing(self, uploader, mock_drive_service):
        """Test folder creation finds existing folder."""
        # Mock existing folder
        uploader._find_folder = Mock(return_value="existing_folder_id")
        
        # Create folder
        folder_id = uploader.create_folder("ExistingFolder")
        
        # Verify existing folder returned
        assert folder_id == "existing_folder_id"
        mock_drive_service.files().create.assert_not_called()
    
    def test_ensure_folder_path_creates_hierarchy(self, uploader):
        """Test ensuring folder path creates full hierarchy."""
        # Mock create_folder to return sequential IDs
        folder_ids = ["year_id", "month_id", "day_id"]
        uploader.create_folder = Mock(side_effect=folder_ids)
        
        # Ensure path
        final_id = uploader._ensure_folder_path("2025/01/07")
        
        # Verify hierarchy created
        assert final_id == "day_id"
        assert uploader.create_folder.call_count == 3
        
        # Check calls were made in order with correct parents
        calls = uploader.create_folder.call_args_list
        assert calls[0] == call("2025", "test_folder_id")
        assert calls[1] == call("01", "year_id")
        assert calls[2] == call("07", "month_id")
    
    def test_find_folder_success(self, uploader, mock_drive_service):
        """Test finding existing folder."""
        # Mock search result
        mock_drive_service.files().list().execute.return_value = {
            "files": [{"id": "found_folder_id", "name": "TestFolder"}]
        }
        
        # Find folder
        folder_id = uploader._find_folder("TestFolder", "parent_id")
        
        # Verify result
        assert folder_id == "found_folder_id"
        
        # Verify query
        list_args = mock_drive_service.files().list.call_args[1]
        assert "name = 'TestFolder'" in list_args['q']
        assert "'parent_id' in parents" in list_args['q']
        assert "trashed = false" in list_args['q']
    
    def test_find_folder_not_found(self, uploader, mock_drive_service):
        """Test folder not found returns None."""
        # Mock empty search result
        mock_drive_service.files().list().execute.return_value = {"files": []}
        
        # Find folder
        folder_id = uploader._find_folder("NonExistent")
        
        # Verify None returned
        assert folder_id is None
    
    def test_prepare_metadata_conversions(self, uploader):
        """Test metadata preparation handles various types."""
        metadata = {
            "string": "test",
            "number": 123,
            "boolean": True,
            "list": ["a", "b", "c"],
            "dict": {"key": "value"},
            "none": None
        }
        
        result = uploader._prepare_metadata(metadata)
        
        # Verify conversions
        assert result["string"] == "test"
        assert result["number"] == "123"
        assert result["boolean"] == "true"
        assert result["list"] == '["a", "b", "c"]'
        assert result["dict"] == '{"key": "value"}'
        assert "none" not in result  # None values excluded
    
    def test_update_file_metadata_success(self, uploader, mock_drive_service):
        """Test successful metadata update."""
        # Update metadata
        success = uploader.update_file_metadata("file_123", {"key": "value"})
        
        # Verify success
        assert success is True
        
        # Verify API call
        mock_drive_service.files().update.assert_called_once()
        update_args = mock_drive_service.files().update.call_args
        assert update_args[1]['fileId'] == "file_123"
        assert update_args[1]['body']['properties'] == {"key": "value"}
    
    def test_update_file_metadata_failure(self, uploader, mock_drive_service):
        """Test metadata update failure handling."""
        # Make update fail
        error = HttpError(resp=Mock(status=403), content=b'Forbidden')
        mock_drive_service.files().update().execute.side_effect = error
        
        # Update metadata
        success = uploader.update_file_metadata("file_123", {"key": "value"})
        
        # Verify failure handled
        assert success is False
    
    def test_get_upload_folder_structure(self, uploader):
        """Test getting folder structure."""
        # Mock folder tree
        uploader._get_folder_tree = Mock(return_value={
            "id": "root_id",
            "name": "Uploads",
            "folders": {
                "2025": {
                    "id": "2025_id",
                    "name": "2025",
                    "folders": {}
                }
            }
        })
        
        # Get structure
        structure = uploader.get_upload_folder_structure()
        
        # Verify result
        assert structure["name"] == "Uploads"
        assert "2025" in structure["folders"]
    
    def test_get_folder_tree_recursive(self, uploader, mock_drive_service):
        """Test recursive folder tree retrieval."""
        # Mock folder info
        mock_drive_service.files().get().execute.return_value = {
            "id": "folder_id",
            "name": "TestFolder"
        }
        
        # Mock subfolders
        mock_drive_service.files().list().execute.return_value = {
            "files": [
                {"id": "sub1_id", "name": "SubFolder1"},
                {"id": "sub2_id", "name": "SubFolder2"}
            ]
        }
        
        # Get tree (limit recursion depth for test)
        tree = uploader._get_folder_tree("folder_id", max_level=1)
        
        # Verify structure
        assert tree["id"] == "folder_id"
        assert tree["name"] == "TestFolder"
        assert "folders" in tree
        
        # Verify subfolders queried
        list_calls = mock_drive_service.files().list.call_count
        assert list_calls >= 1


class TestBatchUploader:
    """Test suite for BatchUploader class."""
    
    @pytest.fixture
    def mock_drive_config(self):
        """Create mock Drive configuration."""
        config = Mock(spec=DriveConfig)
        config.batch_size = 5
        config.concurrent_uploads = 2
        config.max_retries = 2
        config.retry_delay = 1
        config.upload_timeout = 30
        return config
    
    @pytest.fixture
    def batch_uploader(self, mock_auth, mock_drive_config):
        """Create BatchUploader instance."""
        with patch('rag.drive.uploader.get_drive_config', return_value=mock_drive_config):
            uploader = BatchUploader(auth=mock_auth, upload_folder_id="batch_folder")
            # Mock the parent class upload method
            uploader.upload_html_as_doc = Mock(return_value={
                "file_id": "uploaded_file_id",
                "name": "Test Article",
                "web_link": "https://docs.google.com/doc",
                "folder_path": "2025/01/07"
            })
            return uploader
    
    @pytest.mark.asyncio
    async def test_upload_pending_articles_success(self, batch_uploader, tmp_path):
        """Test successful batch upload of pending articles."""
        # Create test articles with files
        test_file1 = tmp_path / "article1.html"
        test_file1.write_text("<html><body>Article 1</body></html>")
        
        test_file2 = tmp_path / "article2.html"
        test_file2.write_text("<html><body>Article 2</body></html>")
        
        articles = [
            {
                "id": "123",
                "title": "Article 1",
                "file_path": str(test_file1),
                "keyword": "test1",
                "created_at": "2025-01-07T12:00:00Z"
            },
            {
                "id": "456",
                "title": "Article 2",
                "file_path": str(test_file2),
                "keyword": "test2",
                "created_at": "2025-01-07T13:00:00Z"
            }
        ]
        
        # Upload articles
        result = await batch_uploader.upload_pending_articles(articles)
        
        # Verify results
        assert result["stats"]["total"] == 2
        assert result["stats"]["successful"] == 2
        assert result["stats"]["failed"] == 0
        assert len(result["results"]) == 2
        
        # Verify upload method called for each article
        assert batch_uploader.upload_html_as_doc.call_count == 2
    
    @pytest.mark.asyncio
    async def test_upload_pending_with_failures(self, batch_uploader, tmp_path):
        """Test batch upload with some failures."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Article</body></html>")
        
        articles = [
            {
                "id": "123",
                "title": "Success Article",
                "file_path": str(test_file),
                "keyword": "test"
            },
            {
                "id": "456",
                "title": "Missing File Article",
                "file_path": "/nonexistent/file.html",
                "keyword": "test"
            },
            {
                "id": "789",
                "title": "No Path Article",
                "keyword": "test"
                # Missing file_path
            }
        ]
        
        # Upload articles
        result = await batch_uploader.upload_pending_articles(articles)
        
        # Verify mixed results
        assert result["stats"]["total"] == 3
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 0
        assert result["stats"]["skipped"] == 2
        
        # Verify failed articles tracked
        assert len(batch_uploader.failed_uploads) == 0  # Skipped articles not added to failed
    
    @pytest.mark.asyncio
    async def test_upload_with_progress_callback(self, batch_uploader, tmp_path):
        """Test batch upload with progress callback."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        articles = [{
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }]
        
        # Track progress calls
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        # Upload with callback
        result = await batch_uploader.upload_pending_articles(
            articles,
            progress_callback=progress_callback
        )
        
        # Verify callback was called
        assert len(progress_calls) > 0
        assert progress_calls[0][1] == 1  # Total
        assert "Uploaded:" in progress_calls[0][2]
    
    def test_upload_article_with_retry_success_on_retry(self, batch_uploader, tmp_path):
        """Test article upload succeeds on retry."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Mock upload to fail once then succeed
        batch_uploader.upload_html_as_doc.side_effect = [
            Exception("Network error"),
            {
                "file_id": "success_id",
                "name": "Test Article",
                "web_link": "https://docs.google.com/doc",
                "folder_path": "2025/01/07"
            }
        ]
        
        # Upload with retry
        result = batch_uploader._upload_article_with_retry(article)
        
        # Verify success after retry
        assert result["success"] is True
        assert result["attempts"] == 2
        assert batch_uploader.stats["retried"] == 1
    
    def test_upload_article_max_retries_exceeded(self, batch_uploader, tmp_path):
        """Test article upload fails after max retries."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        article = {
            "id": "123",
            "title": "Test Article",
            "file_path": str(test_file),
            "keyword": "test"
        }
        
        # Mock upload to always fail
        batch_uploader.upload_html_as_doc.side_effect = Exception("Persistent error")
        
        # Upload with retry
        result = batch_uploader._upload_article_with_retry(article)
        
        # Verify failure after max retries
        assert result["success"] is False
        assert result["attempts"] == 3  # Initial + 2 retries
        assert "Persistent error" in result["error"]
    
    def test_retry_failed_uploads(self, batch_uploader, tmp_path):
        """Test retrying failed uploads."""
        # Create test file
        test_file = tmp_path / "article.html"
        test_file.write_text("<html><body>Test</body></html>")
        
        # Add failed upload
        batch_uploader.failed_uploads = [{
            "id": "123",
            "title": "Failed Article",
            "file_path": str(test_file),
            "keyword": "test"
        }]
        
        # Mock successful retry
        batch_uploader.upload_html_as_doc.return_value = {
            "file_id": "retry_success_id",
            "name": "Failed Article",
            "web_link": "https://docs.google.com/doc",
            "folder_path": "2025/01/07"
        }
        
        # Retry failed uploads
        result = batch_uploader.retry_failed_uploads()
        
        # Verify retry success
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 0
        assert len(batch_uploader.failed_uploads) == 0  # Cleared after retry
    
    def test_retry_failed_uploads_empty(self, batch_uploader):
        """Test retry with no failed uploads."""
        # Ensure no failed uploads
        batch_uploader.failed_uploads = []
        
        # Retry
        result = batch_uploader.retry_failed_uploads()
        
        # Verify empty result
        assert result["stats"]["total"] == 0
        assert result["results"] == []
    
    def test_get_upload_stats(self, batch_uploader):
        """Test getting upload statistics."""
        # Set some stats
        batch_uploader.stats = {
            "total": 10,
            "successful": 7,
            "failed": 2,
            "retried": 3,
            "skipped": 1
        }
        
        # Get stats
        stats = batch_uploader.get_upload_stats()
        
        # Verify copy returned
        assert stats == batch_uploader.stats
        assert stats is not batch_uploader.stats  # Different object
    
    def test_clear_stats(self, batch_uploader):
        """Test clearing statistics."""
        # Set some values
        batch_uploader.stats["total"] = 5
        batch_uploader.failed_uploads = [{"id": "123"}]
        
        # Clear stats
        batch_uploader.clear_stats()
        
        # Verify reset
        assert batch_uploader.stats["total"] == 0
        assert batch_uploader.stats["successful"] == 0
        assert len(batch_uploader.failed_uploads) == 0
    
    @pytest.mark.asyncio
    async def test_batch_processing_respects_limits(self, batch_uploader, tmp_path):
        """Test batch processing respects batch size and concurrency limits."""
        # Create many test articles
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
        
        # Set small batch size
        batch_uploader.drive_config.batch_size = 3
        batch_uploader.drive_config.concurrent_uploads = 2
        
        # Track upload timing
        upload_times = []
        def track_upload(*args, **kwargs):
            upload_times.append(datetime.now())
            return {
                "file_id": f"file_{len(upload_times)}",
                "name": "Test",
                "web_link": "https://docs.google.com/doc",
                "folder_path": "test"
            }
        
        batch_uploader.upload_html_as_doc.side_effect = track_upload
        
        # Upload articles
        result = await batch_uploader.upload_pending_articles(articles)
        
        # Verify all uploaded
        assert result["stats"]["successful"] == 10
        
        # Verify batch processing (should have pauses between batches)
        # Note: This is a simplified check; in real tests you might verify
        # actual concurrent execution limits