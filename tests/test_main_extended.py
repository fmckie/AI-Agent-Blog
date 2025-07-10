"""
Extended tests for CLI commands not covered in test_main.py.

This module provides comprehensive coverage for cache, drive, and cleanup commands
that are missing from the main test file.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from click.testing import CliRunner

from main import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock()
    config.output_dir = Path("/tmp/output")
    config.log_level = "INFO"
    return config


class TestCacheCommands:
    """Test cache-related CLI commands."""

    def test_cache_group_help(self, runner):
        """Test cache group help message."""
        result = runner.invoke(cli, ["cache", "--help"])
        assert result.exit_code == 0
        assert "Manage the research cache system" in result.output
        assert "search" in result.output
        assert "stats" in result.output
        assert "clear" in result.output
        assert "warm" in result.output
        assert "metrics" in result.output

    @patch("main.asyncio.run")
    @patch("main.handle_cache_search")
    def test_cache_search_command(self, mock_handler, mock_asyncio_run, runner):
        """Test cache search command."""
        # Configure async mock
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic search
        result = runner.invoke(cli, ["cache", "search", "diabetes"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with("diabetes", limit=10, threshold=0.5)

        # Test with custom options
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["cache", "search", "diabetes", "--limit", "5", "--threshold", "0.8"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with("diabetes", limit=5, threshold=0.8)

    @patch("main.asyncio.run")
    @patch("main.handle_cache_stats")
    def test_cache_stats_command(self, mock_handler, mock_asyncio_run, runner):
        """Test cache stats command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic stats
        result = runner.invoke(cli, ["cache", "stats"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(detailed=False)

        # Test detailed stats
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["cache", "stats", "--detailed"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(detailed=True)

    @patch("main.asyncio.run")
    @patch("main.handle_cache_clear")
    def test_cache_clear_command(self, mock_handler, mock_asyncio_run, runner):
        """Test cache clear command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test clear by age
        result = runner.invoke(cli, ["cache", "clear", "--older-than", "30"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            older_than=30, keyword=None, force=False, dry_run=False
        )

        # Test clear by keyword
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["cache", "clear", "--keyword", "old topic"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            older_than=None, keyword="old topic", force=False, dry_run=False
        )

        # Test force clear all
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["cache", "clear", "--force"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            older_than=None, keyword=None, force=True, dry_run=False
        )

        # Test dry run
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["cache", "clear", "--older-than", "7", "--dry-run"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            older_than=7, keyword=None, force=False, dry_run=True
        )

    @patch("main.asyncio.run")
    @patch("main.handle_cache_warm")
    def test_cache_warm_command(self, mock_handler, mock_asyncio_run, runner):
        """Test cache warm command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic warm
        result = runner.invoke(cli, ["cache", "warm", "diabetes"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with("diabetes", variations=3, verbose=False)

        # Test with custom variations
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["cache", "warm", "heart health", "--variations", "5"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            "heart health", variations=5, verbose=False
        )

        # Test verbose mode
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["cache", "warm", "nutrition", "--verbose"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with("nutrition", variations=3, verbose=True)

    @patch("main.asyncio.run")
    @patch("main.handle_export_cache_metrics")
    def test_cache_metrics_command(self, mock_handler, mock_asyncio_run, runner):
        """Test cache metrics export command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test JSON export to stdout
        result = runner.invoke(cli, ["cache", "metrics"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(format="json", output_path=None)

        # Test CSV export to file
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["cache", "metrics", "--format", "csv", "--output", "/tmp/metrics.csv"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            format="csv", output_path=Path("/tmp/metrics.csv")
        )

        # Test Prometheus format
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["cache", "metrics", "--format", "prometheus"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(format="prometheus", output_path=None)


class TestDriveCommands:
    """Test Google Drive integration commands."""

    def test_drive_group_help(self, runner):
        """Test drive group help message."""
        result = runner.invoke(cli, ["drive", "--help"])
        assert result.exit_code == 0
        assert "Manage Google Drive integration" in result.output
        assert "auth" in result.output
        assert "upload" in result.output
        assert "list" in result.output
        assert "status" in result.output

    @patch("main.handle_drive_auth")
    def test_drive_auth_command(self, mock_handler, runner):
        """Test drive auth command."""
        # Test basic auth
        result = runner.invoke(cli, ["drive", "auth"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(reauth=False)

        # Test force reauth
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["drive", "auth", "--reauth"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(reauth=True)

    @patch("main.asyncio.run")
    @patch("main.handle_drive_upload")
    def test_drive_upload_command(self, mock_handler, mock_asyncio_run, runner):
        """Test drive upload command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test single file upload
        result = runner.invoke(cli, ["drive", "upload", "/path/to/article.html"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            paths=[Path("/path/to/article.html")], folder_name=None, batch_size=5
        )

        # Test multiple files with custom folder
        mock_handler.reset_mock()
        result = runner.invoke(
            cli,
            [
                "drive",
                "upload",
                "file1.html",
                "file2.html",
                "--folder",
                "My Articles",
                "--batch-size",
                "10",
            ],
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(
            paths=[Path("file1.html"), Path("file2.html")],
            folder_name="My Articles",
            batch_size=10,
        )

    @patch("main.asyncio.run")
    @patch("main.handle_drive_list")
    def test_drive_list_command(self, mock_handler, mock_asyncio_run, runner):
        """Test drive list command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic list
        result = runner.invoke(cli, ["drive", "list"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(limit=20, all_files=False)

        # Test list all with custom limit
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["drive", "list", "--limit", "50", "--all"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(limit=50, all_files=True)

    @patch("main.handle_drive_status")
    def test_drive_status_command(self, mock_handler, runner):
        """Test drive status command."""
        result = runner.invoke(cli, ["drive", "status"])
        assert result.exit_code == 0
        mock_handler.assert_called_once()

    @patch("main.handle_drive_logout")
    def test_drive_logout_command(self, mock_handler, runner):
        """Test drive logout command."""
        # Test without force
        result = runner.invoke(cli, ["drive", "logout"], input="y\n")
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(force=False)

        # Test with force
        mock_handler.reset_mock()
        result = runner.invoke(cli, ["drive", "logout", "--force"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(force=True)

    @patch("main.asyncio.run")
    @patch("main.handle_upload_pending")
    def test_drive_upload_pending_command(self, mock_handler, mock_asyncio_run, runner):
        """Test drive upload-pending command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic upload pending
        result = runner.invoke(cli, ["drive", "upload-pending"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(batch_size=5, dry_run=False)

        # Test with custom batch size and dry run
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["drive", "upload-pending", "--batch-size", "10", "--dry-run"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(batch_size=10, dry_run=True)

    @patch("main.asyncio.run")
    @patch("main.handle_retry_failed")
    def test_drive_retry_failed_command(self, mock_handler, mock_asyncio_run, runner):
        """Test drive retry-failed command."""
        mock_asyncio_run.side_effect = (
            lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        )

        # Test basic retry
        result = runner.invoke(cli, ["drive", "retry-failed"])
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(max_retries=3, clear=False)

        # Test with custom retries and clear
        mock_handler.reset_mock()
        result = runner.invoke(
            cli, ["drive", "retry-failed", "--max-retries", "5", "--clear"]
        )
        assert result.exit_code == 0
        mock_handler.assert_called_once_with(max_retries=5, clear=True)


class TestCleanupCommand:
    """Test cleanup command."""

    @patch("main.datetime")
    @patch("main.Path.iterdir")
    @patch("main.shutil.rmtree")
    @patch("main.console")
    def test_cleanup_dry_run(
        self, mock_console, mock_rmtree, mock_iterdir, mock_datetime, runner
    ):
        """Test cleanup command in dry run mode."""
        # Mock current time
        current_time = datetime(2024, 1, 20, 12, 0, 0)
        mock_datetime.now.return_value = current_time

        # Create mock directories with different ages
        old_dir1 = Mock()
        old_dir1.name = "test_20240101_120000"
        old_dir1.is_dir.return_value = True
        old_dir1.stat.return_value.st_mtime = (
            current_time - timedelta(days=20)
        ).timestamp()

        old_dir2 = Mock()
        old_dir2.name = "test_20240105_120000"
        old_dir2.is_dir.return_value = True
        old_dir2.stat.return_value.st_mtime = (
            current_time - timedelta(days=15)
        ).timestamp()

        new_dir = Mock()
        new_dir.name = "test_20240118_120000"
        new_dir.is_dir.return_value = True
        new_dir.stat.return_value.st_mtime = (
            current_time - timedelta(days=2)
        ).timestamp()

        mock_iterdir.return_value = [old_dir1, old_dir2, new_dir]

        with patch("main.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.output_dir = Path("/tmp/output")
            mock_get_config.return_value = mock_config

            # Run cleanup with dry-run
            result = runner.invoke(cli, ["cleanup", "--dry-run"])
            assert result.exit_code == 0

            # Should not delete anything in dry run
            mock_rmtree.assert_not_called()

            # Should show what would be cleaned
            console_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Would clean:" in str(call) for call in console_calls)
            assert any("test_20240101_120000" in str(call) for call in console_calls)
            assert any("test_20240105_120000" in str(call) for call in console_calls)
            assert not any(
                "test_20240118_120000" in str(call) for call in console_calls
            )

    @patch("main.datetime")
    @patch("main.Path.iterdir")
    @patch("main.shutil.rmtree")
    @patch("main.console")
    def test_cleanup_actual_deletion(
        self, mock_console, mock_rmtree, mock_iterdir, mock_datetime, runner
    ):
        """Test cleanup command with actual deletion."""
        # Mock current time
        current_time = datetime(2024, 1, 20, 12, 0, 0)
        mock_datetime.now.return_value = current_time

        # Create mock directories
        old_dir = Mock()
        old_dir.name = "test_20240110_120000"
        old_dir.is_dir.return_value = True
        old_dir.stat.return_value.st_mtime = (
            current_time - timedelta(days=10)
        ).timestamp()

        mock_iterdir.return_value = [old_dir]

        with patch("main.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.output_dir = Path("/tmp/output")
            mock_get_config.return_value = mock_config

            # Run cleanup without dry-run
            result = runner.invoke(cli, ["cleanup", "--older-than", "7"])
            assert result.exit_code == 0

            # Should delete old directory
            mock_rmtree.assert_called_once_with(old_dir)

            # Should show success message
            console_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Cleaned 1 workflow" in str(call) for call in console_calls)

    @patch("main.Path.iterdir")
    @patch("main.console")
    def test_cleanup_no_old_workflows(self, mock_console, mock_iterdir, runner):
        """Test cleanup when no old workflows exist."""
        # Mock no directories
        mock_iterdir.return_value = []

        with patch("main.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.output_dir = Path("/tmp/output")
            mock_get_config.return_value = mock_config

            result = runner.invoke(cli, ["cleanup"])
            assert result.exit_code == 0

            # Should show no workflows found message
            console_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any(
                "No workflow directories older than" in str(call)
                for call in console_calls
            )

    @patch("main.Path.iterdir")
    @patch("main.shutil.rmtree")
    def test_cleanup_error_handling(self, mock_rmtree, mock_iterdir, runner):
        """Test cleanup error handling."""
        # Create mock directory that fails to delete
        old_dir = Mock()
        old_dir.name = "test_20240101_120000"
        old_dir.is_dir.return_value = True
        old_dir.stat.return_value.st_mtime = 0  # Very old

        mock_iterdir.return_value = [old_dir]
        mock_rmtree.side_effect = PermissionError("Access denied")

        with patch("main.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.output_dir = Path("/tmp/output")
            mock_get_config.return_value = mock_config

            result = runner.invoke(cli, ["cleanup"])
            # Should handle error gracefully
            assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test error handling across CLI commands."""

    def test_missing_command(self, runner):
        """Test handling of missing command."""
        result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code != 0
        assert "Error" in result.output or "Usage" in result.output

    def test_missing_required_argument(self, runner):
        """Test handling of missing required arguments."""
        # Cache search requires QUERY
        result = runner.invoke(cli, ["cache", "search"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

        # Generate requires KEYWORD
        result = runner.invoke(cli, ["generate"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_invalid_option_values(self, runner):
        """Test handling of invalid option values."""
        # Invalid limit for cache search
        result = runner.invoke(cli, ["cache", "search", "test", "--limit", "invalid"])
        assert result.exit_code != 0

        # Invalid threshold
        result = runner.invoke(cli, ["cache", "search", "test", "--threshold", "2.0"])
        assert result.exit_code != 0  # Threshold should be between 0 and 1

    @patch("main.get_config")
    def test_configuration_error_handling(self, mock_get_config, runner):
        """Test handling of configuration errors."""
        mock_get_config.side_effect = Exception("Missing API key")

        # Any command should fail with config error
        result = runner.invoke(cli, ["test"])
        assert result.exit_code != 0
        assert "Configuration error" in result.output


class TestCLIHelp:
    """Test help messages for all commands."""

    def test_main_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SEO Content Automation System" in result.output
        assert "generate" in result.output
        assert "config" in result.output
        assert "test" in result.output
        assert "cleanup" in result.output
        assert "cache" in result.output
        assert "drive" in result.output

    def test_command_help_messages(self, runner):
        """Test individual command help messages."""
        commands = [
            (["generate", "--help"], "Generate an SEO-optimized article"),
            (["config", "--help"], "Manage system configuration"),
            (["test", "--help"], "Run a test generation"),
            (["cleanup", "--help"], "Clean up old workflow"),
            (["cache", "--help"], "Manage the research cache"),
            (["drive", "--help"], "Manage Google Drive integration"),
        ]

        for cmd, expected_text in commands:
            result = runner.invoke(cli, cmd)
            assert result.exit_code == 0
            assert expected_text in result.output

    def test_subcommand_help_messages(self, runner):
        """Test subcommand help messages."""
        subcommands = [
            (["cache", "search", "--help"], "Search for cached content"),
            (["cache", "stats", "--help"], "Display cache statistics"),
            (["cache", "clear", "--help"], "Clear cache entries"),
            (["cache", "warm", "--help"], "Pre-warm the cache"),
            (["drive", "auth", "--help"], "Authenticate with Google Drive"),
            (["drive", "upload", "--help"], "Upload articles to Google Drive"),
        ]

        for cmd, expected_text in subcommands:
            result = runner.invoke(cli, cmd)
            assert result.exit_code == 0
            assert expected_text in result.output


# Integration test for command combinations
class TestCLIIntegration:
    """Test realistic command sequences."""

    @patch("main.asyncio.run")
    @patch("main.WorkflowOrchestrator")
    @patch("main.get_config")
    def test_generate_then_cache_stats(
        self, mock_get_config, mock_orchestrator, mock_asyncio_run, runner
    ):
        """Test generating content then checking cache stats."""
        # Setup mocks
        mock_config = Mock()
        mock_config.output_dir = Path("/tmp/output")
        mock_get_config.return_value = mock_config

        mock_workflow = Mock()
        mock_workflow.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/article.html")
        )
        mock_orchestrator.return_value = mock_workflow

        # First generate an article
        result = runner.invoke(cli, ["generate", "test keyword"])
        assert result.exit_code == 0

        # Then check cache stats
        with patch("main.handle_cache_stats") as mock_stats:
            result = runner.invoke(cli, ["cache", "stats"])
            assert result.exit_code == 0


# What questions do you have about these extended CLI tests, Finn?
# Would you like me to explain any specific testing pattern in more detail?
# Try this exercise: Add a test for concurrent command execution!
