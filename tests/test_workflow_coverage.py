"""
Additional tests to improve workflow.py coverage.

This module adds tests for uncovered functionality in workflow.py,
focusing on edge cases and error handling.
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


class TestWorkflowCoverage:
    """Additional test cases to improve workflow coverage."""

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
    def sample_research_findings(self):
        """Create sample research findings."""
        return ResearchFindings(
            keyword="test keyword",
            research_summary="Test summary",
            academic_sources=[
                AcademicSource(
                    title="Test Paper",
                    url="https://test.edu/paper",
                    excerpt="Test excerpt",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            key_statistics=["90% success rate"],
            research_gaps=["More research needed"],
            main_findings=["Key finding 1"],
            total_sources_analyzed=5,
            search_query_used="test keyword",
        )

    @pytest.fixture
    def sample_article_output(self):
        """Create sample article output."""
        return ArticleOutput(
            title="Test Article",
            meta_description="Test meta description",
            focus_keyword="test keyword",
            introduction="Test introduction",
            main_sections=[
                ArticleSection(
                    heading="Test Section",
                    content="Test content with sufficient length to meet requirements.",
                )
            ],
            conclusion="Test conclusion",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.02,
            sources_used=["https://test.edu/paper"],
        )

    @pytest.mark.asyncio
    async def test_workflow_context_manager(self, mock_config):
        """Test workflow orchestrator as async context manager."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                async with WorkflowOrchestrator(mock_config) as orchestrator:
                    assert orchestrator is not None
                    assert orchestrator.current_state == WorkflowState.INITIALIZED

    @pytest.mark.asyncio
    async def test_workflow_cleanup_on_exit(self, mock_config, tmp_path):
        """Test cleanup functionality on context manager exit."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Create temp directory and state file
                orchestrator.temp_output_dir = tmp_path / "temp_dir"
                orchestrator.temp_output_dir.mkdir()
                orchestrator.state_file = tmp_path / "state.json"
                orchestrator.state_file.write_text("{}")
                
                # Exit without completing
                orchestrator.current_state = WorkflowState.RESEARCHING
                
                await orchestrator.__aexit__(None, None, None)
                
                # Verify cleanup
                assert not orchestrator.temp_output_dir.exists()
                assert not orchestrator.state_file.exists()

    @pytest.mark.asyncio
    async def test_workflow_no_cleanup_on_complete(self, mock_config, tmp_path):
        """Test that cleanup doesn't happen for completed workflows."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Create state file
                orchestrator.state_file = tmp_path / "state.json"
                orchestrator.state_file.write_text("{}")
                
                # Mark as complete
                orchestrator.current_state = WorkflowState.COMPLETE
                
                await orchestrator.__aexit__(None, None, None)
                
                # State file should still exist
                assert orchestrator.state_file.exists()

    @pytest.mark.asyncio
    async def test_workflow_cleanup_error_handling(self, mock_config):
        """Test error handling during cleanup."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Mock cleanup to raise error
                orchestrator.temp_output_dir = Mock()
                orchestrator.temp_output_dir.exists.return_value = True
                
                with patch('shutil.rmtree', side_effect=Exception("Cleanup failed")):
                    # Should not raise exception
                    await orchestrator.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_save_workflow_state(self, mock_config, tmp_path):
        """Test saving workflow state."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                orchestrator.workflow_data = {"test": "data"}
                orchestrator.state_file = tmp_path / "test_state.json"
                
                # Save state using internal method
                orchestrator._save_state()
                
                assert orchestrator.state_file.exists()
                saved_data = json.loads(orchestrator.state_file.read_text())
                assert saved_data["state"] == orchestrator.current_state.value
                assert saved_data["data"] == orchestrator.workflow_data

    @pytest.mark.asyncio
    async def test_load_workflow_state(self, mock_config, tmp_path):
        """Test loading workflow state."""
        mock_config.output_dir = tmp_path
        
        # Create state file
        state_data = {
            "state": WorkflowState.RESEARCH_COMPLETE.value,
            "data": {"keyword": "test", "research": "findings"},
            "timestamp": datetime.now().isoformat()
        }
        state_file = tmp_path / ".workflow_state_test_20240101_120000.json"
        state_file.write_text(json.dumps(state_data))
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                loaded = orchestrator._load_state(state_file)
                
                assert loaded == True
                assert orchestrator.current_state == WorkflowState.RESEARCH_COMPLETE
                assert orchestrator.workflow_data["keyword"] == "test"


    @pytest.mark.asyncio
    async def test_update_state(self, mock_config):
        """Test state update functionality."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Test state update
                orchestrator._update_state(WorkflowState.RESEARCHING, {"message": "Starting research"})
                assert orchestrator.current_state == WorkflowState.RESEARCHING
                assert orchestrator.workflow_data["message"] == "Starting research"
                
                # Test progress reporting separately
                callback_called = False
                def progress_callback(phase, message):
                    nonlocal callback_called
                    callback_called = True
                    assert phase == "researching"
                    assert message == "Starting research"
                
                orchestrator.set_progress_callback(progress_callback)
                orchestrator._report_progress("researching", "Starting research")
                assert callback_called

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, mock_config, tmp_path):
        """Test rollback functionality on error."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Create temp directory
                orchestrator.temp_output_dir = tmp_path / "temp"
                orchestrator.temp_output_dir.mkdir()
                test_file = orchestrator.temp_output_dir / "test.txt"
                test_file.write_text("test")
                
                # Perform rollback
                await orchestrator._rollback()
                
                assert orchestrator.current_state == WorkflowState.ROLLED_BACK
                assert not orchestrator.temp_output_dir.exists()

