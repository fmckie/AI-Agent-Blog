"""
Main entry point for the SEO Content Automation System.

This module provides the CLI interface for users to generate
SEO-optimized articles by providing keywords.
"""

# Import required libraries
import asyncio
import click
from pathlib import Path
from typing import Optional
import logging
from rich.console import Console
from rich.logging import RichHandler

# Import our modules (to be implemented)
from config import get_config
from workflow import WorkflowOrchestrator

# Import temporary agent patches (to be removed in Phase 3/4)
import agent_patches

# Set up rich console for beautiful output
console = Console()

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
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
    help="Override output directory from config"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run research only, don't generate article"
)
def generate(
    keyword: str,
    output_dir: Optional[Path],
    verbose: bool,
    dry_run: bool
):
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


async def _run_generation(
    keyword: str,
    output_dir: Optional[Path],
    dry_run: bool
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
        
    # Create workflow orchestrator
    orchestrator = WorkflowOrchestrator(config)
    
    # Run the workflow
    if dry_run:
        # Research only
        console.print("\n[yellow]Running in dry-run mode (research only)[/yellow]")
        findings = await orchestrator.run_research(keyword)
        
        # Display research results
        console.print("\n[bold green]✅ Research completed![/bold green]")
        console.print(findings.to_markdown_summary())
        
    else:
        # Full workflow
        article_path = await orchestrator.run_full_workflow(keyword)
        
        # Show success message
        console.print(f"\n[bold green]✅ Article generated successfully![/bold green]")
        console.print(f"📄 Output saved to: [cyan]{article_path}[/cyan]")
        console.print(f"\n[dim]Open the file in your browser to review.[/dim]")


@cli.command()
@click.option(
    "--check",
    is_flag=True,
    help="Check if configuration is valid"
)
@click.option(
    "--show",
    is_flag=True,
    help="Show current configuration (hides sensitive values)"
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
        console.print("[dim]Check your .env file and ensure all required values are set.[/dim]")
        raise click.exceptions.Exit(1)


@cli.command()
def test():
    """
    Run a test generation with a sample keyword.
    
    This helps verify your setup is working correctly.
    """
    console.print("[bold]🧪 Running test generation...[/bold]")
    console.print("[dim]This will research 'artificial intelligence' as a test.[/dim]\n")
    
    # Run with test keyword
    ctx = click.get_current_context()
    ctx.invoke(generate, keyword="artificial intelligence", dry_run=True)


# Main entry point
if __name__ == "__main__":
    cli()