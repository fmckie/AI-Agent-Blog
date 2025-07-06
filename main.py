"""
Main entry point for the SEO Content Automation System.

This module provides the CLI interface for users to generate
SEO-optimized articles by providing keywords.
"""

# Import required libraries
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

# Import our modules
from config import get_config
from rag.retriever import ResearchRetriever
from rag.storage import VectorStorage
from workflow import WorkflowOrchestrator

# Set up rich console for beautiful output
console = Console()

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="SEO Content Automation")
def cli():
    """
    SEO Content Automation System - Generate optimized articles from academic research.

    This tool researches keywords using academic sources and generates
    SEO-optimized articles ready for publishing.

    \b
    Examples:
      # Generate an article about a topic
      $ seo-content generate "blood sugar management"

      # Run research only without generating article
      $ seo-content generate "keto diet benefits" --dry-run

      # Generate with verbose output
      $ seo-content generate "intermittent fasting" --verbose

      # Check your configuration
      $ seo-content config --check

      # Run a test to verify setup
      $ seo-content test

      # Clean up old workflow files
      $ seo-content cleanup

    \b
    Quick Start:
      1. Copy .env.example to .env
      2. Add your API keys (Tavily and OpenAI)
      3. Run: seo-content generate "your keyword"

    For more help on a command: seo-content COMMAND --help
    """
    # Load configuration at startup to catch errors early
    try:
        config = get_config()
        # Set logging level from config
        logging.getLogger().setLevel(config.log_level)
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("keyword", type=str)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Override output directory from config",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except errors")
@click.option(
    "--dry-run", is_flag=True, help="Run research only, don't generate article"
)
def generate(
    keyword: str, output_dir: Optional[Path], verbose: bool, quiet: bool, dry_run: bool
):
    """
    Generate an SEO-optimized article for the given KEYWORD.

    This command will:
    1. Research the keyword using academic sources
    2. Generate an SEO-optimized article
    3. Save the output as HTML with metadata

    \b
    Examples:
        # Basic usage
        $ seo-content generate "blood sugar management"

        # Research only (no article generation)
        $ seo-content generate "keto diet benefits" --dry-run

        # Custom output directory
        $ seo-content generate "intermittent fasting" -o ./my-articles

        # Verbose output for debugging
        $ seo-content generate "protein synthesis" --verbose

        # Combine multiple options
        $ seo-content generate "muscle building" -o ./output -v

    \b
    Output Structure:
        drafts/
        └── keyword_20250701_120000/
            ├── index.html      # Review interface
            ├── article.html    # Generated article
            └── research.json   # Research data

    \b
    Tips:
        - Use quotes around multi-word keywords
        - Keywords should be specific but not too narrow
        - Check logs in verbose mode if generation fails
    """
    # Handle conflicting verbose/quiet options
    if verbose and quiet:
        console.print(
            "[yellow]Warning: Both --verbose and --quiet specified. Using verbose mode.[/yellow]"
        )
        quiet = False

    # Set logging level based on flags
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also enable debug for all our modules
        logging.getLogger("workflow").setLevel(logging.DEBUG)
        logging.getLogger("research_agent").setLevel(logging.DEBUG)
        logging.getLogger("writer_agent").setLevel(logging.DEBUG)
        logging.getLogger("tools").setLevel(logging.DEBUG)
        console.print("[dim]Verbose mode enabled - showing detailed debug logs[/dim]")
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)
        # Disable console output for quiet mode
        console._quiet = True  # type: ignore

    # Show what we're doing (unless quiet)
    if not quiet:
        console.print(f"\n[bold blue]🔍 Researching '{keyword}'...[/bold blue]")

    try:
        # Create and run the workflow
        asyncio.run(_run_generation(keyword, output_dir, dry_run, quiet))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Generation cancelled by user[/yellow]")
        raise click.Abort()

    except Exception as e:
        logger.exception("Generation failed")
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise click.exceptions.Exit(1)


