"""
PydanticAI agents for research and content generation.

This module defines the Research Agent and Writer Agent that power
the SEO content automation system.
"""

# Import required libraries
import logging
from typing import Any, Dict
from pydantic_ai import Agent, RunContext

# Import our modules
from config import Config
from models import ResearchFindings, ArticleOutput, AcademicSource
from tools import search_academic_sources

# Set up logging
logger = logging.getLogger(__name__)


def create_research_agent(config: Config) -> Agent[None, ResearchFindings]:
    """
    Create and configure the Research Agent.
    
    This agent is responsible for:
    - Searching academic sources via Tavily
    - Analyzing and summarizing findings
    - Extracting key statistics and insights
    - Identifying research gaps
    
    Args:
        config: System configuration
        
    Returns:
        Configured PydanticAI agent for research
    """
    # Create the agent with specific model and output type
    research_agent = Agent(
        model=f"openai:{config.llm_model}",
        output_type=ResearchFindings,
        system_prompt="""You are an expert academic researcher specializing in finding and analyzing 
        peer-reviewed sources. Your role is to:
        
        1. Search for academic sources using the provided tools
        2. Analyze the credibility and relevance of each source
        3. Extract key findings, statistics, and insights
        4. Identify gaps in current research
        5. Provide a comprehensive summary of the research landscape
        
        Focus on:
        - Peer-reviewed journals
        - Educational institutions (.edu domains)
        - Government sources (.gov domains)
        - Recent publications (preferably within the last 5 years)
        
        Always assess source credibility based on:
        - Domain authority (edu/gov/org preferred)
        - Publication recency
        - Author credentials
        - Citation presence
        
        Provide detailed, evidence-based findings that can support article writing."""
    )
    
    # Register the Tavily search tool
    @research_agent.tool
    async def search_academic(ctx: RunContext[None], query: str) -> Dict[str, Any]:
        """
        Search for academic sources using Tavily API.
        
        Args:
            query: Search query for academic sources
            
        Returns:
            Search results from Tavily
        """
        logger.debug(f"Searching academic sources for: {query}")
        
        # Use the Tavily integration from tools.py
        results = await search_academic_sources(query, config)
        
        logger.info(f"Found {len(results.get('results', []))} academic sources")
        return results
    
    return research_agent


def create_writer_agent(config: Config) -> Agent[Dict[str, Any], ArticleOutput]:
    """
    Create and configure the Writer Agent.
    
    This agent is responsible for:
    - Transforming research into engaging articles
    - Applying SEO best practices
    - Structuring content hierarchically
    - Maintaining appropriate keyword density
    
    Args:
        config: System configuration
        
    Returns:
        Configured PydanticAI agent for writing
    """
    # Create the agent with context dependency for research data
    writer_agent = Agent(
        model=f"openai:{config.llm_model}",
        deps_type=Dict[str, Any],  # Expects research context
        output_type=ArticleOutput,
        system_prompt="""You are an expert SEO content writer specializing in creating 
        comprehensive, engaging articles based on academic research. Your role is to:
        
        1. Transform research findings into accessible, engaging content
        2. Apply SEO best practices throughout the article
        3. Maintain optimal keyword density (1-2%)
        4. Structure content with clear hierarchy (H1, H2, H3)
        5. Write in an authoritative yet approachable tone
        
        Article Requirements:
        - Minimum 1000 words for SEO effectiveness
        - Compelling title (50-60 characters)
        - Meta description (150-160 characters)
        - Engaging introduction with a hook
        - Well-structured main sections with subsections
        - Conclusion with call-to-action
        
        SEO Best Practices:
        - Use the focus keyword naturally throughout
        - Include keyword variations and related terms
        - Write scannable content with short paragraphs
        - Use bullet points and lists where appropriate
        - Ensure readability for general audience
        
        Content Style:
        - Authoritative but accessible
        - Evidence-based with source citations
        - Practical and actionable insights
        - Clear and concise language
        
        Base your content on the provided research findings, ensuring all claims
        are supported by the academic sources."""
    )
    
    # Register a tool to access research context
    @writer_agent.tool
    def get_research_context(ctx: RunContext[Dict[str, Any]]) -> ResearchFindings:
        """
        Access the research findings from context.
        
        Returns:
            Research findings to base the article on
        """
        return ctx.deps["research"]
    
    # Register a tool to check keyword density
    @writer_agent.tool
    def calculate_keyword_density(
        ctx: RunContext[Dict[str, Any]], 
        content: str, 
        keyword: str
    ) -> float:
        """
        Calculate keyword density in content.
        
        Args:
            content: Text to analyze
            keyword: Target keyword
            
        Returns:
            Keyword density as a percentage
        """
        # Simple keyword density calculation
        words = content.lower().split()
        keyword_lower = keyword.lower()
        keyword_count = sum(1 for word in words if keyword_lower in word)
        
        if len(words) == 0:
            return 0.0
            
        density = (keyword_count / len(words)) * 100
        return round(density, 2)
    
    return writer_agent


