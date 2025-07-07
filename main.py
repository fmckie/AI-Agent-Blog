"""
Main entry point for the SEO Content Automation System.

This module provides the CLI interface for users to generate
SEO-optimized articles by providing keywords.
"""

# Import required libraries
import asyncio
import json
import logging
from datetime import datetime, timezone
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
from rag.config import get_rag_config
from rag.retriever import ResearchRetriever
from rag.storage import VectorStorage
from workflow import WorkflowOrchestrator

# Import CLI handlers
from cli.cache_handlers import (
    handle_cache_search,
    handle_cache_stats,
    handle_cache_clear,
    handle_cache_warm,
    handle_export_cache_metrics,
)

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


@cli.command()
@click.argument("keywords", nargs=-1, required=True, type=str)
@click.option(
    "-o", "--output-dir", type=Path, help="Output directory for generated articles"
)
@click.option(
    "--parallel",
    "-p",
    default=1,
    type=int,
    help="Number of keywords to process in parallel (default: 1)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Research only (no article generation)",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue processing remaining keywords if one fails",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show progress bar during batch processing",
)
def batch(
    keywords: tuple,
    output_dir: Optional[Path],
    parallel: int,
    dry_run: bool,
    continue_on_error: bool,
    progress: bool,
):
    """
    Generate articles for multiple keywords in batch.

    Process multiple keywords efficiently with optional parallel execution.
    Failed keywords are reported at the end.

    \b
    Examples:
        # Process multiple keywords sequentially
        $ seo-content batch "keto diet" "intermittent fasting" "low carb"

        # Process 3 keywords in parallel
        $ seo-content batch "diabetes" "insulin" "blood sugar" --parallel 3

        # Continue even if some keywords fail
        $ seo-content batch "topic1" "topic2" "topic3" --continue-on-error

        # Research only (no articles)
        $ seo-content batch "keyword1" "keyword2" --dry-run

        # Custom output directory
        $ seo-content batch "seo1" "seo2" -o ./batch-output

    \b
    Performance Tips:
        - Use --parallel 2-3 for optimal performance
        - Too many parallel tasks may hit API rate limits
        - Monitor system resources with many keywords
    """
    if not keywords:
        console.print("[red]❌ No keywords provided[/red]")
        raise click.exceptions.Exit(1)

    # Validate parallel count
    if parallel < 1:
        console.print("[red]❌ Parallel count must be at least 1[/red]")
        raise click.exceptions.Exit(1)
    elif parallel > 5:
        console.print(
            "[yellow]⚠️  Warning: High parallel count may cause rate limiting[/yellow]"
        )

    # Show batch summary
    console.print(f"\n[bold]📦 Batch Processing {len(keywords)} Keywords[/bold]")
    console.print(f"Parallel execution: [cyan]{parallel}[/cyan]")
    console.print(f"Continue on error: [cyan]{continue_on_error}[/cyan]")
    console.print(
        f"Mode: [cyan]{'Research only' if dry_run else 'Full generation'}[/cyan]"
    )

    if output_dir:
        console.print(f"Output directory: [cyan]{output_dir}[/cyan]")

    console.print("\nKeywords to process:")
    for i, keyword in enumerate(keywords, 1):
        console.print(f"  {i}. {keyword}")

    # Run the batch processing
    try:
        asyncio.run(
            _run_batch_generation(
                keywords, output_dir, parallel, dry_run, continue_on_error, progress
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Batch processing cancelled by user[/yellow]")
        raise click.Abort()
    except Exception as e:
        logger.exception("Batch processing failed")
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise click.exceptions.Exit(1)


async def _run_batch_generation(
    keywords: tuple,
    output_dir: Optional[Path],
    parallel: int,
    dry_run: bool,
    continue_on_error: bool,
    show_progress: bool,
):
    """Run batch generation with parallel processing."""
    # Get configuration
    config = get_config()

    # Override output directory if specified
    if output_dir:
        config.output_dir = output_dir

    # Track results
    results = {"success": [], "failed": [], "skipped": []}

    # Create semaphore for parallel execution
    semaphore = asyncio.Semaphore(parallel)

    async def process_keyword(keyword: str, index: int):
        """Process a single keyword with rate limiting."""
        async with semaphore:
            try:
                # Create workflow orchestrator
                orchestrator = WorkflowOrchestrator(config)

                # Update progress if showing
                if show_progress and progress_bar:
                    progress_bar.update(
                        batch_task, description=f"[cyan]Processing: {keyword}"
                    )

                # Run the workflow
                if dry_run:
                    findings = await orchestrator.run_research(keyword)
                    results["success"].append(
                        {"keyword": keyword, "sources": findings.total_sources_analyzed}
                    )
                else:
                    article_path = await orchestrator.run_full_workflow(keyword)
                    results["success"].append(
                        {"keyword": keyword, "path": str(article_path)}
                    )

                # Update progress
                if show_progress and progress_bar:
                    progress_bar.advance(batch_task)

            except Exception as e:
                logger.error(f"Failed to process '{keyword}': {e}")
                results["failed"].append({"keyword": keyword, "error": str(e)})

                if show_progress and progress_bar:
                    progress_bar.advance(batch_task)

                if not continue_on_error:
                    raise

    # Set up progress tracking
    progress_bar = None
    batch_task = None

    if show_progress:
        progress_bar = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )

        with progress_bar:
            batch_task = progress_bar.add_task(
                "[bold blue]Processing keywords", total=len(keywords)
            )

            # Create tasks for all keywords
            tasks = [process_keyword(keyword, i) for i, keyword in enumerate(keywords)]

            # Run all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
    else:
        # No progress bar
        tasks = [process_keyword(keyword, i) for i, keyword in enumerate(keywords)]

        await asyncio.gather(*tasks, return_exceptions=True)

    # Show results summary
    console.print("\n[bold]📊 Batch Processing Summary[/bold]")
    console.print(f"✅ Successful: [green]{len(results['success'])}[/green]")
    console.print(f"❌ Failed: [red]{len(results['failed'])}[/red]")

    if results["success"]:
        console.print("\n[bold green]Successful generations:[/bold green]")
        for item in results["success"]:
            if "path" in item:
                console.print(f"  • {item['keyword']} → {item['path']}")
            else:
                console.print(
                    f"  • {item['keyword']} → {item['sources']} sources found"
                )

    if results["failed"]:
        console.print("\n[bold red]Failed generations:[/bold red]")
        for item in results["failed"]:
            console.print(f"  • {item['keyword']}: {item['error']}")

    # Exit with error if any failed and not continuing on error
    if results["failed"] and not continue_on_error:
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
    default=0.5,
    type=float,
    help="Similarity threshold (0-1, default: 0.5)",
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
    asyncio.run(handle_cache_search(query, limit, threshold))




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
    asyncio.run(handle_cache_stats(detailed))




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
    asyncio.run(handle_cache_clear(older_than, keyword, force, dry_run))




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
    asyncio.run(handle_cache_warm(topic, variations, verbose))




@cache.command("metrics")
@click.option(
    "--format",
    type=click.Choice(["json", "csv", "prometheus"], case_sensitive=False),
    default="json",
    help="Output format for metrics",
)
@click.option(
    "--output",
    "-o",
    type=Path,
    help="Output file path (default: stdout)",
)
def cache_metrics(format: str, output: Optional[Path]):
    """
    Export cache metrics for monitoring and analysis.

    Exports detailed cache performance metrics in various formats
    suitable for monitoring systems and dashboards.

    \b
    Examples:
        # Export as JSON to stdout
        $ seo-content cache metrics

        # Export as CSV to file
        $ seo-content cache metrics --format csv -o metrics.csv

        # Export in Prometheus format
        $ seo-content cache metrics --format prometheus

    \b
    Formats:
        - json: Standard JSON format
        - csv: Comma-separated values for spreadsheets
        - prometheus: Prometheus exposition format
    """
    asyncio.run(handle_export_cache_metrics(format, output))


@cli.group()
def drive():
    """
    Manage Google Drive integration.

    These commands help you authenticate, upload articles, and manage
    your Google Drive integration for the SEO content system.

    \b
    Examples:
        # Authenticate with Google Drive
        $ seo-content drive auth

        # Upload a specific article
        $ seo-content drive upload ./drafts/keyword_20250107_120000/article.html

        # List uploaded articles
        $ seo-content drive list

        # Check sync status
        $ seo-content drive status
    """
    pass


@drive.command("auth")
def drive_auth():
    """
    Authenticate with Google Drive.

    This will open a browser window for OAuth authentication.
    The authentication token will be saved for future use.

    \b
    Examples:
        # First-time authentication
        $ seo-content drive auth

        # Re-authenticate (if token expired)
        $ seo-content drive auth
    """
    console.print("[bold]🔐 Google Drive Authentication[/bold]\n")
    
    try:
        from rag.drive.auth import GoogleDriveAuth
        
        # Initialize auth
        auth = GoogleDriveAuth()
        
        console.print("Opening browser for authentication...")
        console.print("[dim]If browser doesn't open, check the console for the URL[/dim]\n")
        
        # Perform authentication
        auth.authenticate()
        
        # Test the connection
        if auth.test_connection():
            console.print("[green]✅ Successfully authenticated with Google Drive![/green]")
            console.print("\nYou can now use Drive features like automatic upload.")
        else:
            console.print("[red]❌ Authentication succeeded but connection test failed[/red]")
            console.print("Please check your credentials and try again.")
            
    except FileNotFoundError as e:
        console.print(f"[red]❌ Credentials file not found: {e}[/red]")
        console.print("\n[yellow]Please ensure you have:[/yellow]")
        console.print("1. Created OAuth credentials in Google Cloud Console")
        console.print("2. Downloaded the credentials.json file")
        console.print("3. Placed it in your project root or specified path")
    except Exception as e:
        console.print(f"[red]❌ Authentication failed: {e}[/red]")
        raise click.exceptions.Exit(1)


@drive.command("upload")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--title", "-t",
    help="Custom title for the document (defaults to filename)"
)
@click.option(
    "--folder", "-f",
    help="Target folder path in Drive (e.g., '2025/01/07')"
)
def drive_upload(file_path: Path, title: Optional[str], folder: Optional[str]):
    """
    Upload a file to Google Drive.

    FILE_PATH is the path to the HTML file to upload.

    \b
    Examples:
        # Upload an article
        $ seo-content drive upload ./drafts/keyword_20250107/article.html

        # Upload with custom title
        $ seo-content drive upload article.html --title "My SEO Article"

        # Upload to specific folder
        $ seo-content drive upload article.html --folder "2025/01/Articles"
    """
    console.print(f"[bold]📤 Uploading to Google Drive[/bold]\n")
    console.print(f"File: [cyan]{file_path}[/cyan]")
    
    try:
        from rag.drive.auth import GoogleDriveAuth
        from rag.drive.uploader import ArticleUploader
        
        # Initialize components
        auth = GoogleDriveAuth()
        uploader = ArticleUploader(auth=auth)
        
        # Read file content
        if file_path.suffix == ".html":
            content = file_path.read_text(encoding="utf-8")
        else:
            console.print("[red]❌ Only HTML files are supported[/red]")
            raise click.exceptions.Exit(1)
        
        # Determine title
        doc_title = title or file_path.stem.replace("_", " ").title()
        
        # Upload with progress
        with console.status(f"Uploading '{doc_title}'...") as status:
            result = uploader.upload_html_as_doc(
                html_content=content,
                title=doc_title,
                folder_path=folder
            )
        
        if result:
            console.print(f"\n[green]✅ Upload successful![/green]")
            console.print(f"📄 Document: [cyan]{result['name']}[/cyan]")
            console.print(f"🔗 View at: [link]{result['web_link']}[/link]")
            console.print(f"🗂️  Folder: [dim]{result['folder_path']}[/dim]")
        else:
            console.print("[red]❌ Upload failed[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Upload error: {e}[/red]")
        raise click.exceptions.Exit(1)


