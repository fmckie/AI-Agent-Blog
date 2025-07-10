"""
Research workflow orchestration for multi-step research processes.

This module implements the ResearchWorkflow class that manages complex
research pipelines with progress tracking and error recovery.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic_ai import Agent

from config import Config
from models import ResearchFindings

from .strategy import ResearchStrategy

# Set up logging for workflow tracking
logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Enumeration of workflow stages for research pipeline."""

    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"  # Initial search phase
    ANALYSIS = "analysis"  # Domain and source analysis
    EXTRACTION = "extraction"  # Full content extraction
    CRAWLING = "crawling"  # Deep website exploration
    SYNTHESIS = "synthesis"  # Combining all findings
    VALIDATION = "validation"  # Quality checks
    COMPLETION = "completion"  # Final output


class StageStatus(Enum):
    """Status of each workflow stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result from a workflow stage execution."""

    stage: WorkflowStage
    status: StageStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowProgress:
    """Tracks progress through the research workflow."""

    current_stage: WorkflowStage
    completed_stages: List[WorkflowStage] = field(default_factory=list)
    stage_results: Dict[WorkflowStage, StageResult] = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

    def get_completion_percentage(self) -> float:
        """Calculate workflow completion percentage."""
        total_stages = len(WorkflowStage)
        completed = len(self.completed_stages)
        return (completed / total_stages) * 100

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of workflow progress."""
        return {
            "current_stage": self.current_stage.value,
            "completion_percentage": self.get_completion_percentage(),
            "completed_stages": [s.value for s in self.completed_stages],
            "duration_seconds": self.total_duration_seconds,
            "stage_details": {
                stage.value: {
                    "status": result.status.value,
                    "duration": result.duration_seconds,
                    "has_error": result.error is not None,
                }
                for stage, result in self.stage_results.items()
            },
        }


class ResearchWorkflow:
    """
    Orchestrates multi-step research processes with progress tracking.

    This class manages the execution of complex research pipelines,
    handling stage transitions, error recovery, and progress reporting.
    """

    def __init__(
        self,
        agent: Agent,
        config: Config,
        progress_callback: Optional[Callable[[WorkflowProgress], None]] = None,
    ):
        """
        Initialize the research workflow.

        Args:
            agent: The research agent to execute tasks
            config: System configuration
            progress_callback: Optional callback for progress updates
        """
        self.agent = agent
        self.config = config
        self.progress_callback = progress_callback
        self.progress = WorkflowProgress(current_stage=WorkflowStage.INITIALIZATION)
        self._stage_handlers: Dict[WorkflowStage, Callable] = {}
        self.strategy = ResearchStrategy()  # Initialize strategy analyzer

        # Register default stage handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default handlers for each workflow stage."""
        # These will be implemented with specific logic for each stage
        self._stage_handlers = {
            WorkflowStage.INITIALIZATION: self._handle_initialization,
            WorkflowStage.DISCOVERY: self._handle_discovery,
            WorkflowStage.ANALYSIS: self._handle_analysis,
            WorkflowStage.EXTRACTION: self._handle_extraction,
            WorkflowStage.CRAWLING: self._handle_crawling,
            WorkflowStage.SYNTHESIS: self._handle_synthesis,
            WorkflowStage.VALIDATION: self._handle_validation,
            WorkflowStage.COMPLETION: self._handle_completion,
        }

    async def execute_research_pipeline(
        self, keyword: str, strategy: str = "standard", max_retries: int = 3
    ) -> ResearchFindings:
        """
        Execute the complete research pipeline for a keyword.

        Args:
            keyword: The research topic
            strategy: Research strategy ('basic', 'standard', 'comprehensive')
            max_retries: Maximum retries for failed stages

        Returns:
            ResearchFindings with complete analysis

        Raises:
            WorkflowError: If the workflow fails after retries
        """
        logger.info(
            f"Starting research workflow for '{keyword}' with strategy: {strategy}"
        )
        start_time = datetime.now()

        # Create research plan using strategy analyzer
        research_plan = self.strategy.create_research_plan(
            keyword=keyword,
            requirements={
                "strategy": strategy,
                "time_limit_minutes": self.config.workflow_stage_timeout // 60,
            },
        )

        # Initialize workflow context with plan
        context = {
            "keyword": keyword,
            "strategy": strategy,
            "research_plan": research_plan,
            "sources": [],
            "extracted_content": {},
            "crawled_data": {},
            "findings": None,
        }

        # Log the research plan
        logger.info(
            f"Research plan created - Topic: {research_plan.topic_type.value}, "
            f"Depth: {research_plan.research_depth.value}, "
            f"Primary tools: {len(research_plan.primary_tools)}"
        )

        # Determine stages based on strategy
        stages = self._get_stages_for_strategy(strategy)

        # Execute each stage
        for stage in stages:
            try:
                # Update progress
                self.progress.current_stage = stage
                self._report_progress()

                # Execute stage with retry logic
                result = await self._execute_stage_with_retry(
                    stage, context, max_retries
                )

                # Record result
                self.progress.stage_results[stage] = result
                self.progress.completed_stages.append(stage)

                # Update context with stage results
                if result.data:
                    context.update(result.data)

                # Adapt strategy based on results if enabled
                if (
                    self.config.enable_adaptive_strategy
                    and stage == WorkflowStage.DISCOVERY
                ):
                    self._adapt_strategy_based_on_results(context)

            except Exception as e:
                # Handle stage failure
                logger.error(f"Stage {stage.value} failed: {str(e)}")

                # Attempt recovery or skip based on strategy
                if self._can_skip_stage(stage, strategy):
                    logger.warning(f"Skipping failed stage: {stage.value}")
                    self.progress.stage_results[stage] = StageResult(
                        stage=stage, status=StageStatus.SKIPPED, error=str(e)
                    )
                else:
                    # Critical stage failed, abort workflow
                    raise WorkflowError(
                        f"Critical stage {stage.value} failed: {str(e)}"
                    )

        # Calculate total duration
        self.progress.total_duration_seconds = (
            datetime.now() - start_time
        ).total_seconds()

        # Final progress report
        self._report_progress()

        # Return the research findings
        return context.get(
            "findings",
            ResearchFindings(
                keyword=keyword,
                research_summary="Workflow completed but no findings generated",
                academic_sources=[],
                main_findings=[],
                key_statistics=[],
                research_gaps=[],
            ),
        )

    def _get_stages_for_strategy(self, strategy: str) -> List[WorkflowStage]:
        """Determine which stages to execute based on strategy."""
        if strategy == "basic":
            return [
                WorkflowStage.INITIALIZATION,
                WorkflowStage.DISCOVERY,
                WorkflowStage.SYNTHESIS,
                WorkflowStage.COMPLETION,
            ]
        elif strategy == "comprehensive":
            return list(WorkflowStage)  # All stages
        else:  # standard
            return [
                WorkflowStage.INITIALIZATION,
                WorkflowStage.DISCOVERY,
                WorkflowStage.ANALYSIS,
                WorkflowStage.EXTRACTION,
                WorkflowStage.SYNTHESIS,
                WorkflowStage.VALIDATION,
                WorkflowStage.COMPLETION,
            ]

    def _can_skip_stage(self, stage: WorkflowStage, strategy: str) -> bool:
        """Determine if a stage can be skipped on failure."""
        # Critical stages that cannot be skipped
        critical_stages = {
            WorkflowStage.INITIALIZATION,
            WorkflowStage.DISCOVERY,
            WorkflowStage.SYNTHESIS,
            WorkflowStage.COMPLETION,
        }

        return stage not in critical_stages

    async def _execute_stage_with_retry(
        self, stage: WorkflowStage, context: Dict[str, Any], max_retries: int
    ) -> StageResult:
        """Execute a stage with retry logic."""
        start_time = datetime.now()
        last_error = None

        for attempt in range(max_retries):
            try:
                # Get the handler for this stage
                handler = self._stage_handlers.get(stage)
                if not handler:
                    raise ValueError(f"No handler registered for stage: {stage.value}")

                # Execute the stage
                logger.info(f"Executing stage: {stage.value} (attempt {attempt + 1})")
                result_data = await handler(context)

                # Success - create result
                duration = (datetime.now() - start_time).total_seconds()
                return StageResult(
                    stage=stage,
                    status=StageStatus.COMPLETED,
                    data=result_data,
                    duration_seconds=duration,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Stage {stage.value} failed on attempt {attempt + 1}: {str(e)}"
                )

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        # All retries failed
        duration = (datetime.now() - start_time).total_seconds()
        return StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            error=str(last_error),
            duration_seconds=duration,
        )

    def _report_progress(self):
        """Report current progress through callback if available."""
        if self.progress_callback:
            try:
                self.progress_callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {str(e)}")

    # Stage handler methods
    async def _handle_initialization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the workflow and validate configuration."""
        logger.info("Initializing research workflow")

        # Validate keyword
        keyword = context.get("keyword", "")
        if not keyword or len(keyword) < 3:
            raise ValueError("Invalid keyword for research")

        # Check API keys and configuration
        if not self.config.tavily_api_key:
            raise ValueError("Tavily API key not configured")

        return {"initialized": True}

    async def _handle_discovery(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Initial discovery phase using search."""
        keyword = context["keyword"]

        # Use the agent to search for sources
        prompt = f"""
        Search for academic sources about '{keyword}'.
        Focus on finding credible, recent sources from .edu, .gov, and peer-reviewed journals.
        Use the search_academic_tool to find at least 5 relevant sources.
        """

        result = await self.agent.run(prompt)
        findings = result.data

        # Extract sources for next stages
        sources = findings.academic_sources if findings else []

        return {"sources": sources, "initial_findings": findings}

    async def _handle_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze domains and sources for quality."""
        sources = context.get("sources", [])

        if not sources:
            logger.warning("No sources to analyze")
            return {}

        # Get unique domains
        domains = list(set(source.url.split("/")[2] for source in sources[:3]))

        # Use agent to analyze domains
        prompt = f"""
        Analyze these domains for research quality and structure:
        {', '.join(domains)}
        
        Use the analyze_website_tool to understand their organization
        and identify the best sections for deep research.
        """

        result = await self.agent.run(prompt)

        return {"domain_analysis": result.data}

    async def _handle_extraction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract full content from top sources."""
        sources = context.get("sources", [])

        if not sources:
            return {}

        # Get URLs of top sources
        top_urls = [source.url for source in sources[:3]]

        # Use agent to extract content
        prompt = f"""
        Extract full content from these high-value sources:
        {', '.join(top_urls)}
        
        Use the extract_content_tool to get complete articles
        for deep analysis of methodologies and findings.
        """

        result = await self.agent.run(prompt)

        return {"extracted_content": result.data}

    async def _handle_crawling(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Crawl domains for comprehensive coverage."""
        sources = context.get("sources", [])
        keyword = context["keyword"]

        if not sources:
            return {}

        # Find the most authoritative .edu or .gov domain
        edu_gov_sources = [s for s in sources if ".edu" in s.url or ".gov" in s.url]

        if not edu_gov_sources:
            logger.info("No .edu or .gov domains to crawl")
            return {}

        # Use agent to crawl
        target_url = edu_gov_sources[0].url.split("/")[0:3]
        target_url = "/".join(target_url)

        prompt = f"""
        Crawl this authoritative domain for comprehensive research on '{keyword}':
        {target_url}
        
        Use the crawl_website_tool with instructions to find all relevant
        research, publications, and data related to the topic.
        """

        result = await self.agent.run(prompt)

        return {"crawled_data": result.data}

    async def _handle_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize all findings into final research output."""
        keyword = context["keyword"]

        # Prepare comprehensive prompt with all context
        prompt = f"""
        Synthesize comprehensive research findings for '{keyword}'.
        
        You have access to:
        - Initial search results
        - Domain analysis
        - Extracted full content
        - Crawled data
        
        Create a comprehensive ResearchFindings output that includes:
        1. A thorough research summary
        2. All credible academic sources found
        3. Main findings with full context
        4. Key statistics with methodologies
        5. Identified research gaps
        
        Ensure the synthesis represents the full depth of research conducted.
        """

        result = await self.agent.run(prompt)
        findings = result.data

        return {"findings": findings}

    async def _handle_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of research findings."""
        findings = context.get("findings")

        if not findings:
            raise ValueError("No findings to validate")

        # Check minimum requirements
        issues = []

        if len(findings.academic_sources) < 3:
            issues.append("Insufficient academic sources")

        if len(findings.main_findings) < 3:
            issues.append("Too few main findings")

        if not findings.key_statistics:
            issues.append("No key statistics extracted")

        # Calculate quality score
        quality_score = 100
        quality_score -= len(issues) * 20

        return {
            "validation_passed": len(issues) == 0,
            "quality_score": quality_score,
            "issues": issues,
        }

    async def _handle_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the workflow and prepare output."""
        logger.info("Completing research workflow")

        # Log summary statistics
        findings = context.get("findings")
        if findings:
            logger.info(
                f"Research completed: "
                f"{len(findings.academic_sources)} sources, "
                f"{len(findings.main_findings)} findings, "
                f"{len(findings.key_statistics)} statistics"
            )

        return {"completed": True}

    def _adapt_strategy_based_on_results(self, context: Dict[str, Any]):
        """Adapt the research plan based on intermediate results."""
        sources = context.get("sources", [])
        research_plan = context.get("research_plan")

        if not research_plan:
            return

        # Calculate metrics for adaptation
        sources_count = len(sources)
        avg_credibility = (
            sum(s.credibility_score for s in sources) / sources_count
            if sources_count > 0
            else 0
        )
        domains = list(set(s.url.split("/")[2] for s in sources))

        # Create intermediate results summary
        intermediate_results = {
            "sources_count": sources_count,
            "average_credibility": avg_credibility,
            "domains": domains,
        }

        # Adapt the plan
        adapted_plan = self.strategy.adapt_strategy(research_plan, intermediate_results)

        # Update context with adapted plan
        context["research_plan"] = adapted_plan

        # Log adaptation
        if adapted_plan != research_plan:
            logger.info(
                f"Strategy adapted based on results: "
                f"Sources={sources_count}, Credibility={avg_credibility:.2f}"
            )


class WorkflowError(Exception):
    """Custom exception for workflow failures."""

    pass
