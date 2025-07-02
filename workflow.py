"""
Workflow orchestration for the SEO Content Automation System.

This module coordinates the execution of Research and Writer agents,
managing data flow and error handling throughout the pipeline.
"""

# Import required libraries
import asyncio
import json
import logging
import re
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import backoff

# Import our modules
from config import Config
from models import ArticleOutput, ResearchFindings
from research_agent import create_research_agent, run_research_agent
from writer_agent import create_writer_agent

# Set up logging
logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Enum representing the state of a workflow execution."""
    
    INITIALIZED = "initialized"
    RESEARCHING = "researching"
    RESEARCH_COMPLETE = "research_complete"
    WRITING = "writing"
    WRITING_COMPLETE = "writing_complete"
    SAVING = "saving"
    COMPLETE = "complete"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class WorkflowOrchestrator:
    """
    Orchestrates the content generation workflow.

    This class manages the flow from keyword research through
    article generation, handling errors and saving outputs.
    
    Can be used as a context manager for proper resource cleanup:
    
        async with WorkflowOrchestrator(config) as orchestrator:
            await orchestrator.run_full_workflow("keyword")
    """

    def __init__(self, config: Config):
        """
        Initialize the workflow orchestrator.

        Args:
            config: System configuration
        """
        self.config = config

        # Create agents (will be implemented in agents.py)
        self.research_agent = create_research_agent(config)
        self.writer_agent = create_writer_agent(config)

        # Set up output directory
        self.output_dir = config.output_dir
        
        # Transaction state tracking
        self.current_state = WorkflowState.INITIALIZED
        self.workflow_data: Dict[str, Any] = {}
        self.temp_output_dir: Optional[Path] = None
        self.state_file: Optional[Path] = None
        
        # Progress callback for CLI updates
        self.progress_callback: Optional[Callable[[str, str], None]] = None
        
        # Track resources for cleanup
        self._cleanup_required = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        logger.debug("Entering workflow orchestrator context")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit with cleanup.
        
        Ensures all resources are properly cleaned up, even on error.
        """
        logger.debug("Exiting workflow orchestrator context")
        
        # Clean up any remaining temp directories
        if self.temp_output_dir and self.temp_output_dir.exists():
            try:
                shutil.rmtree(self.temp_output_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_output_dir}")
            except Exception as e:
                logger.error(f"Failed to clean up temp directory: {e}")
        
        # Clean up state files if workflow didn't complete
        if self.current_state not in [WorkflowState.COMPLETE, WorkflowState.ROLLED_BACK]:
            if self.state_file and self.state_file.exists():
                try:
                    self.state_file.unlink()
                    logger.debug("Cleaned up incomplete state file")
                except Exception as e:
                    logger.error(f"Failed to clean up state file: {e}")
        
        # Don't suppress exceptions
        return False
    
    @classmethod
    async def cleanup_orphaned_files(cls, output_dir: Path, older_than_hours: int = 24):
        """
        Clean up orphaned state files and temp directories.
        
        Args:
            output_dir: The output directory to scan
            older_than_hours: Clean up files older than this many hours
            
        Returns:
            Tuple of (cleaned_state_files, cleaned_temp_dirs)
        """
        cleaned_state_files = 0
        cleaned_temp_dirs = 0
        current_time = datetime.now()
        
        try:
            # Clean up old state files
            for state_file in output_dir.glob(".workflow_state_*.json"):
                try:
                    # Check file age
                    file_time = datetime.fromtimestamp(state_file.stat().st_mtime)
                    age_hours = (current_time - file_time).total_seconds() / 3600
                    
                    if age_hours > older_than_hours:
                        state_file.unlink()
                        cleaned_state_files += 1
                        logger.info(f"Cleaned up old state file: {state_file.name}")
                except Exception as e:
                    logger.error(f"Failed to clean up {state_file}: {e}")
            
            # Clean up old temp directories
            for temp_dir in output_dir.glob(".temp_*"):
                if temp_dir.is_dir():
                    try:
                        # Check directory age
                        dir_time = datetime.fromtimestamp(temp_dir.stat().st_mtime)
                        age_hours = (current_time - dir_time).total_seconds() / 3600
                        
                        if age_hours > older_than_hours:
                            shutil.rmtree(temp_dir)
                            cleaned_temp_dirs += 1
                            logger.info(f"Cleaned up old temp directory: {temp_dir.name}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {temp_dir}: {e}")
            
            logger.info(f"Cleanup complete: {cleaned_state_files} state files, {cleaned_temp_dirs} temp directories")
            return cleaned_state_files, cleaned_temp_dirs
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0, 0

    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """
        Set a callback function for progress updates.
        
        Args:
            callback: Function that takes phase and message parameters
        """
        self.progress_callback = callback
        
    def _report_progress(self, phase: str, message: str):
        """
        Report progress to the callback if set.
        
        Args:
            phase: The current phase (research, writing, saving, etc.)
            message: The progress message
        """
        if self.progress_callback:
            self.progress_callback(phase, message)

    def _update_state(self, new_state: WorkflowState, data: Optional[Dict[str, Any]] = None):
        """
        Update the workflow state and optionally store data.
        
        Args:
            new_state: The new workflow state
            data: Optional data to store with the state change
        """
        # Log the state transition
        logger.info(f"Workflow state transition: {self.current_state.value} -> {new_state.value}")
        self.current_state = new_state
        
        # Update workflow data if provided
        if data:
            self.workflow_data.update(data)
            
        # Save state to disk for recovery
        if self.state_file:
            self._save_state()
    
    def _save_state(self):
        """Save current workflow state to disk for recovery."""
        try:
            state_data = {
                "state": self.current_state.value,
                "timestamp": datetime.now().isoformat(),
                "data": self.workflow_data,
                "temp_dir": str(self.temp_output_dir) if self.temp_output_dir else None
            }
            
            if self.state_file:
                self.state_file.write_text(json.dumps(state_data, indent=2, default=str))
                logger.debug(f"Saved workflow state to {self.state_file}")
                
        except Exception as e:
            logger.warning(f"Failed to save workflow state: {e}")
    
    def _load_state(self, state_file: Path) -> bool:
        """
        Load workflow state from disk.
        
        Args:
            state_file: Path to the state file
            
        Returns:
            True if state was loaded successfully, False otherwise
        """
        try:
            if state_file.exists():
                state_data = json.loads(state_file.read_text())
                self.current_state = WorkflowState(state_data["state"])
                self.workflow_data = state_data["data"]
                
                if state_data.get("temp_dir"):
                    self.temp_output_dir = Path(state_data["temp_dir"])
                    # Ensure the temp directory exists when loading state
                    self.temp_output_dir.mkdir(parents=True, exist_ok=True)
                    
                logger.info(f"Loaded workflow state: {self.current_state.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to load workflow state: {e}")
            
        return False
    
    async def _rollback(self):
        """
        Rollback any partial changes made during workflow execution.
        
        This method cleans up temporary files and resets the workflow state.
        """
        logger.warning("Rolling back workflow changes...")
        
        try:
            # Clean up temporary output directory if it exists
            if self.temp_output_dir and self.temp_output_dir.exists():
                shutil.rmtree(self.temp_output_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_output_dir}")
                
            # Delete state file
            if self.state_file and self.state_file.exists():
                self.state_file.unlink()
                logger.info("Removed workflow state file")
                
            # Update state to rolled back
            self.current_state = WorkflowState.ROLLED_BACK
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    async def resume_workflow(self, state_file: Path) -> Path:
        """
        Resume an interrupted workflow from a saved state.
        
        Args:
            state_file: Path to the workflow state file
            
        Returns:
            Path to the generated output
            
        Raises:
            Exception: If resume fails or state is unrecoverable
        """
        logger.info(f"Attempting to resume workflow from {state_file}")
        
        # Load the saved state
        if not self._load_state(state_file):
            raise ValueError(f"Failed to load workflow state from {state_file}")
            
        self.state_file = state_file
        keyword = self.workflow_data.get("keyword")
        
        if not keyword:
            raise ValueError("No keyword found in saved workflow state")
            
        try:
            # Resume based on current state
            if self.current_state == WorkflowState.RESEARCHING:
                # Restart research phase
                logger.info("Resuming from research phase...")
                research_findings = await self.run_research(keyword)
                self._update_state(WorkflowState.RESEARCH_COMPLETE, {
                    "research_complete_time": datetime.now().isoformat(),
                    "sources_found": len(research_findings.academic_sources)
                })
                
            elif self.current_state == WorkflowState.RESEARCH_COMPLETE:
                # Research is done, load it and continue to writing
                logger.info("Research complete, moving to writing phase...")
                # In a real implementation, we'd save research to state
                # For now, we'll need to re-run research
                research_findings = await self.run_research(keyword)
                
            elif self.current_state in [WorkflowState.WRITING, WorkflowState.WRITING_COMPLETE]:
                # Need both research and article, re-run both
                logger.info("Resuming from writing phase, re-running research first...")
                research_findings = await self.run_research(keyword)
                self._update_state(WorkflowState.RESEARCH_COMPLETE, {
                    "research_complete_time": datetime.now().isoformat(),
                    "sources_found": len(research_findings.academic_sources)
                })
                
            elif self.current_state == WorkflowState.SAVING:
                # Need all data, re-run everything
                logger.info("Resuming from save phase, re-running full workflow...")
                research_findings = await self.run_research(keyword)
                self._update_state(WorkflowState.RESEARCH_COMPLETE, {
                    "research_complete_time": datetime.now().isoformat(),
                    "sources_found": len(research_findings.academic_sources)
                })
                
            else:
                raise ValueError(f"Cannot resume from state: {self.current_state.value}")
                
            # Continue with remaining steps
            if self.current_state == WorkflowState.RESEARCH_COMPLETE:
                self._update_state(WorkflowState.WRITING)
                logger.info("Generating article...")
                article = await self.run_writing(keyword, research_findings)
                self._update_state(WorkflowState.WRITING_COMPLETE, {
                    "writing_complete_time": datetime.now().isoformat(),
                    "word_count": article.word_count
                })
                
            # Save outputs
            self._update_state(WorkflowState.SAVING)
            logger.info("Saving outputs...")
            output_path = await self._save_outputs_atomic(keyword, research_findings, article)
            
            # Mark as complete
            self._update_state(WorkflowState.COMPLETE, {
                "end_time": datetime.now().isoformat(),
                "output_path": str(output_path),
                "resumed": True
            })
            
            logger.info(f"Workflow resumed and completed successfully. Output: {output_path}")
            
            # Clean up state file
            if self.state_file and self.state_file.exists():
                self.state_file.unlink()
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to resume workflow: {e}")
            self._update_state(WorkflowState.FAILED, {
                "error": str(e),
                "failed_during_resume": True,
                "failure_time": datetime.now().isoformat()
            })
            await self._rollback()
            raise
            
    async def run_full_workflow(self, keyword: str) -> Path:
        """
        Run the complete workflow from research to article generation.

        Args:
            keyword: The keyword to research and write about

        Returns:
            Path to the generated article HTML file

        Raises:
            Exception: If any step in the workflow fails
        """
        logger.info(f"Starting full workflow for keyword: {keyword}")
        
        # Initialize workflow state tracking
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_keyword = re.sub(r'[^\w\-_]', '_', keyword).strip('_')
        self.state_file = self.output_dir / f".workflow_state_{safe_keyword}_{timestamp}.json"
        self.temp_output_dir = self.output_dir / f".temp_{safe_keyword}_{timestamp}"
        
        # Create the temporary directory
        self.temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store initial workflow data
        self.workflow_data = {
            "keyword": keyword,
            "start_time": datetime.now().isoformat()
        }
        
        # Create temp directory for atomic operations
        self.temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Update state and save
            self._update_state(WorkflowState.RESEARCHING)
            
            # Step 1: Run research
            logger.info("Step 1/3: Running research phase...")
            self._report_progress("research", "Searching for academic sources...")
            research_findings = await self.run_research(keyword)
            
            # Save research data in workflow state
            self._update_state(WorkflowState.RESEARCH_COMPLETE, {
                "research_complete_time": datetime.now().isoformat(),
                "sources_found": len(research_findings.academic_sources)
            })
            self._report_progress("research_complete", f"Found {len(research_findings.academic_sources)} sources")

            # Step 2: Generate article
            self._update_state(WorkflowState.WRITING)
            logger.info("Step 2/3: Generating article...")
            self._report_progress("writing", "Generating SEO-optimized content...")
            article = await self.run_writing(keyword, research_findings)
            
            # Save writing completion data
            self._update_state(WorkflowState.WRITING_COMPLETE, {
                "writing_complete_time": datetime.now().isoformat(),
                "word_count": article.word_count
            })
            self._report_progress("writing_complete", f"Generated {article.word_count} words")

            # Step 3: Save outputs (now atomic)
            self._update_state(WorkflowState.SAVING)
            logger.info("Step 3/3: Saving outputs...")
            self._report_progress("saving", "Saving article and research data...")
            output_path = await self._save_outputs_atomic(keyword, research_findings, article)
            
            # Mark workflow as complete
            self._update_state(WorkflowState.COMPLETE, {
                "end_time": datetime.now().isoformat(),
                "output_path": str(output_path)
            })
            self._report_progress("complete", "All outputs saved successfully")

            logger.info(f"Workflow completed successfully. Output: {output_path}")
            
            # Clean up state file on success
            if self.state_file and self.state_file.exists():
                self.state_file.unlink()
                
            return output_path

        except Exception as e:
            logger.error(f"Workflow failed at state {self.current_state.value}: {e}")
            
            # Update state to failed
            self._update_state(WorkflowState.FAILED, {
                "error": str(e),
                "failed_at": self.current_state.value,
                "failure_time": datetime.now().isoformat()
            })
            
            # Perform rollback
            await self._rollback()
            
            raise

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=300,
        on_backoff=lambda details: logger.warning(
            f"Research retry {details['tries']} after {details['wait']:.1f}s"
        ),
    )
    async def run_research(self, keyword: str) -> ResearchFindings:
        """
        Execute the research phase using the Research Agent.

        Args:
            keyword: The keyword to research

        Returns:
            Research findings with academic sources

        Raises:
            Exception: If research fails after retries
        """
        try:
            # Run the research agent with the new implementation
            logger.debug(f"Invoking research agent for: {keyword}")
            self._report_progress("research", f"Analyzing '{keyword}' across academic databases...")

            # Use the new run_research_agent function
            result = await run_research_agent(self.research_agent, keyword)

            # Validate the result
            if not result.academic_sources:
                raise ValueError("No academic sources found in research results")

            # Additional validation
            if len(result.academic_sources) < 3:
                logger.warning(
                    f"Only found {len(result.academic_sources)} sources, "
                    f"which is below the recommended minimum of 3"
                )

            # Log detailed results
            logger.info(
                f"Research completed successfully:\n"
                f"  - Sources found: {len(result.academic_sources)}\n"
                f"  - Main findings: {len(result.main_findings)}\n"
                f"  - Statistics extracted: {len(result.key_statistics)}\n"
                f"  - Research gaps identified: {len(result.research_gaps)}"
            )

            return result

        except Exception as e:
            logger.error(f"Research phase failed: {e}")
            raise

    async def run_writing(
        self, keyword: str, research_findings: ResearchFindings
    ) -> ArticleOutput:
        """
        Execute the writing phase using the Writer Agent.

        Args:
            keyword: The target keyword for SEO
            research_findings: Research data to base the article on

        Returns:
            Generated article with SEO optimization

        Raises:
            Exception: If article generation fails
        """
        try:
            # Import the run_writer_agent function
            from writer_agent.agent import run_writer_agent

            # Log the writing phase start
            logger.debug(f"Starting writing phase for keyword: {keyword}")
            logger.debug(f"Using {len(research_findings.academic_sources)} sources")
            self._report_progress("writing", f"Creating article from {len(research_findings.academic_sources)} sources...")

            # Execute the writer agent
            result = await run_writer_agent(
                self.writer_agent, keyword, research_findings
            )

            # Log detailed results
            logger.info(
                f"Article generated successfully:\n"
                f"  - Title: {result.title}\n"
                f"  - Word count: {result.word_count}\n"
                f"  - Sections: {len(result.main_sections)}\n"
                f"  - Keyword density: {result.keyword_density:.2%}\n"
                f"  - Sources cited: {len(result.sources_used)}"
            )

            return result

        except Exception as e:
            logger.error(f"Writing phase failed: {e}")
            raise

    async def _save_outputs_atomic(
        self, keyword: str, research: ResearchFindings, article: ArticleOutput
    ) -> Path:
        """
        Save all outputs atomically using temporary directory.
        
        This ensures that either all files are saved successfully or none are.
        
        Args:
            keyword: The keyword (used for directory naming)
            research: Research findings to save
            article: Generated article to save
            
        Returns:
            Path to the output directory
        """
        try:
            # Save to temp directory first
            temp_article_path = self.temp_output_dir / "article.html"
            article_html = article.to_html()
            styled_html = self._add_styling_to_html(article_html)
            temp_article_path.write_text(styled_html, encoding="utf-8")
            
            # Save research data
            temp_research_path = self.temp_output_dir / "research.json"
            research_data = research.model_dump()
            temp_research_path.write_text(
                json.dumps(research_data, indent=2, default=str), encoding="utf-8"
            )
            
            # Create review interface
            temp_index_path = self.temp_output_dir / "index.html"
            review_html = self._create_review_interface(keyword, article, research)
            temp_index_path.write_text(review_html, encoding="utf-8")
            
            # Now move from temp to final location atomically
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_keyword = re.sub(r'[^\w\-_]', '_', keyword).strip('_')
            safe_keyword = re.sub(r'_+', '_', safe_keyword)
            final_output_dir = self.output_dir / f"{safe_keyword}_{timestamp}"
            
            # Move the entire directory
            shutil.move(str(self.temp_output_dir), str(final_output_dir))
            
            logger.info(f"Atomically saved outputs to: {final_output_dir}")
            return final_output_dir / "index.html"
            
        except Exception as e:
            logger.error(f"Failed to save outputs atomically: {e}")
            raise

    async def save_outputs(
        self, keyword: str, research: ResearchFindings, article: ArticleOutput
    ) -> Path:
        """
        Save all outputs to the filesystem.

        Creates a directory for each article containing:
        - article.html: The generated article
        - research.json: Research data for reference
        - index.html: Review interface

        Args:
            keyword: The keyword (used for directory naming)
            research: Research findings to save
            article: Generated article to save

        Returns:
            Path to the output directory
        """
        try:
            # Create output directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize keyword for filename - replace special chars with single underscore
            safe_keyword = re.sub(r'[^\w\-_]', '_', keyword)
            # Remove multiple consecutive underscores
            safe_keyword = re.sub(r'_+', '_', safe_keyword)
            # Remove leading/trailing underscores
            safe_keyword = safe_keyword.strip('_')
            output_dir = self.output_dir / f"{safe_keyword}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save article HTML
            article_path = output_dir / "article.html"
            article_html = article.to_html()

            # Add styling to the HTML
            styled_html = self._add_styling_to_html(article_html)
            article_path.write_text(styled_html, encoding="utf-8")
            logger.debug(f"Saved article to: {article_path}")

            # Save research data as JSON
            research_path = output_dir / "research.json"
            research_data = research.model_dump()
            research_path.write_text(
                json.dumps(research_data, indent=2, default=str), encoding="utf-8"
            )
            logger.debug(f"Saved research data to: {research_path}")

            # Create review interface
            index_path = output_dir / "index.html"
            review_html = self._create_review_interface(keyword, article, research)
            index_path.write_text(review_html, encoding="utf-8")
            logger.debug(f"Created review interface at: {index_path}")

            return index_path

        except Exception as e:
            logger.error(f"Failed to save outputs: {e}")
            raise

    def _add_styling_to_html(self, html: str) -> str:
        """
        Add CSS styling to the generated HTML.

        Args:
            html: Raw HTML from article generation

        Returns:
            HTML with embedded CSS styling
        """
        # Insert CSS into the head section
        css = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
            }
            h2 {
                color: #34495e;
                margin-top: 30px;
                margin-bottom: 15px;
            }
            h3 {
                color: #7f8c8d;
                margin-top: 20px;
                margin-bottom: 10px;
            }
            .reading-time {
                color: #7f8c8d;
                font-style: italic;
                margin-bottom: 20px;
            }
            .introduction {
                font-size: 1.1em;
                color: #555;
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 30px;
            }
            .conclusion {
                background-color: #e8f8f5;
                padding: 15px;
                border-radius: 5px;
                margin-top: 30px;
                border-left: 4px solid #27ae60;
            }
            .section-content, .subsection-content {
                margin-bottom: 20px;
                text-align: justify;
            }
        </style>
        """

        # Insert CSS before </head>
        return html.replace("</head>", f"{css}</head>")

    def _create_review_interface(
        self, keyword: str, article: ArticleOutput, research: ResearchFindings
    ) -> str:
        """
        Create an HTML review interface for the generated content.

        Args:
            keyword: The researched keyword
            article: Generated article
            research: Research findings

        Returns:
            HTML for the review interface
        """
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Review: {keyword}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f0f0f0;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .metrics {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .metric {{
                    background-color: white;
                    padding: 15px;
                    border-radius: 5px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metric-value {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #3498db;
                }}
                .metric-label {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                }}
                .content-preview {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .actions {{
                    display: flex;
                    gap: 10px;
                    margin-top: 20px;
                }}
                .button {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .button-primary {{
                    background-color: #3498db;
                    color: white;
                }}
                .button-secondary {{
                    background-color: #95a5a6;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Content Review: {keyword}</h1>
                    <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{article.word_count}</div>
                        <div class="metric-label">Words</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{article.reading_time_minutes}</div>
                        <div class="metric-label">Min Read</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{len(research.academic_sources)}</div>
                        <div class="metric-label">Sources</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{article.keyword_density:.1%}</div>
                        <div class="metric-label">Keyword Density</div>
                    </div>
                </div>
                
                <div class="content-preview">
                    <h2>Article Preview</h2>
                    <h3>{article.title}</h3>
                    <p><strong>Meta Description:</strong> {article.meta_description}</p>
                    <p><strong>Introduction:</strong> {article.introduction[:200]}...</p>
                    
                    <div class="actions">
                        <a href="article.html" class="button button-primary">View Full Article</a>
                        <a href="research.json" class="button button-secondary">View Research Data</a>
                    </div>
                </div>
                
                <div class="content-preview">
                    <h2>Top Sources Used</h2>
                    <ul>
                        {"".join(f'<li><a href="{source.url}">{source.title}</a> (Credibility: {source.credibility_score:.2f})</li>' for source in research.get_top_sources(3))}
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