async def _run_generation(
    keyword: str, output_dir: Optional[Path], dry_run: bool, quiet: bool = False
):
    """
    Internal async function to run the generation workflow.

    Args:
        keyword: The keyword to research and write about
        output_dir: Optional override for output directory
        dry_run: If True, only run research phase
    """
    # Get configuration
    config = get_config()

    # Override output directory if specified
    if output_dir:
        config.output_dir = output_dir

    # Create workflow orchestrator with progress callback
    orchestrator = WorkflowOrchestrator(config)

    # In verbose mode, show configuration details
    if logging.getLogger().level == logging.DEBUG:
        logger.debug(f"Configuration loaded:")
        logger.debug(f"  - Output directory: {config.output_dir}")
        logger.debug(f"  - LLM Model: {config.llm_model}")
        logger.debug(f"  - Tavily search depth: {config.tavily_search_depth}")
        logger.debug(f"  - Max retries: {config.max_retries}")
        logger.debug(f"  - Request timeout: {config.request_timeout}s")

    # Run the workflow with progress tracking
    if dry_run:
        # Research only with progress
        if not quiet:
            console.print("\n[yellow]Running in dry-run mode (research only)[/yellow]")

        # Skip progress display in quiet mode
        if quiet:
            findings = await orchestrator.run_research(keyword)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Add research task
                research_task = progress.add_task(
                    "[cyan]Researching academic sources...", total=None
                )

                # Set up progress callback
                orchestrator.set_progress_callback(
                    lambda phase, msg: progress.update(
                        research_task, description=f"[cyan]{msg}"
                    )
                )

                # Run research
                findings = await orchestrator.run_research(keyword)

                # Mark complete
                progress.update(
                    research_task, description="[green]✓ Research completed!"
                )

        # Display research results (unless quiet)
        if not quiet:
            console.print("\n[bold green]✅ Research completed![/bold green]")
            console.print(findings.to_markdown_summary())

    else:
        # Full workflow with detailed progress
        if quiet:
            # Run without progress display
            article_path = await orchestrator.run_full_workflow(keyword)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                # Add main task
                main_task = progress.add_task(
                    "[bold blue]Generating SEO article", total=3
                )

                # Sub-tasks
                research_task = progress.add_task(
                    "[cyan]• Researching sources", total=None
                )
                writing_task = progress.add_task(
                    "[yellow]• Writing article", total=None, visible=False
                )
                saving_task = progress.add_task(
                    "[green]• Saving outputs", total=None, visible=False
                )

                # Create progress callback
                def update_progress(phase: str, message: str):
                    if phase == "research":
                        progress.update(research_task, description=f"[cyan]• {message}")
                    elif phase == "research_complete":
                        progress.update(
                            research_task, description="[green]✓ Research complete"
                        )
                        progress.update(main_task, advance=1)
                        progress.update(writing_task, visible=True)
                    elif phase == "writing":
                        progress.update(
                            writing_task, description=f"[yellow]• {message}"
                        )
                    elif phase == "writing_complete":
                        progress.update(
                            writing_task, description="[green]✓ Article written"
                        )
                        progress.update(main_task, advance=1)
                        progress.update(saving_task, visible=True)
                    elif phase == "saving":
                        progress.update(saving_task, description=f"[green]• {message}")
                    elif phase == "complete":
                        progress.update(
                            saving_task, description="[green]✓ Outputs saved"
                        )
                        progress.update(main_task, advance=1)

                # Set callback
                orchestrator.set_progress_callback(update_progress)

                # Run workflow
                article_path = await orchestrator.run_full_workflow(keyword)

        # Show success message (unless quiet)
        if not quiet:
            console.print(
                f"\n[bold green]✅ Article generated successfully![/bold green]"
            )
            console.print(f"📄 Output saved to: [cyan]{article_path}[/cyan]")
            console.print(f"\n[dim]Open the file in your browser to review.[/dim]")
        elif quiet:
            # In quiet mode, just print the output path
            click.echo(str(article_path))


@cli.command()
@click.option("--check", is_flag=True, help="Check if configuration is valid")
@click.option(
    "--show", is_flag=True, help="Show current configuration (hides sensitive values)"
)
def config(check: bool, show: bool):
    """
    Manage system configuration.

    Use --check to validate your configuration.
    Use --show to display current settings.
    """
    try:
        cfg = get_config()

        if check:
            # Validate configuration
            console.print("[bold green]✅ Configuration is valid![/bold green]")
            console.print(f"  • Tavily API key: [dim]{'*' * 20}[/dim]")
            console.print(f"  • OpenAI API key: [dim]{'*' * 20}[/dim]")
            console.print(f"  • Output directory: {cfg.output_dir}")

        if show:
            # Show configuration (hiding sensitive values)
            console.print("\n[bold]Current Configuration:[/bold]")
            console.print(f"  • LLM Model: {cfg.llm_model}")
            console.print(f"  • Output Directory: {cfg.output_dir}")
            console.print(f"  • Log Level: {cfg.log_level}")
            console.print(f"  • Max Retries: {cfg.max_retries}")
            console.print(f"  • Request Timeout: {cfg.request_timeout}s")
            console.print(f"  • Tavily Search Depth: {cfg.tavily_search_depth}")
            console.print(f"  • Tavily Include Domains: {cfg.tavily_include_domains}")
            console.print(f"  • Tavily Max Results: {cfg.tavily_max_results}")

    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/red]")
        console.print(
            "[dim]Check your .env file and ensure all required values are set.[/dim]"
        )
        raise click.exceptions.Exit(1)


