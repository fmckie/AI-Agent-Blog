"""
Extended tests for workflow.py to improve coverage further.

This module focuses on testing the main execute method and error scenarios.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from workflow import WorkflowOrchestrator, WorkflowState


class TestWorkflowExecute:
    """Test cases for workflow execute method and error handling."""

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
    def mock_research_findings(self):
        """Create mock research findings."""
        return ResearchFindings(
            keyword="test keyword",
            research_summary="Comprehensive test summary",
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
    def mock_article_output(self):
        """Create mock article output."""
        return ArticleOutput(
            title="Test Article Title",
            meta_description="Test meta description for SEO that provides comprehensive information about the topic and meets search engine requirements.",
            focus_keyword="test keyword",
            introduction="Test introduction paragraph that engages readers and provides a comprehensive overview of the topic. This introduction sets the stage for the detailed content that follows, ensuring readers understand what they will learn.",
            main_sections=[
                ArticleSection(
                    heading="Test Section One",
                    content="Test content with sufficient length to meet requirements. This section provides detailed information about the topic, including examples, explanations, and practical insights that readers will find valuable.",
                ),
                ArticleSection(
                    heading="Test Section Two", 
                    content="Additional test content that explores different aspects of the topic. This section builds upon the previous one, offering deeper insights and more advanced concepts for readers to understand.",
                ),
                ArticleSection(
                    heading="Test Section Three",
                    content="Final test section that concludes the main body of the article. This content ties together all the previous sections and prepares readers for the conclusion that follows.",
                ),
            ],
            conclusion="Test conclusion paragraph that summarizes the key points covered in the article and provides actionable takeaways for readers. This conclusion reinforces the main message and encourages further exploration.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.02,
            sources_used=["https://test.edu/paper"],
        )

    @pytest.mark.asyncio
    async def test_execute_full_workflow_success(
        self, mock_config, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test successful execution of full workflow."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent') as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent') as mock_run_writer:
                        # Setup mocks
                        mock_research_agent = Mock()
                        mock_writer_agent = Mock()
                        mock_create_research.return_value = mock_research_agent
                        mock_create_writer.return_value = mock_writer_agent
                        
                        mock_run_research.return_value = mock_research_findings
                        mock_run_writer.return_value = mock_article_output
                        
                        # Execute workflow
                        orchestrator = WorkflowOrchestrator(mock_config)
                        result_dir = await orchestrator.run_full_workflow("test keyword")
                        
                        # Verify results
                        assert result_dir.exists()
                        assert (result_dir / "article.html").exists()
                        assert (result_dir / "research_data.json").exists()
                        assert (result_dir / "metadata.json").exists()
                        
                        # Verify state progression
                        assert orchestrator.current_state == WorkflowState.COMPLETE

    @pytest.mark.asyncio
    async def test_execute_with_research_failure(self, mock_config):
        """Test workflow handling of research failure."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent') as mock_run_research:
                    # Setup mocks
                    mock_create_research.return_value = Mock()
                    mock_create_writer.return_value = Mock()
                    
                    # Make research fail
                    mock_run_research.side_effect = Exception("Research API failed")
                    
                    # Execute workflow
                    orchestrator = WorkflowOrchestrator(mock_config)
                    
                    with pytest.raises(Exception) as exc_info:
                        await orchestrator.run_full_workflow("test keyword")
                    
                    assert "Research API failed" in str(exc_info.value)
                    assert orchestrator.current_state == WorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_execute_with_writing_failure(
        self, mock_config, mock_research_findings
    ):
        """Test workflow handling of writing failure."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent') as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent') as mock_run_writer:
                        # Setup mocks
                        mock_create_research.return_value = Mock()
                        mock_create_writer.return_value = Mock()
                        
                        mock_run_research.return_value = mock_research_findings
                        # Make writing fail
                        mock_run_writer.side_effect = Exception("Writer API failed")
                        
                        # Execute workflow
                        orchestrator = WorkflowOrchestrator(mock_config)
                        
                        with pytest.raises(Exception) as exc_info:
                            await orchestrator.run_full_workflow("test keyword")
                        
                        assert "Writing phase failed" in str(exc_info.value)
                        assert orchestrator.current_state == WorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_execute_with_save_failure(
        self, mock_config, mock_research_findings, mock_article_output
    ):
        """Test workflow handling of save failure."""
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent') as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent') as mock_run_writer:
                        # Setup mocks
                        mock_create_research.return_value = Mock()
                        mock_create_writer.return_value = Mock()
                        
                        mock_run_research.return_value = mock_research_findings
                        mock_run_writer.return_value = mock_article_output
                        
                        # Make save fail
                        with patch.object(
                            WorkflowOrchestrator, 
                            '_save_outputs', 
                            side_effect=Exception("Disk full")
                        ):
                            # Execute workflow
                            orchestrator = WorkflowOrchestrator(mock_config)
                            
                            with pytest.raises(Exception) as exc_info:
                                await orchestrator.run_full_workflow("test keyword")
                            
                            assert "Save phase failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_progress_callback(
        self, mock_config, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test workflow execution with progress callback."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('workflow.run_research_agent') as mock_run_research:
                    with patch('writer_agent.agent.run_writer_agent') as mock_run_writer:
                        # Setup mocks
                        mock_create_research.return_value = Mock()
                        mock_create_writer.return_value = Mock()
                        
                        mock_run_research.return_value = mock_research_findings
                        mock_run_writer.return_value = mock_article_output
                        
                        # Track progress callbacks
                        progress_updates = []
                        def progress_callback(state, message):
                            progress_updates.append((state, message))
                        
                        # Execute workflow
                        orchestrator = WorkflowOrchestrator(mock_config)
                        orchestrator.progress_callback = progress_callback
                        
                        await orchestrator.run_full_workflow("test keyword")
                        
                        # Verify progress updates
                        assert len(progress_updates) > 0
                        states = [update[0] for update in progress_updates]
                        assert "researching" in states
                        assert "writing" in states
                        assert "saving" in states
                        assert "complete" in states

    @pytest.mark.asyncio
    async def test_resume_workflow_from_research_complete(
        self, mock_config, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test resuming workflow from research complete state."""
        mock_config.output_dir = tmp_path
        
        # Create state file
        state_data = {
            "state": WorkflowState.RESEARCH_COMPLETE.value,
            "data": {
                "keyword": "test keyword",
                "research_findings": mock_research_findings.model_dump()
            },
            "timestamp": datetime.now().isoformat()
        }
        state_file = tmp_path / ".workflow_state_test_keyword_20240101_120000.json"
        state_file.write_text(json.dumps(state_data))
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                with patch('writer_agent.agent.run_writer_agent') as mock_run_writer:
                    # Setup mocks
                    mock_create_research.return_value = Mock()
                    mock_create_writer.return_value = Mock()
                    
                    mock_run_writer.return_value = mock_article_output
                    
                    # Execute workflow with resume
                    orchestrator = WorkflowOrchestrator(mock_config)
                    
                    with patch.object(orchestrator, '_find_state_file', return_value=state_file):
                        result_dir = await orchestrator.resume_workflow(state_file)
                    
                    # Verify resumed from correct state
                    assert result_dir.exists()
                    assert orchestrator.current_state == WorkflowState.COMPLETE

    @pytest.mark.asyncio
    async def test_save_outputs_creates_all_files(
        self, mock_config, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test that save_outputs creates all expected files."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Create temp directory
                orchestrator.temp_output_dir = tmp_path / "temp"
                orchestrator.temp_output_dir.mkdir()
                
                # Save outputs
                await orchestrator._save_outputs_atomic(
                    "test keyword",
                    mock_research_findings,
                    mock_article_output
                )
                
                # Verify all files created
                assert (orchestrator.temp_output_dir / "article.html").exists()
                assert (orchestrator.temp_output_dir / "research_data.json").exists()
                assert (orchestrator.temp_output_dir / "metadata.json").exists()
                assert (orchestrator.temp_output_dir / "article_data.json").exists()

    @pytest.mark.asyncio
    async def test_handle_error_with_rollback(self, mock_config, tmp_path):
        """Test error handling with rollback."""
        mock_config.output_dir = tmp_path
        
        with patch('workflow.create_research_agent') as mock_create_research:
            with patch('workflow.create_writer_agent') as mock_create_writer:
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()
                
                orchestrator = WorkflowOrchestrator(mock_config)
                
                # Create temp directory
                orchestrator.temp_output_dir = tmp_path / "temp"
                orchestrator.temp_output_dir.mkdir()
                
                # Handle error
                test_error = Exception("Test error")
                await orchestrator._rollback()
                
                # Verify rollback
                assert orchestrator.current_state == WorkflowState.FAILED
                assert not orchestrator.temp_output_dir.exists()

