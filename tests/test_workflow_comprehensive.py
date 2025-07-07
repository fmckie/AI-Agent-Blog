"""
Comprehensive tests for workflow.py to achieve maximum coverage.

This module contains all test cases needed to cover the remaining untested
lines in workflow.py, focusing on edge cases, error handling, and complex scenarios.
"""

import asyncio
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import logging

import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from workflow import WorkflowOrchestrator, WorkflowState


def create_orchestrator_with_mocked_agents(config):
    """Helper function to create orchestrator with mocked agents."""
    with patch('workflow.create_research_agent') as mock_create_research:
        with patch('workflow.create_writer_agent') as mock_create_writer:
            mock_create_research.return_value = Mock()
            mock_create_writer.return_value = Mock()
            return WorkflowOrchestrator(config)


# Create fixtures for commonly used mocks
@pytest.fixture
def mock_config(tmp_path):
    """Create a mock configuration for testing."""
    # Create a mock config object with required attributes
    config = Mock(spec=Config)
    config.output_dir = tmp_path / "output"
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
    config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
    config.max_retries = 3
    config.google_drive_upload_folder_id = "test-folder-id"
    config.llm_model = "gpt-4"
    config.temperature = 0.7
    config.max_tokens = 4000
    config.request_timeout = 30
    config.enable_cache = True
    config.cache_expiration_days = 7
    config.log_level = "INFO"
    config.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    return config


@pytest.fixture
def mock_research_findings():
    """Create mock research findings for testing."""
    # Create research findings with all required fields
    return ResearchFindings(
        keyword="test keyword",
        research_summary="Comprehensive test summary of research findings",
        academic_sources=[
            AcademicSource(
                title="Test Research Paper 1",
                url="https://test.edu/paper1",
                excerpt="Important findings from paper 1",
                domain=".edu",
                credibility_score=0.95,
            ),
            AcademicSource(
                title="Test Research Paper 2",
                url="https://test.edu/paper2",
                excerpt="Key insights from paper 2",
                domain=".edu",
                credibility_score=0.90,
            ),
            AcademicSource(
                title="Test Research Paper 3",
                url="https://test.org/paper3",
                excerpt="Supporting evidence from paper 3",
                domain=".org",
                credibility_score=0.85,
            ),
        ],
        key_statistics=["90% success rate", "150 participants studied"],
        research_gaps=["More longitudinal studies needed", "Limited geographic diversity"],
        main_findings=["Finding 1: Significant correlation", "Finding 2: Novel approach"],
        total_sources_analyzed=10,
        search_query_used="test keyword academic research",
    )


@pytest.fixture
def mock_article_output():
    """Create mock article output for testing."""
    # Create article output with sufficient content
    return ArticleOutput(
        title="Comprehensive Guide to Test Keyword: Latest Research and Insights",
        meta_description="Discover the latest research on test keyword with evidence-based insights, statistics, and expert analysis. Learn about key findings and practical applications.",
        focus_keyword="test keyword",
        introduction="This comprehensive guide explores the latest research on test keyword, providing evidence-based insights and practical applications. Based on analysis of multiple academic sources, we present key findings that advance our understanding of this important topic.",
        main_sections=[
            ArticleSection(
                heading="Understanding Test Keyword: Core Concepts",
                content="Test keyword represents a fundamental concept in modern research. Recent studies have shown significant developments in this area, with researchers from leading institutions contributing valuable insights. The evolution of test keyword has been marked by several key milestones that have shaped our current understanding.",
            ),
            ArticleSection(
                heading="Latest Research Findings and Evidence",
                content="Recent peer-reviewed studies have revealed important findings about test keyword. A comprehensive analysis of over 150 participants showed a 90% success rate when applying these principles. These findings have significant implications for both theoretical understanding and practical applications in the field.",
            ),
            ArticleSection(
                heading="Practical Applications and Future Directions",
                content="The practical applications of test keyword extend across multiple domains. Industry leaders have successfully implemented these concepts, resulting in measurable improvements. Future research directions include exploring longitudinal effects and expanding geographic diversity in study populations.",
            ),
        ],
        conclusion="The research on test keyword continues to evolve, offering valuable insights for researchers and practitioners alike. The evidence presented demonstrates the importance of continued investigation while highlighting practical applications that can be implemented today. As the field advances, we can expect further breakthroughs that will enhance our understanding.",
        word_count=1500,
        reading_time_minutes=6,
        keyword_density=0.025,
        sources_used=[
            "https://test.edu/paper1",
            "https://test.edu/paper2",
            "https://test.org/paper3"
        ],
    )