@cli.command()
def test():
    """
    Run a test generation with a sample keyword.

    This helps verify your setup is working correctly.
    """
    console.print("[bold]🧪 Running test generation...[/bold]")
    console.print(
        "[dim]This will research 'artificial intelligence' as a test.[/dim]\n"
    )

    # Run with test keyword
    ctx = click.get_current_context()
    ctx.invoke(generate, keyword="artificial intelligence", dry_run=True)


@cli.command()
@click.option(
    "--older-than",
    default=24,
    help="Clean up files older than this many hours (default: 24)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually deleting",
)
def cleanup(older_than: int, dry_run: bool):
    """
    Clean up orphaned workflow files and temporary directories.

    This command removes:
    - Old workflow state files (.workflow_state_*.json)
    - Old temporary directories (.temp_*)

    By default, only files older than 24 hours are cleaned.
    """
    try:
        config = get_config()

        console.print(f"\n[bold]🧹 Cleaning up old workflow files...[/bold]")
        console.print(f"[dim]Looking for files older than {older_than} hours[/dim]\n")

        if dry_run:
            console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]\n")

        # Count files before cleanup
        state_files = list(config.output_dir.glob(".workflow_state_*.json"))
        temp_dirs = list(config.output_dir.glob(".temp_*"))

        if not state_files and not temp_dirs:
            console.print("[green]✨ No cleanup needed - everything is tidy![/green]")
            return

        # Show what will be cleaned
        console.print(
            f"Found {len(state_files)} state files and {len(temp_dirs)} temp directories"
        )

        if not dry_run:
            # Run actual cleanup
            cleaned_state, cleaned_dirs = asyncio.run(
                WorkflowOrchestrator.cleanup_orphaned_files(
                    config.output_dir, older_than
                )
            )

            console.print(f"\n[green]✅ Cleanup complete![/green]")
            console.print(f"  • Removed {cleaned_state} state files")
            console.print(f"  • Removed {cleaned_dirs} temp directories")
        else:
            # Dry run - just show what would be cleaned
            current_time = datetime.now()
            would_clean_state = 0
            would_clean_dirs = 0

            for state_file in state_files:
                file_time = datetime.fromtimestamp(state_file.stat().st_mtime)
                age_hours = (current_time - file_time).total_seconds() / 3600
                if age_hours > older_than:
                    would_clean_state += 1
                    console.print(
                        f"  • Would delete: {state_file.name} (age: {age_hours:.1f} hours)"
                    )

            for temp_dir in temp_dirs:
                if temp_dir.is_dir():
                    dir_time = datetime.fromtimestamp(temp_dir.stat().st_mtime)
                    age_hours = (current_time - dir_time).total_seconds() / 3600
                    if age_hours > older_than:
                        would_clean_dirs += 1
                        console.print(
                            f"  • Would delete: {temp_dir.name} (age: {age_hours:.1f} hours)"
                        )

            console.print(
                f"\n[yellow]Would clean {would_clean_state} state files and {would_clean_dirs} temp directories[/yellow]"
            )
            console.print(
                "[dim]Run without --dry-run to actually clean these files[/dim]"
            )

    except Exception as e:
        console.print(f"[red]❌ Cleanup failed: {e}[/red]")
        raise click.exceptions.Exit(1)


@cli.group()
def cache():
    """
    Manage the research cache system.

    The cache stores research findings to reduce API costs and improve performance.
    Use these commands to search, analyze, and maintain the cache.

    \b
    Examples:
        # Search for cached research
        $ seo-content cache search "blood sugar"

        # View cache statistics
        $ seo-content cache stats

        # Clear old cache entries
        $ seo-content cache clear --older-than 30

        # Pre-populate cache with research
        $ seo-content cache warm "diabetes management"
    """
    pass


