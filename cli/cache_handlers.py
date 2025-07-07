"""
Cache command handlers for the SEO Content Automation System.

This module contains the async implementation functions for cache-related
CLI commands, extracted from main.py to improve modularity.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from config import get_config
from rag.config import get_rag_config
from rag.storage import VectorStorage

# Set up console and logger
console = Console()
logger = logging.getLogger(__name__)


async def handle_cache_search(query: str, limit: int, threshold: float):
    """Execute cache search asynchronously."""
    try:
        rag_config = get_rag_config()

        # Create storage instance
        async with VectorStorage(rag_config) as storage:
            # Create embeddings generator
            from rag.embeddings import EmbeddingGenerator

            embeddings = EmbeddingGenerator()

            console.print(f"\n[bold blue]🔍 Searching cache for: '{query}'[/bold blue]")

            # Generate embedding for query
            query_embeddings = await embeddings.generate_embeddings([query])
            
            if not query_embeddings:
                console.print("[red]Failed to generate embedding for query[/red]")
                return

            # Search for similar content
            results = await storage.search_similar(
                query_embedding=query_embeddings[0].embedding,
                limit=limit,
                similarity_threshold=threshold,
            )

            if not results:
                console.print("[yellow]No matching results found in cache.[/yellow]")
                console.print(
                    f"[dim]Try lowering the threshold (current: {threshold})[/dim]"
                )
                return

            # Display results
            console.print(f"\n[green]Found {len(results)} matching results:[/green]\n")

            for i, result in enumerate(results, 1):
                console.print(
                    f"[bold cyan]{i}. Similarity: {result['similarity']:.2%}[/bold cyan]"
                )
                console.print(f"   Keyword: [yellow]{result['keyword']}[/yellow]")
                console.print(f"   Content: {result['content'][:200]}...")
                console.print(f"   Cached: {result['created_at']}")
                console.print()

    except Exception as e:
        console.print(f"[red]❌ Search failed: {e}[/red]")
        raise click.exceptions.Exit(1)


async def handle_cache_stats(detailed: bool):
    """Get and display cache statistics."""
    try:
        rag_config = get_rag_config()

        async with VectorStorage(rag_config) as storage:
            # Get cache statistics
            stats = await storage.get_cache_stats()

            console.print("\n[bold]📊 Cache Statistics[/bold]\n")

            # Basic stats
            console.print(
                f"Total cached entries: [cyan]{stats['total_entries']:,}[/cyan]"
            )
            console.print(f"Unique keywords: [cyan]{stats['unique_keywords']:,}[/cyan]")
            console.print(
                f"Storage used: [cyan]{stats['storage_bytes'] / 1024 / 1024:.2f} MB[/cyan]"
            )
            console.print(
                f"Average chunk size: [cyan]{stats['avg_chunk_size']:.0f} chars[/cyan]"
            )

            if stats["oldest_entry"]:
                console.print(f"Oldest entry: [dim]{stats['oldest_entry']}[/dim]")
            if stats["newest_entry"]:
                console.print(f"Newest entry: [dim]{stats['newest_entry']}[/dim]")

            # Hit rate statistics from retriever if available
            try:
                # Import here to avoid circular dependency
                from rag.retriever import ResearchRetriever

                # Try to get hit rate from recent usage
                retriever_stats = ResearchRetriever.get_statistics()
                if retriever_stats:
                    console.print(
                        f"\n[bold]🎯 Cache Performance (Current Session):[/bold]"
                    )
                    console.print(
                        f"Total requests: [cyan]{retriever_stats['cache_requests']:,}[/cyan]"
                    )
                    console.print(
                        f"Cache hits: [green]{retriever_stats['cache_hits']:,}[/green] "
                        f"(Exact: {retriever_stats['exact_hits']}, Semantic: {retriever_stats['semantic_hits']})"
                    )
                    console.print(
                        f"Cache misses: [yellow]{retriever_stats['cache_misses']:,}[/yellow]"
                    )
                    console.print(
                        f"Hit rate: [{'green' if retriever_stats['hit_rate'] > 0.5 else 'yellow'}]"
                        f"{retriever_stats['hit_rate']:.1%}[/{'green' if retriever_stats['hit_rate'] > 0.5 else 'yellow'}]"
                    )
                    console.print(
                        f"Avg response time: [cyan]{retriever_stats['avg_retrieval_time']:.3f}s[/cyan]"
                    )

                    # Cost savings estimate
                    if retriever_stats["cache_hits"] > 0:
                        # Estimate $0.04 per API call saved
                        savings = retriever_stats["cache_hits"] * 0.04
                        console.print(
                            f"Estimated savings: [green]${savings:.2f}[/green]"
                        )
            except Exception as e:
                # Statistics not available in this session
                logger.debug(f"Could not get retriever statistics: {e}")
                pass

            if detailed:
                console.print(f"\n[bold]Detailed Breakdown:[/bold]")

                # Get keyword distribution
                keyword_stats = await storage.get_keyword_distribution(limit=10)

                if keyword_stats:
                    console.print("\n[yellow]Top 10 Cached Keywords:[/yellow]")
                    for keyword, count in keyword_stats:
                        console.print(f"  • {keyword}: [cyan]{count}[/cyan] chunks")

                # Storage breakdown
                console.print(f"\n[yellow]Storage Details:[/yellow]")
                console.print(
                    f"  • Research chunks: [cyan]{stats.get('research_chunks', 0):,}[/cyan]"
                )
                console.print(
                    f"  • Cache entries: [cyan]{stats.get('cache_entries', 0):,}[/cyan]"
                )
                console.print(
                    f"  • Total embeddings: [cyan]{stats.get('total_embeddings', 0):,}[/cyan]"
                )

    except Exception as e:
        console.print(f"[red]❌ Failed to get statistics: {e}[/red]")
        raise click.exceptions.Exit(1)


async def handle_cache_clear(
    older_than: Optional[int], keyword: Optional[str], force: bool, dry_run: bool
):
    """Clear cache entries based on criteria."""
    try:
        rag_config = get_rag_config()

        async with VectorStorage(rag_config) as storage:
            # First, show what will be cleared
            if older_than:
                console.print(
                    f"\n[yellow]Will clear entries older than {older_than} days[/yellow]"
                )
            elif keyword:
                console.print(
                    f"\n[yellow]Will clear entries for keyword: '{keyword}'[/yellow]"
                )
            else:
                console.print("\n[red]Will clear ALL cache entries![/red]")

            if dry_run:
                console.print("[dim]DRY RUN - No entries will be deleted[/dim]")

                # Get stats about what would be cleared
                stats = await storage.get_cache_stats()
                console.print(
                    f"\nWould clear approximately [cyan]{stats['total_entries']:,}[/cyan] entries"
                )
                return

            # Confirm unless forced
            if not force:
                if not click.confirm("\nAre you sure you want to proceed?"):
                    console.print("[yellow]Cancelled.[/yellow]")
                    return

            # Perform cleanup
            deleted_count = await storage.cleanup_cache(
                older_than_days=older_than, keyword=keyword
            )

            console.print(
                f"\n[green]✅ Cleared {deleted_count:,} cache entries[/green]"
            )

    except Exception as e:
        console.print(f"[red]❌ Clear operation failed: {e}[/red]")
        raise click.exceptions.Exit(1)


async def handle_cache_warm(topic: str, variations: int, verbose: bool):
    """Warm the cache by researching topic variations."""
    try:
        from research_agent import create_research_agent, run_research_agent

        config = get_config()

        console.print(f"\n[bold blue]🔥 Warming cache for topic: '{topic}'[/bold blue]")
        console.print(f"[dim]Generating {variations} keyword variations...[/dim]\n")

        # Generate keyword variations
        keywords = [topic]  # Start with original

        # Simple variations (in production, could use LLM for better variations)
        base_variations = [
            f"{topic} benefits",
            f"{topic} research",
            f"{topic} studies",
            f"latest {topic}",
            f"{topic} science",
            f"{topic} evidence",
        ]

        # Take requested number of variations
        keywords.extend(base_variations[: variations - 1])

        # Create research agent
        research_agent = create_research_agent(config)
        success_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            main_task = progress.add_task(
                f"[cyan]Researching {len(keywords)} keywords", total=len(keywords)
            )

            for i, keyword in enumerate(keywords):
                progress.update(main_task, description=f"[cyan]Researching: {keyword}")

                try:
                    if verbose:
                        console.print(f"\n[dim]Researching '{keyword}'...[/dim]")

                    # Run research (will automatically cache)
                    result = await run_research_agent(research_agent, keyword)

                    if result:
                        success_count += 1
                        if verbose:
                            console.print(
                                f"[green]✓ Cached research for '{keyword}'[/green]"
                            )

                except Exception as e:
                    if verbose:
                        console.print(
                            f"[red]✗ Failed to research '{keyword}': {e}[/red]"
                        )

                progress.advance(main_task)

        console.print(f"\n[bold green]✅ Cache warming complete![/bold green]")
        console.print(
            f"Successfully cached: [cyan]{success_count}/{len(keywords)}[/cyan] keywords"
        )

    except Exception as e:
        console.print(f"[red]❌ Cache warming failed: {e}[/red]")
        raise click.exceptions.Exit(1)


async def handle_export_cache_metrics(format: str, output_path: Optional[Path]):
    """Export cache metrics in specified format."""
    try:
        rag_config = get_rag_config()

        # Collect all metrics
        async with VectorStorage(rag_config) as storage:
            stats = await storage.get_cache_stats()

            # Add retriever stats if available
            try:
                from rag.retriever import ResearchRetriever

                retriever_stats = ResearchRetriever.get_statistics()
                if retriever_stats:
                    stats["cache_performance"] = retriever_stats
            except Exception:
                pass

            # Format output based on requested format
            if format == "json":
                output_data = json.dumps(stats, indent=2, default=str)
            elif format == "csv":
                # Simple CSV format
                lines = ["metric,value"]
                for key, value in stats.items():
                    if isinstance(value, (int, float, str)):
                        lines.append(f"{key},{value}")
                output_data = "\n".join(lines)
            elif format == "prometheus":
                # Prometheus exposition format
                lines = []
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        metric_name = f"seo_cache_{key}"
                        lines.append(f"# TYPE {metric_name} gauge")
                        lines.append(f"{metric_name} {value}")
                output_data = "\n".join(lines)
            else:
                raise ValueError(f"Unknown format: {format}")

            # Write output
            if output_path:
                output_path.write_text(output_data)
                console.print(
                    f"[green]✅ Metrics exported to {output_path}[/green]"
                )
            else:
                console.print(output_data)

    except Exception as e:
        console.print(f"[red]❌ Failed to export metrics: {e}[/red]")
        raise click.exceptions.Exit(1)