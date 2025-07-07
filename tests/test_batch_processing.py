"""
Tests for batch processing functionality.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from main import cli, _run_batch_generation
from models import ResearchFindings, AcademicSource


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock()
    config.output_dir = Path("./test_output")
    return config


@pytest.fixture
def mock_orchestrator():
    """Create mock workflow orchestrator."""
    orchestrator = MagicMock()

    # Mock research findings with proper validation
    findings = ResearchFindings(
        keyword="test keyword",  # Added required field
        search_query_used="test keyword",
        total_sources_analyzed=5,
        academic_sources=[
            AcademicSource(
                title="Test Article",
                url="https://example.com",
                excerpt="Test content",
                domain="example.com",
                credibility_score=0.9,
            )
        ],
        research_summary="This is a comprehensive test summary with sufficient length to pass validation.",  # Longer summary
        key_insights=["Insight 1", "Insight 2"],
    )

    orchestrator.run_research = AsyncMock(return_value=findings)
    orchestrator.run_full_workflow = AsyncMock(
        return_value=Path("./drafts/test_keyword_20250106_120000/index.html")
    )

    return orchestrator


def test_batch_command_no_keywords():
    """Test batch command with no keywords."""
    runner = CliRunner()
    result = runner.invoke(cli, ["batch"])

    assert result.exit_code == 2  # Click error for missing arguments
    assert "Missing argument" in result.output


def test_batch_command_help():
    """Test batch command help text."""
    runner = CliRunner()
    result = runner.invoke(cli, ["batch", "--help"])

    assert result.exit_code == 0
    assert "Generate articles for multiple keywords in batch" in result.output
    assert "--parallel" in result.output
    assert "--continue-on-error" in result.output


@pytest.mark.asyncio
async def test_batch_generation_sequential(mock_config, mock_orchestrator):
    """Test sequential batch processing."""
    keywords = ("keyword1", "keyword2", "keyword3")

    with patch("main.get_config", return_value=mock_config):
        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            # Run batch generation
            await _run_batch_generation(
                keywords=keywords,
                output_dir=None,
                parallel=1,
                dry_run=False,
                continue_on_error=False,
                show_progress=False,
            )

    # Verify all keywords were processed
    assert mock_orchestrator.run_full_workflow.call_count == 3

    # Verify they were called with correct keywords
    calls = mock_orchestrator.run_full_workflow.call_args_list
    called_keywords = [call[0][0] for call in calls]
    assert set(called_keywords) == set(keywords)


@pytest.mark.asyncio
async def test_batch_generation_parallel(mock_config, mock_orchestrator):
    """Test parallel batch processing."""
    keywords = ("keyword1", "keyword2", "keyword3", "keyword4")

    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    async def track_concurrent(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent
        async with lock:
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)

        # Simulate some work
        await asyncio.sleep(0.1)

        async with lock:
            concurrent_count -= 1

        return Path("./drafts/test/index.html")

    mock_orchestrator.run_full_workflow = track_concurrent

    with patch("main.get_config", return_value=mock_config):
        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            # Run with parallel=2
            await _run_batch_generation(
                keywords=keywords,
                output_dir=None,
                parallel=2,
                dry_run=False,
                continue_on_error=False,
                show_progress=False,
            )

    # Should have run with max 2 concurrent
    assert max_concurrent == 2


@pytest.mark.asyncio
async def test_batch_generation_dry_run(mock_config, mock_orchestrator):
    """Test batch processing in dry-run mode."""
    keywords = ("keyword1", "keyword2")

    with patch("main.get_config", return_value=mock_config):
        with patch("main.WorkflowOrchestrator", return_value=mock_orchestrator):
            await _run_batch_generation(
                keywords=keywords,
                output_dir=None,
                parallel=1,
                dry_run=True,
                continue_on_error=False,
                show_progress=False,
            )

    # Should only run research, not full workflow
    assert mock_orchestrator.run_research.call_count == 2
    assert mock_orchestrator.run_full_workflow.call_count == 0


@pytest.mark.asyncio
async def test_batch_generation_continue_on_error(mock_config):
    """Test batch processing continues on error when specified."""
    keywords = ("good1", "bad", "good2")

    # Create orchestrator that fails on "bad" keyword
    orchestrator = MagicMock()

    async def mock_workflow(keyword):
        if keyword == "bad":
            raise Exception("Test error")
        return Path(f"./drafts/{keyword}/index.html")

    orchestrator.run_full_workflow = mock_workflow

    with patch("main.get_config", return_value=mock_config):
        with patch("main.WorkflowOrchestrator", return_value=orchestrator):
            # Should complete without raising
            await _run_batch_generation(
                keywords=keywords,
                output_dir=None,
                parallel=1,
                dry_run=False,
                continue_on_error=True,
                show_progress=False,
            )


@pytest.mark.asyncio
async def test_batch_generation_fail_fast(mock_config):
    """Test batch processing stops on error by default."""
    keywords = ("good1", "bad", "good2")

    # Create orchestrator that fails on "bad" keyword
    orchestrator = MagicMock()
    call_count = 0

    async def mock_workflow(keyword):
        nonlocal call_count
        call_count += 1
        if keyword == "bad":
            raise Exception("Test error")
        return Path(f"./drafts/{keyword}/index.html")

    orchestrator.run_full_workflow = mock_workflow

    with patch("main.get_config", return_value=mock_config):
        with patch("main.WorkflowOrchestrator", return_value=orchestrator):
            # Should raise on error - Click Exit exception
            with pytest.raises(click.exceptions.Exit) as exc_info:
                await _run_batch_generation(
                    keywords=keywords,
                    output_dir=None,
                    parallel=1,
                    dry_run=False,
                    continue_on_error=False,
                    show_progress=False,
                )

            # Verify it's a click Exit with code 1
            assert exc_info.value.exit_code == 1


def test_batch_command_integration():
    """Test batch command through CLI."""
    runner = CliRunner()

    with patch("main.asyncio.run") as mock_run:
        result = runner.invoke(
            cli, ["batch", "keyword1", "keyword2", "--parallel", "2", "--dry-run"]
        )

    # Check command executed
    assert result.exit_code == 0
    mock_run.assert_called_once()

    # Check output
    assert "Batch Processing 2 Keywords" in result.output
    assert "Parallel execution: 2" in result.output
    assert "Mode: Research only" in result.output


def test_batch_command_validation():
    """Test batch command input validation."""
    runner = CliRunner()

    # Test invalid parallel count
    result = runner.invoke(cli, ["batch", "keyword", "--parallel", "0"])
    assert result.exit_code == 1
    assert "Parallel count must be at least 1" in result.output

    # Test high parallel count warning
    result = runner.invoke(cli, ["batch", "keyword", "--parallel", "10", "--dry-run"])
    assert "Warning: High parallel count may cause rate limiting" in result.output
