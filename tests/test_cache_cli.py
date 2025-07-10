"""
Tests for cache management CLI commands.

This module tests all cache-related CLI commands including search, stats,
clear, and warm operations.
"""

import asyncio
import os
from datetime import datetime, timezone
from functools import wraps
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from main import cache, cache_clear, cache_search, cache_stats, cache_warm


def with_mocked_env(func):
    """Decorator to mock environment variables for tests."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        env_vars = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key",
            "OPENAI_API_KEY": "sk-test-" + "x" * 40,  # Make it long enough
            "TAVILY_API_KEY": "tvly-" + "x" * 40,  # Make it long enough
            "DISABLE_DOTENV": "true",  # Prevent loading .env file
        }
        with patch.dict(os.environ, env_vars):
            return func(*args, **kwargs)

    return wrapper


class TestCacheSearch:
    """Test the cache search command."""

    @with_mocked_env
    def test_cache_search_basic(self):
        """Test basic cache search functionality."""
        # Create a test runner
        runner = CliRunner()

        # Mock the async handler function - asyncio.run() needs a coroutine
        async def mock_search(query, limit, threshold):
            # Simulate the output from handle_cache_search
            from rich.console import Console

            console = Console()
            console.print(f"\n[bold blue]🔍 Searching cache for: '{query}'[/bold blue]")
            console.print(f"\n[green]Found 1 matching results:[/green]\n")
            console.print(f"[bold cyan]1. Similarity: 95.00%[/bold cyan]")
            console.print(f"   Keyword: [yellow]test keyword[/yellow]")
            console.print(f"   Content: This is test content about the topic...")
            console.print(f"   Cached: 2024-01-01T12:00:00Z")
            console.print()

        with patch("main.handle_cache_search", new=mock_search):
            # Run the command
            result = runner.invoke(cache_search, ["test query"])

            # Debug output if test fails
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                if result.exception:
                    print(f"Exception: {result.exception}")
                    import traceback

                    traceback.print_exception(
                        type(result.exception),
                        result.exception,
                        result.exception.__traceback__,
                    )

            # Check the result
            assert result.exit_code == 0
            assert "Searching cache for: 'test query'" in result.output
            assert "Found 1 matching results" in result.output
            assert "95.00%" in result.output  # Similarity score
            assert "test keyword" in result.output

    @with_mocked_env
    def test_cache_search_no_results(self):
        """Test cache search with no results."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_search(query, limit, threshold):
            from rich.console import Console

            console = Console()
            console.print(f"\n[bold blue]🔍 Searching cache for: '{query}'[/bold blue]")
            console.print("[yellow]No matching results found in cache.[/yellow]")
            console.print(
                f"[dim]Try lowering the threshold (current: {threshold})[/dim]"
            )

        with patch("main.handle_cache_search", new=mock_search):
            # Run the command
            result = runner.invoke(cache_search, ["no matches"])

            # Debug output if test fails
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")

            assert result.exit_code == 0
            assert "No matching results found" in result.output
            assert "Try lowering the threshold" in result.output

    @with_mocked_env
    def test_cache_search_with_options(self):
        """Test cache search with custom options."""
        runner = CliRunner()

        # Track if correct arguments were passed
        called_with = {}

        # Mock the async handler function
        async def mock_search(query, limit, threshold):
            called_with["query"] = query
            called_with["limit"] = limit
            called_with["threshold"] = threshold
            from rich.console import Console

            console = Console()
            console.print(f"\n[bold blue]🔍 Searching cache for: '{query}'[/bold blue]")
            console.print("[yellow]No matching results found in cache.[/yellow]")
            console.print(
                f"[dim]Try lowering the threshold (current: {threshold})[/dim]"
            )

        with patch("main.handle_cache_search", new=mock_search):
            # Run with custom limit and threshold
            result = runner.invoke(
                cache_search, ["test", "--limit", "20", "--threshold", "0.9"]
            )

            assert result.exit_code == 0
            # Verify the options were passed
            assert called_with["query"] == "test"
            assert called_with["limit"] == 20
            assert called_with["threshold"] == 0.9


