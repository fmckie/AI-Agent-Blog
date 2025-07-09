"""
Research Agent module for academic source discovery and analysis.

This module provides the Research Agent that searches for and analyzes
academic sources using the Tavily API, with advanced workflow orchestration
and dynamic strategy selection.
"""

from .agent import create_research_agent, run_research_agent, run_research_workflow
from .workflow import ResearchWorkflow, WorkflowProgress, WorkflowStage
from .strategy import ResearchStrategy, ResearchPlan, TopicType

__all__ = [
    "create_research_agent", 
    "run_research_agent",
    "run_research_workflow",
    "ResearchWorkflow",
    "WorkflowProgress",
    "WorkflowStage",
    "ResearchStrategy",
    "ResearchPlan",
    "TopicType",
]
