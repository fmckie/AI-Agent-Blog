"""
Comprehensive tests for CLI functionality.

This test file covers the command-line interface in main.py,
including all commands, options, and error handling.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Import testing utilities
import pytest
from click.testing import CliRunner

from config import Config

# Import CLI components to test
from main import _run_generation, cli, config, generate, test
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings


# Module-level fixtures
@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)
    config.output_dir = Path("/tmp/output")
    config.log_level = "INFO"
    config.llm_model = "gpt-4"
    config.max_retries = 3
    config.request_timeout = 30
    config.tavily_search_depth = "basic"
    config.tavily_include_domains = [".edu", ".gov"]
    config.tavily_max_results = 10
    config.openai_api_key = "sk-openai1234567890abcdef1234567890"
    config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
    return config


@pytest.fixture
def mock_successful_workflow(mock_config):
    """Mock successful workflow execution."""
    # Mock research findings
    mock_findings = ResearchFindings(
        keyword="test keyword",
        research_summary="This is a comprehensive test research summary that provides detailed findings about the research topic with sufficient length to meet validation requirements.",
        academic_sources=[
            AcademicSource(
                title="Test Source",
                url="https://test.edu",
                excerpt="Test excerpt",
                domain=".edu",
                credibility_score=0.8,
            )
        ],
        main_findings=["Finding 1", "Finding 2", "Finding 3"],
        total_sources_analyzed=5,
        search_query_used="test keyword research",
    )

    # Mock workflow orchestrator
    mock_orchestrator = Mock()
    mock_orchestrator.run_research = AsyncMock(return_value=mock_findings)
    mock_orchestrator.run_full_workflow = AsyncMock(
        return_value=Path("/tmp/output/test_keyword_20240101_120000/index.html")
    )

    return mock_orchestrator


class TestCLICommands:
    """Test cases for CLI commands."""

    def test_cli_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self, runner):
        """Test help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SEO Content Automation System" in result.output
        assert "generate" in result.output
        assert "config" in result.output
        assert "test" in result.output

    def test_cli_invalid_config(self, runner):
        """Test CLI with invalid configuration."""
        with patch("main.get_config", side_effect=Exception("Invalid API key")):
            result = runner.invoke(cli, ["generate", "test"])
            assert result.exit_code == 1
            assert "Configuration error" in result.output


class TestGenerateCommand:
    """Test cases for the generate command."""

    def test_generate_basic(self, runner, mock_config, mock_successful_workflow):
        """Test basic article generation."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_successful_workflow
            ):
                result = runner.invoke(cli, ["generate", "machine learning"])

                assert result.exit_code == 0
                assert "Researching 'machine learning'" in result.output
                assert "Article generated successfully" in result.output
                assert "index.html" in result.output

    def test_generate_with_output_dir(
        self, runner, mock_config, mock_successful_workflow
    ):
        """Test generation with custom output directory."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_successful_workflow
            ):
                result = runner.invoke(
                    cli, ["generate", "AI research", "--output-dir", "/custom/output"]
                )

                assert result.exit_code == 0
                # Verify config was updated
                assert mock_config.output_dir == Path("/custom/output")

    def test_generate_verbose(self, runner, mock_config, mock_successful_workflow):
        """Test generation with verbose output."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_successful_workflow
            ):
                with patch("logging.getLogger") as mock_logger:
                    result = runner.invoke(cli, ["generate", "test", "--verbose"])

                    assert result.exit_code == 0
                    # Verify debug logging was enabled
                    mock_logger().setLevel.assert_called_with(10)  # logging.DEBUG = 10

    def test_generate_dry_run(self, runner, mock_config, mock_successful_workflow):
        """Test dry run mode (research only)."""
        with patch("main.get_config", return_value=mock_config):
            with patch(
                "main.WorkflowOrchestrator", return_value=mock_successful_workflow
            ):
                result = runner.invoke(cli, ["generate", "blockchain", "--dry-run"])

                assert result.exit_code == 0
                assert "dry-run mode" in result.output
                assert "Research completed" in result.output
                # Should not generate article
                mock_successful_workflow.run_full_workflow.assert_not_called()
                mock_successful_workflow.run_research.assert_called_once()

    def test_generate_keyboard_interrupt(self, runner, mock_config):
        """Test handling of keyboard interrupt."""
        with patch("main.get_config", return_value=mock_config):
            with patch("main.asyncio.run", side_effect=KeyboardInterrupt()):
                result = runner.invoke(cli, ["generate", "test"])

                assert result.exit_code == 1
                assert "cancelled by user" in result.output

    def test_generate_exception(self, runner, mock_config):
        """Test handling of generation exceptions."""
        with patch("main.get_config", return_value=mock_config):
            with patch("main.asyncio.run", side_effect=Exception("API error")):
                result = runner.invoke(cli, ["generate", "test"])

                assert result.exit_code == 1
                assert "Error: API error" in result.output

    def test_generate_help(self, runner):
        """Test generate command help."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate an SEO-optimized article" in result.output
        assert "--output-dir" in result.output
        assert "--verbose" in result.output
        assert "--dry-run" in result.output


