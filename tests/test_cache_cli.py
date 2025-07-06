"""
Tests for cache management CLI commands.

This module tests all cache-related CLI commands including search, stats,
clear, and warm operations.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from main import cache, cache_clear, cache_search, cache_stats, cache_warm


class TestCacheSearch:
    """Test the cache search command."""

    def test_cache_search_basic(self):
        """Test basic cache search functionality."""
        # Create a test runner
        runner = CliRunner()

        # Mock the async components
        with patch("main.VectorStorage") as mock_storage_class:
            with patch("rag.embeddings.EmbeddingGenerator") as mock_embeddings_class:
                with patch("rag.processor.TextProcessor") as mock_processor_class:
                    with patch("main.ResearchRetriever") as mock_retriever_class:
                        # Set up mock instances
                        mock_storage = AsyncMock()
                        mock_embeddings = AsyncMock()

                        # Configure mock classes to return mock instances
                        mock_storage_class.return_value = mock_storage
                        mock_embeddings_class.return_value = mock_embeddings

                        # Mock the embedding generation
                        mock_embeddings.generate_embedding.return_value = [0.1] * 1536

                        # Mock search results
                        mock_storage.search_similar.return_value = [
                            {
                                "similarity": 0.95,
                                "keyword": "test keyword",
                                "content": "This is test content about the topic...",
                                "created_at": "2024-01-01T12:00:00Z",
                                "metadata": {},
                            }
                        ]

                        # Mock async context manager
                        mock_storage.__aenter__.return_value = mock_storage
                        mock_storage.__aexit__.return_value = None

                        # Run the command
                        result = runner.invoke(cache_search, ["test query"])

                        # Check the result
                        assert result.exit_code == 0
                        assert "Searching cache for: 'test query'" in result.output
                        assert "Found 1 matching results" in result.output
                        assert "95.00%" in result.output  # Similarity score
                        assert "test keyword" in result.output

    def test_cache_search_no_results(self):
        """Test cache search with no results."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            with patch("rag.embeddings.EmbeddingGenerator") as mock_embeddings_class:
                # Set up mocks
                mock_storage = AsyncMock()
                mock_embeddings = AsyncMock()

                mock_storage_class.return_value = mock_storage
                mock_embeddings_class.return_value = mock_embeddings

                mock_embeddings.generate_embedding.return_value = [0.1] * 1536
                mock_storage.search_similar.return_value = []

                mock_storage.__aenter__.return_value = mock_storage
                mock_storage.__aexit__.return_value = None

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

    def test_cache_search_with_options(self):
        """Test cache search with custom options."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            with patch("rag.embeddings.EmbeddingGenerator") as mock_embeddings_class:
                # Set up mocks
                mock_storage = AsyncMock()
                mock_embeddings = AsyncMock()

                mock_storage_class.return_value = mock_storage
                mock_embeddings_class.return_value = mock_embeddings

                mock_embeddings.generate_embedding.return_value = [0.1] * 1536
                mock_storage.search_similar.return_value = []

                mock_storage.__aenter__.return_value = mock_storage
                mock_storage.__aexit__.return_value = None

                # Run with custom limit and threshold
                result = runner.invoke(
                    cache_search, ["test", "--limit", "20", "--threshold", "0.9"]
                )

                assert result.exit_code == 0
                # Verify the options were passed
                mock_storage.search_similar.assert_called_once()
                call_args = mock_storage.search_similar.call_args
                assert call_args[1]["limit"] == 20
                assert call_args[1]["similarity_threshold"] == 0.9


class TestCacheStats:
    """Test the cache stats command."""

    def test_cache_stats_basic(self):
        """Test basic cache statistics display."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            # Set up mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage

            # Mock statistics
            mock_storage.get_cache_stats.return_value = {
                "total_entries": 100,
                "unique_keywords": 25,
                "storage_bytes": 1024 * 1024 * 10,  # 10 MB
                "avg_chunk_size": 500,
                "oldest_entry": "2024-01-01T00:00:00Z",
                "newest_entry": "2024-01-10T00:00:00Z",
            }

            mock_storage.__aenter__.return_value = mock_storage
            mock_storage.__aexit__.return_value = None

            # Mock ResearchRetriever statistics
            with patch("main.ResearchRetriever.get_statistics") as mock_get_stats:
                mock_get_stats.return_value = None  # No active instances

                # Run the command
                result = runner.invoke(cache_stats)

                assert result.exit_code == 0
                assert "Cache Statistics" in result.output
                assert "Total cached entries: 100" in result.output
                assert "Unique keywords: 25" in result.output
                assert "Storage used: 10.00 MB" in result.output

    def test_cache_stats_detailed(self):
        """Test detailed cache statistics."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            # Set up mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage

            # Mock basic stats
            mock_storage.get_cache_stats.return_value = {
                "total_entries": 100,
                "unique_keywords": 25,
                "storage_bytes": 1024 * 1024 * 10,
                "avg_chunk_size": 500,
                "research_chunks": 80,
                "cache_entries": 20,
                "total_embeddings": 80,
                "oldest_entry": "2024-01-01T00:00:00Z",
                "newest_entry": "2024-01-10T00:00:00Z",
            }

            # Mock keyword distribution
            mock_storage.get_keyword_distribution.return_value = [
                ("diabetes", 15),
                ("insulin", 12),
                ("blood sugar", 10),
            ]

            mock_storage.__aenter__.return_value = mock_storage
            mock_storage.__aexit__.return_value = None

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

    def test_cache_clear_dry_run(self):
        """Test cache clear in dry run mode."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            # Set up mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage

            mock_storage.get_cache_stats.return_value = {"total_entries": 50}

            mock_storage.__aenter__.return_value = mock_storage
            mock_storage.__aexit__.return_value = None

            # Run in dry run mode
            result = runner.invoke(cache_clear, ["--older-than", "7", "--dry-run"])

            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Would clear approximately 50 entries" in result.output
            # Verify cleanup was not called
            mock_storage.cleanup_cache.assert_not_called()

    def test_cache_clear_with_confirmation(self):
        """Test cache clear with user confirmation."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            # Set up mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage

            mock_storage.cleanup_cache.return_value = 25

            mock_storage.__aenter__.return_value = mock_storage
            mock_storage.__aexit__.return_value = None

            # Run with user input
            result = runner.invoke(
                cache_clear, ["--older-than", "30"], input="y\n"  # Confirm
            )

            assert result.exit_code == 0
            assert "Are you sure you want to proceed?" in result.output
            assert "Cleared 25 cache entries" in result.output

    def test_cache_clear_force(self):
        """Test cache clear with force flag."""
        runner = CliRunner()

        with patch("main.VectorStorage") as mock_storage_class:
            # Set up mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage

            mock_storage.cleanup_cache.return_value = 100

            mock_storage.__aenter__.return_value = mock_storage
            mock_storage.__aexit__.return_value = None

            # Run with force flag
            result = runner.invoke(cache_clear, ["--force"])

            assert result.exit_code == 0
            assert "Are you sure" not in result.output  # No confirmation
            assert "Cleared 100 cache entries" in result.output


class TestCacheWarm:
    """Test the cache warm command."""

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

                assert result.exit_code == 0
                assert "Warming cache for topic: 'diabetes'" in result.output
                assert "Successfully cached: 3/3" in result.output

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
