"""
Writer Agent implementation.

This module contains the main Writer Agent that transforms research findings
into SEO-optimized articles.
"""

import logging
from typing import Any, Dict, List

from pydantic_ai import Agent, RunContext

from config import Config
from models import (
    ArticleOutput, 
    ArticleSection, 
    ArticleSubsection,
    ResearchFindings,
    ExpertQuote,
    FAQItem,
    TableData
)
from model_factories.openrouter import create_openrouter_model

from .prompts import WRITER_AGENT_SYSTEM_PROMPT
from .tools import (
    calculate_keyword_density,
    check_seo_requirements,
    format_sources_for_citation,
    generate_keyword_variations,
    get_research_context,
    generate_expert_quote,
    create_faq_items,
    structure_bullet_points,
    format_hyperlink,
    create_comparison_table,
    expand_research_finding,
)

# Set up logging
logger = logging.getLogger(__name__)


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
    
    # Determine which model to use based on configuration
    if config.use_openrouter:
        # Use OpenRouter for multi-model support
        logger.info(f"Using OpenRouter model: {config.get_model_for_task('writer')}")
        model = create_openrouter_model(
            model_name=config.get_model_for_task("writer"),
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url,
            extra_headers={
                "HTTP-Referer": config.openrouter_site_url,
                "X-Title": config.openrouter_app_name,
            } if config.openrouter_site_url else None
        )
    else:
        # Fallback to direct OpenAI
        logger.info(f"Using OpenAI model: {config.llm_model}")
        model = f"openai:{config.llm_model}"
    
    writer_agent = Agent(
        model=model,
        deps_type=Dict[str, Any],  # Expects research context
        output_type=ArticleOutput,
        system_prompt=WRITER_AGENT_SYSTEM_PROMPT,
    )

    # Register the tool to access research context
    @writer_agent.tool
    def get_research_context_tool(ctx: RunContext[Dict[str, Any]]) -> ResearchFindings:
        """Access the research findings from context."""
        return get_research_context(ctx)

    # Register the tool to check keyword density
    @writer_agent.tool
    def calculate_keyword_density_tool(
        ctx: RunContext[Dict[str, Any]], content: str, keyword: str
    ) -> float:
        """Calculate keyword density in content."""
        return calculate_keyword_density(ctx, content, keyword)

    # Register the tool to format sources for citation
    @writer_agent.tool
    def format_sources_tool(
        ctx: RunContext[Dict[str, Any]], source_urls: List[str]
    ) -> List[str]:
        """Format source URLs into proper citations."""
        return format_sources_for_citation(ctx, source_urls)

    # Register the tool to check SEO requirements
    @writer_agent.tool
    def check_seo_tool(
        ctx: RunContext[Dict[str, Any]],
        title: str,
        meta_description: str,
        content: str,
        keyword: str,
    ) -> Dict[str, Any]:
        """Check if content meets SEO requirements."""
        return check_seo_requirements(ctx, title, meta_description, content, keyword)

    # Register the tool to generate keyword variations
    @writer_agent.tool
    def generate_variations_tool(
        ctx: RunContext[Dict[str, Any]], keyword: str
    ) -> List[str]:
        """Generate keyword variations for better SEO."""
        return generate_keyword_variations(ctx, keyword)
    
    # Register new enhanced tools
    @writer_agent.tool
    def generate_expert_quote_tool(
        ctx: RunContext[Dict[str, Any]], 
        context: str, 
        topic: str,
        quote_type: str = "introduction"
    ) -> ExpertQuote:
        """Generate a realistic expert quote."""
        return generate_expert_quote(ctx, context, topic, quote_type)
    
    @writer_agent.tool
    def create_faq_items_tool(
        ctx: RunContext[Dict[str, Any]], 
        research_findings: ResearchFindings,
        keyword: str,
        num_items: int = 6
    ) -> List[FAQItem]:
        """Create FAQ items based on research."""
        return create_faq_items(ctx, research_findings, keyword, num_items)
    
    @writer_agent.tool
    def structure_bullet_points_tool(
        ctx: RunContext[Dict[str, Any]], 
        content_list: List[str],
        list_type: str = "benefits"
    ) -> List[str]:
        """Structure content into bullet points."""
        return structure_bullet_points(ctx, content_list, list_type)
    
    @writer_agent.tool
    def format_hyperlink_tool(
        ctx: RunContext[Dict[str, Any]], 
        text: str, 
        url: str,
        source_type: str = "research"
    ) -> str:
        """Format text with hyperlink."""
        return format_hyperlink(ctx, text, url, source_type)
    
    @writer_agent.tool
    def create_comparison_table_tool(
        ctx: RunContext[Dict[str, Any]], 
        data: Dict[str, List[str]],
        title: str,
        caption: str = None
    ) -> TableData:
        """Create a comparison table."""
        return create_comparison_table(ctx, data, title, caption)
    
    @writer_agent.tool
    def expand_research_finding_tool(
        ctx: RunContext[Dict[str, Any]], 
        finding: str,
        target_words: int = 300
    ) -> str:
        """Expand a research finding into comprehensive content."""
        return expand_research_finding(ctx, finding, target_words)

    return writer_agent


