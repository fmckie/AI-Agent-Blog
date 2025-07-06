"""
Tests for workflow transaction behavior and recovery mechanisms.

This test file covers the new Phase 5 features including:
- Transaction-like behavior
- State persistence and recovery
- Resource cleanup
- Context manager support
"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from workflow import WorkflowOrchestrator, WorkflowState


class TestWorkflowTransactions:
    """Test transaction-like behavior in workflow orchestrator."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration with temp directory."""
        config = Mock(spec=Config)
        config.output_dir = tmp_path
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        return ResearchFindings(
            keyword="test keyword",
            research_summary="Comprehensive test summary that provides detailed insights into the research topic with sufficient length to meet validation requirements.",
            academic_sources=[
                AcademicSource(
                    title="Test Source",
                    url="https://test.edu",
                    excerpt="Test excerpt",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Finding 1", "Finding 2"],
            total_sources_analyzed=5,
            search_query_used="test query",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        return ArticleOutput(
            title="Test Article",
            meta_description="This is a comprehensive test meta description that provides a detailed summary of the article content with proper length.",
            focus_keyword="test keyword",
            introduction="This is a comprehensive test introduction that provides readers with a detailed overview of the article's content, setting the stage for the information to follow and meeting the minimum character requirements for a proper introduction.",
            main_sections=[
                ArticleSection(
                    heading="First Test Section",
                    content="This is the first comprehensive test content section that provides detailed information about the topic at hand with sufficient length to meet the validation requirements for proper article sections.",
                ),
                ArticleSection(
                    heading="Second Test Section",
                    content="This is the second comprehensive test content section that continues the discussion with additional detailed information, ensuring the article has multiple sections as required by the validation rules.",
                ),
                ArticleSection(
                    heading="Third Test Section",
                    content="This is the third comprehensive test content section that concludes the main discussion points with final insights and analysis, completing the minimum section requirements for a valid article.",
                ),
            ],
            conclusion="This is a comprehensive test conclusion that summarizes all the key points discussed in the article and provides final thoughts with sufficient detail to meet validation requirements.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.02,
            sources_used=["https://test.edu"],
        )

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, mock_config):
        """Test that workflow states transition correctly."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Initial state
                assert orchestrator.current_state == WorkflowState.INITIALIZED

                # Update state
                orchestrator._update_state(WorkflowState.RESEARCHING)
                assert orchestrator.current_state == WorkflowState.RESEARCHING

                # Update with data
                orchestrator._update_state(
                    WorkflowState.RESEARCH_COMPLETE, {"sources_found": 5}
                )
                assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE
                assert orchestrator.workflow_data["sources_found"] == 5

    @pytest.mark.asyncio
    async def test_state_persistence(self, mock_config):
        """Test that workflow state is persisted to disk."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Create state file
                state_file = mock_config.output_dir / "test_state.json"
                orchestrator.state_file = state_file

                # Update state and save
                orchestrator._update_state(
                    WorkflowState.RESEARCHING,
                    {"keyword": "test", "start_time": "2024-01-01T00:00:00"},
                )

                # Verify file exists and contains correct data
                assert state_file.exists()
                state_data = json.loads(state_file.read_text())
                assert state_data["state"] == "researching"
                assert state_data["data"]["keyword"] == "test"

    @pytest.mark.asyncio
    async def test_state_recovery(self, mock_config):
        """Test loading workflow state from disk."""
        # Create a state file
        state_file = mock_config.output_dir / "test_state.json"
        state_data = {
            "state": "research_complete",
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "recovered keyword", "sources_found": 10},
            "temp_dir": str(mock_config.output_dir / "temp_dir"),
        }
        state_file.write_text(json.dumps(state_data))

        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Load state
                success = orchestrator._load_state(state_file)

                assert success
                assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE
                assert orchestrator.workflow_data["keyword"] == "recovered keyword"
                assert orchestrator.workflow_data["sources_found"] == 10
                assert (
                    orchestrator.temp_output_dir == mock_config.output_dir / "temp_dir"
                )

    @pytest.mark.asyncio
    async def test_rollback_cleanup(self, mock_config):
        """Test that rollback properly cleans up resources."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Create temp directory and state file
                temp_dir = mock_config.output_dir / "temp_test"
                temp_dir.mkdir()
                (temp_dir / "test.txt").write_text("test")

                state_file = mock_config.output_dir / "state.json"
                state_file.write_text("{}")

                orchestrator.temp_output_dir = temp_dir
                orchestrator.state_file = state_file

                # Perform rollback
                await orchestrator._rollback()

                # Verify cleanup
                assert not temp_dir.exists()
                assert not state_file.exists()
                assert orchestrator.current_state == WorkflowState.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_atomic_save_operations(
        self, mock_config, mock_research_findings, mock_article_output
    ):
        """Test atomic save operations using temp directory."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Set up temp directory
                orchestrator.temp_output_dir = mock_config.output_dir / "temp_atomic"
                orchestrator.temp_output_dir.mkdir()

                # Perform atomic save
                output_path = await orchestrator._save_outputs_atomic(
                    "test keyword", mock_research_findings, mock_article_output
                )

                # Verify final output exists
                assert output_path.exists()
                assert output_path.name == "index.html"

                # Verify temp directory was moved (no longer exists)
                assert not orchestrator.temp_output_dir.exists()

                # Verify all files in final location
                final_dir = output_path.parent
                assert (final_dir / "article.html").exists()
                assert (final_dir / "research.json").exists()
                assert (final_dir / "index.html").exists()

    @pytest.mark.asyncio
    async def test_workflow_failure_triggers_rollback(
        self, mock_config, mock_research_findings
    ):
        """Test that workflow failures trigger rollback."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Mock methods to simulate failure
                orchestrator.run_research = AsyncMock(
                    return_value=mock_research_findings
                )
                orchestrator.run_writing = AsyncMock(
                    side_effect=Exception("Writing failed")
                )
                orchestrator._rollback = AsyncMock()

                # Run workflow expecting failure
                with pytest.raises(Exception, match="Writing failed"):
                    await orchestrator.run_full_workflow("test keyword")

                # Verify rollback was called
                orchestrator._rollback.assert_called_once()

                # Verify state is failed
                assert orchestrator.current_state == WorkflowState.FAILED
                assert "error" in orchestrator.workflow_data


class TestWorkflowRecovery:
    """Test workflow recovery mechanisms."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = tmp_path
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        return ResearchFindings(
            keyword="test keyword",
            research_summary="Comprehensive test summary that provides detailed insights into the research topic with sufficient length to meet validation requirements.",
            academic_sources=[
                AcademicSource(
                    title="Test Source",
                    url="https://test.edu",
                    excerpt="Test excerpt",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Finding 1", "Finding 2"],
            total_sources_analyzed=5,
            search_query_used="test query",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        return ArticleOutput(
            title="Test Article",
            meta_description="This is a comprehensive test meta description that provides a detailed summary of the article content with proper length.",
            focus_keyword="test keyword",
            introduction="This is a comprehensive test introduction that provides readers with a detailed overview of the article's content, setting the stage for the information to follow and meeting the minimum character requirements for a proper introduction.",
            main_sections=[
                ArticleSection(
                    heading="First Test Section",
                    content="This is the first comprehensive test content section that provides detailed information about the topic at hand with sufficient length to meet the validation requirements for proper article sections.",
                ),
                ArticleSection(
                    heading="Second Test Section",
                    content="This is the second comprehensive test content section that continues the discussion with additional detailed information, ensuring the article has multiple sections as required by the validation rules.",
                ),
                ArticleSection(
                    heading="Third Test Section",
                    content="This is the third comprehensive test content section that concludes the main discussion points with final insights and analysis, completing the minimum section requirements for a valid article.",
                ),
            ],
            conclusion="This is a comprehensive test conclusion that summarizes all the key points discussed in the article and provides final thoughts with sufficient detail to meet validation requirements.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.02,
            sources_used=["https://test.edu"],
        )

    @pytest.mark.asyncio
    async def test_resume_from_research_state(
        self, mock_config, mock_research_findings, mock_article_output
    ):
        """Test resuming workflow from research state."""
        # Create state file
        state_file = mock_config.output_dir / "state.json"
        state_data = {
            "state": "researching",
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "test keyword"},
            "temp_dir": str(mock_config.output_dir / "temp"),
        }
        state_file.write_text(json.dumps(state_data))

        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch(
                    "workflow.run_research_agent",
                    AsyncMock(return_value=mock_research_findings),
                ):
                    with patch(
                        "writer_agent.agent.run_writer_agent",
                        AsyncMock(return_value=mock_article_output),
                    ):
                        orchestrator = WorkflowOrchestrator(mock_config)
                        orchestrator._save_outputs_atomic = AsyncMock(
                            return_value=mock_config.output_dir
                            / "output"
                            / "index.html"
                        )

                        # Resume workflow
                        result = await orchestrator.resume_workflow(state_file)

                        # Verify completion
                        assert orchestrator.current_state == WorkflowState.COMPLETE
                        assert result.name == "index.html"
                        assert orchestrator.workflow_data.get("resumed") is True

    @pytest.mark.asyncio
    async def test_resume_cleans_up_on_success(
        self, mock_config, mock_research_findings, mock_article_output
    ):
        """Test that successful resume cleans up state file."""
        # Create state file
        state_file = mock_config.output_dir / "state.json"
        state_data = {
            "state": "researching",
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "test keyword"},
        }
        state_file.write_text(json.dumps(state_data))

        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch(
                    "workflow.run_research_agent",
                    AsyncMock(return_value=mock_research_findings),
                ):
                    with patch(
                        "writer_agent.agent.run_writer_agent",
                        AsyncMock(return_value=mock_article_output),
                    ):
                        orchestrator = WorkflowOrchestrator(mock_config)
                        orchestrator._save_outputs_atomic = AsyncMock(
                            return_value=mock_config.output_dir
                            / "output"
                            / "index.html"
                        )

                        # Resume workflow
                        await orchestrator.resume_workflow(state_file)

                        # Verify state file was cleaned up
                        assert not state_file.exists()

    @pytest.mark.asyncio
    async def test_resume_rollback_on_failure(self, mock_config):
        """Test that failed resume triggers rollback."""
        # Create state file
        state_file = mock_config.output_dir / "state.json"
        state_data = {
            "state": "researching",
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "test keyword"},
        }
        state_file.write_text(json.dumps(state_data))

        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch(
                    "workflow.run_research_agent",
                    AsyncMock(side_effect=Exception("Research failed")),
                ):
                    orchestrator = WorkflowOrchestrator(mock_config)
                    orchestrator._rollback = AsyncMock()

                    # Attempt resume
                    with pytest.raises(Exception, match="Research failed"):
                        await orchestrator.resume_workflow(state_file)

                    # Verify rollback was called
                    orchestrator._rollback.assert_called_once()
                    assert orchestrator.current_state == WorkflowState.FAILED


class TestResourceCleanup:
    """Test resource cleanup and context manager support."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = tmp_path
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_config):
        """Test context manager cleans up resources."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                # Create resources that should be cleaned
                temp_dir = mock_config.output_dir / "temp_context"
                state_file = mock_config.output_dir / "state_context.json"

                async with WorkflowOrchestrator(mock_config) as orchestrator:
                    # Simulate incomplete workflow
                    orchestrator.temp_output_dir = temp_dir
                    orchestrator.state_file = state_file
                    orchestrator.current_state = WorkflowState.RESEARCHING

                    temp_dir.mkdir()
                    state_file.write_text("{}")

                    assert temp_dir.exists()
                    assert state_file.exists()

                # After context exit, resources should be cleaned
                assert not temp_dir.exists()
                assert not state_file.exists()

    @pytest.mark.asyncio
    async def test_context_manager_preserves_complete_state(self, mock_config):
        """Test context manager doesn't clean up completed workflows."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                state_file = mock_config.output_dir / "complete_state.json"

                async with WorkflowOrchestrator(mock_config) as orchestrator:
                    orchestrator.state_file = state_file
                    orchestrator.current_state = WorkflowState.COMPLETE

                    state_file.write_text("{}")
                    assert state_file.exists()

                # Complete workflows should not have state cleaned
                assert state_file.exists()

                # Clean up manually
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files(self, mock_config):
        """Test cleanup of orphaned workflow files."""
        # Create old files
        old_state = mock_config.output_dir / ".workflow_state_old_20240101_000000.json"
        old_temp = mock_config.output_dir / ".temp_old_20240101_000000"
        new_state = mock_config.output_dir / ".workflow_state_new_20240101_000000.json"
        new_temp = mock_config.output_dir / ".temp_new_20240101_000000"

        # Create files with different ages
        old_state.write_text("{}")
        old_temp.mkdir()
        new_state.write_text("{}")
        new_temp.mkdir()

        # Modify times to simulate age
        old_time = datetime.now().timestamp() - (25 * 3600)  # 25 hours old
        new_time = datetime.now().timestamp() - (1 * 3600)  # 1 hour old

        import os

        os.utime(old_state, (old_time, old_time))
        os.utime(old_temp, (old_time, old_time))
        os.utime(new_state, (new_time, new_time))
        os.utime(new_temp, (new_time, new_time))

        # Run cleanup for files older than 24 hours
        cleaned_state, cleaned_dirs = await WorkflowOrchestrator.cleanup_orphaned_files(
            mock_config.output_dir, 24
        )

        # Verify old files were cleaned
        assert not old_state.exists()
        assert not old_temp.exists()

        # Verify new files remain
        assert new_state.exists()
        assert new_temp.exists()

        # Verify counts
        assert cleaned_state == 1
        assert cleaned_dirs == 1

        # Clean up remaining files
        new_state.unlink()
        shutil.rmtree(new_temp)

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors_gracefully(self, mock_config):
        """Test cleanup continues despite individual file errors."""
        # Create files
        state1 = mock_config.output_dir / ".workflow_state_test1.json"
        state2 = mock_config.output_dir / ".workflow_state_test2.json"

        state1.write_text("{}")
        state2.write_text("{}")

        # Make old
        old_time = datetime.now().timestamp() - (25 * 3600)
        import os

        os.utime(state1, (old_time, old_time))
        os.utime(state2, (old_time, old_time))

        # Mock to simulate error on first file
        original_unlink = Path.unlink

        def mock_unlink(self):
            # If this is state1, raise error
            if self.name == ".workflow_state_test1.json":
                raise PermissionError("Cannot delete")
            return original_unlink(self)

        with patch.object(Path, "unlink", mock_unlink):
            # Run cleanup
            cleaned_state, cleaned_dirs = (
                await WorkflowOrchestrator.cleanup_orphaned_files(
                    mock_config.output_dir, 24
                )
            )

        # Should have cleaned second file despite first file error
        assert cleaned_state == 1
        assert not state2.exists()

        # First file should remain due to error
        assert state1.exists()

        # Clean up
        state1.unlink()


class TestProgressCallbacks:
    """Test progress callback functionality."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = tmp_path
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    def test_progress_callback_setup(self, mock_config):
        """Test setting up progress callbacks."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Initially no callback
                assert orchestrator.progress_callback is None

                # Set callback
                callback = Mock()
                orchestrator.set_progress_callback(callback)

                assert orchestrator.progress_callback == callback

    def test_progress_reporting(self, mock_config):
        """Test progress is reported to callback."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Set up callback
                callback = Mock()
                orchestrator.set_progress_callback(callback)

                # Report progress
                orchestrator._report_progress("research", "Searching sources...")

                # Verify callback was called
                callback.assert_called_once_with("research", "Searching sources...")

    def test_progress_without_callback(self, mock_config):
        """Test progress reporting works without callback."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Should not raise error
                orchestrator._report_progress("research", "Test message")

    @pytest.mark.asyncio
    async def test_workflow_reports_progress(
        self, mock_config, mock_research_findings, mock_article_output
    ):
        """Test that workflow execution reports progress."""
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch(
                    "workflow.run_research_agent",
                    AsyncMock(return_value=mock_research_findings),
                ):
                    with patch(
                        "writer_agent.agent.run_writer_agent",
                        AsyncMock(return_value=mock_article_output),
                    ):
                        orchestrator = WorkflowOrchestrator(mock_config)

                        # Mock save method
                        orchestrator._save_outputs_atomic = AsyncMock(
                            return_value=mock_config.output_dir
                            / "output"
                            / "index.html"
                        )

                        # Set up progress tracking
                        progress_calls = []
                        orchestrator.set_progress_callback(
                            lambda phase, msg: progress_calls.append((phase, msg))
                        )

                        # Run workflow
                        await orchestrator.run_full_workflow("test keyword")

                        # Verify progress was reported
                        phases = [call[0] for call in progress_calls]
                        assert "research" in phases
                        assert "research_complete" in phases
                        assert "writing" in phases
                        assert "writing_complete" in phases
                        assert "saving" in phases
                        assert "complete" in phases
