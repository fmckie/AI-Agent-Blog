#!/usr/bin/env python
"""
Script to demonstrate workflow recovery from a saved state.

This shows how interrupted workflows can be resumed.
"""

import asyncio
import sys
from pathlib import Path

from config import get_config
from workflow import WorkflowOrchestrator


async def main():
    """Resume an interrupted workflow."""
    if len(sys.argv) != 2:
        print("Usage: python resume_workflow.py <state_file>")
        sys.exit(1)

    state_file = Path(sys.argv[1])
    if not state_file.exists():
        print(f"Error: State file '{state_file}' not found")
        sys.exit(1)

    print(f"📥 Loading workflow state from: {state_file}")

    # Get configuration
    config = get_config()

    # Create workflow orchestrator
    orchestrator = WorkflowOrchestrator(config)

    try:
        # Resume the workflow
        print("🔄 Resuming interrupted workflow...")
        result = await orchestrator.resume_workflow(state_file)

        print(f"✅ Workflow resumed and completed successfully!")
        print(f"📄 Output saved to: {result}")

    except Exception as e:
        print(f"❌ Failed to resume workflow: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