class TestCacheStats:
    """Test the cache stats command."""

    @with_mocked_env
    def test_cache_stats_basic(self):
        """Test basic cache statistics display."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_stats(detailed):
            from rich.console import Console

            console = Console()
            console.print("\n[bold]📊 Cache Statistics[/bold]\n")
            console.print("Total cached entries: [cyan]100[/cyan]")
            console.print("Unique keywords: [cyan]25[/cyan]")
            console.print("Storage used: [cyan]10.00 MB[/cyan]")
            console.print("Average chunk size: [cyan]500 chars[/cyan]")
            console.print("Oldest entry: [dim]2024-01-01T00:00:00Z[/dim]")
            console.print("Newest entry: [dim]2024-01-10T00:00:00Z[/dim]")

        with patch("main.handle_cache_stats", new=mock_stats):
            # Run the command
            result = runner.invoke(cache_stats)

            assert result.exit_code == 0
            assert "Cache Statistics" in result.output
            assert "Total cached entries: 100" in result.output
            assert "Unique keywords: 25" in result.output
            assert "Storage used: 10.00 MB" in result.output

    @with_mocked_env
    def test_cache_stats_detailed(self):
        """Test detailed cache statistics."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_stats(detailed):
            from rich.console import Console

            console = Console()
            console.print("\n[bold]📊 Cache Statistics[/bold]\n")
            console.print("Total cached entries: [cyan]100[/cyan]")
            console.print("Unique keywords: [cyan]25[/cyan]")
            console.print("Storage used: [cyan]10.00 MB[/cyan]")
            console.print("Average chunk size: [cyan]500 chars[/cyan]")
            console.print("Oldest entry: [dim]2024-01-01T00:00:00Z[/dim]")
            console.print("Newest entry: [dim]2024-01-10T00:00:00Z[/dim]")

            if detailed:
                console.print(f"\n[bold]Detailed Breakdown:[/bold]")
                console.print("\n[yellow]Top 10 Cached Keywords:[/yellow]")
                console.print("  • diabetes: [cyan]15[/cyan] chunks")
                console.print("  • insulin: [cyan]12[/cyan] chunks")
                console.print("  • blood sugar: [cyan]10[/cyan] chunks")

        with patch("main.handle_cache_stats", new=mock_stats):
            # Run with detailed flag
            result = runner.invoke(cache_stats, ["--detailed"])

            # Debug output if test fails
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")

            assert result.exit_code == 0
            assert "Detailed Breakdown" in result.output
            assert "Top 10 Cached Keywords" in result.output
            assert "diabetes: 15" in result.output


class TestCacheClear:
    """Test the cache clear command."""

    @with_mocked_env
    def test_cache_clear_dry_run(self):
        """Test cache clear in dry run mode."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_clear(older_than, keyword, force, dry_run):
            from rich.console import Console

            console = Console()
            console.print(
                f"\n[yellow]Will clear entries older than {older_than} days[/yellow]"
            )
            console.print("[dim]DRY RUN - No entries will be deleted[/dim]")
            console.print("\nWould clear approximately [cyan]50[/cyan] entries")

        with patch("main.handle_cache_clear", new=mock_clear):
            # Run in dry run mode
            result = runner.invoke(cache_clear, ["--older-than", "7", "--dry-run"])

            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Would clear approximately 50 entries" in result.output

    @with_mocked_env
    def test_cache_clear_with_confirmation(self):
        """Test cache clear with user confirmation."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_clear(older_than, keyword, force, dry_run):
            from rich.console import Console
            import click

            console = Console()
            console.print(
                f"\n[yellow]Will clear entries older than {older_than} days[/yellow]"
            )
            if not force:
                if not click.confirm("\nAre you sure you want to proceed?"):
                    console.print("[yellow]Cancelled.[/yellow]")
                    return
            console.print("\n[green]✅ Cleared 25 cache entries[/green]")

        with patch("main.handle_cache_clear", new=mock_clear):
            # Run with user input
            result = runner.invoke(
                cache_clear, ["--older-than", "30"], input="y\n"  # Confirm
            )

            assert result.exit_code == 0
            assert "Are you sure you want to proceed?" in result.output
            assert "Cleared 25 cache entries" in result.output

    @with_mocked_env
    def test_cache_clear_force(self):
        """Test cache clear with force flag."""
        runner = CliRunner()

        # Mock the async handler function
        async def mock_clear(older_than, keyword, force, dry_run):
            from rich.console import Console

            console = Console()
            console.print("\n[red]Will clear ALL cache entries![/red]")
            # No confirmation since force=True
            console.print("\n[green]✅ Cleared 100 cache entries[/green]")

        with patch("main.handle_cache_clear", new=mock_clear):
            # Run with force flag
            result = runner.invoke(cache_clear, ["--force"])

            assert result.exit_code == 0
            assert "Are you sure" not in result.output  # No confirmation
            assert "Cleared 100 cache entries" in result.output


