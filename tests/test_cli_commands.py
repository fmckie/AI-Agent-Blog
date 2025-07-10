"""
Comprehensive test suite for CLI commands in main.py.

This module tests all CLI commands including generate, config, test,
cleanup, batch, and cache management commands.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import click
import pytest
from click.testing import CliRunner

from main import (
    cli,
    generate,
    config,
    test,
    cleanup,
    batch,
    cache,
    cache_search,
    cache_stats,
    cache_clear,
    cache_warm,
    cache_metrics,
    drive,
    _run_generation,
    _run_batch_generation,
)
from cli.cache_handlers import (
    handle_cache_clear as _cache_clear,
    handle_cache_search as _cache_search,
    handle_cache_stats as _cache_stats,
    handle_cache_warm as _cache_warm,
    handle_export_cache_metrics as _export_cache_metrics,
)


class TestCLICommands:
    """Test suite for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.output_dir = Path("/tmp/test_output")
        config.log_level = "INFO"
        config.llm_model = "gpt-4"
        config.tavily_search_depth = "advanced"
        config.tavily_include_domains = [".edu", ".gov", ".org"]
        config.tavily_max_results = 10
        config.max_retries = 3
        config.request_timeout = 30
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        findings = Mock()
        findings.keyword = "test keyword"
        findings.total_sources_analyzed = 5
        findings.to_markdown_summary.return_value = (
            "# Research Summary\nTest findings..."
        )
        return findings

    @pytest.fixture
    def mock_workflow_orchestrator(self):
        """Create mock workflow orchestrator."""
        orchestrator = Mock()
        orchestrator.run_research = AsyncMock()
        orchestrator.run_full_workflow = AsyncMock()
        orchestrator.set_progress_callback = Mock()
        return orchestrator

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SEO Content Automation System" in result.output
        assert "generate" in result.output
        assert "config" in result.output
        assert "test" in result.output

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version 0.1.0" in result.output

    @patch("main.get_config")
    def test_cli_config_error(self, mock_get_config, runner):
        """Test CLI with configuration error."""
        mock_get_config.side_effect = Exception("Config error")
        result = runner.invoke(cli, ["generate", "test"])
        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_generate_command_basic(
        self, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test basic generate command."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(generate, ["test keyword"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_generate_command_with_options(
        self, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test generate command with options."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(
            generate,
            [
                "test keyword",
                "--output-dir",
                "/custom/output",
                "--verbose",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_generate_command_quiet_mode(
        self, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test generate command in quiet mode."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(generate, ["test keyword", "--quiet"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.get_config")
    def test_generate_command_keyboard_interrupt(
        self, mock_get_config, runner, mock_config
    ):
        """Test generate command with keyboard interrupt."""
        mock_get_config.return_value = mock_config

        with patch("main.asyncio.run", side_effect=KeyboardInterrupt):
            result = runner.invoke(generate, ["test keyword"])
            assert result.exit_code == 1

    @patch("main.get_config")
    def test_config_check(self, mock_get_config, runner, mock_config):
        """Test config check command."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(config, ["--check"])
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output

    @patch("main.get_config")
    def test_config_show(self, mock_get_config, runner, mock_config):
        """Test config show command."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(config, ["--show"])
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "LLM Model: gpt-4" in result.output

    @patch("main.get_config")
    def test_config_error(self, mock_get_config, runner):
        """Test config command with error."""
        mock_get_config.side_effect = Exception("Invalid config")

        result = runner.invoke(config, ["--check"])
        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_generate_verbose_quiet_conflict(
        self, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test handling of conflicting verbose and quiet flags."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(generate, ["test keyword", "--verbose", "--quiet"])
        assert result.exit_code == 2  # Click should error on conflicting flags
        assert "Error" in result.output

    @patch("main.get_config")
    @patch("main.generate")
    def test_test_command(self, mock_generate, mock_get_config, runner, mock_config):
        """Test the test command."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(test)
        assert result.exit_code == 0
        assert "Running test generation" in result.output

    @patch("main.get_config")
    @patch("main.asyncio.run")
    @patch("pathlib.Path.glob")
    def test_cleanup_command(
        self, mock_glob, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test cleanup command."""
        mock_get_config.return_value = mock_config
        mock_glob.side_effect = [
            [Path(".workflow_state_test.json")],  # state files
            [Path(".temp_test")],  # temp dirs
        ]

        mock_async_run.return_value = (1, 1)  # cleaned counts

        result = runner.invoke(cleanup)
        assert result.exit_code == 0
        assert "Cleanup complete" in result.output

    @patch("main.get_config")
    @patch("pathlib.Path.glob")
    def test_cleanup_command_dry_run(
        self, mock_glob, mock_get_config, runner, mock_config
    ):
        """Test cleanup command in dry run mode."""
        mock_get_config.return_value = mock_config

        # Create mock files
        mock_state_file = Mock()
        mock_state_file.stat.return_value.st_mtime = (
            datetime.now() - timedelta(hours=48)
        ).timestamp()
        mock_state_file.name = "old_state.json"

        mock_glob.side_effect = [[mock_state_file], []]  # state files  # temp dirs

        result = runner.invoke(cleanup, ["--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_batch_command(self, mock_async_run, mock_get_config, runner, mock_config):
        """Test batch command."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(batch, ["keyword1", "keyword2", "keyword3"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.get_config")
    @patch("main.asyncio.run")
    def test_batch_command_with_options(
        self, mock_async_run, mock_get_config, runner, mock_config
    ):
        """Test batch command with options."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(
            batch,
            [
                "keyword1",
                "keyword2",
                "--parallel",
                "2",
                "--dry-run",
                "--continue-on-error",
            ],
        )
        assert result.exit_code == 0
        assert "Parallel execution: 2" in result.output

    def test_batch_command_no_keywords(self, runner):
        """Test batch command without keywords."""
        result = runner.invoke(batch, [])
        assert result.exit_code == 2  # Click exits with 2 for missing required args
        assert "Error" in result.output  # Click shows error for missing args

    @patch("main.get_config")
    def test_batch_command_invalid_parallel(self, mock_get_config, runner, mock_config):
        """Test batch command with invalid parallel count."""
        mock_get_config.return_value = mock_config

        result = runner.invoke(batch, ["keyword1", "--parallel", "0"])
        assert result.exit_code == 1
        assert "Parallel count must be at least 1" in result.output

    def test_cache_help(self, runner):
        """Test cache command help."""
        result = runner.invoke(cli, ["cache", "--help"])
        assert result.exit_code == 0
        assert "Manage the research cache system" in result.output

    @patch("main.asyncio.run")
    def test_cache_search_command(self, mock_async_run, runner):
        """Test cache search command."""
        result = runner.invoke(cache_search, ["test query"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.asyncio.run")
    def test_cache_stats_command(self, mock_async_run, runner):
        """Test cache stats command."""
        result = runner.invoke(cache_stats)
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.asyncio.run")
    def test_cache_stats_detailed(self, mock_async_run, runner):
        """Test cache stats command with detailed flag."""
        result = runner.invoke(cache_stats, ["--detailed"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.asyncio.run")
    def test_cache_clear_command(self, mock_async_run, runner):
        """Test cache clear command."""
        result = runner.invoke(cache_clear, ["--force"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.asyncio.run")
    def test_cache_warm_command(self, mock_async_run, runner):
        """Test cache warm command."""
        result = runner.invoke(cache_warm, ["test topic"])
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @patch("main.asyncio.run")
    def test_cache_metrics_command(self, mock_async_run, runner):
        """Test cache metrics command."""
        result = runner.invoke(cache_metrics)
        assert result.exit_code == 0
        mock_async_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_generation_basic(
        self, mock_config, mock_workflow_orchestrator, mock_research_findings
    ):
        """Test _run_generation function."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_workflow_orchestrator
            ):
                mock_workflow_orchestrator.run_full_workflow.return_value = Path(
                    "/output/article.html"
                )

                await _run_generation("test keyword", None, False, False)

                mock_workflow_orchestrator.run_full_workflow.assert_called_once_with(
                    "test keyword"
                )

    @pytest.mark.asyncio
    async def test_run_generation_dry_run(
        self, mock_config, mock_workflow_orchestrator, mock_research_findings
    ):
        """Test _run_generation in dry run mode."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_workflow_orchestrator
            ):
                mock_workflow_orchestrator.run_research.return_value = (
                    mock_research_findings
                )

                await _run_generation("test keyword", None, True, False)

                mock_workflow_orchestrator.run_research.assert_called_once_with(
                    "test keyword"
                )
                mock_workflow_orchestrator.run_full_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_batch_generation(self, mock_config):
        """Test _run_batch_generation function."""
        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator") as mock_orchestrator_class:
                mock_orchestrator = Mock()
                mock_orchestrator.run_full_workflow = AsyncMock(
                    return_value=Path("/output/article.html")
                )
                mock_orchestrator_class.return_value = mock_orchestrator

                keywords = ("keyword1", "keyword2")
                await _run_batch_generation(keywords, None, 1, False, False, False)

                assert mock_orchestrator.run_full_workflow.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_search_function(self):
        """Test _cache_search function."""
        with patch("main.get_rag_config") as mock_get_config:
            with patch("main.VectorStorage") as mock_storage_class:
                with patch(
                    "rag.embeddings.EmbeddingGenerator"
                ) as mock_embeddings_class:
                    mock_storage = AsyncMock()
                    mock_storage.search_similar = AsyncMock(
                        return_value=[
                            {
                                "similarity": 0.95,
                                "keyword": "test",
                                "content": "Test content",
                                "created_at": "2024-01-01",
                                "metadata": {},
                            }
                        ]
                    )
                    mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                    mock_storage.__aexit__ = AsyncMock()
                    mock_storage_class.return_value = mock_storage

                    mock_embeddings = Mock()
                    mock_embeddings.generate_embedding = AsyncMock(
                        return_value=[0.1] * 1536
                    )
                    mock_embeddings_class.return_value = mock_embeddings

                    await _cache_search("test query", 10, 0.7)

    @pytest.mark.asyncio
    async def test_cache_stats_function(self):
        """Test _cache_stats function."""
        with patch("main.get_rag_config"):
            with patch("main.VectorStorage") as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_cache_stats = AsyncMock(
                    return_value={
                        "total_entries": 100,
                        "unique_keywords": 50,
                        "storage_bytes": 1024000,
                        "avg_chunk_size": 500,
                        "oldest_entry": "2024-01-01",
                        "newest_entry": "2024-01-10",
                    }
                )
                mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                mock_storage.__aexit__ = AsyncMock()
                mock_storage_class.return_value = mock_storage

                # Mock ResearchRetriever.get_statistics as a class method
                with patch("main.ResearchRetriever") as mock_retriever:
                    mock_retriever.get_statistics = Mock(
                        return_value={
                            "cache_requests": 100,
                            "cache_hits": 80,
                            "exact_hits": 60,
                            "semantic_hits": 20,
                            "cache_misses": 20,
                            "hit_rate": 0.8,
                            "avg_retrieval_time": 0.05,
                        }
                    )

                    await _cache_stats(False)

    @pytest.mark.asyncio
    async def test_cache_clear_function(self):
        """Test _cache_clear function."""
        with patch("main.get_rag_config"):
            with patch("main.VectorStorage") as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.cleanup_cache = AsyncMock(return_value=10)
                mock_storage.get_cache_stats = AsyncMock(
                    return_value={"total_entries": 100}
                )
                mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                mock_storage.__aexit__ = AsyncMock()
                mock_storage_class.return_value = mock_storage

                await _cache_clear(7, None, True, False)

    @pytest.mark.asyncio
    async def test_cache_warm_function(self, mock_config):
        """Test _cache_warm function."""
        with patch("main.get_config", return_value=mock_config):
            with patch("research_agent.create_research_agent") as mock_create_agent:
                with patch("research_agent.run_research_agent") as mock_run_agent:
                    mock_agent = Mock()
                    mock_create_agent.return_value = mock_agent
                    mock_run_agent.return_value = Mock()

                    await _cache_warm("test topic", 3, True)

                    assert mock_run_agent.call_count >= 3

    @pytest.mark.asyncio
    async def test_export_cache_metrics_json(self):
        """Test _export_cache_metrics with JSON format."""
        with patch("main.get_rag_config"):
            with patch("main.VectorStorage") as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_cache_stats = AsyncMock(
                    return_value={
                        "total_entries": 100,
                        "unique_keywords": 50,
                        "storage_bytes": 1024000,
                    }
                )
                mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                mock_storage.__aexit__ = AsyncMock()
                mock_storage_class.return_value = mock_storage

                with patch("main.ResearchRetriever") as mock_retriever:
                    mock_retriever.get_statistics = Mock(
                        return_value={
                            "cache_requests": 100,
                            "cache_hits": 80,
                            "hit_rate": 0.8,
                        }
                    )

                    await _export_cache_metrics("json", None)

    @pytest.mark.asyncio
    async def test_export_cache_metrics_csv(self, tmp_path):
        """Test _export_cache_metrics with CSV format."""
        with patch("main.get_rag_config"):
            with patch("main.VectorStorage") as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_cache_stats = AsyncMock(
                    return_value={"total_entries": 100, "unique_keywords": 50}
                )
                mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                mock_storage.__aexit__ = AsyncMock()
                mock_storage_class.return_value = mock_storage

                with patch("main.ResearchRetriever") as mock_retriever:
                    mock_retriever.get_statistics = Mock(return_value=None)

                    output_file = tmp_path / "metrics.csv"
                    await _export_cache_metrics("csv", output_file)

                    assert output_file.exists()

    @pytest.mark.asyncio
    async def test_export_cache_metrics_prometheus(self):
        """Test _export_cache_metrics with Prometheus format."""
        with patch("main.get_rag_config"):
            with patch("main.VectorStorage") as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_cache_stats = AsyncMock(
                    return_value={"total_entries": 100, "storage_bytes": 1024000}
                )
                mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                mock_storage.__aexit__ = AsyncMock()
                mock_storage_class.return_value = mock_storage

                with patch("main.ResearchRetriever") as mock_retriever:
                    mock_retriever.get_statistics = Mock(
                        return_value={
                            "cache_requests": 100,  # Changed from total_requests
                            "exact_hits": 60,
                            "semantic_hits": 20,
                            "hit_rate": 0.8,
                            "avg_retrieval_time": 0.05,  # Changed from avg_response_time_seconds
                        }
                    )

                    await _export_cache_metrics("prometheus", None)
