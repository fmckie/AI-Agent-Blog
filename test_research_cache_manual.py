#!/usr/bin/env python3
"""
Manual test script to verify research caching in Supabase.

This script demonstrates the caching functionality by:
1. Running a research query
2. Showing cache statistics
3. Verifying data in Supabase
4. Testing cache hits
"""

import asyncio
import json
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

# Import our modules
from config import get_config
from rag.config import get_rag_config
from rag.retriever import ResearchRetriever
from rag.storage import VectorStorage
from research_agent import create_research_agent, run_research_agent

# Set up rich console for beautiful output
console = Console()

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger(__name__)


async def test_research_with_caching():
    """Test research functionality with caching enabled."""

    console.print("\n[bold blue]🧪 Testing Research Cache Functionality[/bold blue]\n")

    # Get configurations
    config = get_config()
    rag_config = get_rag_config()

    # Test keyword
    test_keyword = "blood sugar monitoring"

    # Create research agent
    console.print(f"[yellow]1. Creating research agent for: '{test_keyword}'[/yellow]")
    agent = create_research_agent(config)

    # Run research (first time - should be cache miss)
    console.print(
        "\n[yellow]2. Running research query (expecting cache miss)...[/yellow]"
    )
    start_time = datetime.now()

    try:
        findings = await run_research_agent(agent, test_keyword)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        console.print(f"[green]✓ Research completed in {duration:.2f} seconds[/green]")
        console.print(f"   Found {len(findings.academic_sources)} sources")
        console.print(f"   Summary: {findings.research_summary[:100]}...")

    except Exception as e:
        console.print(f"[red]✗ Research failed: {e}[/red]")
        return

    # Check cache statistics
    console.print("\n[yellow]3. Checking cache statistics...[/yellow]")
    retriever = ResearchRetriever()
    stats = retriever.get_statistics()

    # Display retriever statistics
    retriever_stats = stats.get("retriever", {})
    console.print("\n[bold]Retriever Statistics:[/bold]")
    stats_table = Table(show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Total Requests", str(retriever_stats.get("total_requests", 0)))
    stats_table.add_row("Exact Cache Hits", str(retriever_stats.get("exact_hits", 0)))
    stats_table.add_row(
        "Semantic Cache Hits", str(retriever_stats.get("semantic_hits", 0))
    )
    stats_table.add_row("Cache Misses", str(retriever_stats.get("cache_misses", 0)))
    stats_table.add_row("Cache Hit Rate", retriever_stats.get("cache_hit_rate", "0%"))

    console.print(stats_table)

    # Query Supabase directly
    console.print("\n[yellow]4. Querying Supabase tables directly...[/yellow]")

    async with VectorStorage() as storage:
        # Get storage statistics
        storage_stats = await storage.get_statistics()

        console.print("\n[bold]Storage Statistics:[/bold]")
        storage_table = Table(show_header=True, header_style="bold magenta")
        storage_table.add_column("Table", style="cyan")
        storage_table.add_column("Count", style="green")

        storage_table.add_row(
            "Research Chunks", str(storage_stats.get("total_chunks", 0))
        )
        storage_table.add_row(
            "Cache Entries", str(storage_stats.get("total_cache_entries", 0))
        )
        storage_table.add_row(
            "Unique Keywords", str(storage_stats.get("unique_keywords", 0))
        )

        console.print(storage_table)

        # Get cached response for our keyword
        cached = await storage.get_cached_response(test_keyword)

        if cached:
            console.print(f"\n[green]✓ Found cache entry for '{test_keyword}':[/green]")
            console.print(f"   Cache ID: {cached['id']}")
            console.print(f"   Created: {cached['created_at']}")
            console.print(f"   Hit Count: {cached['hit_count']}")
            console.print(f"   Chunks: {len(cached['chunks'])} associated chunks")
        else:
            console.print(f"\n[red]✗ No cache entry found for '{test_keyword}'[/red]")

    # Test cache hit (second query)
    console.print(
        f"\n[yellow]5. Running same query again (expecting cache hit)...[/yellow]"
    )

    # Reset statistics for cleaner comparison
    retriever = ResearchRetriever()

    start_time = datetime.now()
    findings2 = await run_research_agent(agent, test_keyword)
    end_time = datetime.now()
    duration2 = (end_time - start_time).total_seconds()

    console.print(f"[green]✓ Research completed in {duration2:.2f} seconds[/green]")

    # Compare times
    if duration2 < duration:
        speedup = (duration - duration2) / duration * 100
        console.print(
            f"[bold green]⚡ {speedup:.1f}% faster due to caching![/bold green]"
        )

    # Final statistics
    final_stats = retriever.get_statistics()
    final_retriever_stats = final_stats.get("retriever", {})

    console.print("\n[bold]Final Cache Performance:[/bold]")
    if final_retriever_stats.get("exact_hits", 0) > 0:
        console.print(
            "[green]✓ Cache hit confirmed! Research was served from cache.[/green]"
        )
    else:
        console.print(
            "[yellow]⚠ No cache hit detected. Check cache configuration.[/yellow]"
        )


async def show_recent_cache_entries():
    """Show recent cache entries from Supabase."""

    console.print("\n[bold blue]📊 Recent Cache Entries[/bold blue]\n")

    try:
        async with VectorStorage() as storage:
            # Query recent cache entries
            table = storage.supabase.table("cache_entries")
            response = (
                table.select("*").order("created_at", desc=True).limit(5).execute()
            )

            if response.data:
                entries_table = Table(show_header=True, header_style="bold magenta")
                entries_table.add_column("Keyword", style="cyan")
                entries_table.add_column("Created", style="yellow")
                entries_table.add_column("Hits", style="green")
                entries_table.add_column("Chunks", style="blue")

                for entry in response.data:
                    entries_table.add_row(
                        entry["keyword"],
                        entry["created_at"][:16],
                        str(entry["hit_count"]),
                        str(len(entry.get("chunk_ids", []))),
                    )

                console.print(entries_table)
            else:
                console.print("[yellow]No cache entries found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error querying cache entries: {e}[/red]")


async def main():
    """Main test runner."""

    console.print(
        Panel.fit(
            "[bold]Research Cache Testing Tool[/bold]\n"
            "This tool tests the research caching functionality\n"
            "and verifies data is being stored in Supabase.",
            border_style="blue",
        )
    )

    try:
        # Run the main test
        await test_research_with_caching()

        # Show recent cache entries
        await show_recent_cache_entries()

        console.print(
            "\n[bold green]✅ Cache testing completed successfully![/bold green]"
        )
        console.print(
            "\n[dim]Tip: Run 'python main.py cache stats' for more statistics[/dim]"
        )

    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
