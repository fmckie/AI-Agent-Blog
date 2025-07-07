"""
Extended tests for workflow orchestration to improve coverage.

This module adds additional test cases for edge cases, error handling,
and untested methods in the WorkflowOrchestrator class.
"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from workflow import WorkflowOrchestrator, WorkflowState


class TestWorkflowOrchestratorExtended:
    """Extended test cases for workflow orchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.max_retries = 3
        return config

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                return WorkflowOrchestrator(mock_config)

    @pytest.mark.asyncio
    async def test_context_manager_usage(self, mock_config):
        """Test orchestrator as async context manager."""
        with patch("workflow.create_research_agent"):
            with patch("workflow.create_writer_agent"):
                async with WorkflowOrchestrator(mock_config) as orchestrator:
                    assert orchestrator is not None
                    assert orchestrator.current_state == WorkflowState.INITIALIZED

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_error(self, mock_config):
        """Test cleanup happens even on error."""
        with patch("workflow.create_research_agent"):
            with patch("workflow.create_writer_agent"):
                try:
                    async with WorkflowOrchestrator(mock_config) as orchestrator:
                        # Create temp directory
                        orchestrator.temp_output_dir = Path("/tmp/test_temp")
                        orchestrator.temp_output_dir.mkdir(exist_ok=True)
                        orchestrator._cleanup_required = True

                        # Simulate error
                        raise ValueError("Test error")
                except ValueError:
                    pass

    @pytest.mark.asyncio
    async def test_set_progress_callback(self, orchestrator):
        """Test setting progress callback."""
        callback = Mock()
        orchestrator.set_progress_callback(callback)
        assert orchestrator.progress_callback == callback

    @pytest.mark.asyncio
    async def test_update_progress(self, orchestrator):
        """Test progress update with callback."""
        callback = Mock()
        orchestrator.set_progress_callback(callback)

        orchestrator._update_progress("research", "Searching sources...")
        callback.assert_called_once_with("research", "Searching sources...")

    @pytest.mark.asyncio
    async def test_update_progress_no_callback(self, orchestrator):
        """Test progress update without callback doesn't error."""
        # Should not raise error
        orchestrator._update_progress("research", "Searching sources...")

    @pytest.mark.asyncio
    async def test_state_transition_valid(self, orchestrator):
        """Test valid state transitions."""
        # Initialize to researching
        await orchestrator._transition_state(WorkflowState.RESEARCHING)
        assert orchestrator.current_state == WorkflowState.RESEARCHING

        # Research to complete
        await orchestrator._transition_state(WorkflowState.RESEARCH_COMPLETE)
        assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE

    @pytest.mark.asyncio
    async def test_state_transition_with_data(self, orchestrator):
        """Test state transition with data update."""
        test_data = {"research_result": "test"}
        await orchestrator._transition_state(WorkflowState.RESEARCH_COMPLETE, test_data)

        assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE
        assert orchestrator.workflow_data["research_result"] == "test"

    @pytest.mark.asyncio
    async def test_save_state(self, orchestrator, tmp_path):
        """Test saving workflow state."""
        orchestrator.output_dir = tmp_path
        orchestrator.current_state = WorkflowState.RESEARCH_COMPLETE
        orchestrator.workflow_data = {"keyword": "test", "timestamp": "2024-01-01"}

        state_file = await orchestrator._save_state()

        assert state_file.exists()
        assert state_file.name.startswith(".workflow_state_")

        # Verify content
        with open(state_file) as f:
            saved_state = json.load(f)

        assert saved_state["state"] == "research_complete"
        assert saved_state["data"]["keyword"] == "test"

    @pytest.mark.asyncio
    async def test_create_temp_directory(self, orchestrator, tmp_path):
        """Test temporary directory creation."""
        orchestrator.output_dir = tmp_path

        temp_dir = await orchestrator._create_temp_directory()

        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert temp_dir.name.startswith(".temp_")
        assert orchestrator.temp_output_dir == temp_dir

    @pytest.mark.asyncio
    async def test_run_research_with_progress(self, orchestrator):
        """Test research execution with progress updates."""
        mock_findings = Mock(spec=ResearchFindings)
        callback = Mock()
        orchestrator.set_progress_callback(callback)

        with patch("workflow.run_research_agent", return_value=mock_findings):
            result = await orchestrator.run_research("test keyword")

        assert result == mock_findings
        assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE

        # Check progress updates
        callback.assert_any_call("research", "Starting academic research...")
        callback.assert_any_call("research_complete", "Research phase completed")

    @pytest.mark.asyncio
    async def test_run_research_error_handling(self, orchestrator):
        """Test research error handling."""
        with patch("workflow.run_research_agent", side_effect=Exception("API Error")):
            with pytest.raises(Exception) as exc_info:
                await orchestrator.run_research("test keyword")

            assert "API Error" in str(exc_info.value)
            assert orchestrator.current_state == WorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_run_writing_with_progress(self, orchestrator):
        """Test writing execution with progress updates."""
        mock_findings = Mock(spec=ResearchFindings)
        mock_article = Mock(spec=ArticleOutput)
        callback = Mock()
        orchestrator.set_progress_callback(callback)

        with patch("writer_agent.agent.run_writer_agent", return_value=mock_article):
            result = await orchestrator.run_writing("test keyword", mock_findings)

        assert result == mock_article
        assert orchestrator.current_state == WorkflowState.WRITING_COMPLETE

        # Check progress updates
        callback.assert_any_call("writing", "Generating SEO-optimized article...")
        callback.assert_any_call("writing_complete", "Article generation completed")

    @pytest.mark.asyncio
    async def test_save_outputs_creates_files(self, orchestrator, tmp_path):
        """Test output file creation."""
        orchestrator.output_dir = tmp_path
        orchestrator.temp_output_dir = tmp_path / "temp"
        orchestrator.temp_output_dir.mkdir()

        mock_findings = Mock(spec=ResearchFindings)
        mock_findings.to_json.return_value = {"findings": "test"}
        mock_findings.to_markdown_summary.return_value = "# Research Summary"

        mock_article = Mock(spec=ArticleOutput)
        mock_article.to_html.return_value = "<html>Test Article</html>"
        mock_article.to_json.return_value = {"article": "test"}
        mock_article.to_markdown.return_value = "# Test Article"

        output_path = await orchestrator.save_outputs(
            "test_keyword", mock_findings, mock_article
        )

        assert output_path.exists()
        assert output_path.name == "index.html"

        # Check all files were created
        keyword_dir = tmp_path / "test_keyword_2024"
        assert (keyword_dir / "research_data.json").exists()
        assert (keyword_dir / "article_data.json").exists()
        assert (keyword_dir / "article.md").exists()

    @pytest.mark.asyncio
    async def test_rollback_workflow(self, orchestrator, tmp_path):
        """Test workflow rollback."""
        orchestrator.output_dir = tmp_path
        orchestrator.temp_output_dir = tmp_path / "temp"
        orchestrator.temp_output_dir.mkdir()

        # Create a state file
        orchestrator.state_file = tmp_path / ".workflow_state_test.json"
        orchestrator.state_file.write_text('{"state": "writing"}')

        await orchestrator._rollback_workflow()

        assert orchestrator.current_state == WorkflowState.ROLLED_BACK
        assert not orchestrator.temp_output_dir.exists()
        assert not orchestrator.state_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files(self, tmp_path):
        """Test cleanup of old workflow files."""
        # Create old files
        old_state = tmp_path / ".workflow_state_old.json"
        old_state.write_text('{"state": "complete"}')
        old_state.touch()

        old_temp = tmp_path / ".temp_old"
        old_temp.mkdir()

        # Create recent files (should not be deleted)
        new_state = tmp_path / ".workflow_state_new.json"
        new_state.write_text('{"state": "complete"}')

        # Make old files actually old
        import time

        old_time = time.time() - (25 * 3600)  # 25 hours ago
        import os

        os.utime(old_state, (old_time, old_time))
        os.utime(old_temp, (old_time, old_time))

        # Run cleanup
        cleaned_state, cleaned_dirs = await WorkflowOrchestrator.cleanup_orphaned_files(
            tmp_path, max_age_hours=24
        )

        assert cleaned_state == 1
        assert cleaned_dirs == 1
        assert not old_state.exists()
        assert not old_temp.exists()
        assert new_state.exists()

    @pytest.mark.asyncio
    async def test_sanitize_filename(self, orchestrator):
        """Test filename sanitization."""
        test_cases = [
            ("normal keyword", "normal_keyword"),
            ("keyword/with/slashes", "keyword_with_slashes"),
            ("keyword with  spaces", "keyword_with_spaces"),
            ("UPPERCASE", "uppercase"),
            ("special!@#$%chars", "special_chars"),
        ]

        for input_name, expected in test_cases:
            result = orchestrator._sanitize_filename(input_name)
            assert result == expected

    @pytest.mark.asyncio
    async def test_full_workflow_with_retry(self, orchestrator):
        """Test full workflow with retry logic."""
        mock_findings = Mock(spec=ResearchFindings)
        mock_article = Mock(spec=ArticleOutput)

        # First call fails, second succeeds
        with patch("workflow.run_research_agent") as mock_research:
            mock_research.side_effect = [Exception("Temporary error"), mock_findings]

            with patch(
                "writer_agent.agent.run_writer_agent", return_value=mock_article
            ):
                with patch.object(
                    orchestrator, "save_outputs", return_value=Path("/tmp/out.html")
                ):
                    # Should succeed on retry
                    result = await orchestrator.run_full_workflow("test keyword")

                    assert result == Path("/tmp/out.html")
                    assert mock_research.call_count == 2

    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self, orchestrator, tmp_path):
        """Test workflow state is persisted between operations."""
        orchestrator.output_dir = tmp_path

        # Transition through states
        await orchestrator._transition_state(WorkflowState.RESEARCHING)
        state_file_1 = await orchestrator._save_state()

        await orchestrator._transition_state(
            WorkflowState.RESEARCH_COMPLETE, {"result": "data"}
        )
        state_file_2 = await orchestrator._save_state()

        # Old state file should be deleted
        assert not state_file_1.exists()
        assert state_file_2.exists()

        # Verify latest state
        with open(state_file_2) as f:
            state_data = json.load(f)

        assert state_data["state"] == "research_complete"
        assert state_data["data"]["result"] == "data"