async def run_writer_agent(
    agent: Agent[Dict[str, Any], ArticleOutput],
    keyword: str,
    research_findings: ResearchFindings,
) -> ArticleOutput:
    """
    Execute the writer agent to generate an SEO-optimized article.

    Args:
        agent: The configured writer agent
        keyword: The target keyword for SEO
        research_findings: Research data to base the article on

    Returns:
        ArticleOutput with the generated article

    Raises:
        Exception: If article generation fails
    """
    try:
        # Create a comprehensive writing prompt
        prompt = f"""
        Create a comprehensive, authoritative article about '{keyword}' that is AT LEAST 2,500 words.
        
        CRITICAL Requirements:
        1. Write a 2,500+ word article (this is MANDATORY)
        2. Include 6-8 main sections with 2-3 subsections each
        3. Generate 2-4 expert quotes throughout the article
        4. Create 5-7 FAQ items at the end
        5. Use bullet points in EVERY major section
        6. Include at least one comparison table
        7. Add "What You'll Learn" section with 6-8 key takeaways
        
        Article Structure:
        - Title: 50-70 characters with keyword + benefit + current year
        - Meta description: 150-160 characters with compelling promise
        - Introduction (300-400 words):
          * Problem statement with statistics
          * Expert quote (use generate_expert_quote_tool)
          * Overview with hyperlinked sources
          * "What You'll Learn" bullet points
        - Main Sections (6-8 sections, 300-400 words each):
          * Clear H2 heading
          * Introduction paragraph
          * 2-3 H3 subsections
          * Bullet points (use structure_bullet_points_tool)
          * Hyperlinked research citations (use format_hyperlink_tool)
          * Expert quote every 2-3 sections
        - FAQ Section (use create_faq_items_tool):
          * 5-7 comprehensive Q&A pairs
        - Conclusion (400-500 words):
          * Summary of key points
          * 5-step action plan
          * Final motivational message
        
        Content Expansion:
        - Use expand_research_finding_tool to turn simple findings into 300+ word sections
        - Transform statistics into context and application
        - Include specific numbers, timelines, and measurements
        - Add implementation details and practical steps
        
        SEO Requirements:
        - Keyword density: 0.5-2% (return as decimal like 0.015)
        - Use keyword variations naturally
        - Hyperlink ALL source citations within text
        - Include LSI keywords and semantic variations
        
        REMEMBER: The article MUST be at least 2,500 words. Each main section should be substantial (300-400 words) with multiple subsections. Use all available tools to create expert quotes, FAQ items, bullet points, and expand content.
        """

        # Prepare the context with research findings
        context = {"research": research_findings, "keyword": keyword}

        # Run the agent
        logger.info(f"Running writer agent for keyword: {keyword}")
        result = await agent.run(prompt, deps=context)

        # PydanticAI returns an AgentRunResult, access the data attribute
        article = result.data

        # Validate the output
        if article.word_count < 2500:
            logger.warning(
                f"Article word count ({article.word_count}) is below required minimum of 2,500 words"
            )

        if not article.sources_used:
            raise ValueError("Article must cite research sources")
        
        # Validate new requirements
        if len(article.main_sections) < 6:
            logger.warning(
                f"Article has only {len(article.main_sections)} sections, should have 6-8"
            )
        
        if len(article.expert_quotes) < 2:
            logger.warning(
                f"Article has only {len(article.expert_quotes)} expert quotes, should have 2-4"
            )
        
        if len(article.faq_items) < 5:
            logger.warning(
                f"Article has only {len(article.faq_items)} FAQ items, should have 5-7"
            )

        # Log success
        logger.info(
            f"Article generated successfully: "
            f"'{article.title}' - {article.word_count} words, "
            f"{len(article.main_sections)} sections"
        )

        return article

    except Exception as e:
        logger.error(f"Writer agent failed: {e}")
        raise