class TestWorkflowContextManager:
    """Test context manager functionality and cleanup operations."""

    @pytest.mark.asyncio
    async def test_context_manager_normal_exit(self, mock_config):
        """Test context manager normal exit without errors."""
        # Test normal context manager usage
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                async with WorkflowOrchestrator(mock_config) as orchestrator:
                    assert orchestrator is not None
                    assert isinstance(orchestrator, WorkflowOrchestrator)
                
                # Verify no exceptions were raised
                assert True

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self, mock_config):
        """Test context manager cleanup when exception occurs."""
        # Create orchestrator and set up temp directory
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                temp_dir = mock_config.output_dir / ".temp_test_123"
                temp_dir.mkdir(parents=True, exist_ok=True)
                orchestrator.temp_output_dir = temp_dir
                
                # Create state file
                state_file = mock_config.output_dir / ".workflow_state_test.json"
                state_file.write_text('{"state": "initialized"}')
                orchestrator.state_file = state_file
                orchestrator.current_state = WorkflowState.RESEARCHING
                
                # Test cleanup on exception
                with pytest.raises(ValueError):
                    async with orchestrator:
                        raise ValueError("Test exception")
                
                # Verify cleanup occurred
                assert not temp_dir.exists()
                assert not state_file.exists()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_error_handling(self, mock_config):
        """Test context manager handles errors during cleanup."""
        # Create orchestrator with problematic cleanup
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                
                # Create temp directory that will fail to delete
                temp_dir = mock_config.output_dir / ".temp_test_456"
                temp_dir.mkdir(parents=True, exist_ok=True)
                orchestrator.temp_output_dir = temp_dir
                
                # Mock shutil.rmtree to raise an exception
                with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
                    # Should not raise exception even if cleanup fails
                    async with orchestrator:
                        pass
                
                # Directory still exists due to failed cleanup
                assert temp_dir.exists()
                # Clean up manually
                shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_context_manager_no_cleanup_on_complete(self, mock_config):
        """Test no cleanup occurs when workflow completes successfully."""
        # Create orchestrator
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                
                # Set state to complete
                orchestrator.current_state = WorkflowState.COMPLETE
                
                # Create state file that should not be cleaned up
                state_file = mock_config.output_dir / ".workflow_state_complete.json"
                state_file.write_text('{"state": "complete"}')
                orchestrator.state_file = state_file
                
                # Exit context manager
                async with orchestrator:
                    pass
                
                # State file should still exist (no cleanup for completed workflows)
                assert state_file.exists()
                # Clean up manually
                state_file.unlink()


class TestOrphanedFileCleanup:
    """Test cleanup of orphaned state files and temp directories."""

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files_old_files(self, mock_config):
        """Test cleanup of old orphaned files."""
        # Create old state files and temp directories
        output_dir = mock_config.output_dir
        current_time = datetime.now()
        old_time = current_time - timedelta(hours=25)
        
        # Create old state file
        old_state_file = output_dir / ".workflow_state_old_123.json"
        old_state_file.write_text('{"state": "failed"}')
        # Set modification time to 25 hours ago
        import os
        old_timestamp = old_time.timestamp()
        os.utime(old_state_file, (old_timestamp, old_timestamp))
        
        # Create old temp directory
        old_temp_dir = output_dir / ".temp_old_456"
        old_temp_dir.mkdir(parents=True, exist_ok=True)
        os.utime(old_temp_dir, (old_timestamp, old_timestamp))
        
        # Create recent files that should not be cleaned
        recent_state_file = output_dir / ".workflow_state_recent_789.json"
        recent_state_file.write_text('{"state": "running"}')
        recent_temp_dir = output_dir / ".temp_recent_012"
        recent_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Run cleanup
        cleaned_states, cleaned_dirs = await WorkflowOrchestrator.cleanup_orphaned_files(
            output_dir, older_than_hours=24
        )
        
        # Verify old files were cleaned
        assert cleaned_states == 1
        assert cleaned_dirs == 1
        assert not old_state_file.exists()
        assert not old_temp_dir.exists()
        
        # Verify recent files were not cleaned
        assert recent_state_file.exists()
        assert recent_temp_dir.exists()
        
        # Clean up remaining files
        recent_state_file.unlink()
        shutil.rmtree(recent_temp_dir)

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files_error_handling(self, mock_config):
        """Test cleanup handles errors gracefully."""
        # Create a state file
        output_dir = mock_config.output_dir
        state_file = output_dir / ".workflow_state_test.json"
        state_file.write_text('{"state": "failed"}')
        
        # Mock file operations to raise exceptions
        with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
            cleaned_states, cleaned_dirs = await WorkflowOrchestrator.cleanup_orphaned_files(
                output_dir, older_than_hours=1
            )
        
        # Should return 0 for both due to errors
        assert cleaned_states == 0
        assert cleaned_dirs == 0
        
        # File should still exist
        assert state_file.exists()
        state_file.unlink()

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files_nonexistent_dir(self, mock_config):
        """Test cleanup with non-existent directory."""
        # Try to clean up non-existent directory
        fake_dir = Path("/nonexistent/directory")
        
        # Should handle gracefully
        cleaned_states, cleaned_dirs = await WorkflowOrchestrator.cleanup_orphaned_files(
            fake_dir, older_than_hours=24
        )
        
        assert cleaned_states == 0
        assert cleaned_dirs == 0


