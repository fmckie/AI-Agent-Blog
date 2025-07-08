"""
Comprehensive test suite for rag.drive.storage module.

This test file provides extensive coverage for the DriveStorageHandler class,
testing all methods with various scenarios including success, failure, and edge cases.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from supabase import Client

from rag.drive.storage import DriveStorageHandler


class TestDriveStorageHandler:
    """Test suite for DriveStorageHandler class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration objects."""
        with patch("rag.drive.storage.get_config") as mock_get_config, \
             patch("rag.drive.storage.get_rag_config") as mock_get_rag_config:
            
            # Mock main config
            mock_config = Mock()
            mock_get_config.return_value = mock_config
            
            # Mock RAG config
            mock_rag_config = Mock()
            mock_rag_config.supabase_url = "https://test.supabase.co"
            mock_rag_config.supabase_service_key = "test-key"
            mock_get_rag_config.return_value = mock_rag_config
            
            yield mock_config, mock_rag_config

    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock(spec=Client)
        
        # Mock table operations
        client.table = Mock(return_value=Mock())
        
        # Setup chainable mocks for common operations
        table_mock = client.table.return_value
        table_mock.update = Mock(return_value=table_mock)
        table_mock.insert = Mock(return_value=table_mock)
        table_mock.select = Mock(return_value=table_mock)
        table_mock.upsert = Mock(return_value=table_mock)
        table_mock.delete = Mock(return_value=table_mock)
        table_mock.eq = Mock(return_value=table_mock)
        table_mock.is_ = Mock(return_value=table_mock)
        table_mock.not_ = Mock(return_value=table_mock)
        table_mock.order = Mock(return_value=table_mock)
        table_mock.limit = Mock(return_value=table_mock)
        table_mock.offset = Mock(return_value=table_mock)
        table_mock.single = Mock(return_value=table_mock)
        
        # Mock execute to return data
        table_mock.execute = Mock(return_value=Mock(data=[{"id": "test-id"}]))
        
        return client

    @pytest.fixture
    def storage_handler(self, mock_config, mock_supabase_client):
        """Create DriveStorageHandler instance with mocked dependencies."""
        with patch("rag.drive.storage.create_client", return_value=mock_supabase_client):
            handler = DriveStorageHandler(client=mock_supabase_client)
            return handler

    # Constructor Tests
    
    def test_init_with_provided_client(self, mock_config, mock_supabase_client):
        """Test initialization with a provided Supabase client."""
        # Initialize handler with provided client
        handler = DriveStorageHandler(client=mock_supabase_client)
        
        # Verify client is used
        assert handler.client == mock_supabase_client
        
    def test_init_without_client(self, mock_config):
        """Test initialization without client (creates new one)."""
        mock_client = Mock(spec=Client)
        
        with patch("rag.drive.storage.create_client", return_value=mock_client) as mock_create:
            handler = DriveStorageHandler()
            
            # Verify client was created
            mock_create.assert_called_once()
            assert handler.client == mock_client

    # track_upload Tests
    
    def test_track_upload_success(self, storage_handler, mock_supabase_client):
        """Test successful article upload tracking."""
        # Setup test data
        article_id = uuid4()
        drive_file_id = "drive-123"
        drive_url = "https://drive.google.com/file/123"
        folder_path = "2025/01/07"
        
        # Mock successful update
        mock_supabase_client.table.return_value.execute.return_value = Mock(
            data=[{"id": str(article_id)}]
        )
        
        # Call method
        result = storage_handler.track_upload(
            article_id=article_id,
            drive_file_id=drive_file_id,
            drive_url=drive_url,
            folder_path=folder_path
        )
        
        # Verify result
        assert result is True
        
        # Verify database calls
        mock_supabase_client.table.assert_called_with("generated_articles")
        update_mock = mock_supabase_client.table.return_value.update
        update_mock.assert_called_once()
        
        # Verify update data
        update_data = update_mock.call_args[0][0]
        assert update_data["drive_file_id"] == drive_file_id
        assert update_data["drive_url"] == drive_url
        assert "updated_at" in update_data

    def test_track_upload_failure(self, storage_handler, mock_supabase_client):
        """Test handling of upload tracking failure."""
        # Setup
        article_id = uuid4()
        
        # Mock empty result (failure)
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=[])
        
        # Call method
        result = storage_handler.track_upload(
            article_id=article_id,
            drive_file_id="drive-123",
            drive_url="https://drive.google.com/file/123",
            folder_path="2025/01/07"
        )
        
        # Verify failure
        assert result is False

    def test_track_upload_exception(self, storage_handler, mock_supabase_client):
        """Test exception handling in track_upload."""
        # Mock exception
        mock_supabase_client.table.side_effect = Exception("Database error")
        
        # Call method
        result = storage_handler.track_upload(
            article_id=uuid4(),
            drive_file_id="drive-123",
            drive_url="https://drive.google.com/file/123",
            folder_path="2025/01/07"
        )
        
        # Verify exception handled
        assert result is False

    # track_drive_document Tests
    
    def test_track_drive_document_success(self, storage_handler, mock_supabase_client):
        """Test successful Drive document tracking."""
        # Setup test data
        file_id = "drive-doc-456"
        file_name = "research_paper.pdf"
        mime_type = "application/pdf"
        drive_url = "https://drive.google.com/file/456"
        folder_path = "Research/2025"
        metadata = {"author": "John Doe", "year": 2025}
        
        # Mock successful insert
        doc_id = str(uuid4())
        mock_supabase_client.table.return_value.execute.return_value = Mock(
            data=[{"id": doc_id}]
        )
        
        # Call method
        result = storage_handler.track_drive_document(
            file_id=file_id,
            file_name=file_name,
            mime_type=mime_type,
            drive_url=drive_url,
            folder_path=folder_path,
            metadata=metadata
        )
        
        # Verify result
        assert result == UUID(doc_id)
        
        # Verify database calls
        mock_supabase_client.table.assert_called_with("research_documents")
        insert_mock = mock_supabase_client.table.return_value.insert
        insert_mock.assert_called_once()
        
        # Verify insert data
        insert_data = insert_mock.call_args[0][0]
        assert insert_data["source"] == file_name
        assert insert_data["source_type"] == "drive"
        assert insert_data["drive_file_id"] == file_id
        
        # Verify metadata JSON
        metadata_json = json.loads(insert_data["metadata"])
        assert metadata_json["mime_type"] == mime_type
        assert metadata_json["author"] == "John Doe"

    def test_track_drive_document_no_metadata(self, storage_handler, mock_supabase_client):
        """Test tracking document without additional metadata."""
        # Mock successful insert
        doc_id = str(uuid4())
        mock_supabase_client.table.return_value.execute.return_value = Mock(
            data=[{"id": doc_id}]
        )
        
        # Call without metadata
        result = storage_handler.track_drive_document(
            file_id="drive-789",
            file_name="document.txt",
            mime_type="text/plain",
            drive_url="https://drive.google.com/file/789",
            folder_path="Docs"
        )
        
        # Verify success
        assert result == UUID(doc_id)

    # get_uploaded_articles Tests
    
    def test_get_uploaded_articles_success(self, storage_handler, mock_supabase_client):
        """Test retrieving uploaded articles."""
        # Mock articles data
        articles = [
            {
                "id": str(uuid4()),
                "title": "Article 1",
                "keyword": "AI",
                "drive_file_id": "drive-1",
                "drive_url": "https://drive.google.com/file/1",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid4()),
                "title": "Article 2",
                "keyword": "ML",
                "drive_file_id": "drive-2",
                "drive_url": "https://drive.google.com/file/2",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=articles)
        
        # Call method
        result = storage_handler.get_uploaded_articles(limit=10, offset=0)
        
        # Verify results
        assert len(result) == 2
        assert result[0]["title"] == "Article 1"
        assert result[1]["title"] == "Article 2"
        
        # Verify query construction
        mock_supabase_client.table.assert_called_with("generated_articles")
        mock_supabase_client.table.return_value.not_.is_.assert_called_with("drive_file_id", "null")

    def test_get_uploaded_articles_with_metadata(self, storage_handler, mock_supabase_client):
        """Test retrieving articles with sync metadata."""
        # Mock article
        article = {
            "id": str(uuid4()),
            "title": "Test Article",
            "drive_file_id": "drive-123"
        }
        
        # Mock sync status
        sync_status = {
            "file_id": "drive-123",
            "sync_status": "synced",
            "last_synced": datetime.now(timezone.utc).isoformat()
        }
        
        # Setup mocks
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=[article])
        
        # Mock get_sync_status
        with patch.object(storage_handler, 'get_sync_status', return_value=sync_status):
            result = storage_handler.get_uploaded_articles(include_metadata=True)
            
            # Verify sync status added
            assert result[0]["sync_status"] == sync_status

    def test_get_uploaded_articles_empty(self, storage_handler, mock_supabase_client):
        """Test handling empty results."""
        # Mock empty result
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=[])
        
        # Call method
        result = storage_handler.get_uploaded_articles()
        
        # Verify empty list returned
        assert result == []

    # get_sync_status Tests
    
    def test_get_sync_status_found(self, storage_handler, mock_supabase_client):
        """Test retrieving existing sync status."""
        # Mock sync data
        sync_data = {
            "file_id": "drive-123",
            "local_path": "article_456",
            "sync_status": "synced",
            "last_synced": datetime.now(timezone.utc).isoformat()
        }
        
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=sync_data)
        
        # Call method
        result = storage_handler.get_sync_status("drive-123")
        
        # Verify result
        assert result == sync_data
        
        # Verify query
        mock_supabase_client.table.assert_called_with("drive_sync_status")
        mock_supabase_client.table.return_value.eq.assert_called_with("file_id", "drive-123")

    def test_get_sync_status_not_found(self, storage_handler, mock_supabase_client):
        """Test sync status not found."""
        # Mock no data
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=None)
        
        # Call method
        result = storage_handler.get_sync_status("nonexistent")
        
        # Verify None returned
        assert result is None

    # _update_sync_status Tests
    
    def test_update_sync_status_success(self, storage_handler, mock_supabase_client):
        """Test successful sync status update."""
        # Mock successful upsert
        mock_supabase_client.table.return_value.execute.return_value = Mock(
            data=[{"file_id": "drive-123"}]
        )
        
        # Call method
        result = storage_handler._update_sync_status(
            file_id="drive-123",
            local_path="article_456",
            drive_url="https://drive.google.com/file/123",
            status="synced"
        )
        
        # Verify success
        assert result is True
        
        # Verify upsert call
        mock_supabase_client.table.assert_called_with("drive_sync_status")
        upsert_mock = mock_supabase_client.table.return_value.upsert
        upsert_mock.assert_called_once()
        
        # Verify upsert data
        upsert_data = upsert_mock.call_args[0][0]
        assert upsert_data["file_id"] == "drive-123"
        assert upsert_data["sync_status"] == "synced"
        assert "last_synced" in upsert_data

    def test_update_sync_status_with_error(self, storage_handler, mock_supabase_client):
        """Test updating sync status with error message."""
        # Mock successful upsert
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=[{}])
        
        # Call with error
        result = storage_handler._update_sync_status(
            file_id="error-123",
            local_path="article_789",
            drive_url="",
            status="error",
            error_message="Upload failed: Network timeout"
        )
        
        # Verify error message included
        upsert_data = mock_supabase_client.table.return_value.upsert.call_args[0][0]
        assert upsert_data["error_message"] == "Upload failed: Network timeout"

    # get_pending_uploads Tests
    
    def test_get_pending_uploads_success(self, storage_handler, mock_supabase_client):
        """Test retrieving pending uploads."""
        # Mock pending articles
        pending = [
            {
                "id": str(uuid4()),
                "title": "Pending Article 1",
                "keyword": "Blockchain",
                "file_path": "/drafts/article1.html",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=pending)
        
        # Call method
        result = storage_handler.get_pending_uploads(limit=5)
        
        # Verify results
        assert len(result) == 1
        assert result[0]["title"] == "Pending Article 1"
        
        # Verify query filters for null drive_file_id
        mock_supabase_client.table.return_value.is_.assert_called_with("drive_file_id", "null")

    # mark_upload_error Tests
    
    def test_mark_upload_error_success(self, storage_handler):
        """Test marking an upload as failed."""
        article_id = uuid4()
        error_msg = "Authentication failed"
        
        # Mock _update_sync_status
        with patch.object(storage_handler, '_update_sync_status', return_value=True) as mock_update:
            result = storage_handler.mark_upload_error(article_id, error_msg)
            
            # Verify success
            assert result is True
            
            # Verify update called correctly
            mock_update.assert_called_once_with(
                file_id=f"error_{article_id}",
                local_path=f"article_{article_id}",
                drive_url="",
                status="error",
                error_message=error_msg
            )

    # get_drive_documents Tests
    
    def test_get_drive_documents_success(self, storage_handler, mock_supabase_client):
        """Test retrieving Drive documents."""
        # Mock documents with JSON metadata
        docs = [
            {
                "id": str(uuid4()),
                "source": "research.pdf",
                "drive_file_id": "drive-doc-1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": json.dumps({"pages": 50, "author": "Jane Smith"})
            }
        ]
        
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=docs)
        
        # Call method
        result = storage_handler.get_drive_documents()
        
        # Verify results
        assert len(result) == 1
        assert result[0]["source"] == "research.pdf"
        
        # Verify metadata parsed
        assert isinstance(result[0]["metadata"], dict)
        assert result[0]["metadata"]["pages"] == 50

    def test_get_drive_documents_invalid_metadata(self, storage_handler, mock_supabase_client):
        """Test handling invalid JSON metadata."""
        # Mock document with invalid metadata
        docs = [
            {
                "id": str(uuid4()),
                "source": "broken.pdf",
                "metadata": "invalid json"
            }
        ]
        
        mock_supabase_client.table.return_value.execute.return_value = Mock(data=docs)
        
        # Call method
        result = storage_handler.get_drive_documents()
        
        # Verify metadata set to empty dict on parse failure
        assert result[0]["metadata"] == {}

    # cleanup_orphaned_sync_records Tests
    
    def test_cleanup_orphaned_sync_records_dry_run(self, storage_handler, mock_supabase_client):
        """Test cleanup in dry run mode (default)."""
        # Mock sync records
        sync_records = [
            {"file_id": "file-1", "local_path": "article_123"},
            {"file_id": "file-2", "local_path": "drive_doc_456"},
            {"file_id": "file-3", "local_path": "article_789"}  # This will be orphaned
        ]
        
        # Setup mocks for checking existence
        def mock_execute_side_effect(*args, **kwargs):
            # Check which table is being queried
            if "generated_articles" in str(mock_supabase_client.table.call_args):
                # Article 789 doesn't exist
                if "789" in str(mock_supabase_client.table.return_value.eq.call_args):
                    return Mock(data=[])
                return Mock(data=[{"id": "exists"}])
            elif "research_documents" in str(mock_supabase_client.table.call_args):
                return Mock(data=[{"id": "exists"}])
            else:
                return Mock(data=sync_records)
        
        mock_supabase_client.table.return_value.execute.side_effect = mock_execute_side_effect
        
        # Call method
        count, orphaned_ids = storage_handler.cleanup_orphaned_sync_records(dry_run=True)
        
        # Verify results
        assert count == 1
        assert "file-3" in orphaned_ids
        
        # Verify no deletions in dry run
        mock_supabase_client.table.return_value.delete.assert_not_called()

    def test_cleanup_orphaned_sync_records_actual_delete(self, storage_handler, mock_supabase_client):
        """Test cleanup with actual deletion."""
        # Mock sync records
        sync_records = [
            {"file_id": "orphan-1", "local_path": "article_missing"}
        ]
        
        # Mock queries
        mock_supabase_client.table.return_value.execute.side_effect = [
            Mock(data=sync_records),  # Initial sync records query
            Mock(data=[]),  # Article doesn't exist
            Mock(data=[])   # Delete result
        ]
        
        # Call method with dry_run=False
        count, orphaned_ids = storage_handler.cleanup_orphaned_sync_records(dry_run=False)
        
        # Verify deletion called
        assert count == 1
        assert "orphan-1" in orphaned_ids
        mock_supabase_client.table.return_value.delete.assert_called()

    # Exception Handling Tests
    
    def test_exception_handling_in_all_methods(self, storage_handler, mock_supabase_client):
        """Test that all methods handle exceptions gracefully."""
        # Mock database error
        mock_supabase_client.table.side_effect = Exception("Connection failed")
        
        # Test each method handles exceptions
        assert storage_handler.track_upload(uuid4(), "file", "url", "path") is False
        assert storage_handler.track_drive_document("id", "name", "type", "url", "path") is None
        assert storage_handler.get_uploaded_articles() == []
        assert storage_handler.get_sync_status("id") is None
        assert storage_handler._update_sync_status("id", "path", "url", "status") is False
        assert storage_handler.get_pending_uploads() == []
        assert storage_handler.mark_upload_error(uuid4(), "error") is False
        assert storage_handler.get_drive_documents() == []
        
        # Cleanup should return empty results on error
        count, ids = storage_handler.cleanup_orphaned_sync_records()
        assert count == 0
        assert ids == []