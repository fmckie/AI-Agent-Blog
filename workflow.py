"""
Workflow orchestration for the SEO Content Automation System.

This module coordinates the execution of Research and Writer agents,
managing data flow and error handling throughout the pipeline.
"""

# Import required libraries
import asyncio
from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Optional, Tuple
import backoff

# Import our modules
from config import Config
from models import ResearchFindings, ArticleOutput
from research_agent import create_research_agent, run_research_agent
from writer_agent import create_writer_agent

# Set up logging
logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates the content generation workflow.
    
    This class manages the flow from keyword research through
    article generation, handling errors and saving outputs.
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
        
        try:
            # Step 1: Run research
            logger.info("Step 1/3: Running research phase...")
            research_findings = await self.run_research(keyword)
            
            # Step 2: Generate article
            logger.info("Step 2/3: Generating article...")
            article = await self.run_writing(keyword, research_findings)
            
            # Step 3: Save outputs
            logger.info("Step 3/3: Saving outputs...")
            output_path = await self.save_outputs(keyword, research_findings, article)
            
            logger.info(f"Workflow completed successfully. Output: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise
            
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=300,
        on_backoff=lambda details: logger.warning(
            f"Research retry {details['tries']} after {details['wait']:.1f}s"
        )
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
        self,
        keyword: str,
        research_findings: ResearchFindings
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
            
            # Execute the writer agent
            result = await run_writer_agent(
                self.writer_agent,
                keyword,
                research_findings
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
            
    async def save_outputs(
        self,
        keyword: str,
        research: ResearchFindings,
        article: ArticleOutput
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
            safe_keyword = "".join(c if c.isalnum() or c in "-_" else "_" for c in keyword)
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
                json.dumps(research_data, indent=2, default=str),
                encoding="utf-8"
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
        self,
        keyword: str,
        article: ArticleOutput,
        research: ResearchFindings
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