class TestResumeWorkflow:
    """Test workflow resume functionality from various states."""

    @pytest.mark.asyncio
    async def test_resume_from_researching_state(self, mock_config, mock_research_findings, mock_article_output):
        """Test resuming workflow from RESEARCHING state."""
        # Create state file with researching state
        state_data = {
            "state": WorkflowState.RESEARCHING.value,
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "test keyword"},
            "temp_dir": None
        }
        state_file = mock_config.output_dir / ".workflow_state_test.json"
        state_file.write_text(json.dumps(state_data))
        
        # Mock the agent creation and execution
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings) as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output) as mock_run_writer:
                        # Mock Drive functionality
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            mock_rag_config.return_value.google_drive_enabled = False
                            
                            # Create orchestrator and resume
                            orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                            
                            # Mock the atomic save to avoid temp_output_dir issues
                            mock_output_path = mock_config.output_dir / "test_output" / "index.html"
                            mock_output_path.parent.mkdir(parents=True, exist_ok=True)
                            mock_output_path.write_text("<html>Test</html>")
                            
                            with patch.object(orchestrator, '_save_outputs_atomic', return_value=mock_output_path):
                                result_path = await orchestrator.resume_workflow(state_file)
                            
                            # Verify workflow completed
                            assert orchestrator.current_state == WorkflowState.COMPLETE
                            assert result_path.exists()
                            assert mock_run_research.called
                            assert mock_run_writer.called

    @pytest.mark.asyncio
    async def test_resume_from_writing_state(self, mock_config, mock_research_findings, mock_article_output):
        """Test resuming workflow from WRITING state."""
        # Create state file with writing state
        state_data = {
            "state": WorkflowState.WRITING.value,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "keyword": "test keyword",
                "research_complete_time": datetime.now().isoformat(),
                "sources_found": 3
            },
            "temp_dir": None
        }
        state_file = mock_config.output_dir / ".workflow_state_test.json"
        state_file.write_text(json.dumps(state_data))
        
        # Mock the agent creation and execution
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings) as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output) as mock_run_writer:
                        # Mock Drive functionality
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            mock_rag_config.return_value.google_drive_enabled = False
                            
                            # Create orchestrator and resume
                            orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                            
                            # Mock the atomic save to avoid temp_output_dir issues
                            mock_output_path = mock_config.output_dir / "test_output2" / "index.html"
                            mock_output_path.parent.mkdir(parents=True, exist_ok=True)
                            mock_output_path.write_text("<html>Test</html>")
                            
                            with patch.object(orchestrator, '_save_outputs_atomic', return_value=mock_output_path):
                                result_path = await orchestrator.resume_workflow(state_file)
                            
                            # Verify workflow completed
                            assert orchestrator.current_state == WorkflowState.COMPLETE
                            assert result_path.exists()
                            # Both agents should be called since we need to re-run from writing state
                            assert mock_run_research.called
                            assert mock_run_writer.called

    @pytest.mark.asyncio
    async def test_resume_from_saving_state(self, mock_config, mock_research_findings, mock_article_output):
        """Test resuming workflow from SAVING state."""
        # Create state file with saving state
        state_data = {
            "state": WorkflowState.SAVING.value,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "keyword": "test keyword",
                "research_complete_time": datetime.now().isoformat(),
                "writing_complete_time": datetime.now().isoformat(),
                "word_count": 1500
            },
            "temp_dir": str(mock_config.output_dir / ".temp_test")
        }
        state_file = mock_config.output_dir / ".workflow_state_test.json"
        state_file.write_text(json.dumps(state_data))
        
        # Create temp directory
        temp_dir = Path(state_data["temp_dir"])
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the agent creation and execution
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings) as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output) as mock_run_writer:
                        # Mock Drive functionality
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            mock_rag_config.return_value.google_drive_enabled = False
                            
                            # Create orchestrator and resume
                            orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                            result_path = await orchestrator.resume_workflow(state_file)
                            
                            # Verify workflow completed
                            assert orchestrator.current_state == WorkflowState.COMPLETE
                            assert result_path.exists()
                            # All steps need to be re-run from saving state
                            assert mock_run_research.called
                            assert mock_run_writer.called

    @pytest.mark.asyncio
    async def test_resume_with_invalid_state(self, mock_config):
        """Test resume with invalid workflow state."""
        # Create state file with invalid state
        state_data = {
            "state": "invalid_state",
            "timestamp": datetime.now().isoformat(),
            "data": {"keyword": "test keyword"}
        }
        state_file = mock_config.output_dir / ".workflow_state_test.json"
        state_file.write_text(json.dumps(state_data))
        
        # Create orchestrator and attempt resume
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                
                # Should raise ValueError for invalid state
                with pytest.raises(ValueError):
                    await orchestrator.resume_workflow(state_file)

    @pytest.mark.asyncio
    async def test_resume_with_missing_keyword(self, mock_config):
        """Test resume with missing keyword in state."""
        # Create state file without keyword
        state_data = {
            "state": WorkflowState.RESEARCHING.value,
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        state_file = mock_config.output_dir / ".workflow_state_test.json"
        state_file.write_text(json.dumps(state_data))
        
        # Create orchestrator and attempt resume
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                
                # Should raise ValueError for missing keyword
                with pytest.raises(ValueError) as exc_info:
                    await orchestrator.resume_workflow(state_file)
                
                assert "No keyword found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resume_nonexistent_state_file(self, mock_config):
        """Test resume with non-existent state file."""
        # Try to resume with non-existent file
        fake_state_file = mock_config.output_dir / "nonexistent.json"
        
        # Create orchestrator and attempt resume
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                
                # Should raise ValueError
                with pytest.raises(ValueError) as exc_info:
                    await orchestrator.resume_workflow(fake_state_file)
                
                assert "Failed to load workflow state" in str(exc_info.value)


class TestGoogleDriveUpload:
    """Test Google Drive upload functionality."""

    @pytest.mark.asyncio
    async def test_drive_upload_success(self, mock_config, mock_article_output):
        """Test successful Google Drive upload."""
        # Create article file
        article_path = mock_config.output_dir / "article.html"
        article_path.write_text("<html><body>Test Article</body></html>")
        
        # Mock Drive components
        with patch('workflow.get_rag_config') as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True
            
            with patch('workflow.GoogleDriveAuth') as mock_drive_auth:
                with patch('workflow.ArticleUploader') as mock_uploader_class:
                    with patch('workflow.DriveStorageHandler') as mock_storage:
                        # Configure upload mock
                        mock_uploader = Mock()
                        mock_uploader_class.return_value = mock_uploader
                        mock_uploader.upload_html_as_doc.return_value = {
                            "file_id": "test-file-id",
                            "web_link": "https://docs.google.com/document/d/test-file-id",
                            "name": "Test Article"
                        }
                        
                        # Create orchestrator and test upload
                        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                        result = await orchestrator._upload_to_drive(
                            article_path, mock_article_output, "test keyword"
                        )
                        
                        # Verify success
                        assert result is not None
                        assert result["file_id"] == "test-file-id"
                        assert "web_link" in result
                        assert mock_uploader.upload_html_as_doc.called

    @pytest.mark.asyncio
    async def test_drive_upload_disabled(self, mock_config, mock_article_output):
        """Test Drive upload when disabled in config."""
        # Create article file
        article_path = mock_config.output_dir / "article.html"
        article_path.write_text("<html><body>Test Article</body></html>")
        
        # Mock Drive config as disabled
        with patch('workflow.get_rag_config') as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = False
            
            # Create orchestrator and test upload
            orchestrator = create_orchestrator_with_mocked_agents(mock_config)
            result = await orchestrator._upload_to_drive(
                article_path, mock_article_output, "test keyword"
            )
            
            # Should return None when disabled
            assert result is None

    @pytest.mark.asyncio
    async def test_drive_upload_missing_folder_id(self, mock_config, mock_article_output):
        """Test Drive upload with missing folder ID."""
        # Create article file
        article_path = mock_config.output_dir / "article.html"
        article_path.write_text("<html><body>Test Article</body></html>")
        
        # Remove folder ID from config
        mock_config.google_drive_upload_folder_id = None
        
        # Mock Drive config as enabled
        with patch('workflow.get_rag_config') as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True
            
            # Create orchestrator and test upload
            orchestrator = create_orchestrator_with_mocked_agents(mock_config)
            result = await orchestrator._upload_to_drive(
                article_path, mock_article_output, "test keyword"
            )
            
            # Should return None when folder ID missing
            assert result is None

    @pytest.mark.asyncio
    async def test_drive_upload_auth_failure(self, mock_config, mock_article_output):
        """Test Drive upload with authentication failure."""
        # Create article file
        article_path = mock_config.output_dir / "article.html"
        article_path.write_text("<html><body>Test Article</body></html>")
        
        # Mock Drive components with auth failure
        with patch('workflow.get_rag_config') as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True
            
            with patch('workflow.GoogleDriveAuth', side_effect=Exception("Auth failed")):
                # Create orchestrator and test upload
                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                result = await orchestrator._upload_to_drive(
                    article_path, mock_article_output, "test keyword"
                )
                
                # Should return None on auth failure
                assert result is None

    @pytest.mark.asyncio
    async def test_drive_upload_api_failure(self, mock_config, mock_article_output):
        """Test Drive upload with API failure."""
        # Create article file
        article_path = mock_config.output_dir / "article.html"
        article_path.write_text("<html><body>Test Article</body></html>")
        
        # Mock Drive components
        with patch('workflow.get_rag_config') as mock_rag_config:
            mock_rag_config.return_value.google_drive_enabled = True
            mock_rag_config.return_value.google_drive_auto_upload = True
            
            with patch('workflow.GoogleDriveAuth') as mock_drive_auth:
                with patch('workflow.ArticleUploader') as mock_uploader_class:
                    with patch('workflow.DriveStorageHandler') as mock_storage:
                        # Configure upload to fail
                        mock_uploader = Mock()
                        mock_uploader_class.return_value = mock_uploader
                        mock_uploader.upload_html_as_doc.side_effect = Exception("API error")
                        
                        # Create orchestrator and test upload
                        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                        result = await orchestrator._upload_to_drive(
                            article_path, mock_article_output, "test keyword"
                        )
                        
                        # Should return None on API failure
                        assert result is None


class TestEdgeCasesAndValidation:
    """Test edge cases and input validation."""

    @pytest.mark.asyncio
    async def test_empty_keyword_validation(self, mock_config):
        """Test validation of empty keyword."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Test empty string
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.run_full_workflow("")
        assert "Keyword cannot be empty" in str(exc_info.value)
        
        # Test whitespace only
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.run_full_workflow("   ")
        assert "Keyword cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_long_keyword_validation(self, mock_config):
        """Test validation of overly long keyword."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Create keyword longer than 200 characters
        long_keyword = "a" * 201
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.run_full_workflow(long_keyword)
        assert "Keyword too long" in str(exc_info.value)
        assert "201" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_state_save_error_handling(self, mock_config):
        """Test error handling during state save."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Set up state file that will fail to write
        orchestrator.state_file = mock_config.output_dir / "readonly" / "state.json"
        orchestrator.current_state = WorkflowState.RESEARCHING
        orchestrator.workflow_data = {"keyword": "test"}
        
        # Mock logger to verify warning
        with patch('workflow.logger') as mock_logger:
            # Try to save state (should fail but not raise)
            orchestrator._save_state()
            
            # Verify warning was logged
            mock_logger.warning.assert_called()
            assert "Failed to save workflow state" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_state_load_error_handling(self, mock_config):
        """Test error handling during state load."""
        # Create corrupted state file
        state_file = mock_config.output_dir / "corrupted_state.json"
        state_file.write_text("{ invalid json")
        
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Try to load corrupted state
        result = orchestrator._load_state(state_file)
        
        # Should return False on failure
        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_error_handling(self, mock_config):
        """Test error handling during rollback."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Set up state that will fail during rollback
        orchestrator.temp_output_dir = Path("/nonexistent/path")
        orchestrator.state_file = Path("/nonexistent/state.json")
        
        # Perform rollback (should handle errors gracefully)
        await orchestrator._rollback()
        
        # Verify state changed to rolled back
        assert orchestrator.current_state == WorkflowState.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, mock_config, mock_research_findings, mock_article_output):
        """Test concurrent workflow execution handling."""
        # Mock the agent creation and execution
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings):
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output):
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            mock_rag_config.return_value.google_drive_enabled = False
                            
                            # Create multiple orchestrators
                            keywords = ["keyword1", "keyword2", "keyword3"]
                            tasks = []
                            
                            # Start concurrent workflows
                            for keyword in keywords:
                                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                                task = asyncio.create_task(orchestrator.run_full_workflow(keyword))
                                tasks.append(task)
                            
                            # Wait for all to complete
                            results = await asyncio.gather(*tasks)
                            
                            # Verify all completed successfully
                            assert len(results) == 3
                            for result in results:
                                assert result.exists()

    @pytest.mark.asyncio
    async def test_atomic_save_failure(self, mock_config, mock_research_findings, mock_article_output):
        """Test atomic save operation failure handling."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Create temp directory
        orchestrator.temp_output_dir = mock_config.output_dir / "temp"
        orchestrator.temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock shutil.move to fail
        with patch('shutil.move', side_effect=OSError("Disk full")):
            # Try atomic save
            with pytest.raises(OSError):
                await orchestrator._save_outputs_atomic(
                    "test keyword", mock_research_findings, mock_article_output
                )

    @pytest.mark.asyncio
    async def test_progress_callback_functionality(self, mock_config):
        """Test progress callback is called correctly."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(phase, message):
            progress_updates.append((phase, message))
        
        # Set callback
        orchestrator.set_progress_callback(progress_callback)
        
        # Test progress reporting
        orchestrator._report_progress("test_phase", "Test message")
        
        # Verify callback was called
        assert len(progress_updates) == 1
        assert progress_updates[0] == ("test_phase", "Test message")

    @pytest.mark.asyncio
    async def test_save_outputs_special_characters(self, mock_config, mock_research_findings, mock_article_output):
        """Test save outputs with special characters in keyword."""
        # Create orchestrator
        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
        
        # Test with special characters
        special_keyword = "test/keyword\\with*special?chars<>|"
        
        # Save outputs
        result_path = await orchestrator.save_outputs(
            special_keyword, mock_research_findings, mock_article_output
        )
        
        # Verify path was created with sanitized name
        assert result_path.exists()
        assert "/" not in result_path.parent.name
        assert "\\" not in result_path.parent.name
        assert "*" not in result_path.parent.name


