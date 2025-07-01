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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn

# Import our modules
from config import get_config
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
@click.option(
    "--dry-run", is_flag=True, help="Run research only, don't generate article"
)
def generate(keyword: str, output_dir: Optional[Path], verbose: bool, dry_run: bool):
    """
    Generate an SEO-optimized article for the given KEYWORD.

    This command will:
    1. Research the keyword using academic sources
    2. Generate an SEO-optimized article
    3. Save the output as HTML with metadata

    Example:
        seo-content generate "blood sugar management"
    """
    # Set verbose logging if requested
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Show what we're doing
    console.print(f"\n[bold blue]🔍 Researching '{keyword}'...[/bold blue]")

    try:
        # Create and run the workflow
        asyncio.run(_run_generation(keyword, output_dir, dry_run))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Generation cancelled by user[/yellow]")
        raise click.Abort()

    except Exception as e:
        logger.exception("Generation failed")
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise click.exceptions.Exit(1)


async def _run_generation(keyword: str, output_dir: Optional[Path], dry_run: bool):
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

    # Run the workflow with progress tracking
    if dry_run:
        # Research only with progress
        console.print("\n[yellow]Running in dry-run mode (research only)[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Add research task
            research_task = progress.add_task("[cyan]Researching academic sources...", total=None)
            
            # Set up progress callback
            orchestrator.set_progress_callback(lambda phase, msg: progress.update(research_task, description=f"[cyan]{msg}"))
            
            # Run research
            findings = await orchestrator.run_research(keyword)
            
            # Mark complete
            progress.update(research_task, description="[green]✓ Research completed!")

        # Display research results
        console.print("\n[bold green]✅ Research completed![/bold green]")
        console.print(findings.to_markdown_summary())

    else:
        # Full workflow with detailed progress
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
            main_task = progress.add_task("[bold blue]Generating SEO article", total=3)
            
            # Sub-tasks
            research_task = progress.add_task("[cyan]• Researching sources", total=None)
            writing_task = progress.add_task("[yellow]• Writing article", total=None, visible=False)
            saving_task = progress.add_task("[green]• Saving outputs", total=None, visible=False)
            
            # Create progress callback
            def update_progress(phase: str, message: str):
                if phase == "research":
                    progress.update(research_task, description=f"[cyan]• {message}")
                elif phase == "research_complete":
                    progress.update(research_task, description="[green]✓ Research complete")
                    progress.update(main_task, advance=1)
                    progress.update(writing_task, visible=True)
                elif phase == "writing":
                    progress.update(writing_task, description=f"[yellow]• {message}")
                elif phase == "writing_complete":
                    progress.update(writing_task, description="[green]✓ Article written")
                    progress.update(main_task, advance=1)
                    progress.update(saving_task, visible=True)
                elif phase == "saving":
                    progress.update(saving_task, description=f"[green]• {message}")
                elif phase == "complete":
                    progress.update(saving_task, description="[green]✓ Outputs saved")
                    progress.update(main_task, advance=1)
            
            # Set callback
            orchestrator.set_progress_callback(update_progress)
            
            # Run workflow
            article_path = await orchestrator.run_full_workflow(keyword)

        # Show success message
        console.print(f"\n[bold green]✅ Article generated successfully![/bold green]")
        console.print(f"📄 Output saved to: [cyan]{article_path}[/cyan]")
        console.print(f"\n[dim]Open the file in your browser to review.[/dim]")


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
        console.print(f"Found {len(state_files)} state files and {len(temp_dirs)} temp directories")
        
        if not dry_run:
            # Run actual cleanup
            cleaned_state, cleaned_dirs = asyncio.run(
                WorkflowOrchestrator.cleanup_orphaned_files(config.output_dir, older_than)
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
                    console.print(f"  • Would delete: {state_file.name} (age: {age_hours:.1f} hours)")
            
            for temp_dir in temp_dirs:
                if temp_dir.is_dir():
                    dir_time = datetime.fromtimestamp(temp_dir.stat().st_mtime)
                    age_hours = (current_time - dir_time).total_seconds() / 3600
                    if age_hours > older_than:
                        would_clean_dirs += 1
                        console.print(f"  • Would delete: {temp_dir.name} (age: {age_hours:.1f} hours)")
            
            console.print(f"\n[yellow]Would clean {would_clean_state} state files and {would_clean_dirs} temp directories[/yellow]")
            console.print("[dim]Run without --dry-run to actually clean these files[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Cleanup failed: {e}[/red]")
        raise click.exceptions.Exit(1)


# Main entry point
if __name__ == "__main__":
    cli()
