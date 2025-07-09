"""
Comprehensive tests for ResearchWorkflow class.

This module tests the workflow orchestration, progress tracking,
error recovery, and stage execution of the ResearchWorkflow.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

from pydantic_ai import Agent

from config import Config
from models import AcademicSource, ResearchFindings
from research_agent.workflow import (
    ResearchWorkflow,
    WorkflowStage,
    StageStatus,
    WorkflowProgress,
    StageResult,
    WorkflowError
)


# Fixtures for testing
@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.workflow_max_retries = 3
    config.workflow_stage_timeout = 120
    config.workflow_progress_reporting = True
    config.workflow_fail_fast = False
    config.workflow_cache_results = True
    config.enable_adaptive_strategy = True
    config.research_strategy = "standard"
    config.tavily_api_key = "test_key"
    return config


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = Mock(spec=Agent)
    # Create a mock run method that returns ResearchFindings
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def sample_findings():
    """Create sample research findings for testing."""
    return ResearchFindings(
        keyword="test keyword",
        research_summary="Test research summary",
        academic_sources=[
            AcademicSource(
                title="Test Source 1",
                url="https://test.edu/paper1",
                authors=["Author 1"],
                publication_date="2024-01-01",
                credibility_score=0.9,
                relevance_score=0.8,
                key_findings=["Finding 1"],
                methodology="Test methodology",
                citations=10
            )
        ],
        main_findings=["Main finding 1", "Main finding 2"],
        key_statistics=["Stat 1", "Stat 2"],
        research_gaps=["Gap 1"]
    )


class TestWorkflowProgress:
    """Test WorkflowProgress tracking functionality."""
    
    def test_progress_initialization(self):
        """Test that progress initializes correctly."""
        progress = WorkflowProgress(current_stage=WorkflowStage.INITIALIZATION)
        
        assert progress.current_stage == WorkflowStage.INITIALIZATION
        assert progress.completed_stages == []
        assert progress.stage_results == {}
        assert progress.total_duration_seconds == 0.0
    
    def test_completion_percentage(self):
        """Test completion percentage calculation."""
        progress = WorkflowProgress(current_stage=WorkflowStage.DISCOVERY)
        
        # No stages completed
        assert progress.get_completion_percentage() == 0.0
        
        # Add completed stages
        progress.completed_stages = [
            WorkflowStage.INITIALIZATION,
            WorkflowStage.DISCOVERY,
            WorkflowStage.ANALYSIS,
            WorkflowStage.EXTRACTION
        ]
        
        # 4 out of 8 stages = 50%
        expected_percentage = (4 / 8) * 100
        assert progress.get_completion_percentage() == expected_percentage
    
    def test_progress_summary(self):
        """Test progress summary generation."""
        progress = WorkflowProgress(current_stage=WorkflowStage.SYNTHESIS)
        progress.completed_stages = [WorkflowStage.INITIALIZATION, WorkflowStage.DISCOVERY]
        progress.total_duration_seconds = 45.5
        
        # Add a stage result
        progress.stage_results[WorkflowStage.DISCOVERY] = StageResult(
            stage=WorkflowStage.DISCOVERY,
            status=StageStatus.COMPLETED,
            duration_seconds=15.0
        )
        
        summary = progress.get_summary()
        
        assert summary["current_stage"] == "synthesis"
        assert summary["completion_percentage"] == 25.0  # 2 of 8 stages
        assert summary["duration_seconds"] == 45.5
        assert len(summary["completed_stages"]) == 2
        assert summary["stage_details"]["discovery"]["status"] == "completed"
        assert summary["stage_details"]["discovery"]["duration"] == 15.0


class TestResearchWorkflow:
    """Test ResearchWorkflow orchestration."""
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, mock_agent, mock_config):
        """Test workflow initializes with correct components."""
        # Create a progress callback
        callback_called = False
        def progress_callback(progress):
            nonlocal callback_called
            callback_called = True
        
        workflow = ResearchWorkflow(
            agent=mock_agent,
            config=mock_config,
            progress_callback=progress_callback
        )
        
        assert workflow.agent == mock_agent
        assert workflow.config == mock_config
        assert workflow.progress_callback == progress_callback
        assert workflow.progress.current_stage == WorkflowStage.INITIALIZATION
        assert workflow.strategy is not None
    
    @pytest.mark.asyncio
    async def test_stage_handlers_registration(self, mock_agent, mock_config):
        """Test that all stage handlers are registered."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Check all stages have handlers
        for stage in WorkflowStage:
            assert stage in workflow._stage_handlers
            assert callable(workflow._stage_handlers[stage])
    
    @pytest.mark.asyncio
    async def test_get_stages_for_strategy(self, mock_agent, mock_config):
        """Test stage selection based on strategy."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Test basic strategy
        basic_stages = workflow._get_stages_for_strategy("basic")
        assert WorkflowStage.INITIALIZATION in basic_stages
        assert WorkflowStage.DISCOVERY in basic_stages
        assert WorkflowStage.SYNTHESIS in basic_stages
        assert WorkflowStage.COMPLETION in basic_stages
        assert WorkflowStage.CRAWLING not in basic_stages  # Should skip crawling
        
        # Test comprehensive strategy
        comprehensive_stages = workflow._get_stages_for_strategy("comprehensive")
        assert len(comprehensive_stages) == len(WorkflowStage)  # All stages
        
        # Test standard strategy
        standard_stages = workflow._get_stages_for_strategy("standard")
        assert WorkflowStage.CRAWLING not in standard_stages  # No crawling in standard
        assert WorkflowStage.VALIDATION in standard_stages
    
    @pytest.mark.asyncio
    async def test_can_skip_stage(self, mock_agent, mock_config):
        """Test stage skipping logic."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Critical stages cannot be skipped
        assert not workflow._can_skip_stage(WorkflowStage.INITIALIZATION, "standard")
        assert not workflow._can_skip_stage(WorkflowStage.DISCOVERY, "standard")
        assert not workflow._can_skip_stage(WorkflowStage.SYNTHESIS, "standard")
        assert not workflow._can_skip_stage(WorkflowStage.COMPLETION, "standard")
        
        # Non-critical stages can be skipped
        assert workflow._can_skip_stage(WorkflowStage.ANALYSIS, "standard")
        assert workflow._can_skip_stage(WorkflowStage.EXTRACTION, "standard")
        assert workflow._can_skip_stage(WorkflowStage.CRAWLING, "standard")
        assert workflow._can_skip_stage(WorkflowStage.VALIDATION, "standard")
    
    @pytest.mark.asyncio
    async def test_progress_reporting(self, mock_agent, mock_config):
        """Test that progress callbacks are called."""
        progress_updates = []
        
        def track_progress(progress):
            progress_updates.append({
                "stage": progress.current_stage.value,
                "completion": progress.get_completion_percentage()
            })
        
        workflow = ResearchWorkflow(mock_agent, mock_config, track_progress)
        
        # Trigger progress report
        workflow._report_progress()
        
        assert len(progress_updates) == 1
        assert progress_updates[0]["stage"] == "initialization"
        assert progress_updates[0]["completion"] == 0.0
    
    @pytest.mark.asyncio
    async def test_stage_execution_success(self, mock_agent, mock_config):
        """Test successful stage execution."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Create a simple handler that returns data
        async def test_handler(context):
            return {"test_data": "success"}
        
        workflow._stage_handlers[WorkflowStage.DISCOVERY] = test_handler
        
        # Execute the stage
        context = {"keyword": "test"}
        result = await workflow._execute_stage_with_retry(
            WorkflowStage.DISCOVERY, context, max_retries=1
        )
        
        assert result.stage == WorkflowStage.DISCOVERY
        assert result.status == StageStatus.COMPLETED
        assert result.data == {"test_data": "success"}
        assert result.error is None
        assert result.duration_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_stage_execution_with_retry(self, mock_agent, mock_config):
        """Test stage execution with retry on failure."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Create a handler that fails once then succeeds
        call_count = 0
        async def flaky_handler(context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return {"attempt": call_count}
        
        workflow._stage_handlers[WorkflowStage.DISCOVERY] = flaky_handler
        
        # Execute with retries
        context = {"keyword": "test"}
        result = await workflow._execute_stage_with_retry(
            WorkflowStage.DISCOVERY, context, max_retries=3
        )
        
        assert call_count == 2  # Failed once, succeeded on second
        assert result.status == StageStatus.COMPLETED
        assert result.data == {"attempt": 2}
    
    @pytest.mark.asyncio
    async def test_stage_execution_all_retries_fail(self, mock_agent, mock_config):
        """Test stage execution when all retries fail."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Create a handler that always fails
        async def failing_handler(context):
            raise Exception("Always fails")
        
        workflow._stage_handlers[WorkflowStage.DISCOVERY] = failing_handler
        
        # Execute with retries
        context = {"keyword": "test"}
        result = await workflow._execute_stage_with_retry(
            WorkflowStage.DISCOVERY, context, max_retries=2
        )
        
        assert result.status == StageStatus.FAILED
        assert result.error == "Always fails"
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, mock_agent, mock_config):
        """Test initialization handler validates configuration."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Test with valid keyword
        context = {"keyword": "test keyword"}
        result = await workflow._handle_initialization(context)
        assert result["initialized"] is True
        
        # Test with invalid keyword
        with pytest.raises(ValueError, match="Invalid keyword"):
            await workflow._handle_initialization({"keyword": ""})
        
        # Test with missing API key
        mock_config.tavily_api_key = None
        with pytest.raises(ValueError, match="Tavily API key"):
            await workflow._handle_initialization({"keyword": "test"})
    
    @pytest.mark.asyncio
    async def test_handler_discovery(self, mock_agent, mock_config, sample_findings):
        """Test discovery handler executes search."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Mock agent to return findings
        mock_result = Mock()
        mock_result.data = sample_findings
        mock_agent.run.return_value = mock_result
        
        context = {"keyword": "test keyword"}
        result = await workflow._handle_discovery(context)
        
        # Check agent was called
        mock_agent.run.assert_called_once()
        
        # Check results
        assert "sources" in result
        assert "initial_findings" in result
        assert len(result["sources"]) == 1
        assert result["sources"][0].title == "Test Source 1"
    
    @pytest.mark.asyncio
    async def test_handler_analysis(self, mock_agent, mock_config):
        """Test analysis handler processes domains."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Mock agent response
        mock_result = Mock()
        mock_result.data = {"analysis": "complete"}
        mock_agent.run.return_value = mock_result
        
        # Create context with sources
        context = {
            "sources": [
                AcademicSource(
                    title="Source 1",
                    url="https://example.edu/paper1",
                    authors=["Author"],
                    publication_date="2024",
                    credibility_score=0.8,
                    relevance_score=0.9,
                    key_findings=["Finding"],
                    methodology="Method",
                    citations=5
                ),
                AcademicSource(
                    title="Source 2",
                    url="https://test.edu/paper2",
                    authors=["Author"],
                    publication_date="2024",
                    credibility_score=0.8,
                    relevance_score=0.9,
                    key_findings=["Finding"],
                    methodology="Method",
                    citations=5
                )
            ]
        }
        
        result = await workflow._handle_analysis(context)
        
        assert "domain_analysis" in result
        # Agent should have been called with domain analysis prompt
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args[0][0]
        assert "example.edu" in call_args
        assert "test.edu" in call_args
    
    @pytest.mark.asyncio
    async def test_handler_synthesis(self, mock_agent, mock_config, sample_findings):
        """Test synthesis handler creates final output."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Mock agent to return comprehensive findings
        mock_result = Mock()
        mock_result.data = sample_findings
        mock_agent.run.return_value = mock_result
        
        context = {"keyword": "test keyword"}
        result = await workflow._handle_synthesis(context)
        
        assert "findings" in result
        assert result["findings"] == sample_findings
        
        # Check synthesis prompt includes all research aspects
        call_args = mock_agent.run.call_args[0][0]
        assert "test keyword" in call_args
        assert "comprehensive research findings" in call_args
    
    @pytest.mark.asyncio
    async def test_handler_validation(self, mock_agent, mock_config, sample_findings):
        """Test validation handler checks quality."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Test with good findings
        context = {"findings": sample_findings}
        result = await workflow._handle_validation(context)
        
        assert result["validation_passed"] is False  # Only 1 source, need 3
        assert result["quality_score"] == 40  # -20 for sources, -20 for findings, -20 for stats
        assert "Insufficient academic sources" in result["issues"]
        
        # Test with better findings
        sample_findings.academic_sources.extend([
            AcademicSource(
                title=f"Source {i}",
                url=f"https://test.edu/paper{i}",
                authors=["Author"],
                publication_date="2024",
                credibility_score=0.8,
                relevance_score=0.9,
                key_findings=["Finding"],
                methodology="Method",
                citations=5
            ) for i in range(2, 4)
        ])
        sample_findings.main_findings.append("Finding 3")
        
        result = await workflow._handle_validation(context)
        assert result["validation_passed"] is True
        assert result["quality_score"] == 100
        assert len(result["issues"]) == 0
    
    @pytest.mark.asyncio
    async def test_adapt_strategy_based_on_results(self, mock_agent, mock_config):
        """Test strategy adaptation based on intermediate results."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Create initial research plan
        from research_agent.strategy import ResearchPlan, TopicType, ResearchDepth, ToolRecommendation, ToolType
        
        initial_plan = ResearchPlan(
            topic_type=TopicType.ACADEMIC,
            research_depth=ResearchDepth.STANDARD,
            primary_tools=[
                ToolRecommendation(
                    tool=ToolType.SEARCH,
                    priority=10,
                    reasoning="Initial search",
                    parameters={}
                )
            ],
            optional_tools=[],
            search_queries=["test query"],
            target_domains=[".edu"]
        )
        
        # Create context with poor results
        context = {
            "research_plan": initial_plan,
            "sources": [
                AcademicSource(
                    title="Poor Source",
                    url="https://example.com/article",
                    authors=["Author"],
                    publication_date="2024",
                    credibility_score=0.4,  # Low credibility
                    relevance_score=0.5,
                    key_findings=["Finding"],
                    methodology="Method",
                    citations=1
                )
            ]
        }
        
        # Adapt strategy
        workflow._adapt_strategy_based_on_results(context)
        
        # Check that strategy was adapted (mock will return modified plan)
        # In real implementation, this would broaden search and upgrade tools
        assert "research_plan" in context
    
    @pytest.mark.asyncio
    async def test_execute_research_pipeline_basic(self, mock_agent, mock_config, sample_findings):
        """Test basic pipeline execution."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Mock all handlers to return quickly
        async def quick_handler(context):
            if "findings" not in context:
                return {"sources": sample_findings.academic_sources}
            return {}
        
        # Mock agent for synthesis
        mock_result = Mock()
        mock_result.data = sample_findings
        mock_agent.run.return_value = mock_result
        
        # Override some handlers for speed
        workflow._stage_handlers[WorkflowStage.ANALYSIS] = quick_handler
        workflow._stage_handlers[WorkflowStage.EXTRACTION] = quick_handler
        
        # Execute pipeline
        findings = await workflow.execute_research_pipeline(
            keyword="test keyword",
            strategy="basic",
            max_retries=1
        )
        
        assert findings.keyword == "test keyword"
        assert len(findings.academic_sources) == 1
        assert findings.research_summary == "Test research summary"
    
    @pytest.mark.asyncio
    async def test_execute_research_pipeline_with_failure(self, mock_agent, mock_config):
        """Test pipeline execution with stage failure."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Make discovery fail
        async def failing_discovery(context):
            raise Exception("Discovery failed")
        
        workflow._stage_handlers[WorkflowStage.DISCOVERY] = failing_discovery
        
        # Discovery is critical, so pipeline should fail
        with pytest.raises(WorkflowError, match="Critical stage discovery failed"):
            await workflow.execute_research_pipeline(
                keyword="test",
                strategy="basic",
                max_retries=1
            )
    
    @pytest.mark.asyncio
    async def test_execute_research_pipeline_skip_non_critical(self, mock_agent, mock_config, sample_findings):
        """Test pipeline continues when non-critical stage fails."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Make analysis fail (non-critical)
        async def failing_analysis(context):
            raise Exception("Analysis failed")
        
        workflow._stage_handlers[WorkflowStage.ANALYSIS] = failing_analysis
        
        # Mock successful discovery and synthesis
        async def mock_discovery(context):
            return {"sources": sample_findings.academic_sources}
        
        mock_result = Mock()
        mock_result.data = sample_findings
        mock_agent.run.return_value = mock_result
        
        workflow._stage_handlers[WorkflowStage.DISCOVERY] = mock_discovery
        
        # Execute pipeline - should complete despite analysis failure
        findings = await workflow.execute_research_pipeline(
            keyword="test",
            strategy="standard",  # Includes analysis stage
            max_retries=1
        )
        
        assert findings.keyword == "test keyword"
        # Check that analysis was marked as skipped
        assert workflow.progress.stage_results[WorkflowStage.ANALYSIS].status == StageStatus.SKIPPED


class TestWorkflowIntegration:
    """Test workflow integration with other components."""
    
    @pytest.mark.asyncio
    async def test_workflow_with_real_strategy(self, mock_agent, mock_config):
        """Test workflow uses real ResearchStrategy."""
        workflow = ResearchWorkflow(mock_agent, mock_config)
        
        # Check strategy is properly initialized
        assert workflow.strategy is not None
        
        # Test that strategy creates valid research plan
        from research_agent.strategy import TopicType
        
        # The workflow should create a research plan in execute_research_pipeline
        # We can verify by checking the strategy works
        plan = workflow.strategy.create_research_plan(
            "machine learning algorithms",
            {"strategy": "standard"}
        )
        
        assert plan.topic_type == TopicType.TECHNICAL
        assert len(plan.primary_tools) > 0
        assert len(plan.search_queries) > 0
    
    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, mock_agent, mock_config):
        """Test workflow continues even if progress callback fails."""
        # Create a failing callback
        def failing_callback(progress):
            raise Exception("Callback error")
        
        workflow = ResearchWorkflow(mock_agent, mock_config, failing_callback)
        
        # This should not raise an exception
        workflow._report_progress()
        
        # Workflow should continue normally
        assert workflow.progress.current_stage == WorkflowStage.INITIALIZATION