class TestDriveUploadIntegration:
    """Test Google Drive upload integration in full workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_drive_upload(self, mock_config, mock_research_findings, mock_article_output):
        """Test full workflow with successful Drive upload."""
        # Mock all components
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings):
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output):
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            # Enable Drive upload
                            mock_rag_config.return_value.google_drive_enabled = True
                            mock_rag_config.return_value.google_drive_auto_upload = True
                            
                            with patch('workflow.GoogleDriveAuth'):
                                with patch('workflow.ArticleUploader') as mock_uploader_class:
                                    with patch('workflow.DriveStorageHandler'):
                                        # Configure successful upload
                                        mock_uploader = Mock()
                                        mock_uploader_class.return_value = mock_uploader
                                        mock_uploader.upload_html_as_doc.return_value = {
                                            "file_id": "test-file-id",
                                            "web_link": "https://docs.google.com/document/d/test-file-id",
                                            "name": "Test Article"
                                        }
                                        
                                        # Run workflow
                                        orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                                        result_path = await orchestrator.run_full_workflow("test keyword")
                                        
                                        # Verify workflow completed with Drive upload
                                        assert result_path.exists()
                                        assert orchestrator.workflow_data.get("drive_uploaded") is True
                                        assert orchestrator.workflow_data.get("drive_web_link") is not None

    @pytest.mark.asyncio
    async def test_workflow_continues_on_drive_failure(self, mock_config, mock_research_findings, mock_article_output):
        """Test workflow continues even if Drive upload fails."""
        # Mock all components
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent', return_value=mock_research_findings):
                    with patch('writer_agent.agent.run_writer_agent', return_value=mock_article_output):
                        with patch('workflow.get_rag_config') as mock_rag_config:
                            # Enable Drive upload
                            mock_rag_config.return_value.google_drive_enabled = True
                            mock_rag_config.return_value.google_drive_auto_upload = True
                            
                            # Make Drive auth fail
                            with patch('workflow.GoogleDriveAuth', side_effect=Exception("Auth failed")):
                                # Run workflow
                                orchestrator = create_orchestrator_with_mocked_agents(mock_config)
                                result_path = await orchestrator.run_full_workflow("test keyword")
                                
                                # Verify workflow completed despite Drive failure
                                assert result_path.exists()
                                assert orchestrator.current_state == WorkflowState.COMPLETE
                                assert orchestrator.workflow_data.get("drive_uploaded") is False


class TestWorkflowUniqueFeatures:
    """Unique tests merged from other workflow test files."""

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create orchestrator for testing."""
        return WorkflowOrchestrator(mock_config)

    # From test_workflow.py
    @pytest.mark.asyncio
    async def test_run_research_minimum_sources_warning(self, orchestrator, caplog):
        """Test warning when minimum sources aren't found."""
        # Mock research agent to return fewer sources than minimum
        mock_result = Mock()
        mock_result.sources = [
            {"title": "Source 1", "url": "http://example.com", "credibility": 0.9}
        ]
        orchestrator.research_agent.run = AsyncMock(return_value=mock_result)
        
        with caplog.at_level("WARNING"):
            await orchestrator._run_research("test keyword")
            
        assert "Found only 1 sources, which is below the recommended minimum" in caplog.text

    def test_add_styling_to_html(self, orchestrator):
        """Test HTML styling functionality."""
        html_content = "<html><head></head><body><h1>Test</h1></body></html>"
        styled_html = orchestrator._add_styling_to_html(html_content)
        
        assert "<style>" in styled_html
        assert "font-family" in styled_html
        assert "max-width" in styled_html
        assert "<h1>Test</h1>" in styled_html

    def test_create_review_interface(self, orchestrator):
        """Test review interface creation."""
        content = "Test article content"
        sources = [
            {"title": "Source 1", "url": "http://example.com", "snippet": "Test snippet"}
        ]
        
        review_html = orchestrator._create_review_interface(content, sources)
        
        assert "Review Interface" in review_html
        assert "Test article content" in review_html
        assert "Source 1" in review_html
        assert "http://example.com" in review_html

    @pytest.mark.asyncio
    async def test_workflow_with_unicode_keyword(self, mock_config, tmp_path):
        """Test workflow with unicode characters in keyword."""
        mock_config.output_dir = tmp_path
        
        orchestrator = WorkflowOrchestrator(mock_config)
        orchestrator.research_agent.run = AsyncMock(
            return_value=Mock(
                sources=[{"title": "Test", "url": "http://test.com"}],
                findings=["Finding with émojis 🚀"]
            )
        )
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content="<html><body>Contenu français</body></html>")
        )
        
        result = await orchestrator.run_full_workflow("café français 🥐")
        
        assert result is not None
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Contenu français" in content

    @pytest.mark.asyncio
    async def test_workflow_performance_benchmark(self, mock_config, tmp_path):
        """Test workflow performance stays within acceptable bounds."""
        mock_config.output_dir = tmp_path
        
        orchestrator = WorkflowOrchestrator(mock_config)
        # Mock fast responses
        orchestrator.research_agent.run = AsyncMock(
            return_value=Mock(sources=[{"title": "Test"}], findings=["Finding"])
        )
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content="<html><body>Test</body></html>")
        )
        
        start_time = time.time()
        await orchestrator.run_full_workflow("test keyword")
        elapsed_time = time.time() - start_time
        
        # Workflow should complete in reasonable time (adjust as needed)
        assert elapsed_time < 5.0, f"Workflow took {elapsed_time}s, expected < 5s"

    @pytest.mark.asyncio
    async def test_workflow_large_content_handling(self, mock_config, tmp_path):
        """Test workflow handles large content gracefully."""
        mock_config.output_dir = tmp_path
        
        orchestrator = WorkflowOrchestrator(mock_config)
        # Create large content
        large_content = "Large content. " * 10000  # ~140KB of text
        
        orchestrator.research_agent.run = AsyncMock(
            return_value=Mock(
                sources=[{"title": f"Source {i}"} for i in range(50)],
                findings=[f"Finding {i}" for i in range(100)]
            )
        )
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content=f"<html><body>{large_content}</body></html>")
        )
        
        result = await orchestrator.run_full_workflow("test keyword")
        
        assert result is not None
        assert result.exists()
        # Check file size is reasonable
        file_size = result.stat().st_size
        assert file_size > 100000  # Should be > 100KB
        assert file_size < 10000000  # But < 10MB

    # From test_workflow_transactions.py
    @pytest.mark.asyncio  
    async def test_atomic_save_operations(self, mock_config, tmp_path):
        """Test that save operations are atomic."""
        mock_config.output_dir = tmp_path
        orchestrator = WorkflowOrchestrator(mock_config)
        
        # Set up workflow state
        orchestrator.current_state = WorkflowState.SAVING
        orchestrator.keyword = "test"
        orchestrator.research_result = Mock(sources=[], findings=[])
        orchestrator.article_content = "<html><body>Test</body></html>"
        
        # Mock file write to fail partway through
        original_write = Path.write_text
        write_count = 0
        
        def failing_write(self, *args, **kwargs):
            nonlocal write_count
            write_count += 1
            if write_count == 2:  # Fail on second write
                raise IOError("Simulated write failure")
            return original_write(self, *args, **kwargs)
        
        with patch.object(Path, 'write_text', failing_write):
            with pytest.raises(IOError):
                await orchestrator._save_output("test content", tmp_path / "test.html")
        
        # Verify no partial files remain
        assert not (tmp_path / "test.html").exists()
        assert write_count >= 2  # Ensure we tried multiple writes

    @pytest.mark.asyncio
    async def test_resume_cleans_up_on_success(self, mock_config, tmp_path):
        """Test that successful resume cleans up state file."""
        mock_config.output_dir = tmp_path
        orchestrator = WorkflowOrchestrator(mock_config)
        
        # Create state file
        state_file = tmp_path / f".workflow_state_{orchestrator.session_id}.json"
        state_data = {
            "state": WorkflowState.WRITING.value,
            "keyword": "test",
            "research_result": {"sources": [], "findings": []},
            "session_id": orchestrator.session_id
        }
        state_file.write_text(json.dumps(state_data))
        
        # Mock writer to succeed
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content="<html><body>Test</body></html>")
        )
        
        # Resume workflow
        result = await orchestrator.resume_workflow()
        
        assert result is not None
        assert not state_file.exists()  # State file should be cleaned up

    @pytest.mark.asyncio
    async def test_workflow_reports_progress(self, mock_config, tmp_path):
        """Test full workflow progress reporting."""
        mock_config.output_dir = tmp_path
        orchestrator = WorkflowOrchestrator(mock_config)
        
        progress_updates = []
        
        def capture_progress(state, message, details=None):
            progress_updates.append({
                "state": state,
                "message": message,
                "details": details
            })
        
        orchestrator.set_progress_callback(capture_progress)
        
        # Mock agents
        orchestrator.research_agent.run = AsyncMock(
            return_value=Mock(sources=[{"title": "Test"}], findings=["Finding"])
        )
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content="<html><body>Test</body></html>")
        )
        
        await orchestrator.run_full_workflow("test keyword")
        
        # Verify all workflow states were reported
        states_reported = [update["state"] for update in progress_updates]
        assert WorkflowState.INITIALIZING in states_reported
        assert WorkflowState.RESEARCHING in states_reported
        assert WorkflowState.WRITING in states_reported
        assert WorkflowState.SAVING in states_reported
        assert WorkflowState.COMPLETED in states_reported

    # From test_workflow_extended.py
    def test_sanitize_filename(self, orchestrator):
        """Test filename sanitization for various inputs."""
        test_cases = [
            ("normal keyword", "normal_keyword"),
            ("keyword/with/slashes", "keyword_with_slashes"),
            ("keyword:with:colons", "keyword_with_colons"),
            ("keyword|with|pipes", "keyword_with_pipes"),
            ("keyword<>with<>brackets", "keyword_with_brackets"),
            ("keyword?with?questions", "keyword_with_questions"),
            ("keyword*with*asterisks", "keyword_with_asterisks"),
            ("keyword\\with\\backslashes", "keyword_with_backslashes"),
            ("keyword\"with\"quotes", "keyword_with_quotes"),
            ("   spaces   around   ", "spaces_around"),
            ("🚀 emoji keyword 🎉", "emoji_keyword"),
        ]
        
        for input_keyword, expected_base in test_cases:
            result = orchestrator._sanitize_filename(input_keyword)
            assert expected_base in result
            assert result.endswith(".html")

    @pytest.mark.asyncio
    async def test_full_workflow_with_retry(self, mock_config, tmp_path):
        """Test full workflow with retry logic."""
        mock_config.output_dir = tmp_path
        mock_config.max_retries = 3
        
        orchestrator = WorkflowOrchestrator(mock_config)
        
        # Mock research to fail twice then succeed
        call_count = 0
        
        async def research_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return Mock(sources=[{"title": "Test"}], findings=["Finding"])
        
        orchestrator.research_agent.run = AsyncMock(side_effect=research_with_retry)
        orchestrator.writer_agent.run = AsyncMock(
            return_value=Mock(content="<html><body>Test</body></html>")
        )
        
        result = await orchestrator.run_full_workflow("test keyword")
        
        assert result is not None
        assert call_count == 3  # Failed twice, succeeded on third try


if __name__ == "__main__":
    pytest.main([__file__, "-v"])