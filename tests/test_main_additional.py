"""
Additional tests for main.py to improve coverage.

This file contains tests for uncovered functions and edge cases.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import shutil
import tempfile

import pytest
from click.testing import CliRunner

from config import Config
from main import cli, batch, cleanup, cache, drive, _run_batch_generation
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from workflow import WorkflowOrchestrator


class TestBatchCommand:
    """Test cases for the batch command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.log_level = "INFO"
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        return ResearchFindings(
            keyword="test keyword",
            research_summary="Test research summary.",
            academic_sources=[
                AcademicSource(
                    title="Test Study",
                    url="https://test.edu/study",
                    excerpt="Test excerpt",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Finding 1"],
            total_sources_analyzed=1,
            search_query_used="test keyword",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        return ArticleOutput(
            title="Test Article",
            meta_description="Test description",
            focus_keyword="test keyword",
            introduction="Test introduction",
            main_sections=[
                ArticleSection(
                    heading="Section 1",
                    content="Test content " * 50,  # 50 words
                )
            ],
            conclusion="Test conclusion",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.015,
            sources_used=["https://test.edu/study"],
        )

    @patch("main.get_config")
    @patch("main._run_batch_generation")
    def test_batch_with_parallel_processing(
        self, mock_run_batch, mock_get_config, runner, mock_config
    ):
        """Test batch command with parallel processing."""
        mock_get_config.return_value = mock_config
        mock_run_batch.return_value = None

        result = runner.invoke(
            cli,
            ["batch", "keyword1", "keyword2", "keyword3", "--parallel", "3"],
        )

        assert result.exit_code == 0
        mock_run_batch.assert_called_once()
        call_args = mock_run_batch.call_args[0]
        assert call_args[0] == ["keyword1", "keyword2", "keyword3"]
        assert call_args[1] == 3  # parallel count

    @patch("main.get_config")
    @patch("main._run_batch_generation")
    def test_batch_with_continue_on_error(
        self, mock_run_batch, mock_get_config, runner, mock_config
    ):
        """Test batch command with continue-on-error flag."""
        mock_get_config.return_value = mock_config
        mock_run_batch.return_value = None

        result = runner.invoke(
            cli,
            ["batch", "keyword1", "keyword2", "--continue-on-error"],
        )

        assert result.exit_code == 0
        mock_run_batch.assert_called_once()
        call_args = mock_run_batch.call_args[0]
        assert call_args[3] is True  # continue_on_error

    @patch("main.get_config")
    @patch("main._run_batch_generation")
    def test_batch_with_output_dir(
        self, mock_run_batch, mock_get_config, runner, mock_config
    ):
        """Test batch command with custom output directory."""
        mock_get_config.return_value = mock_config
        mock_run_batch.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                cli,
                ["batch", "keyword1", "--output-dir", tmpdir],
            )

            assert result.exit_code == 0
            mock_run_batch.assert_called_once()
            call_args = mock_run_batch.call_args[0]
            assert call_args[4] == Path(tmpdir)  # output_dir

    @patch("main.get_config")
    def test_batch_configuration_error(self, mock_get_config, runner):
        """Test batch command when configuration fails."""
        mock_get_config.side_effect = Exception("Config error")

        result = runner.invoke(cli, ["batch", "keyword1"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output


class TestCleanupCommand:
    """Test cases for the cleanup command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        # Use a real temporary directory for cleanup tests
        config.output_dir = Path(tempfile.mkdtemp())
        return config

    @patch("main.get_config")
    def test_cleanup_no_files(self, mock_get_config, runner, mock_config):
        """Test cleanup when no files to clean."""
        mock_get_config.return_value = mock_config

        try:
            result = runner.invoke(cli, ["cleanup"])

            assert result.exit_code == 0
            assert "No cleanup needed" in result.output
            assert "everything is tidy" in result.output
        finally:
            # Clean up temp directory
            shutil.rmtree(mock_config.output_dir, ignore_errors=True)

    @patch("main.get_config")
    def test_cleanup_with_old_files(self, mock_get_config, runner, mock_config):
        """Test cleanup with old workflow files."""
        mock_get_config.return_value = mock_config

        try:
            # Create old workflow state files
            old_time = datetime.now() - timedelta(hours=48)

            # Create old state file
            state_file = (
                mock_config.output_dir / ".workflow_state_test_20240101_120000.json"
            )
            state_file.write_text("{}")
            # Set modification time to 48 hours ago
            import os

            old_timestamp = old_time.timestamp()
            os.utime(state_file, (old_timestamp, old_timestamp))

            # Create old temp directory
            temp_dir = mock_config.output_dir / ".temp_test_20240101"
            temp_dir.mkdir()
            os.utime(temp_dir, (old_timestamp, old_timestamp))

            # Mock the cleanup function
            with patch(
                "main.WorkflowOrchestrator.cleanup_orphaned_files"
            ) as mock_cleanup:
                mock_cleanup.return_value = (1, 1)  # Cleaned 1 state file, 1 temp dir

                result = runner.invoke(cli, ["cleanup"])

                assert result.exit_code == 0
                assert "Cleanup complete" in result.output
                assert "Removed 1 state files" in result.output
                assert "Removed 1 temp directories" in result.output
                mock_cleanup.assert_called_once_with(mock_config.output_dir, 24)

        finally:
            # Clean up temp directory
            shutil.rmtree(mock_config.output_dir, ignore_errors=True)

    @patch("main.get_config")
    def test_cleanup_dry_run(self, mock_get_config, runner, mock_config):
        """Test cleanup in dry run mode."""
        mock_get_config.return_value = mock_config

        try:
            # Create files that would be cleaned
            old_time = datetime.now() - timedelta(hours=48)

            state_file = (
                mock_config.output_dir / ".workflow_state_old_20240101_120000.json"
            )
            state_file.write_text("{}")

            # Set old modification time
            import os

            old_timestamp = old_time.timestamp()
            os.utime(state_file, (old_timestamp, old_timestamp))

            result = runner.invoke(cli, ["cleanup", "--dry-run"])

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "Would delete:" in result.output
            assert state_file.exists()  # File should still exist

        finally:
            # Clean up temp directory
            shutil.rmtree(mock_config.output_dir, ignore_errors=True)

    @patch("main.get_config")
    def test_cleanup_with_custom_age(self, mock_get_config, runner, mock_config):
        """Test cleanup with custom age threshold."""
        mock_get_config.return_value = mock_config

        try:
            # Create a file that's 6 hours old
            recent_time = datetime.now() - timedelta(hours=6)

            state_file = (
                mock_config.output_dir / ".workflow_state_recent_20240101_180000.json"
            )
            state_file.write_text("{}")

            import os

            recent_timestamp = recent_time.timestamp()
            os.utime(state_file, (recent_timestamp, recent_timestamp))

            # Mock the cleanup function
            with patch(
                "main.WorkflowOrchestrator.cleanup_orphaned_files"
            ) as mock_cleanup:
                mock_cleanup.return_value = (1, 0)

                # Should clean files older than 5 hours
                result = runner.invoke(cli, ["cleanup", "--older-than", "5"])

                assert result.exit_code == 0
                mock_cleanup.assert_called_once_with(mock_config.output_dir, 5)

        finally:
            # Clean up temp directory
            shutil.rmtree(mock_config.output_dir, ignore_errors=True)

    @patch("main.get_config")
    @patch("main.WorkflowOrchestrator.cleanup_orphaned_files")
    def test_cleanup_error_handling(
        self, mock_cleanup, mock_get_config, runner, mock_config
    ):
        """Test cleanup error handling."""
        mock_get_config.return_value = mock_config
        mock_cleanup.side_effect = Exception("Cleanup failed")

        result = runner.invoke(cli, ["cleanup"])

        assert result.exit_code == 1
        assert "Cleanup failed" in result.output


class TestBatchGeneration:
    """Test cases for _run_batch_generation function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        return config

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock workflow orchestrator."""
        orchestrator = Mock(spec=WorkflowOrchestrator)
        orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/output/test/index.html")
        )
        return orchestrator

    @pytest.mark.asyncio
    async def test_batch_generation_sequential(self, mock_config, mock_orchestrator):
        """Test sequential batch generation."""
        keywords = ["keyword1", "keyword2", "keyword3"]

        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            with patch("main.console") as mock_console:
                await _run_batch_generation(
                    keywords,
                    parallel=1,
                    dry_run=False,
                    continue_on_error=False,
                    output_dir=None,
                    show_progress=True,
                    config=mock_config,
                )

                # Should process all keywords sequentially
                assert mock_orchestrator.run_full_workflow.call_count == 3
                for keyword in keywords:
                    mock_orchestrator.run_full_workflow.assert_any_call(
                        keyword, dry_run=False
                    )

    @pytest.mark.asyncio
    async def test_batch_generation_parallel(self, mock_config, mock_orchestrator):
        """Test parallel batch generation."""
        keywords = ["keyword1", "keyword2", "keyword3", "keyword4"]

        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            with patch("main.console") as mock_console:
                await _run_batch_generation(
                    keywords,
                    parallel=2,  # Process 2 at a time
                    dry_run=False,
                    continue_on_error=False,
                    output_dir=None,
                    show_progress=True,
                    config=mock_config,
                )

                # All keywords should be processed
                assert mock_orchestrator.run_full_workflow.call_count == 4

    @pytest.mark.asyncio
    async def test_batch_generation_with_error_continue(
        self, mock_config, mock_orchestrator
    ):
        """Test batch generation continues on error when flag is set."""
        keywords = ["keyword1", "keyword2", "keyword3"]

        # Make second keyword fail
        mock_orchestrator.run_full_workflow.side_effect = [
            Path("/tmp/output/keyword1/index.html"),
            Exception("Processing failed"),
            Path("/tmp/output/keyword3/index.html"),
        ]

        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            with patch("main.console") as mock_console:
                await _run_batch_generation(
                    keywords,
                    parallel=1,
                    dry_run=False,
                    continue_on_error=True,  # Should continue despite error
                    output_dir=None,
                    show_progress=True,
                    config=mock_config,
                )

                # All keywords should be attempted
                assert mock_orchestrator.run_full_workflow.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_generation_with_error_fail_fast(
        self, mock_config, mock_orchestrator
    ):
        """Test batch generation stops on error when fail-fast is enabled."""
        keywords = ["keyword1", "keyword2", "keyword3"]

        # Make second keyword fail
        mock_orchestrator.run_full_workflow.side_effect = [
            Path("/tmp/output/keyword1/index.html"),
            Exception("Processing failed"),
            Path("/tmp/output/keyword3/index.html"),
        ]

        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            with patch("main.console") as mock_console:
                with pytest.raises(Exception, match="Processing failed"):
                    await _run_batch_generation(
                        keywords,
                        parallel=1,
                        dry_run=False,
                        continue_on_error=False,  # Should stop on error
                        output_dir=None,
                        show_progress=True,
                        config=mock_config,
                    )

                # Should only process up to the error
                assert mock_orchestrator.run_full_workflow.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_generation_dry_run(self, mock_config, mock_orchestrator):
        """Test batch generation in dry run mode."""
        keywords = ["keyword1", "keyword2"]

        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            with patch("main.console") as mock_console:
                await _run_batch_generation(
                    keywords,
                    parallel=1,
                    dry_run=True,  # Dry run mode
                    continue_on_error=False,
                    output_dir=None,
                    show_progress=True,
                    config=mock_config,
                )

                # Should call with dry_run=True
                assert mock_orchestrator.run_full_workflow.call_count == 2
                for call in mock_orchestrator.run_full_workflow.call_args_list:
                    assert call[1]["dry_run"] is True


class TestCacheCommands:
    """Test cases for cache commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        return config

    @patch("main.get_config")
    @patch("main.handle_cache_search")
    def test_cache_search_with_limit(
        self, mock_handle_search, mock_get_config, runner, mock_config
    ):
        """Test cache search with result limit."""
        mock_get_config.return_value = mock_config
        mock_handle_search.return_value = None

        result = runner.invoke(cli, ["cache", "search", "test query", "--limit", "5"])

        assert result.exit_code == 0
        mock_handle_search.assert_called_once()
        call_args = mock_handle_search.call_args[0]
        assert call_args[0] == "test query"
        assert call_args[1] == 5  # limit

    @patch("main.get_config")
    @patch("main.handle_cache_stats")
    def test_cache_stats_detailed(
        self, mock_handle_stats, mock_get_config, runner, mock_config
    ):
        """Test cache stats with detailed flag."""
        mock_get_config.return_value = mock_config
        mock_handle_stats.return_value = None

        result = runner.invoke(cli, ["cache", "stats", "--detailed"])

        assert result.exit_code == 0
        mock_handle_stats.assert_called_once_with(detailed=True)

    @patch("main.get_config")
    @patch("main.handle_cache_clear")
    def test_cache_clear_force(
        self, mock_handle_clear, mock_get_config, runner, mock_config
    ):
        """Test cache clear with force flag."""
        mock_get_config.return_value = mock_config
        mock_handle_clear.return_value = None

        result = runner.invoke(cli, ["cache", "clear", "--force"])

        assert result.exit_code == 0
        mock_handle_clear.assert_called_once_with(force=True, pattern=None)

    @patch("main.get_config")
    @patch("main.handle_cache_clear")
    def test_cache_clear_with_pattern(
        self, mock_handle_clear, mock_get_config, runner, mock_config
    ):
        """Test cache clear with pattern."""
        mock_get_config.return_value = mock_config
        mock_handle_clear.return_value = None

        result = runner.invoke(cli, ["cache", "clear", "--pattern", "blood_sugar*"])

        assert result.exit_code == 0
        mock_handle_clear.assert_called_once_with(force=False, pattern="blood_sugar*")

    @patch("main.get_config")
    @patch("main.handle_cache_warm")
    def test_cache_warm_with_variations(
        self, mock_handle_warm, mock_get_config, runner, mock_config
    ):
        """Test cache warm with keyword variations."""
        mock_get_config.return_value = mock_config
        mock_handle_warm.return_value = None

        result = runner.invoke(cli, ["cache", "warm", "diabetes", "--variations"])

        assert result.exit_code == 0
        mock_handle_warm.assert_called_once()
        call_args = mock_handle_warm.call_args[0]
        assert "diabetes" in call_args[0]  # keywords list
        assert call_args[1] is True  # include_variations

    @patch("main.get_config")
    @patch("main.handle_export_cache_metrics")
    def test_cache_export_csv(
        self, mock_handle_export, mock_get_config, runner, mock_config
    ):
        """Test cache export to CSV format."""
        mock_get_config.return_value = mock_config
        mock_handle_export.return_value = None

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            result = runner.invoke(
                cli, ["cache", "export", tmp.name, "--format", "csv"]
            )

            assert result.exit_code == 0
            mock_handle_export.assert_called_once_with(Path(tmp.name), format="csv")

            # Clean up
            Path(tmp.name).unlink(missing_ok=True)


class TestDriveCommands:
    """Test cases for Google Drive commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        return config

    @patch("main.get_config")
    @patch("main.GoogleDriveAuth")
    def test_drive_auth(self, mock_auth_class, mock_get_config, runner, mock_config):
        """Test drive auth command."""
        mock_get_config.return_value = mock_config
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth
        mock_auth.authenticate.return_value = True

        result = runner.invoke(cli, ["drive", "auth"])

        assert result.exit_code == 0
        assert "Authentication successful" in result.output
        mock_auth.authenticate.assert_called_once()

    @patch("main.get_config")
    @patch("main.ArticleUploader")
    def test_drive_upload_article(
        self, mock_uploader_class, mock_get_config, runner, mock_config
    ):
        """Test drive upload command."""
        mock_get_config.return_value = mock_config
        mock_uploader = Mock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.upload_article.return_value = "file_id_123"

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp.write(b"<html><body>Test article</body></html>")
            tmp.flush()

            result = runner.invoke(cli, ["drive", "upload", tmp.name])

            assert result.exit_code == 0
            assert "Upload successful" in result.output
            mock_uploader.upload_article.assert_called_once()

            # Clean up
            Path(tmp.name).unlink(missing_ok=True)

    @patch("main.get_config")
    @patch("main.DriveStorageHandler")
    def test_drive_list(self, mock_storage_class, mock_get_config, runner, mock_config):
        """Test drive list command."""
        mock_get_config.return_value = mock_config
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Mock uploaded articles
        mock_storage.get_uploaded_articles.return_value = [
            {
                "keyword": "diabetes",
                "file_id": "id123",
                "upload_date": "2024-01-01",
                "title": "Diabetes Article",
            },
            {
                "keyword": "nutrition",
                "file_id": "id456",
                "upload_date": "2024-01-02",
                "title": "Nutrition Guide",
            },
        ]

        result = runner.invoke(cli, ["drive", "list"])

        assert result.exit_code == 0
        assert "diabetes" in result.output
        assert "nutrition" in result.output
        mock_storage.get_uploaded_articles.assert_called_once()

    @patch("main.get_config")
    @patch("main.get_rag_config")
    @patch("main.GoogleDriveAuth")
    @patch("main.DriveStorageHandler")
    def test_drive_status(
        self,
        mock_storage_class,
        mock_auth_class,
        mock_get_rag_config,
        mock_get_config,
        runner,
        mock_config,
    ):
        """Test drive status command."""
        mock_config.google_drive_upload_folder_id = "folder_id_123"
        mock_get_config.return_value = mock_config

        # Mock RAG config
        mock_rag_config = Mock()
        mock_rag_config.google_drive_enabled = True
        mock_rag_config.google_drive_auto_upload = True
        mock_get_rag_config.return_value = mock_rag_config

        # Mock auth
        mock_auth = Mock()
        mock_auth.is_authenticated = True
        mock_auth.test_connection.return_value = True
        mock_auth_class.return_value = mock_auth

        # Mock storage
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_uploaded_articles.return_value = [
            {"title": "Article 1", "uploaded_at": "2024-01-01"},
            {"title": "Article 2", "uploaded_at": "2024-01-02"},
        ]
        mock_storage.get_pending_uploads.return_value = []

        result = runner.invoke(cli, ["drive", "status"])

        assert result.exit_code == 0
        assert "Authenticated" in result.output
        assert "Total Uploaded: 2" in result.output


class TestMainHelperFunctions:
    """Test helper functions in main.py."""

    def test_format_error_message(self):
        """Test error message formatting."""
        from main import _format_error_message

        # Test with simple exception
        error = ValueError("Test error")
        message = _format_error_message(error)
        assert "Test error" in message

        # Test with exception chain
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        except RuntimeError as e:
            message = _format_error_message(e)
            assert "Outer error" in message
            assert "Inner error" in message

    def test_validate_keywords(self):
        """Test keyword validation."""
        from main import _validate_keywords

        # Valid keywords
        assert _validate_keywords(["diabetes", "nutrition"]) is True

        # Empty keywords
        assert _validate_keywords([]) is False

        # Keywords with only whitespace
        assert _validate_keywords(["", "  ", "\t"]) is False

        # Mixed valid and invalid
        assert _validate_keywords(["diabetes", "", "nutrition"]) is True

    @patch("main.console")
    def test_print_batch_summary(self, mock_console):
        """Test batch summary printing."""
        from main import _print_batch_summary

        results = {
            "keyword1": Path("/tmp/output/keyword1/index.html"),
            "keyword2": Exception("Failed"),
            "keyword3": Path("/tmp/output/keyword3/index.html"),
        }

        _print_batch_summary(results, total_time=120.5)

        # Should print summary with success/failure counts
        assert mock_console.print.called
        calls = [str(call) for call in mock_console.print.call_args_list]
        summary_printed = any("2 successful" in str(call) for call in calls)
        assert summary_printed