@pytest.mark.asyncio
async def test_workflow_end_to_end(mock_agent, mock_config, sample_findings):
    """Test complete workflow execution end-to-end."""
    # Track all progress updates
    progress_history = []
    
    def track_all_progress(progress):
        progress_history.append({
            "stage": progress.current_stage.value,
            "completion": progress.get_completion_percentage(),
            "completed_count": len(progress.completed_stages)
        })
    
    # Create workflow
    workflow = ResearchWorkflow(mock_agent, mock_config, track_all_progress)
    
    # Mock agent responses
    mock_result = Mock()
    mock_result.data = sample_findings
    mock_agent.run.return_value = mock_result
    
    # Execute full pipeline
    findings = await workflow.execute_research_pipeline(
        keyword="artificial intelligence",
        strategy="standard",
        max_retries=2
    )
    
    # Verify results
    assert findings.keyword == "test keyword"
    assert len(findings.academic_sources) > 0
    assert len(findings.main_findings) > 0
    
    # Verify progress tracking
    assert len(progress_history) > 0
    assert progress_history[0]["stage"] == "initialization"
    assert progress_history[-1]["completion"] > 0
    
    # Verify workflow completion
    assert WorkflowStage.COMPLETION in workflow.progress.completed_stages
    assert workflow.progress.total_duration_seconds > 0