# Placeholder functions for testing
# These will be properly implemented in later phases
async def _mock_research_agent_run(prompt: str) -> ResearchFindings:
    """
    Mock research agent run for testing.
    
    This will be replaced with actual agent execution in Phase 3.
    """
    return ResearchFindings(
        keyword="test keyword",
        research_summary="This is a comprehensive test research summary that provides detailed insights into the topic. It includes multiple findings from academic sources and presents a thorough analysis of the current state of research in this field.",
        academic_sources=[
            AcademicSource(
                title="Test Academic Paper",
                url="https://example.edu/paper",
                excerpt="Test excerpt from paper",
                domain=".edu",
                credibility_score=0.9
            )
        ],
        main_findings=["Finding 1", "Finding 2", "Finding 3"],
        total_sources_analyzed=5,
        search_query_used="test query"
    )


async def _mock_writer_agent_run(
    prompt: str, 
    context: Dict[str, Any]
) -> ArticleOutput:
    """
    Mock writer agent run for testing.
    
    This will be replaced with actual agent execution in Phase 4.
    """
    from models import ArticleSection
    
    return ArticleOutput(
        title="Test Article Title",
        meta_description="A comprehensive test meta description for SEO that summarizes the article content and encourages clicks from search results.",
        focus_keyword="test keyword",
        introduction="This is a detailed test introduction that provides context for the article. It engages readers with compelling information about the topic, sets expectations for what they'll learn, and includes relevant keywords naturally throughout the text to ensure proper SEO optimization.",
        main_sections=[
            ArticleSection(
                heading="Test Section 1",
                content="Test content for section 1. " * 50  # Make it long enough
            ),
            ArticleSection(
                heading="Test Section 2", 
                content="Test content for section 2. " * 50
            ),
            ArticleSection(
                heading="Test Section 3",
                content="Test content for section 3. " * 50
            )
        ],
        conclusion="This is a comprehensive test conclusion that summarizes the key points discussed in the article and provides readers with actionable next steps to apply what they've learned.",
        word_count=1200,
        reading_time_minutes=6,
        keyword_density=0.015,
        sources_used=["https://example.edu/paper"]
    )


# Temporarily patch the agents to use mock functions
# This allows the workflow to run before full implementation
def _patch_agents_for_testing():
    """
    Patch agents with mock implementations for testing.
    
    This will be removed once agents are fully implemented.
    """
    # Store original methods
    if not hasattr(Agent, '_original_run'):
        Agent._original_run = Agent.run
        Agent._original_run_sync = Agent.run_sync
    
    # Patch with mock implementations
    async def mock_run(self, *args, **kwargs):
        if self.output_type == ResearchFindings:
            return await _mock_research_agent_run(args[0] if args else "")
        elif self.output_type == ArticleOutput:
            return await _mock_writer_agent_run(
                args[0] if args else "",
                kwargs.get("context", {})
            )
        else:
            return await self._original_run(*args, **kwargs)
    
    Agent.run = mock_run


# Apply patches for now (remove in Phase 3/4)
_patch_agents_for_testing()