@cache.command("search")
@click.argument("query", type=str)
@click.option("--limit", "-l", default=10, help="Maximum results to show (default: 10)")
@click.option(
    "--threshold",
    "-t",
    default=0.7,
    type=float,
    help="Similarity threshold (0-1, default: 0.7)",
)
def cache_search(query: str, limit: int, threshold: float):
    """
    Search the cache for research related to QUERY.

    This performs semantic search to find cached research similar to your query.
    Results are ranked by similarity score.

    \b
    Examples:
        # Basic search
        $ seo-content cache search "insulin resistance"

        # Show more results
        $ seo-content cache search "keto diet" --limit 20

        # Adjust similarity threshold (stricter)
        $ seo-content cache search "fasting" --threshold 0.8
    """
    asyncio.run(_cache_search(query, limit, threshold))


async def _cache_search(query: str, limit: int, threshold: float):
    """Execute cache search asynchronously."""
    try:
        config = get_config()

        # Create storage instance
        async with VectorStorage(config) as storage:
            # Create embeddings generator
            from rag.embeddings import EmbeddingGenerator

            embeddings = EmbeddingGenerator()

            console.print(f"\n[bold blue]🔍 Searching cache for: '{query}'[/bold blue]")

            # Generate embedding for query
            query_embedding = await embeddings.generate_embedding(query)

            # Search for similar content
            results = await storage.search_similar(
                query_embedding=query_embedding,
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


@cache.command("stats")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed statistics")
def cache_stats(detailed: bool):
    """
    Display cache statistics and performance metrics.

    Shows cache hit rates, storage usage, and other metrics.
    Use --detailed for more comprehensive statistics.

    \b
    Examples:
        # Basic statistics
        $ seo-content cache stats

        # Detailed breakdown
        $ seo-content cache stats --detailed
    """
    asyncio.run(_cache_stats(detailed))


async def _cache_stats(detailed: bool):
    """Get and display cache statistics."""
    try:
        config = get_config()

        async with VectorStorage(config) as storage:
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
                # Try to get hit rate from recent usage
                retriever_stats = ResearchRetriever.get_statistics()
                if retriever_stats:
                    console.print(f"\n[bold]Performance Metrics:[/bold]")
                    console.print(
                        f"Cache requests: [cyan]{retriever_stats['cache_requests']:,}[/cyan]"
                    )
                    console.print(
                        f"Cache hits: [green]{retriever_stats['cache_hits']:,}[/green]"
                    )
                    console.print(
                        f"Hit rate: [green]{retriever_stats['hit_rate']:.1%}[/green]"
                    )
                    console.print(
                        f"Avg retrieval time: [cyan]{retriever_stats['avg_retrieval_time']:.3f}s[/cyan]"
                    )
            except:
                # Statistics not available in this session
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


@cache.command("clear")
@click.option("--older-than", "-o", type=int, help="Clear entries older than N days")
@click.option("--keyword", "-k", type=str, help="Clear entries for specific keyword")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be cleared without deleting"
)
def cache_clear(
    older_than: Optional[int], keyword: Optional[str], force: bool, dry_run: bool
):
    """
    Clear cache entries based on criteria.

    Use with caution - cleared entries cannot be recovered.
    By default, requires confirmation unless --force is used.

    \b
    Examples:
        # Clear entries older than 30 days
        $ seo-content cache clear --older-than 30

        # Clear all entries for a keyword
        $ seo-content cache clear --keyword "old topic"

        # Clear everything (requires confirmation)
        $ seo-content cache clear --force

        # Preview what would be cleared
        $ seo-content cache clear --older-than 7 --dry-run
    """
    asyncio.run(_cache_clear(older_than, keyword, force, dry_run))


async def _cache_clear(
    older_than: Optional[int], keyword: Optional[str], force: bool, dry_run: bool
):
    """Clear cache entries based on criteria."""
    try:
        config = get_config()

        async with VectorStorage(config) as storage:
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


@cache.command("warm")
@click.argument("topic", type=str)
@click.option(
    "--variations", "-v", default=3, help="Number of keyword variations to research"
)
@click.option("--verbose", is_flag=True, help="Show detailed progress")
def cache_warm(topic: str, variations: int, verbose: bool):
    """
    Pre-populate cache by researching a TOPIC.

    This command generates keyword variations and researches them,
    storing results in the cache for faster future access.

    \b
    Examples:
        # Basic cache warming
        $ seo-content cache warm "diabetes management"

        # Research more variations
        $ seo-content cache warm "heart health" --variations 5

        # Show detailed progress
        $ seo-content cache warm "nutrition" --verbose
    """
    asyncio.run(_cache_warm(topic, variations, verbose))


async def _cache_warm(topic: str, variations: int, verbose: bool):
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


# Main entry point
if __name__ == "__main__":
    cli()