@drive.command("list")
@click.option(
    "--limit", "-l",
    default=20,
    help="Maximum number of articles to show (default: 20)"
)
@click.option(
    "--json", "as_json",
    is_flag=True,
    help="Output as JSON"
)
def drive_list(limit: int, as_json: bool):
    """
    List articles uploaded to Google Drive.

    Shows recently uploaded articles with their Drive links and metadata.

    \b
    Examples:
        # List recent uploads
        $ seo-content drive list

        # Show more results
        $ seo-content drive list --limit 50

        # Export as JSON
        $ seo-content drive list --json > uploads.json
    """
    try:
        from rag.drive.storage import DriveStorageHandler
        
        # Get uploaded articles
        storage = DriveStorageHandler()
        articles = storage.get_uploaded_articles(limit=limit)
        
        if as_json:
            # Output as JSON
            import json
            print(json.dumps(articles, indent=2, default=str))
        else:
            # Pretty print
            console.print(f"[bold]📋 Uploaded Articles (Latest {limit})[/bold]\n")
            
            if not articles:
                console.print("[dim]No uploaded articles found[/dim]")
                return
            
            for article in articles:
                console.print(f"[bold]{article['title']}[/bold]")
                console.print(f"  Keyword: [cyan]{article['keyword']}[/cyan]")
                console.print(f"  Uploaded: {article['uploaded_at']}")
                console.print(f"  Drive: [link]{article['drive_url']}[/link]")
                console.print()
                
    except Exception as e:
        console.print(f"[red]❌ Error listing articles: {e}[/red]")
        raise click.exceptions.Exit(1)


