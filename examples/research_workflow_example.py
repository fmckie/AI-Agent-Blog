#!/usr/bin/env python3
"""
Example usage of the enhanced research workflow system.

This script demonstrates:
1. Basic workflow execution
2. Progress tracking
3. Different research strategies
4. Adaptive research capabilities
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from config import get_config
from research_agent import (
    create_research_agent,
    run_research_workflow,
    WorkflowProgress,
    WorkflowStage,
)

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Example 1: Basic Research Workflow
async def basic_research_example():
    """
    Demonstrates basic research workflow execution.

    This example shows the simplest way to use the enhanced workflow
    without any progress tracking or customization.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Research Workflow")
    print("=" * 60)

    # Get configuration
    config = get_config()

    # Create research agent
    agent = create_research_agent(config)

    # Execute research workflow
    keyword = "quantum computing applications"
    print(f"\nResearching: '{keyword}'")
    print(f"Strategy: {config.research_strategy}")

    # Run the workflow
    findings = await run_research_workflow(agent, keyword, config)

    # Display results
    print(f"\n✅ Research completed!")
    print(f"Found {len(findings.academic_sources)} sources")
    print(f"Identified {len(findings.main_findings)} main findings")
    print(f"Extracted {len(findings.key_statistics)} key statistics")

    # Show a sample of findings
    print("\nSample findings:")
    for i, finding in enumerate(findings.main_findings[:3], 1):
        print(f"{i}. {finding}")

    return findings


# Example 2: Research with Progress Tracking
async def progress_tracking_example():
    """
    Demonstrates research workflow with real-time progress tracking.

    This example shows how to monitor workflow progress and display
    updates to users during long-running research operations.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Research with Progress Tracking")
    print("=" * 60)

    config = get_config()
    agent = create_research_agent(config)

    # Progress tracking variables
    stage_times = {}

    # Define progress callback
    def track_progress(progress: WorkflowProgress):
        """Display progress updates in a user-friendly format."""
        current_stage = progress.current_stage.value
        completion = progress.get_completion_percentage()

        # Track stage timing
        if current_stage not in stage_times:
            stage_times[current_stage] = datetime.now()

        # Create progress bar
        bar_length = 30
        filled = int(bar_length * completion / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Display progress
        print(
            f"\r[{bar}] {completion:.1f}% - {current_stage.upper()}", end="", flush=True
        )

        # Show stage completion
        if progress.completed_stages:
            last_completed = progress.completed_stages[-1]
            if last_completed in progress.stage_results:
                duration = progress.stage_results[last_completed].duration_seconds
                print(f"\n✓ {last_completed.value} completed in {duration:.2f}s")

    # Execute with progress tracking
    keyword = "artificial intelligence in healthcare"
    print(f"\nResearching: '{keyword}' with progress tracking\n")

    findings = await run_research_workflow(
        agent, keyword, config, progress_callback=track_progress
    )

    print(
        f"\n\n✅ Research completed in {sum(stage_times.values(), datetime.now()).total_seconds():.2f}s"
    )
    print(f"\nResearch Summary: {findings.research_summary[:200]}...")

    return findings


# Example 3: Different Research Strategies
async def strategy_comparison_example():
    """
    Demonstrates different research strategies for the same topic.

    This example shows how different strategies (basic, standard, comprehensive)
    affect the depth and breadth of research results.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Comparing Research Strategies")
    print("=" * 60)

    config = get_config()
    agent = create_research_agent(config)
    keyword = "renewable energy technologies"

    # Test different strategies
    strategies = ["basic", "standard", "comprehensive"]
    results = {}

    for strategy in strategies:
        print(f"\n\nTesting {strategy.upper()} strategy...")

        # Override strategy in config
        config.research_strategy = strategy

        # Track execution time
        start_time = datetime.now()

        # Simple progress indicator
        def show_stage(progress):
            print(f"  → {progress.current_stage.value}")

        # Run research
        findings = await run_research_workflow(
            agent, keyword, config, progress_callback=show_stage
        )

        # Calculate metrics
        duration = (datetime.now() - start_time).total_seconds()

        results[strategy] = {
            "sources": len(findings.academic_sources),
            "findings": len(findings.main_findings),
            "statistics": len(findings.key_statistics),
            "gaps": len(findings.research_gaps),
            "duration": duration,
        }

    # Display comparison
    print("\n\nStrategy Comparison Results:")
    print("-" * 50)
    print(
        f"{'Strategy':<15} {'Sources':<10} {'Findings':<10} {'Stats':<10} {'Time (s)':<10}"
    )
    print("-" * 50)

    for strategy, metrics in results.items():
        print(
            f"{strategy:<15} {metrics['sources']:<10} {metrics['findings']:<10} "
            f"{metrics['statistics']:<10} {metrics['duration']:<10.2f}"
        )

    return results


