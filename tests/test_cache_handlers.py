"""
Comprehensive tests for cache command handlers.

This module tests the actual implementation of cache handler functions
in cli/cache_handlers.py to ensure proper coverage and functionality.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from click.exceptions import Exit

from cli.cache_handlers import (
    handle_cache_search,
    handle_cache_stats,
    handle_cache_clear,
    handle_cache_warm,
    handle_export_cache_metrics,
)


class TestHandleCacheSearch:
    """Test the handle_cache_search function."""

    @pytest.mark.asyncio
    async def test_search_success_with_results(self):
        """Test successful search that finds matching results."""
        # Create mock configurations
        mock_rag_config = MagicMock()

        # Create mock storage with async context manager
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        # Mock search results
        mock_storage.search_similar.return_value = [
            {
                "similarity": 0.95,
                "keyword": "diabetes management",
                "content": "This is a comprehensive guide about diabetes management strategies including diet, exercise, and medication...",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "similarity": 0.87,
                "keyword": "blood sugar control",
                "content": "Understanding blood sugar levels is crucial for diabetes management. Normal ranges vary...",
                "created_at": "2024-01-14T15:45:00Z",
            },
        ]

        # Create mock embeddings generator
        mock_embeddings = AsyncMock()
        mock_embedding_result = MagicMock()
        mock_embedding_result.embedding = [0.1, 0.2, 0.3]  # Mock embedding vector
        mock_embeddings.generate_embeddings.return_value = [mock_embedding_result]

        # Mock console to capture output
        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch(
                    "rag.embeddings.EmbeddingGenerator", return_value=mock_embeddings
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        # Execute the function
                        await handle_cache_search("diabetes", limit=10, threshold=0.5)

        # Verify the flow
        mock_embeddings.generate_embeddings.assert_called_once_with(["diabetes"])
        mock_storage.search_similar.assert_called_once_with(
            query_embedding=[0.1, 0.2, 0.3],
            limit=10,
            similarity_threshold=0.5,
        )

        # Verify console output
        console_calls = mock_console.print.call_args_list
        assert any(
            "Searching cache for: 'diabetes'" in str(call) for call in console_calls
        )
        assert any("Found 2 matching results" in str(call) for call in console_calls)
        assert any("95.00%" in str(call) for call in console_calls)
        assert any("diabetes management" in str(call) for call in console_calls)

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test search that finds no matching results."""
        # Setup mocks
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None
        mock_storage.search_similar.return_value = []  # No results

        mock_embeddings = AsyncMock()
        mock_embedding_result = MagicMock()
        mock_embedding_result.embedding = [0.1, 0.2, 0.3]
        mock_embeddings.generate_embeddings.return_value = [mock_embedding_result]

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch(
                    "rag.embeddings.EmbeddingGenerator", return_value=mock_embeddings
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        await handle_cache_search(
                            "obscure topic", limit=5, threshold=0.8
                        )

        # Verify console output for no results
        console_calls = mock_console.print.call_args_list
        assert any("No matching results found" in str(call) for call in console_calls)
        assert any("Try lowering the threshold" in str(call) for call in console_calls)
        assert any("0.8" in str(call) for call in console_calls)  # Current threshold

    @pytest.mark.asyncio
    async def test_search_embedding_generation_failure(self):
        """Test search when embedding generation fails."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_embeddings = AsyncMock()
        mock_embeddings.generate_embeddings.return_value = []  # No embeddings generated

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch(
                    "rag.embeddings.EmbeddingGenerator", return_value=mock_embeddings
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        await handle_cache_search("test", limit=10, threshold=0.5)

        # Should print error message
        console_calls = mock_console.print.call_args_list
        assert any(
            "Failed to generate embedding" in str(call) for call in console_calls
        )

        # Should not attempt to search
        mock_storage.search_similar.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_exception_handling(self):
        """Test search handles exceptions properly."""
        mock_rag_config = MagicMock()

        # Make VectorStorage raise an exception
        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch(
                "cli.cache_handlers.VectorStorage",
                side_effect=Exception("Database connection failed"),
            ):
                with pytest.raises(Exit) as exc_info:
                    await handle_cache_search("test", limit=10, threshold=0.5)

                assert exc_info.value.exit_code == 1


class TestHandleCacheStats:
    """Test the handle_cache_stats function."""

    @pytest.mark.asyncio
    async def test_stats_basic(self):
        """Test basic cache statistics display."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        # Mock cache statistics
        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1500,
            "unique_keywords": 75,
            "storage_bytes": 52428800,  # 50 MB
            "avg_chunk_size": 350,
            "oldest_entry": "2024-01-01T00:00:00Z",
            "newest_entry": "2024-01-20T12:00:00Z",
        }

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_cache_stats(detailed=False)

        # Verify basic stats are displayed
        console_calls = mock_console.print.call_args_list
        assert any("Cache Statistics" in str(call) for call in console_calls)
        assert any("1,500" in str(call) for call in console_calls)  # Total entries
        assert any("75" in str(call) for call in console_calls)  # Unique keywords
        assert any("50.00 MB" in str(call) for call in console_calls)  # Storage used
        assert any("350" in str(call) for call in console_calls)  # Avg chunk size

    @pytest.mark.asyncio
    async def test_stats_detailed(self):
        """Test detailed cache statistics with keyword distribution."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        # Mock cache statistics
        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1500,
            "unique_keywords": 75,
            "storage_bytes": 52428800,
            "avg_chunk_size": 350,
            "oldest_entry": "2024-01-01T00:00:00Z",
            "newest_entry": "2024-01-20T12:00:00Z",
            "research_chunks": 1200,
            "cache_entries": 300,
            "total_embeddings": 1500,
        }

        # Mock keyword distribution
        mock_storage.get_keyword_distribution.return_value = [
            ("diabetes management", 45),
            ("blood sugar control", 38),
            ("insulin resistance", 32),
            ("keto diet", 28),
            ("intermittent fasting", 25),
        ]

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_cache_stats(detailed=True)

        # Verify detailed stats are displayed
        console_calls = mock_console.print.call_args_list

        # Debug: print all console calls to see what's happening
        print("\n=== Console Output ===")
        for call in console_calls:
            print(f"Call: {call}")
        print("=== End Console Output ===\n")

        assert any("Detailed Breakdown" in str(call) for call in console_calls)
        assert any("Top 10 Cached Keywords" in str(call) for call in console_calls)
        assert any(
            "diabetes management" in str(call) and "45" in str(call)
            for call in console_calls
        )
        assert any("Storage Details" in str(call) for call in console_calls)
        assert any(
            "Research chunks" in str(call) and "1,200" in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_stats_with_retriever_statistics(self):
        """Test stats display with retriever performance metrics."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1000,
            "unique_keywords": 50,
            "storage_bytes": 10485760,  # 10 MB
            "avg_chunk_size": 300,
            "oldest_entry": None,
            "newest_entry": None,
        }

        # Mock retriever statistics
        mock_retriever_stats = {
            "cache_requests": 100,
            "cache_hits": 75,
            "exact_hits": 50,
            "semantic_hits": 25,
            "cache_misses": 25,
            "hit_rate": 0.75,
            "avg_retrieval_time": 0.125,
        }

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch(
                    "rag.retriever.ResearchRetriever.get_statistics",
                    return_value=mock_retriever_stats,
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        await handle_cache_stats(detailed=False)

        # Verify retriever stats are displayed
        console_calls = mock_console.print.call_args_list
        assert any("Cache Performance" in str(call) for call in console_calls)
        assert any(
            "Total requests" in str(call) and "100" in str(call)
            for call in console_calls
        )
        assert any(
            "Cache hits" in str(call) and "75" in str(call) for call in console_calls
        )
        assert any(
            "Hit rate" in str(call) and "75.0%" in str(call) for call in console_calls
        )
        assert any(
            "Estimated savings" in str(call) and "$3.00" in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_stats_exception_handling(self):
        """Test stats handles exceptions properly."""
        mock_rag_config = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch(
                "cli.cache_handlers.VectorStorage",
                side_effect=Exception("Storage error"),
            ):
                with pytest.raises(Exit) as exc_info:
                    await handle_cache_stats(detailed=False)

                assert exc_info.value.exit_code == 1


class TestHandleCacheClear:
    """Test the handle_cache_clear function."""

    @pytest.mark.asyncio
    async def test_clear_by_age_dry_run(self):
        """Test clearing entries by age in dry run mode."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {"total_entries": 250}

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_cache_clear(
                        older_than=30, keyword=None, force=False, dry_run=True
                    )

        # Verify dry run behavior
        console_calls = mock_console.print.call_args_list
        assert any(
            "Will clear entries older than 30 days" in str(call)
            for call in console_calls
        )
        assert any("DRY RUN" in str(call) for call in console_calls)
        assert any(
            "Would clear approximately" in str(call) and "250" in str(call)
            for call in console_calls
        )

        # Should not actually cleanup
        mock_storage.cleanup_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_by_keyword_with_confirmation(self):
        """Test clearing entries by keyword with user confirmation."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.cleanup_cache.return_value = 42  # Number of deleted entries

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    with patch("click.confirm", return_value=True):  # User confirms
                        await handle_cache_clear(
                            older_than=None,
                            keyword="old topic",
                            force=False,
                            dry_run=False,
                        )

        # Verify cleanup was called with correct parameters
        mock_storage.cleanup_cache.assert_called_once_with(
            older_than_days=None, keyword="old topic"
        )

        # Verify success message
        console_calls = mock_console.print.call_args_list
        assert any(
            "Will clear entries for keyword: 'old topic'" in str(call)
            for call in console_calls
        )
        assert any("Cleared 42 cache entries" in str(call) for call in console_calls)

    @pytest.mark.asyncio
    async def test_clear_all_forced(self):
        """Test clearing all entries with force flag."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.cleanup_cache.return_value = 500

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    # Force=True should skip confirmation
                    await handle_cache_clear(
                        older_than=None, keyword=None, force=True, dry_run=False
                    )

        # Verify cleanup was called
        mock_storage.cleanup_cache.assert_called_once_with(
            older_than_days=None, keyword=None
        )

        # Verify warning message
        console_calls = mock_console.print.call_args_list
        assert any(
            "Will clear ALL cache entries!" in str(call) for call in console_calls
        )
        assert any("Cleared 500 cache entries" in str(call) for call in console_calls)

    @pytest.mark.asyncio
    async def test_clear_cancelled_by_user(self):
        """Test clear operation cancelled by user."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    with patch("click.confirm", return_value=False):  # User cancels
                        await handle_cache_clear(
                            older_than=7, keyword=None, force=False, dry_run=False
                        )

        # Should not cleanup when cancelled
        mock_storage.cleanup_cache.assert_not_called()

        # Verify cancellation message
        console_calls = mock_console.print.call_args_list
        assert any("Cancelled" in str(call) for call in console_calls)

    @pytest.mark.asyncio
    async def test_clear_exception_handling(self):
        """Test clear handles exceptions properly."""
        mock_rag_config = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch(
                "cli.cache_handlers.VectorStorage",
                side_effect=Exception("Cleanup failed"),
            ):
                with pytest.raises(Exit) as exc_info:
                    await handle_cache_clear(
                        older_than=None, keyword=None, force=True, dry_run=False
                    )

                assert exc_info.value.exit_code == 1


class TestHandleCacheWarm:
    """Test the handle_cache_warm function."""

    @pytest.mark.asyncio
    async def test_warm_basic_success(self):
        """Test basic cache warming with default variations."""
        mock_config = MagicMock()
        mock_research_agent = MagicMock()
        mock_research_findings = MagicMock()

        mock_console = MagicMock()

        # Mock Progress to avoid issues with MagicMock timestamps
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=None)
        mock_progress.add_task.return_value = 1  # task id

        with patch("cli.cache_handlers.get_config", return_value=mock_config):
            with patch(
                "research_agent.create_research_agent", return_value=mock_research_agent
            ):
                with patch(
                    "research_agent.run_research_agent",
                    return_value=mock_research_findings,
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        with patch(
                            "cli.cache_handlers.Progress", return_value=mock_progress
                        ):
                            await handle_cache_warm(
                                "diabetes", variations=3, verbose=False
                            )

        # Verify by checking console output since we can't easily count async calls
        # The console output will show "Successfully cached: 3/3"

        # Verify console output
        console_calls = mock_console.print.call_args_list
        assert any(
            "Warming cache for topic: 'diabetes'" in str(call) for call in console_calls
        )
        # The success count message appears after the progress bar completes
        assert any(
            "Successfully cached:" in str(call) and "/3" in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_warm_with_custom_variations_verbose(self):
        """Test cache warming with custom variations and verbose output."""
        mock_config = MagicMock()
        mock_research_agent = MagicMock()
        mock_research_findings = MagicMock()

        mock_console = MagicMock()

        # Track calls to run_research_agent
        research_calls = []

        async def mock_run_research(agent, keyword):
            research_calls.append(keyword)
            return mock_research_findings

        # Mock Progress to avoid issues with MagicMock timestamps
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=None)
        mock_progress.add_task.return_value = 1  # task id

        with patch("cli.cache_handlers.get_config", return_value=mock_config):
            with patch(
                "research_agent.create_research_agent", return_value=mock_research_agent
            ):
                with patch(
                    "research_agent.run_research_agent", side_effect=mock_run_research
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        with patch(
                            "cli.cache_handlers.Progress", return_value=mock_progress
                        ):
                            await handle_cache_warm(
                                "heart health", variations=5, verbose=True
                            )

        # Should research 5 keywords
        assert len(research_calls) == 5
        assert research_calls[0] == "heart health"
        assert "heart health benefits" in research_calls
        assert "heart health research" in research_calls

        # Verify verbose output
        console_calls = mock_console.print.call_args_list
        assert any("Researching 'heart health'" in str(call) for call in console_calls)
        assert any(
            "✓ Cached research for 'heart health'" in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_warm_partial_failure(self):
        """Test cache warming with some failures."""
        mock_config = MagicMock()
        mock_research_agent = MagicMock()

        mock_console = MagicMock()

        # Make some research calls fail
        call_count = 0

        async def mock_run_research(agent, keyword):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                raise Exception("API rate limit")
            return MagicMock()

        # Mock Progress to avoid issues with MagicMock timestamps
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=None)
        mock_progress.add_task.return_value = 1  # task id

        with patch("cli.cache_handlers.get_config", return_value=mock_config):
            with patch(
                "research_agent.create_research_agent", return_value=mock_research_agent
            ):
                with patch(
                    "research_agent.run_research_agent", side_effect=mock_run_research
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        with patch(
                            "cli.cache_handlers.Progress", return_value=mock_progress
                        ):
                            await handle_cache_warm(
                                "nutrition", variations=3, verbose=True
                            )

        # Verify partial success message
        console_calls = mock_console.print.call_args_list
        assert any(
            "Successfully cached:" in str(call) and "/3" in str(call)
            for call in console_calls
        )
        assert any(
            "Failed to research" in str(call) and "API rate limit" in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_warm_exception_handling(self):
        """Test warm handles exceptions properly."""
        with patch(
            "cli.cache_handlers.get_config", side_effect=Exception("Config error")
        ):
            with pytest.raises(Exit) as exc_info:
                await handle_cache_warm("test", variations=3, verbose=False)

            assert exc_info.value.exit_code == 1


class TestHandleExportCacheMetrics:
    """Test the handle_export_cache_metrics function."""

    @pytest.mark.asyncio
    async def test_export_json_to_stdout(self):
        """Test exporting metrics as JSON to stdout."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1000,
            "unique_keywords": 50,
            "storage_bytes": 10485760,
            "created_at": datetime.now(timezone.utc),
        }

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_export_cache_metrics(format="json", output_path=None)

        # Verify JSON output to console
        console_calls = mock_console.print.call_args_list
        assert len(console_calls) > 0
        # Check that JSON was printed (contains braces and quotes)
        json_output = str(console_calls[-1])
        assert "{" in json_output and "}" in json_output
        assert "total_entries" in json_output

    @pytest.mark.asyncio
    async def test_export_csv_to_file(self, tmp_path):
        """Test exporting metrics as CSV to file."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1000,
            "unique_keywords": 50,
            "storage_bytes": 10485760,
            "avg_chunk_size": 300,
        }

        output_file = tmp_path / "metrics.csv"
        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_export_cache_metrics(
                        format="csv", output_path=output_file
                    )

        # Verify file was created with CSV content
        assert output_file.exists()
        content = output_file.read_text()
        assert "metric,value" in content
        assert "total_entries,1000" in content
        assert "unique_keywords,50" in content
        assert "storage_bytes,10485760" in content

        # Verify success message
        console_calls = mock_console.print.call_args_list
        assert any(
            "Metrics exported to" in str(call) and str(output_file) in str(call)
            for call in console_calls
        )

    @pytest.mark.asyncio
    async def test_export_prometheus_format(self):
        """Test exporting metrics in Prometheus format."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {
            "total_entries": 1000,
            "unique_keywords": 50,
            "storage_bytes": 10485760,
            "hit_rate": 0.75,
            "oldest_entry": "2024-01-01",  # String should be skipped
        }

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch("cli.cache_handlers.console", mock_console):
                    await handle_export_cache_metrics(
                        format="prometheus", output_path=None
                    )

        # Verify Prometheus format output
        console_calls = mock_console.print.call_args_list
        prometheus_output = str(console_calls[-1])
        assert "# TYPE seo_cache_total_entries gauge" in prometheus_output
        assert "seo_cache_total_entries 1000" in prometheus_output
        assert "# TYPE seo_cache_hit_rate gauge" in prometheus_output
        assert "seo_cache_hit_rate 0.75" in prometheus_output
        # String values should not be included
        assert "oldest_entry" not in prometheus_output

    @pytest.mark.asyncio
    async def test_export_with_retriever_stats(self):
        """Test export includes retriever statistics when available."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {
            "total_entries": 500,
            "storage_bytes": 5242880,
        }

        mock_retriever_stats = {
            "cache_requests": 100,
            "cache_hits": 80,
            "hit_rate": 0.8,
        }

        mock_console = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with patch(
                    "rag.retriever.ResearchRetriever.get_statistics",
                    return_value=mock_retriever_stats,
                ):
                    with patch("cli.cache_handlers.console", mock_console):
                        await handle_export_cache_metrics(
                            format="json", output_path=None
                        )

        # Verify combined stats in output
        console_calls = mock_console.print.call_args_list
        json_output = str(console_calls[-1])
        assert "cache_performance" in json_output
        assert "cache_requests" in json_output
        assert "80" in json_output  # cache_hits value

    @pytest.mark.asyncio
    async def test_export_unknown_format(self):
        """Test export with unknown format raises error."""
        mock_rag_config = MagicMock()
        mock_storage = AsyncMock()
        mock_storage.__aenter__.return_value = mock_storage
        mock_storage.__aexit__.return_value = None

        mock_storage.get_cache_stats.return_value = {"total_entries": 100}

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch("cli.cache_handlers.VectorStorage", return_value=mock_storage):
                with pytest.raises(Exit) as exc_info:
                    await handle_export_cache_metrics(format="xml", output_path=None)

                assert exc_info.value.exit_code == 1

    @pytest.mark.asyncio
    async def test_export_exception_handling(self):
        """Test export handles exceptions properly."""
        mock_rag_config = MagicMock()

        with patch("cli.cache_handlers.get_rag_config", return_value=mock_rag_config):
            with patch(
                "cli.cache_handlers.VectorStorage",
                side_effect=Exception("Export failed"),
            ):
                with pytest.raises(Exit) as exc_info:
                    await handle_export_cache_metrics(format="json", output_path=None)

                assert exc_info.value.exit_code == 1


# Integration test class for testing handler interactions
@pytest.mark.integration
class TestCacheHandlersIntegration:
    """Integration tests for cache handlers working together."""

    @pytest.mark.asyncio
    async def test_warm_then_search_workflow(self):
        """Test warming cache and then searching for content."""
        # This would test the full workflow:
        # 1. Warm cache with a topic
        # 2. Search for related content
        # 3. Verify the warmed content is found
        pass

    @pytest.mark.asyncio
    async def test_stats_after_operations(self):
        """Test that stats accurately reflect cache operations."""
        # This would test:
        # 1. Get initial stats
        # 2. Perform operations (warm, clear)
        # 3. Verify stats are updated correctly
        pass


# Helper fixtures for common test setups
@pytest.fixture
def mock_rag_config():
    """Create a mock RAG configuration."""
    config = MagicMock()
    config.collection_name = "test_collection"
    config.embedding_model = "text-embedding-ada-002"
    return config


@pytest.fixture
def mock_vector_storage():
    """Create a mock VectorStorage with async context manager."""
    storage = AsyncMock()
    storage.__aenter__.return_value = storage
    storage.__aexit__.return_value = None
    return storage


@pytest.fixture
def mock_console():
    """Create a mock console for output capture."""
    return MagicMock()


# Test utility functions
def assert_console_contains(mock_console, text):
    """Assert that console output contains specific text."""
    console_calls = mock_console.print.call_args_list
    return any(text in str(call) for call in console_calls)


def get_console_output(mock_console):
    """Get all console output as a single string."""
    console_calls = mock_console.print.call_args_list
    return "\n".join(str(call) for call in console_calls)


# What questions do you have about these tests, Finn?
# Would you like me to explain any specific testing pattern in more detail?
# Try this exercise: Add a test for concurrent cache operations!