@drive.command("status")
@click.option(
    "--detailed", "-d",
    is_flag=True,
    help="Show detailed sync information"
)
def drive_status(detailed: bool):
    """
    Check Google Drive sync status.

    Shows authentication status, configuration, and sync statistics.

    \b
    Examples:
        # Basic status check
        $ seo-content drive status

        # Detailed information
        $ seo-content drive status --detailed
    """
    console.print("[bold]📊 Google Drive Status[/bold]\n")
    
    try:
        from rag.drive.auth import GoogleDriveAuth
        from rag.drive.storage import DriveStorageHandler
        from rag.config import get_rag_config
        
        # Check configuration
        config = get_config()
        rag_config = get_rag_config()
        
        console.print("[bold]Configuration:[/bold]")
        console.print(f"  Drive Enabled: {'✅' if rag_config.google_drive_enabled else '❌'}")
        console.print(f"  Auto Upload: {'✅' if rag_config.google_drive_auto_upload else '❌'}")
        console.print(f"  Upload Folder ID: {'✅ Set' if config.google_drive_upload_folder_id else '❌ Not set'}")
        console.print()
        
        # Check authentication
        console.print("[bold]Authentication:[/bold]")
        try:
            auth = GoogleDriveAuth()
            if auth.is_authenticated:
                console.print("  Status: [green]✅ Authenticated[/green]")
                if auth.test_connection():
                    console.print("  Connection: [green]✅ Active[/green]")
                else:
                    console.print("  Connection: [red]❌ Failed[/red]")
            else:
                console.print("  Status: [yellow]⚠️  Not authenticated[/yellow]")
                console.print("  Run 'seo-content drive auth' to authenticate")
        except Exception as e:
            console.print(f"  Status: [red]❌ Error: {e}[/red]")
        
        console.print()
        
        # Show statistics
        console.print("[bold]Statistics:[/bold]")
        try:
            storage = DriveStorageHandler()
            
            # Count uploaded articles
            uploaded = storage.get_uploaded_articles(limit=1000)
            console.print(f"  Total Uploaded: [cyan]{len(uploaded)}[/cyan] articles")
            
            # Count pending uploads
            pending = storage.get_pending_uploads(limit=1000)
            console.print(f"  Pending Upload: [yellow]{len(pending)}[/yellow] articles")
            
            if detailed and uploaded:
                console.print("\n[bold]Recent Uploads:[/bold]")
                for article in uploaded[:5]:
                    console.print(f"  - {article['title']} ({article['uploaded_at']})")
                    
        except Exception as e:
            console.print(f"  [red]Error getting statistics: {e}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")
        raise click.exceptions.Exit(1)




# Main entry point
if __name__ == "__main__":
    cli()