class TestConfigCommand:
    """Test cases for the config command."""

    def test_config_check(self, runner, mock_config):
        """Test configuration validation."""
        with patch("main.get_config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "--check"])

            assert result.exit_code == 0
            assert "Configuration is valid" in result.output
            assert "Tavily API key:" in result.output
            assert "****" in result.output  # Hidden API key

    def test_config_show(self, runner, mock_config):
        """Test configuration display."""
        with patch("main.get_config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "--show"])

            assert result.exit_code == 0
            assert "Current Configuration" in result.output
            assert "LLM Model: gpt-4" in result.output
            assert "Output Directory:" in result.output
            assert "Log Level: INFO" in result.output
            assert "Max Retries: 3" in result.output

    def test_config_check_and_show(self, runner, mock_config):
        """Test both check and show options together."""
        with patch("main.get_config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "--check", "--show"])

            assert result.exit_code == 0
            assert "Configuration is valid" in result.output
            assert "Current Configuration" in result.output

    def test_config_invalid(self, runner):
        """Test config command with invalid configuration."""
        with patch("main.get_config", side_effect=Exception("Missing API key")):
            result = runner.invoke(cli, ["config", "--check"])

            assert result.exit_code == 1
            assert "Configuration error" in result.output
            assert "Missing API key" in result.output

    def test_config_help(self, runner):
        """Test config command help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage system configuration" in result.output
        assert "--check" in result.output
        assert "--show" in result.output


class TestTestCommand:
    """Test cases for the test command."""

    def test_test_command(self, runner, mock_config):
        """Test the test command."""
        mock_findings = ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive AI research summary revealing significant advancements in artificial intelligence applications across multiple domains and industries worldwide.",
            academic_sources=[
                AcademicSource(
                    title="AI Paper",
                    url="https://test.edu/ai",
                    excerpt="AI research",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["AI finding 1", "AI finding 2", "AI finding 3"],
            total_sources_analyzed=5,
            search_query_used="artificial intelligence",
        )

        mock_orchestrator = Mock()
        mock_orchestrator.run_research = AsyncMock(return_value=mock_findings)

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                result = runner.invoke(cli, ["test"])

                assert result.exit_code == 0
                assert "Running test generation" in result.output
                assert "artificial intelligence" in result.output
                assert "Research completed" in result.output

    def test_test_command_help(self, runner):
        """Test test command help."""
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        assert "Run a test generation" in result.output
        assert "verify your setup" in result.output


class TestRunGeneration:
    """Test cases for the internal _run_generation function."""

    @pytest.mark.asyncio
    async def test_run_generation_full_workflow(self, mock_config):
        """Test full workflow execution."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/output/test/index.html")
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                with patch("main.console") as mock_console:
                    await _run_generation("test keyword", None, False)

                    # Verify workflow was called
                    mock_orchestrator.run_full_workflow.assert_called_once_with(
                        "test keyword"
                    )

                    # Verify success messages
                    assert any(
                        "generated successfully" in str(call)
                        for call in mock_console.print.call_args_list
                    )

    @pytest.mark.asyncio
    async def test_run_generation_dry_run(self, mock_config):
        """Test dry run mode."""
        mock_findings = ResearchFindings(
            keyword="test",
            research_summary="This is a detailed test summary that contains comprehensive information about the research findings and meets all validation requirements for the system.",
            academic_sources=[
                AcademicSource(
                    title="Test",
                    url="https://test.edu",
                    excerpt="Test",
                    domain=".edu",
                    credibility_score=0.8,
                )
            ],
            main_findings=["1", "2", "3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        mock_orchestrator = Mock()
        mock_orchestrator.run_research = AsyncMock(return_value=mock_findings)

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                with patch("main.console") as mock_console:
                    await _run_generation("test", None, True)

                    # Should only call research
                    mock_orchestrator.run_research.assert_called_once_with("test")

                    # Should display research results
                    assert any(
                        "Research completed" in str(call)
                        for call in mock_console.print.call_args_list
                    )

    @pytest.mark.asyncio
    async def test_run_generation_custom_output_dir(self, mock_config):
        """Test with custom output directory."""
        custom_path = Path("/custom/output")

        mock_orchestrator = Mock()
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=custom_path / "test/index.html"
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                await _run_generation("test", custom_path, False)

                # Verify config was updated
                assert mock_config.output_dir == custom_path


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_complete_workflow_simulation(self, runner, mock_config):
        """Test complete workflow from CLI to output."""
        # Create comprehensive mocks
        mock_findings = ResearchFindings(
            keyword="quantum computing",
            research_summary="Quantum computing represents the next frontier in computational technology, offering exponential speedups for specific problems and revolutionizing fields from cryptography to drug discovery.",
            academic_sources=[
                AcademicSource(
                    title="Quantum Algorithms",
                    url="https://university.edu/quantum",
                    excerpt="Novel quantum algorithms for optimization",
                    domain=".edu",
                    credibility_score=0.95,
                )
            ],
            main_findings=[
                "Quantum supremacy achieved",
                "Error correction improving",
                "Commercial applications emerging",
            ],
            total_sources_analyzed=10,
            search_query_used="quantum computing research",
        )

        mock_orchestrator = Mock()
        mock_orchestrator.run_research = AsyncMock(return_value=mock_findings)
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/quantum_computing_20240101/index.html")
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                # Test normal execution
                result = runner.invoke(cli, ["generate", "quantum computing"])
                assert result.exit_code == 0

                # Test with options
                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "quantum computing",
                        "--verbose",
                        "--output-dir",
                        "/tmp/custom",
                    ],
                )
                assert result.exit_code == 0

    def test_multiple_commands_sequence(self, runner, mock_config):
        """Test running multiple commands in sequence."""
        with patch("main.get_config", return_value=mock_config):
            # Check config
            result = runner.invoke(cli, ["config", "--check"])
            assert result.exit_code == 0

            # Show config
            result = runner.invoke(cli, ["config", "--show"])
            assert result.exit_code == 0

            # Run test
            mock_orchestrator = Mock()
            mock_orchestrator.run_research = AsyncMock(
                return_value=Mock(to_markdown_summary=lambda: "# Test Results")
            )

            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                result = runner.invoke(cli, ["test"])
                assert result.exit_code == 0


# Edge case tests
class TestCLIEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_empty_keyword(self, runner, mock_config):
        """Test generation with empty keyword."""
        with patch("main.get_config", return_value=mock_config):
            result = runner.invoke(cli, ["generate", ""])
            # Click should handle empty argument
            assert result.exit_code != 0

    def test_special_characters_keyword(self, runner, mock_config):
        """Test generation with special characters in keyword."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/output/index.html")
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                result = runner.invoke(cli, ["generate", "C++ & Python!"])
                assert result.exit_code == 0

                # Verify keyword was passed correctly
                mock_orchestrator.run_full_workflow.assert_called_with("C++ & Python!")

    def test_invalid_output_directory(self, runner, mock_config):
        """Test with invalid output directory path."""
        with patch("main.get_config", return_value=mock_config):
            # Invalid path characters
            result = runner.invoke(
                cli, ["generate", "test", "--output-dir", "\0invalid\0path"]
            )
            # Should handle gracefully
            assert result.exit_code != 0

    def test_unicode_keyword(self, runner, mock_config):
        """Test generation with Unicode keyword."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/output/index.html")
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                result = runner.invoke(cli, ["generate", "café culture"])
                assert result.exit_code == 0

    def test_very_long_keyword(self, runner, mock_config):
        """Test with extremely long keyword."""
        long_keyword = "artificial intelligence " * 50  # Very long

        mock_orchestrator = Mock()
        mock_orchestrator.run_full_workflow = AsyncMock(
            return_value=Path("/tmp/output/index.html")
        )

        with patch("main.get_config", return_value=mock_config):
            with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
                result = runner.invoke(cli, ["generate", long_keyword])
                # Should handle long keywords
                assert result.exit_code == 0
