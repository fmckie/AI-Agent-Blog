"""
Temporary patching for agents during development.

This module provides mock implementations for testing while
the agents are being fully implemented. This will be removed
in Phase 3/4.
"""

from pydantic_ai import Agent
from models import ResearchFindings, ArticleOutput
from research_agent.agent import _mock_research_agent_run
from writer_agent.agent import _mock_writer_agent_run


def patch_agents_for_testing():
    """
    Patch agents with mock implementations for testing.
    
    This will be removed once agents are fully implemented.
    """
    # Store original methods
    if not hasattr(Agent, '_original_run'):
        Agent._original_run = Agent.run
        Agent._original_run_sync = Agent.run_sync
    
    # Patch with mock implementations
    async def mock_run(self, *args, **kwargs):
        if self.output_type == ResearchFindings:
            return await _mock_research_agent_run(args[0] if args else "")
        elif self.output_type == ArticleOutput:
            return await _mock_writer_agent_run(
                args[0] if args else "",
                kwargs.get("context", {})
            )
        else:
            return await self._original_run(*args, **kwargs)
    
    Agent.run = mock_run


# Apply patches for now (remove in Phase 3/4)
patch_agents_for_testing()