# Example 4: Adaptive Research
async def adaptive_research_example():
    """
    Demonstrates adaptive research capabilities.

    This example shows how the workflow adapts its strategy based on
    intermediate results to improve research quality.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Adaptive Research")
    print("=" * 60)

    config = get_config()
    # Enable adaptive strategy
    config.enable_adaptive_strategy = True

    agent = create_research_agent(config)

    # Track strategy adaptations
    adaptations = []

    def track_adaptations(progress: WorkflowProgress):
        """Monitor when strategy adapts."""
        stage = progress.current_stage

        # Log stage transitions
        logger.info(f"Current stage: {stage.value}")

        # Check for adaptations (would need access to internal state)
        if stage == WorkflowStage.ANALYSIS:
            print(f"\n🔄 Analyzing initial results for adaptation...")

    # Research a challenging topic
    keyword = "emerging quantum computing algorithms 2024"
    print(f"\nResearching challenging topic: '{keyword}'")
    print("Adaptive strategy is ENABLED")

    findings = await run_research_workflow(
        agent, keyword, config, progress_callback=track_adaptations
    )

    print(f"\n✅ Adaptive research completed!")
    print(
        f"\nTopic classification: {findings.academic_sources[0].url if findings.academic_sources else 'Unknown'}"
    )

    # Show how the system adapted
    if findings.academic_sources:
        domains = list(set(s.url.split("/")[2] for s in findings.academic_sources))
        print(f"Domains explored: {', '.join(domains[:5])}")

    return findings


# Example 5: Custom Progress Handler
class DetailedProgressTracker:
    """
    A custom progress handler that provides detailed workflow insights.

    This class demonstrates how to build sophisticated progress tracking
    for production applications.
    """

    def __init__(self):
        self.stage_history = []
        self.stage_durations = {}
        self.total_start = None
        self.current_stage_start = None

    def __call__(self, progress: WorkflowProgress):
        """Process progress updates."""
        now = datetime.now()

        if self.total_start is None:
            self.total_start = now

        # Track stage transitions
        if self.current_stage_start:
            # Calculate duration of previous stage
            duration = (now - self.current_stage_start).total_seconds()
            if self.stage_history:
                last_stage = self.stage_history[-1]
                self.stage_durations[last_stage] = duration

        # Record new stage
        self.stage_history.append(progress.current_stage)
        self.current_stage_start = now

        # Display detailed progress
        self._display_progress(progress)

    def _display_progress(self, progress: WorkflowProgress):
        """Display formatted progress information."""
        summary = progress.get_summary()

        print(f"\n📊 Workflow Progress Report")
        print(f"├─ Current Stage: {summary['current_stage']}")
        print(f"├─ Completion: {summary['completion_percentage']:.1f}%")
        print(f"├─ Completed Stages: {len(summary['completed_stages'])}")
        print(f"└─ Total Duration: {summary['duration_seconds']:.2f}s")

        # Show stage details
        if summary["stage_details"]:
            print(f"\n📋 Stage Details:")
            for stage, details in summary["stage_details"].items():
                status_icon = "✅" if details["status"] == "completed" else "❌"
                print(f"  {status_icon} {stage}: {details['duration']:.2f}s")

    def get_report(self):
        """Generate final report."""
        total_duration = (datetime.now() - self.total_start).total_seconds()

        report = {
            "total_duration": total_duration,
            "stages_completed": len(self.stage_durations),
            "stage_durations": self.stage_durations,
            "average_stage_time": (
                sum(self.stage_durations.values()) / len(self.stage_durations)
                if self.stage_durations
                else 0
            ),
        }

        return report


async def custom_progress_example():
    """
    Demonstrates custom progress tracking implementation.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Custom Progress Tracking")
    print("=" * 60)

    config = get_config()
    agent = create_research_agent(config)

    # Create custom tracker
    tracker = DetailedProgressTracker()

    # Run research with custom tracking
    keyword = "sustainable agriculture innovations"
    print(f"\nResearching: '{keyword}' with detailed tracking\n")

    findings = await run_research_workflow(
        agent, keyword, config, progress_callback=tracker
    )

    # Display final report
    report = tracker.get_report()
    print(f"\n\n📈 Final Workflow Report:")
    print(f"├─ Total Duration: {report['total_duration']:.2f}s")
    print(f"├─ Stages Completed: {report['stages_completed']}")
    print(f"└─ Average Stage Time: {report['average_stage_time']:.2f}s")

    return findings


# Main execution
async def main():
    """
    Run all examples to demonstrate workflow capabilities.
    """
    print("\n" + "=" * 60)
    print("RESEARCH WORKFLOW EXAMPLES")
    print("Demonstrating Phase 2 Enhanced Capabilities")
    print("=" * 60)

    try:
        # Run examples based on user choice
        print("\nAvailable examples:")
        print("1. Basic Research Workflow")
        print("2. Research with Progress Tracking")
        print("3. Strategy Comparison")
        print("4. Adaptive Research")
        print("5. Custom Progress Handler")
        print("6. Run All Examples")

        choice = input("\nSelect example (1-6): ").strip()

        if choice == "1":
            await basic_research_example()
        elif choice == "2":
            await progress_tracking_example()
        elif choice == "3":
            await strategy_comparison_example()
        elif choice == "4":
            await adaptive_research_example()
        elif choice == "5":
            await custom_progress_example()
        elif choice == "6":
            # Run all examples
            await basic_research_example()
            await progress_tracking_example()
            await strategy_comparison_example()
            await adaptive_research_example()
            await custom_progress_example()
        else:
            print("Invalid choice. Please run again and select 1-6.")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise

    print("\n\n✨ All examples completed successfully!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