class TestCacheWarm:
    """Test the cache warm command."""

    @with_mocked_env
    def test_cache_warm_basic(self):
        """Test basic cache warming."""
        runner = CliRunner()

        with patch("research_agent.create_research_agent") as mock_create_agent:
            with patch("research_agent.run_research_agent") as mock_run_agent:
                # Set up mock agent
                mock_agent = MagicMock()
                mock_create_agent.return_value = mock_agent

                # Mock successful research - run_research_agent returns ResearchFindings
                mock_findings = MagicMock()
                mock_run_agent.return_value = mock_findings

                # Run the command
                result = runner.invoke(cache_warm, ["diabetes"])

                # Debug output if test fails
                if result.exit_code != 0:
                    print(f"Exit code: {result.exit_code}")
                    print(f"Output: {result.output}")
                    if result.exception:
                        print(f"Exception: {result.exception}")

                assert result.exit_code == 0
                assert "Warming cache for topic: 'diabetes'" in result.output
                assert "Successfully cached: 3/3" in result.output

    @with_mocked_env
    def test_cache_warm_with_variations(self):
        """Test cache warming with custom variations."""
        runner = CliRunner()

        with patch("research_agent.create_research_agent") as mock_create_agent:
            with patch("research_agent.run_research_agent") as mock_run_agent:
                # Set up mock agent
                mock_agent = MagicMock()
                mock_create_agent.return_value = mock_agent

                # Mock research results
                mock_findings = MagicMock()
                mock_run_agent.return_value = mock_findings

                # Run with custom variations
                result = runner.invoke(
                    cache_warm, ["heart health", "--variations", "5", "--verbose"]
                )

                assert result.exit_code == 0
                assert "Generating 5 keyword variations" in result.output
                # Should research 5 keywords total
                assert mock_run_agent.call_count == 5

    @with_mocked_env
    def test_cache_warm_error_handling(self):
        """Test cache warming with errors."""
        runner = CliRunner()

        with patch("research_agent.create_research_agent") as mock_create_agent:
            with patch("research_agent.run_research_agent") as mock_run_agent:
                # Set up mock agent
                mock_agent = MagicMock()
                mock_create_agent.return_value = mock_agent

                # Mock failure
                mock_run_agent.side_effect = Exception("API error")

                # Run the command
                result = runner.invoke(cache_warm, ["test topic"])

                assert result.exit_code == 0  # Should not fail completely
                assert "Successfully cached: 0/3" in result.output


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for cache commands."""

    @pytest.mark.asyncio
    async def test_cache_workflow(self):
        """Test a complete cache workflow."""
        # This would test:
        # 1. Warm cache with a topic
        # 2. Search for related content
        # 3. Check statistics
        # 4. Clear old entries
        #
        # Requires actual database connection
        pass


# Test fixtures for common mocks
@pytest.fixture
def mock_storage():
    """Create a mock VectorStorage instance."""
    storage = AsyncMock()
    storage.__aenter__.return_value = storage
    storage.__aexit__.return_value = None
    return storage


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock()
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-key"
    return config


# Utility functions for testing
def assert_command_success(result):
    """Assert that a CLI command succeeded."""
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


def assert_command_failed(result):
    """Assert that a CLI command failed."""
    assert (
        result.exit_code != 0
    ), f"Command succeeded unexpectedly with output:\n{result.output}"


# What questions do you have about these tests, Finn?
# Would you like me to explain any specific testing pattern?
# Try this exercise: Add a test for error handling when the database connection fails!
