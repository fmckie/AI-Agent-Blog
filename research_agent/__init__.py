"""
Research Agent module for academic source discovery and analysis.

This module provides the Research Agent that searches for and analyzes
academic sources using the Tavily API.
"""

from .agent import create_research_agent, run_research_agent

__all__ = ["create_research_agent", "run_research_agent"]
