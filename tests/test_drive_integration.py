"""
Integration tests for Google Drive upload functionality.

Tests the complete flow from article generation to Drive upload.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import pytest
from click.testing import CliRunner

from config import Config
from models import ArticleOutput, ResearchFindings
from workflow import WorkflowOrchestrator
from rag.drive.auth import GoogleDriveAuth
from rag.drive.uploader import ArticleUploader
from rag.drive.storage import DriveStorageHandler
from main import cli


@pytest.fixture
def runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_article():
    """Create a mock article output."""
    return ArticleOutput(
        title="Test Article About SEO",
        meta_description="A comprehensive test article for SEO optimization that explores various aspects of search engine optimization strategies and techniques",
        introduction="This is the introduction to our comprehensive article about SEO optimization. In this article, we will explore various strategies and techniques that can help improve your website's search engine rankings and visibility. We'll cover both on-page and off-page optimization methods.",
        main_sections=[
            {
                "heading": "Section 1: Understanding SEO Basics",
                "content": "Content for section 1 that provides a detailed overview of search engine optimization fundamentals. This section covers the basic principles of how search engines work, what they look for in websites, and how you can optimize your content to rank better in search results.",
                "subsections": [],
            },
            {
                "heading": "Section 2: On-Page Optimization Techniques",
                "content": "This section delves into on-page optimization strategies including title tags, meta descriptions, header tags, and content optimization. We'll explore how to structure your content for maximum SEO impact and user engagement.",
                "subsections": [],
            },
            {
                "heading": "Section 3: Off-Page SEO Strategies",
                "content": "In this final section, we examine off-page SEO tactics such as link building, social signals, and brand mentions. Understanding these external factors is crucial for building your website's authority and improving search rankings.",
                "subsections": [],
            },
        ],
        conclusion="This is the conclusion of our comprehensive SEO article. We've covered the fundamental aspects of search engine optimization and provided practical strategies you can implement.",
        focus_keyword="SEO optimization",
        word_count=1500,
        keyword_density=0.02,
        readability_score=8.5,
        seo_score=9.0,
        reading_time_minutes=7,
        sources_used=["source1", "source2"],
    )


@pytest.fixture
def mock_research():
    """Create mock research findings."""
    return ResearchFindings(
        keyword="test keyword",
        summary="Test summary",
        research_summary="This is a comprehensive research summary covering all aspects of the topic",
        search_query_used="test keyword research",
        academic_sources=[],
        key_statistics=[],
        research_gaps=[],
        total_sources_analyzed=5,
        credible_sources_found=3,
    )


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


class TestDriveUploadIntegration:
    """Test Google Drive upload integration with workflow."""

    @pytest.mark.asyncio
    async def test_workflow_with_drive_upload_enabled(
        self, mock_config, mock_article, mock_research, temp_output_dir
    ):
        """Test that workflow uploads to Drive when enabled."""
        # Configure for Drive upload
        mock_config.output_dir = temp_output_dir
        mock_config.google_drive_upload_folder_id = "test_folder_id"

        with patch("rag.config.get_rag_config") as mock_rag_config:
            # Enable Drive features
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True

            # Mock Drive components
            with (
                patch("workflow.GoogleDriveAuth") as mock_auth_class,
                patch("workflow.ArticleUploader") as mock_uploader_class,
                patch("workflow.DriveStorageHandler") as mock_storage_class,
            ):

                # Setup mocks
                mock_auth = Mock()
                mock_auth_class.return_value = mock_auth

                mock_uploader = Mock()
                mock_uploader.upload_html_as_doc.return_value = {
                    "file_id": "drive_file_123",
                    "name": "Test Article About SEO",
                    "web_link": "https://docs.google.com/document/d/drive_file_123",
                    "folder_path": "2025/01/07",
                }
                mock_uploader_class.return_value = mock_uploader

                # Create orchestrator
                orchestrator = WorkflowOrchestrator(mock_config)

                # Mock the agent runs
                with (
                    patch.object(
                        orchestrator, "run_research", return_value=mock_research
                    ),
                    patch.object(
                        orchestrator, "run_writing", return_value=mock_article
                    ),
                ):

                    # Run workflow
                    result_path = await orchestrator.run_full_workflow("test keyword")

                    # Verify Drive upload was called
                    mock_uploader.upload_html_as_doc.assert_called_once()

                    # Check upload parameters
                    call_args = mock_uploader.upload_html_as_doc.call_args
                    assert "Test Article About SEO" in str(call_args)
                    assert call_args.kwargs.get("title") == mock_article.title

                    # Verify workflow completed successfully
                    assert result_path.exists()
                    assert orchestrator.current_state.value == "complete"

                    # Check workflow data contains Drive info
                    assert "drive_upload" in orchestrator.workflow_data
                    assert (
                        orchestrator.workflow_data["drive_upload"]["file_id"]
                        == "drive_file_123"
                    )

    @pytest.mark.asyncio
    async def test_workflow_continues_on_drive_failure(
        self, mock_config, mock_article, mock_research, temp_output_dir
    ):
        """Test that workflow continues even if Drive upload fails."""
        mock_config.output_dir = temp_output_dir
        mock_config.google_drive_upload_folder_id = "test_folder_id"

        with patch("rag.config.get_rag_config") as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True

            # Mock Drive auth to fail
            with patch("workflow.GoogleDriveAuth") as mock_auth_class:
                mock_auth_class.side_effect = Exception("Auth failed")

                # Create orchestrator
                orchestrator = WorkflowOrchestrator(mock_config)

                # Mock the agent runs
                with (
                    patch.object(
                        orchestrator, "run_research", return_value=mock_research
                    ),
                    patch.object(
                        orchestrator, "run_writing", return_value=mock_article
                    ),
                ):

                    # Run workflow - should not fail
                    result_path = await orchestrator.run_full_workflow("test keyword")

                    # Verify workflow completed despite Drive failure
                    assert result_path.exists()
                    assert orchestrator.current_state.value == "complete"

                    # Check that Drive upload was marked as failed
                    workflow_data = orchestrator.workflow_data
                    assert workflow_data.get("drive_uploaded") is False
                    assert workflow_data.get("drive_web_link") is None

    @pytest.mark.asyncio
    async def test_workflow_skips_drive_when_disabled(
        self, mock_config, mock_article, mock_research, temp_output_dir
    ):
        """Test that workflow skips Drive upload when disabled."""
        mock_config.output_dir = temp_output_dir

        with patch("rag.config.get_rag_config") as mock_rag_config:
            # Disable Drive features
            mock_rag_config.return_value.google_drive_enabled = False

            # Ensure Drive classes are not instantiated
            with (
                patch("workflow.GoogleDriveAuth") as mock_auth_class,
                patch("workflow.ArticleUploader") as mock_uploader_class,
            ):

                # Create orchestrator
                orchestrator = WorkflowOrchestrator(mock_config)

                # Mock the agent runs
                with (
                    patch.object(
                        orchestrator, "run_research", return_value=mock_research
                    ),
                    patch.object(
                        orchestrator, "run_writing", return_value=mock_article
                    ),
                ):

                    # Run workflow
                    result_path = await orchestrator.run_full_workflow("test keyword")

                    # Verify Drive classes were never instantiated
                    mock_auth_class.assert_not_called()
                    mock_uploader_class.assert_not_called()

                    # Verify workflow completed successfully
                    assert result_path.exists()
                    assert orchestrator.current_state.value == "complete"


class TestDriveStorageHandler:
    """Test Drive storage database operations."""

    def test_track_upload(self):
        """Test tracking a successful upload."""
        with patch("rag.drive.storage.create_client") as mock_create_client:
            # Setup mock client
            mock_client = Mock()
            mock_table = Mock()
            mock_create_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "123"}
            ]
            mock_table.upsert.return_value.execute.return_value.data = True

            # Create handler and track upload
            handler = DriveStorageHandler()
            result = handler.track_upload(
                article_id="550e8400-e29b-41d4-a716-446655440000",
                drive_file_id="drive_123",
                drive_url="https://docs.google.com/document/d/drive_123",
                folder_path="2025/01/07",
            )

            assert result is True
            mock_table.update.assert_called_once()

    def test_get_uploaded_articles(self):
        """Test retrieving uploaded articles."""
        with patch("rag.drive.storage.create_client") as mock_create_client:
            # Setup mock response
            mock_data = [
                {
                    "id": "123",
                    "title": "Test Article",
                    "keyword": "test",
                    "drive_file_id": "drive_123",
                    "drive_url": "https://docs.google.com/...",
                    "uploaded_at": "2025-01-07T12:00:00Z",
                }
            ]

            mock_client = Mock()
            mock_table = Mock()
            mock_query = Mock()
            mock_create_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_query
            mock_query.not_.is_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.execute.return_value.data = mock_data

            # Get articles
            handler = DriveStorageHandler()
            articles = handler.get_uploaded_articles(limit=10)

            assert len(articles) == 1
            assert articles[0]["title"] == "Test Article"
            assert articles[0]["drive_file_id"] == "drive_123"


class TestDriveCLICommands:
    """Test Drive CLI commands."""

    def test_drive_auth_command(self, runner):
        """Test drive auth command."""
        with patch("rag.drive.auth.GoogleDriveAuth") as mock_auth_class:
            mock_auth = Mock()
            mock_auth.authenticate.return_value = None
            mock_auth.test_connection.return_value = True
            mock_auth_class.return_value = mock_auth

            result = runner.invoke(cli, ["drive", "auth"])

            assert result.exit_code == 0
            assert "Successfully authenticated" in result.output
            mock_auth.authenticate.assert_called_once()

    def test_drive_upload_command(self, runner, tmp_path):
        """Test drive upload command."""
        # Create test HTML file
        test_file = tmp_path / "test.html"
        test_file.write_text("<html><body>Test</body></html>")

        with (
            patch("rag.drive.auth.GoogleDriveAuth") as mock_auth_class,
            patch("rag.drive.uploader.ArticleUploader") as mock_uploader_class,
        ):

            mock_uploader = Mock()
            mock_uploader.upload_html_as_doc.return_value = {
                "file_id": "123",
                "name": "Test",
                "web_link": "https://docs.google.com/...",
                "folder_path": "root",
            }
            mock_uploader_class.return_value = mock_uploader

            result = runner.invoke(cli, ["drive", "upload", str(test_file)])

            assert result.exit_code == 0
            assert "Upload successful" in result.output
            mock_uploader.upload_html_as_doc.assert_called_once()

    def test_drive_list_command(self, runner):
        """Test drive list command."""
        with patch("rag.drive.storage.DriveStorageHandler") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.get_uploaded_articles.return_value = [
                {
                    "title": "Test Article",
                    "keyword": "test",
                    "uploaded_at": "2025-01-07T12:00:00Z",
                    "drive_url": "https://docs.google.com/...",
                }
            ]
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(cli, ["drive", "list"])

            assert result.exit_code == 0
            assert "Test Article" in result.output
            assert "test" in result.output

    def test_drive_status_command(self, runner):
        """Test drive status command."""
        with (
            patch("config.get_config") as mock_config,
            patch("rag.config.get_rag_config") as mock_rag_config,
            patch("rag.drive.auth.GoogleDriveAuth") as mock_auth_class,
            patch("rag.drive.storage.DriveStorageHandler") as mock_storage_class,
        ):

            # Setup config mocks
            mock_config.return_value.google_drive_upload_folder_id = "folder_123"
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True

            # Setup auth mock
            mock_auth = Mock()
            mock_auth.is_authenticated = True
            mock_auth.test_connection.return_value = True
            mock_auth_class.return_value = mock_auth

            # Setup storage mock
            mock_storage = Mock()
            mock_storage.get_uploaded_articles.return_value = [{"id": "1"}, {"id": "2"}]
            mock_storage.get_pending_uploads.return_value = [{"id": "3"}]
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(cli, ["drive", "status"])

            assert result.exit_code == 0
            assert "Drive Enabled: ✅" in result.output
            assert "Status: ✅ Authenticated" in result.output
            assert "Total Uploaded: 2 articles" in result.output
            assert "Pending Upload: 1 articles" in result.output
