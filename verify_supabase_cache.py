#!/usr/bin/env python3
"""
Direct verification of Supabase cache data.

This script queries Supabase tables directly to show:
- Cache entries
- Research chunks
- Recent activity
"""

import asyncio
import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Load environment variables
load_dotenv()

# Set up console
console = Console()


def get_supabase_client() -> Client:
    """Create a Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    
    return create_client(url, key)


async def verify_cache_data():
    """Verify cache data in Supabase tables."""
    
    console.print(Panel.fit(
        "[bold]Supabase Cache Verification[/bold]\n"
        "Direct query of Supabase tables",
        border_style="blue"
    ))
    
    # Create Supabase client
    supabase = get_supabase_client()
    
    # 1. Check cache_entries table
    console.print("\n[bold yellow]1. Cache Entries Table[/bold yellow]")
    
    try:
        # Get all cache entries
        cache_response = supabase.table("cache_entries").select("*").execute()
        
        if cache_response.data:
            cache_table = Table(show_header=True, header_style="bold magenta")
            cache_table.add_column("Keyword", style="cyan", width=30)
            cache_table.add_column("Created", style="yellow")
            cache_table.add_column("Hits", style="green", justify="right")
            cache_table.add_column("Chunks", style="blue", justify="right")
            cache_table.add_column("Expires", style="red")
            
            for entry in cache_response.data:
                cache_table.add_row(
                    entry["keyword"][:30],
                    entry["created_at"][:16],
                    str(entry["hit_count"]),
                    str(len(entry.get("chunk_ids", []))),
                    entry["expires_at"][:16]
                )
            
            console.print(cache_table)
            console.print(f"\n[green]Total cache entries: {len(cache_response.data)}[/green]")
        else:
            console.print("[yellow]No cache entries found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error querying cache_entries: {e}[/red]")
    
    # 2. Check research_chunks table
    console.print("\n[bold yellow]2. Research Chunks Table[/bold yellow]")
    
    try:
        # Get chunk statistics
        chunks_response = supabase.table("research_chunks").select("keyword, source_id").execute()
        
        if chunks_response.data:
            # Count chunks by keyword
            keyword_counts = {}
            source_counts = {}
            
            for chunk in chunks_response.data:
                keyword = chunk.get("keyword", "Unknown")
                source_id = chunk.get("source_id", "Unknown")
                
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                source_counts[source_id] = source_counts.get(source_id, 0) + 1
            
            # Display keyword statistics
            chunks_table = Table(show_header=True, header_style="bold magenta")
            chunks_table.add_column("Keyword", style="cyan")
            chunks_table.add_column("Chunks", style="green", justify="right")
            
            for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True):
                chunks_table.add_row(keyword, str(count))
            
            console.print(chunks_table)
            console.print(f"\n[green]Total chunks: {len(chunks_response.data)}[/green]")
            console.print(f"[green]Unique keywords: {len(keyword_counts)}[/green]")
            console.print(f"[green]Unique sources: {len(source_counts)}[/green]")
        else:
            console.print("[yellow]No research chunks found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error querying research_chunks: {e}[/red]")
    
    # 3. Recent activity
    console.print("\n[bold yellow]3. Recent Cache Activity (Last 5 entries)[/bold yellow]")
    
    try:
        # Get most recent cache entries
        recent_response = (
            supabase.table("cache_entries")
            .select("keyword, created_at, hit_count, research_summary")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        
        if recent_response.data:
            for i, entry in enumerate(recent_response.data, 1):
                console.print(f"\n[bold cyan]{i}. {entry['keyword']}[/bold cyan]")
                console.print(f"   Created: {entry['created_at']}")
                console.print(f"   Hits: {entry['hit_count']}")
                console.print(f"   Summary: {entry['research_summary'][:100]}...")
        else:
            console.print("[yellow]No recent activity[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error querying recent activity: {e}[/red]")
    
    # 4. Check if vector extension is working
    console.print("\n[bold yellow]4. Vector Extension Status[/bold yellow]")
    
    try:
        # Try to execute a simple vector query
        test_query = """
        SELECT COUNT(*) as vector_count 
        FROM research_chunks 
        WHERE embedding IS NOT NULL
        """
        
        # Note: Supabase client doesn't support raw SQL directly
        # We'll check if chunks have embeddings stored
        chunks_with_embeddings = (
            supabase.table("research_chunks")
            .select("id")
            .not_.is_("embedding", "null")
            .limit(1)
            .execute()
        )
        
        if chunks_with_embeddings.data:
            console.print("[green]✓ Vector embeddings are being stored[/green]")
        else:
            console.print("[yellow]⚠ No vector embeddings found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error checking vector status: {e}[/red]")


async def main():
    """Main runner."""
    try:
        await verify_cache_data()
        console.print("\n[bold green]✅ Verification complete![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Verification failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())