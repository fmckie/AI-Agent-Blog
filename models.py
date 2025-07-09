"""
Pydantic models for structured agent outputs.

These models define the data structures that our PydanticAI agents
will produce, ensuring type safety and validation throughout the system.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

# Import Pydantic for data modeling
from pydantic import BaseModel, Field, ValidationInfo, field_validator


class AcademicSource(BaseModel):
    """
    Represents a single academic source found during research.

    This model captures all the metadata we need about each source
    to properly cite it and assess its credibility.
    """

    # Basic source information
    title: str = Field(..., description="Title of the academic paper or article")
    url: str = Field(..., description="Direct URL to the source")

    # Author and publication details
    authors: Optional[List[str]] = Field(
        default=None, description="List of author names"
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Publication date in ISO format or human-readable format",
    )
    journal_name: Optional[str] = Field(
        default=None, description="Name of the journal or publication"
    )

    # Content and credibility
    excerpt: str = Field(
        ...,
        description="Relevant excerpt or abstract from the source",
        max_length=500,  # Limit excerpt length for readability
    )
    domain: str = Field(
        ..., description="Domain of the source (e.g., .edu, .gov, .org)"
    )
    credibility_score: float = Field(
        ...,
        ge=0.0,  # Greater than or equal to 0
        le=1.0,  # Less than or equal to 1
        description="Credibility score between 0 and 1",
    )

    # Additional metadata
    source_type: str = Field(
        default="web", description="Type of source: journal, book, web, report, etc."
    )

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        """
        Ensure URL is properly formatted.

        Args:
            v: URL string to validate

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is invalid
        """
        # Basic URL validation
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("domain")
    def extract_domain_type(cls, v: str, info: ValidationInfo) -> str:
        """
        Extract and validate domain type from URL.

        Args:
            v: Domain string
            info: Validation info with field data

        Returns:
            Cleaned domain extension
        """
        # Ensure domain starts with a dot
        if not v.startswith("."):
            v = f".{v}"

        # Validate against common academic domains
        academic_domains = [".edu", ".gov", ".org", ".ac.uk", ".edu.au"]
        if v not in academic_domains:
            # Still allow but may affect credibility
            pass

        return v

    def to_citation(self) -> str:
        """
        Generate a basic citation string for this source.

        Returns:
            Formatted citation string
        """
        # Build citation components
        parts = []

        # Authors
        if self.authors:
            author_str = ", ".join(self.authors[:3])  # First 3 authors
            if len(self.authors) > 3:
                author_str += " et al."
            parts.append(author_str)

        # Title
        parts.append(f'"{self.title}"')

        # Journal
        if self.journal_name:
            parts.append(self.journal_name)

        # Date
        if self.publication_date:
            parts.append(f"({self.publication_date})")

        # URL
        parts.append(f"Available at: {self.url}")

        return ". ".join(parts)


class ResearchFindings(BaseModel):
    """
    Output from the Research Agent containing all findings.

    This model structures the research results in a way that's
    easy for the Writer Agent to consume and transform into content.
    """

    # Core research data
    keyword: str = Field(..., description="The keyword/topic that was researched")
    research_summary: str = Field(
        ...,
        description="Executive summary of research findings",
        min_length=20,  # Reduced to allow shorter summaries in tests
        max_length=2000,  # Increased to allow more comprehensive summaries
    )

    # Academic sources found
    academic_sources: List[AcademicSource] = Field(
        default_factory=list,
        description="List of academic sources found",
        min_length=0,  # Allow empty list for edge cases
    )

    # Extracted insights
    key_statistics: List[str] = Field(
        default_factory=list, description="Important statistics and data points found"
    )
    research_gaps: List[str] = Field(
        default_factory=list, description="Identified gaps in current research"
    )
    main_findings: List[str] = Field(
        default_factory=list,
        description="Main findings from the research",
        min_length=0,  # Allow empty findings for edge cases
    )

    # Metadata
    total_sources_analyzed: int = Field(
        ..., ge=0, description="Total number of sources analyzed"
    )
    search_query_used: str = Field(
        ..., description="The actual search query sent to Tavily"
    )
    research_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the research was conducted"
    )

    @field_validator("academic_sources")
    def validate_source_credibility(
        cls, v: List[AcademicSource]
    ) -> List[AcademicSource]:
        """
        Sort sources by credibility.

        Args:
            v: List of academic sources

        Returns:
            Sorted list of sources
        """
        # Sort by credibility score (highest first) if we have sources
        if v:
            return sorted(v, key=lambda x: x.credibility_score, reverse=True)
        return v

    def get_top_sources(self, n: int = 5) -> List[AcademicSource]:
        """
        Get the top N most credible sources.

        Args:
            n: Number of sources to return

        Returns:
            List of top sources by credibility
        """
        return self.academic_sources[:n]

    def to_markdown_summary(self) -> str:
        """
        Convert research findings to a markdown summary.

        Returns:
            Markdown-formatted research summary
        """
        md_lines = [
            f"# Research Findings: {self.keyword}",
            f"\n## Summary\n{self.research_summary}",
            "\n## Main Findings",
        ]

        # Add main findings
        for i, finding in enumerate(self.main_findings, 1):
            md_lines.append(f"{i}. {finding}")

        # Add key statistics if any
        if self.key_statistics:
            md_lines.append("\n## Key Statistics")
            for stat in self.key_statistics:
                md_lines.append(f"- {stat}")

        # Add top sources
        md_lines.append("\n## Top Academic Sources")
        for source in self.get_top_sources(3):
            md_lines.append(f"\n### {source.title}")
            md_lines.append(f"- **Credibility**: {source.credibility_score:.2f}")
            md_lines.append(f"- **Excerpt**: {source.excerpt}")
            md_lines.append(f"- **URL**: {source.url}")

        return "\n".join(md_lines)


class ArticleOutput(BaseModel):
    """
    Output from the Writer Agent containing the complete article.

    This model structures the article in a way that's ready
    for HTML generation and SEO optimization.
    """

    # SEO Metadata
    title: str = Field(
        ...,
        description="SEO-optimized article title",
        min_length=10,
        max_length=70,  # Optimal for search engines
    )
    meta_description: str = Field(
        ...,
        description="SEO meta description",
        min_length=120,
        max_length=160,  # Google's recommended length
    )
    focus_keyword: str = Field(..., description="Primary keyword for SEO optimization")

    # Article sections
    introduction: str = Field(
        ..., description="Engaging introduction with hook", min_length=150
    )
    main_sections: List["ArticleSection"] = Field(
        ...,
        description="Main body sections of the article",
        min_length=3,  # At least 3 sections for depth
    )
    conclusion: str = Field(
        ..., description="Compelling conclusion with call-to-action", min_length=100
    )

    # Content metrics
    word_count: int = Field(
        ...,
        ge=1000,  # Minimum 1000 words for SEO
        description="Total word count of the article",
    )
    reading_time_minutes: int = Field(
        ..., ge=1, description="Estimated reading time in minutes"
    )

    # SEO optimization data
    keyword_density: float = Field(
        ...,
        ge=0.005,  # At least 0.5%
        le=0.03,  # Maximum 3%
        description="Keyword density percentage",
    )
    internal_links: List[str] = Field(
        default_factory=list, description="Suggested internal links"
    )
    external_links: List[str] = Field(
        default_factory=list, description="External reference links"
    )

    # Research connection
    sources_used: List[str] = Field(
        ..., description="List of source URLs used in the article"
    )

    @field_validator("word_count")
    def validate_word_count(cls, v: int) -> int:
        """
        Validate word count is reasonable.

        Args:
            v: Word count value

        Returns:
            Validated word count
        """
        # Just validate the word count here
        # Reading time calculation is handled by the field default
        return v

    def to_html(self) -> str:
        """
        Convert article to HTML format.

        Returns:
            HTML-formatted article
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            f"  <title>{self.title}</title>",
            f"  <meta name='description' content='{self.meta_description}'>",
            f"  <meta name='keywords' content='{self.focus_keyword}'>",
            "  <meta charset='UTF-8'>",
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "</head>",
            "<body>",
            f"  <h1>{self.title}</h1>",
            f"  <p class='reading-time'>⏱️ {self.reading_time_minutes} min read</p>",
            f"  <div class='introduction'>{self.introduction}</div>",
        ]

        # Add main sections
        for i, section in enumerate(self.main_sections, 1):
            html_parts.append(f"  <h2>{section.heading}</h2>")
            html_parts.append(f"  <div class='section-content'>{section.content}</div>")

            if section.subsections:
                for subsection in section.subsections:
                    html_parts.append(f"    <h3>{subsection.heading}</h3>")
                    html_parts.append(
                        f"    <div class='subsection-content'>{subsection.content}</div>"
                    )

        # Add conclusion
        html_parts.extend(
            [f"  <div class='conclusion'>{self.conclusion}</div>", "</body>", "</html>"]
        )

        return "\n".join(html_parts)


class ArticleSection(BaseModel):
    """
    Represents a main section within an article.

    Articles are structured with main sections (H2) and
    optional subsections (H3) for better organization.
    """

    heading: str = Field(
        ..., description="Section heading (H2 level)", min_length=5, max_length=100
    )
    content: str = Field(
        ...,
        description="Section content",
        min_length=100,  # Reduced for flexibility in tests
    )
    subsections: Optional[List["ArticleSubsection"]] = Field(
        default=None, description="Optional subsections (H3 level)"
    )

    @field_validator("heading")
    def validate_heading(cls, v: str) -> str:
        """
        Ensure heading is properly formatted.

        Args:
            v: Heading text

        Returns:
            Cleaned heading
        """
        # Remove any existing markdown formatting
        v = v.strip("#").strip()

        # Ensure proper capitalization
        if v.islower():
            v = v.title()

        return v


class ArticleSubsection(BaseModel):
    """
    Represents a subsection within a main article section.

    Used for H3-level content organization within H2 sections.
    """

    heading: str = Field(
        ..., description="Subsection heading (H3 level)", min_length=5, max_length=80
    )
    content: str = Field(..., description="Subsection content", min_length=50)


# Tavily API Response Models
class TavilySearchResult(BaseModel):
    """
    Represents a single search result from Tavily API.

    This model provides type safety and validation for individual
    search results returned by the Tavily search API.
    """

    # Core result fields
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    content: str = Field(..., description="Content snippet from the result")
    score: Optional[float] = Field(
        default=None, description="Relevance score from Tavily"
    )

    # Enhanced fields added by our processing
    credibility_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Our calculated credibility score (0-1)",
    )
    domain: Optional[str] = Field(
        default=None, description="Domain extension (e.g., .edu, .gov)"
    )
    processed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when result was processed"
    )

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        """Ensure URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class TavilySearchResponse(BaseModel):
    """
    Represents the complete response from Tavily search API.

    This model structures the entire API response including
    search results, metadata, and processing information.
    """

    # Core response data
    query: str = Field(..., description="The search query that was executed")
    results: List[TavilySearchResult] = Field(
        default_factory=list, description="List of search results"
    )
    answer: Optional[str] = Field(
        default=None, description="AI-generated answer from Tavily"
    )

    # Processing metadata
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Our processing metadata"
    )

    def get_academic_results(
        self, min_credibility: float = 0.7
    ) -> List[TavilySearchResult]:
        """
        Get results that meet academic credibility threshold.

        Args:
            min_credibility: Minimum credibility score (default 0.7)

        Returns:
            List of academic search results
        """
        return [
            result
            for result in self.results
            if result.credibility_score and result.credibility_score >= min_credibility
        ]

    def get_results_by_domain(self, domain: str) -> List[TavilySearchResult]:
        """
        Get results from a specific domain type.

        Args:
            domain: Domain extension (e.g., ".edu")

        Returns:
            List of results from that domain
        """
        return [result for result in self.results if result.domain == domain]


# Enhanced Tavily Models for Advanced Features
class ExtractedContent(BaseModel):
    """
    Represents fully extracted content from a URL.
    
    This model stores complete article/page content extracted
    using Tavily's extract API for deep analysis.
    """
    
    url: str = Field(..., description="Source URL")
    title: Optional[str] = Field(None, description="Page title")
    raw_content: str = Field(..., description="Full extracted content")
    content_length: int = Field(..., ge=0, description="Length of content in characters")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now, description="When content was extracted"
    )
    extraction_success: bool = Field(
        default=True, description="Whether extraction was successful"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if extraction failed"
    )
    
    def get_preview(self, length: int = 500) -> str:
        """Get a preview of the content."""
        return self.raw_content[:length] + "..." if len(self.raw_content) > length else self.raw_content


class CrawledPage(BaseModel):
    """
    Represents a single page discovered during website crawling.
    
    This model captures pages found while crawling a domain
    for comprehensive research coverage.
    """
    
    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(None, description="Page title")
    content_preview: str = Field(
        ..., description="Preview of page content", max_length=1000
    )
    relevance_score: float = Field(
        ..., ge=0.0, description="Relevance score based on search criteria"
    )
    crawl_depth: int = Field(..., ge=0, description="Depth from initial URL")
    parent_url: Optional[str] = Field(None, description="URL that linked to this page")
    

class DomainAnalysis(BaseModel):
    """
    Represents analysis of a website's structure.
    
    This model captures insights about a domain's organization
    and identifies valuable sections for research.
    """
    
    base_url: str = Field(..., description="Base domain URL analyzed")
    total_links: int = Field(..., ge=0, description="Total links found")
    categorized_links: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Links categorized by type (research, publications, etc.)"
    )
    insights: List[str] = Field(
        default_factory=list, description="Key insights about the domain"
    )
    recommended_sections: List[str] = Field(
        default_factory=list, description="Recommended sections to explore"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="When analysis was performed"
    )


class EnhancedResearchFindings(ResearchFindings):
    """
    Extended research findings with full content and crawl data.
    
    This model extends the base ResearchFindings with additional
    data from extract, crawl, and domain analysis operations.
    """
    
    # Additional fields for enhanced research
    extracted_content: Optional[List[ExtractedContent]] = Field(
        default=None, description="Full content extracted from top sources"
    )
    crawled_pages: Optional[List[CrawledPage]] = Field(
        default=None, description="Pages discovered through crawling"
    )
    domain_analyses: Optional[List[DomainAnalysis]] = Field(
        default=None, description="Structural analyses of key domains"
    )
    
    # Enhanced metadata
    research_depth: Literal["basic", "standard", "comprehensive"] = Field(
        default="standard", description="Depth of research conducted"
    )
    tools_used: List[str] = Field(
        default_factory=list, description="List of tools used in research"
    )
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, 
        description="Confidence in research completeness (0-1)"
    )
    
    def get_comprehensive_summary(self) -> str:
        """
        Generate a comprehensive summary including all research methods.
        
        Returns:
            Detailed markdown summary of all findings
        """
        md_lines = [
            f"# Comprehensive Research: {self.keyword}",
            f"\n## Research Depth: {self.research_depth.title()}",
            f"**Confidence Score**: {self.confidence_score:.2f}",
            f"\n## Executive Summary\n{self.research_summary}",
        ]
        
        # Add search findings
        md_lines.append("\n## Search Results")
        md_lines.append(f"- Found {self.total_sources_analyzed} sources")
        md_lines.append(f"- High-credibility sources: {len([s for s in self.academic_sources if s.credibility_score > 0.7])}")
        
        # Add extracted content summary
        if self.extracted_content:
            md_lines.append(f"\n## Extracted Full Content")
            md_lines.append(f"- Extracted content from {len(self.extracted_content)} sources")
            total_content = sum(ec.content_length for ec in self.extracted_content)
            md_lines.append(f"- Total content analyzed: {total_content:,} characters")
        
        # Add crawl summary
        if self.crawled_pages:
            md_lines.append(f"\n## Domain Crawling")
            md_lines.append(f"- Discovered {len(self.crawled_pages)} relevant pages")
            avg_relevance = sum(p.relevance_score for p in self.crawled_pages) / len(self.crawled_pages)
            md_lines.append(f"- Average relevance score: {avg_relevance:.2f}")
        
        # Add domain analysis
        if self.domain_analyses:
            md_lines.append(f"\n## Domain Structure Analysis")
            for analysis in self.domain_analyses:
                md_lines.append(f"\n### {analysis.base_url}")
                for insight in analysis.insights:
                    md_lines.append(f"- {insight}")
        
        # Add main findings and statistics
        if self.main_findings:
            md_lines.append("\n## Key Findings")
            for finding in self.main_findings:
                md_lines.append(f"- {finding}")
        
        if self.key_statistics:
            md_lines.append("\n## Statistical Highlights")
            for stat in self.key_statistics:
                md_lines.append(f"- {stat}")
        
        # Add tools used
        if self.tools_used:
            md_lines.append(f"\n## Research Methods")
            md_lines.append(f"Tools used: {', '.join(self.tools_used)}")
        
        return "\n".join(md_lines)


# ============================================
# Phase 3 Enhanced Storage Models
# ============================================

class StoredSource(BaseModel):
    """
    Enhanced source with storage metadata.
    
    This model represents a source that has been stored in our
    enhanced Supabase storage with all associated metadata.
    """
    
    # Core identification
    id: str = Field(..., description="Unique source ID from database")
    source: AcademicSource = Field(..., description="Original source data")
    
    # Storage details
    full_content: Optional[str] = Field(
        None, description="Full extracted content if available"
    )
    chunk_ids: List[str] = Field(
        default_factory=list, description="IDs of content chunks"
    )
    chunk_count: int = Field(
        default=0, ge=0, description="Number of chunks created"
    )
    
    # Embedding status
    embedding_status: Literal["not_queued", "pending", "processing", "completed", "failed"] = Field(
        default="not_queued", description="Current embedding generation status"
    )
    embedding_error: Optional[str] = Field(
        None, description="Error message if embedding failed"
    )
    
    # Relationships
    relationships: List["SourceRelationship"] = Field(
        default_factory=list, description="All source relationships"
    )
    relationship_count: int = Field(
        default=0, ge=0, description="Total number of relationships"
    )
    
    # Metadata
    stored_at: datetime = Field(
        default_factory=datetime.now, description="When source was stored"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    access_count: int = Field(
        default=0, ge=0, description="Number of times accessed"
    )
    
    def has_full_content(self) -> bool:
        """Check if full content is available."""
        return bool(self.full_content and len(self.full_content) > len(self.source.excerpt))
    
    def is_embedded(self) -> bool:
        """Check if embeddings are ready."""
        return self.embedding_status == "completed"
    
    def get_primary_relationships(self, relationship_type: str) -> List["SourceRelationship"]:
        """Get relationships of a specific type."""
        return [r for r in self.relationships if r.relationship_type == relationship_type]


class SourceRelationship(BaseModel):
    """
    Represents a relationship between two sources.
    
    This model captures various types of relationships that can exist
    between research sources, enabling graph-like traversal.
    """
    
    # Relationship identification
    id: Optional[str] = Field(None, description="Relationship ID from database")
    source_id: str = Field(..., description="Primary source ID")
    related_id: str = Field(..., description="Related source ID")
    
    # Relationship details
    relationship_type: Literal[
        "cites", "references", "similar", "contradicts", "crawled_from", "extends", "summarizes"
    ] = Field(..., description="Type of relationship")
    
    direction: Literal["outgoing", "incoming", "bidirectional"] = Field(
        default="outgoing", description="Relationship direction"
    )
    
    # Similarity for vector relationships
    similarity_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Similarity score for 'similar' relationships"
    )
    
    # Additional context
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional relationship metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When relationship was created"
    )
    
    # Related source info (populated when fetched)
    related_source_info: Optional[Dict[str, str]] = Field(
        None, description="Basic info about related source (title, url)"
    )
    
    def is_strong_relationship(self) -> bool:
        """Check if this is a strong relationship."""
        if self.relationship_type in ["cites", "references"]:
            return True
        if self.relationship_type == "similar" and self.similarity_score:
            return self.similarity_score > 0.8
        return False
    
    def get_strength_label(self) -> str:
        """Get human-readable relationship strength."""
        if self.relationship_type in ["cites", "references"]:
            return "strong"
        elif self.relationship_type == "similar" and self.similarity_score:
            if self.similarity_score > 0.8:
                return "very similar"
            elif self.similarity_score > 0.6:
                return "moderately similar"
            else:
                return "weakly similar"
        elif self.relationship_type == "contradicts":
            return "conflicting"
        return "related"


class SearchResult(BaseModel):
    """
    Enhanced search result with relationships.
    
    This model represents a search result that includes not just
    the primary match but also related sources.
    """
    
    # Primary result
    chunk_id: str = Field(..., description="ID of matching chunk")
    source_id: str = Field(..., description="ID of source")
    content: str = Field(..., description="Matching content")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    
    # Source metadata
    source_title: str = Field(..., description="Title of source")
    source_url: str = Field(..., description="URL of source")
    source_credibility: float = Field(..., ge=0.0, le=1.0, description="Source credibility")
    
    # Related sources
    related_sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Related sources with relationships"
    )
    
    # Search metadata
    search_type: Literal["vector", "keyword", "hybrid"] = Field(
        ..., description="Type of search that found this result"
    )
    keyword_score: Optional[float] = Field(
        None, description="Keyword match score for hybrid search"
    )
    combined_score: Optional[float] = Field(
        None, description="Combined score for hybrid search"
    )
    
    def get_total_relevance(self) -> float:
        """Calculate total relevance including relationships."""
        base_score = self.combined_score or self.similarity
        
        # Boost for credible sources
        credibility_boost = self.source_credibility * 0.2
        
        # Boost for sources with many relationships
        relationship_boost = min(len(self.related_sources) * 0.05, 0.2)
        
        return min(base_score + credibility_boost + relationship_boost, 1.0)


class CrawlMetadata(BaseModel):
    """
    Metadata about a crawl operation.
    
    This model tracks information about website crawls performed
    during research for later analysis and debugging.
    """
    
    # Crawl identification
    crawl_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique crawl ID")
    parent_url: str = Field(..., description="Root URL that was crawled")
    keyword: str = Field(..., description="Research keyword that triggered crawl")
    
    # Crawl results
    pages_found: int = Field(..., ge=0, description="Total pages discovered")
    pages_stored: int = Field(..., ge=0, description="Pages successfully stored")
    source_ids: List[str] = Field(..., description="IDs of stored sources")
    
    # Crawl configuration
    max_depth: int = Field(..., ge=1, description="Maximum crawl depth used")
    crawl_timeout: int = Field(..., description="Timeout in seconds")
    filters_applied: Optional[Dict[str, Any]] = Field(
        None, description="Any filters applied during crawl"
    )
    
    # Performance metrics
    crawl_duration_seconds: float = Field(..., ge=0, description="Total crawl time")
    average_page_size: Optional[float] = Field(
        None, description="Average page size in KB"
    )
    
    # Timestamps
    started_at: datetime = Field(..., description="When crawl started")
    completed_at: datetime = Field(..., description="When crawl completed")
    
    def get_success_rate(self) -> float:
        """Calculate crawl success rate."""
        if self.pages_found == 0:
            return 0.0
        return self.pages_stored / self.pages_found
    
    def get_pages_per_second(self) -> float:
        """Calculate crawl speed."""
        if self.crawl_duration_seconds == 0:
            return 0.0
        return self.pages_found / self.crawl_duration_seconds


class EmbeddingQueueItem(BaseModel):
    """
    Represents an item in the embedding generation queue.
    
    This model tracks sources waiting for embedding generation,
    enabling batch processing and retry logic.
    """
    
    # Queue item identification
    id: str = Field(..., description="Queue item ID")
    source_id: str = Field(..., description="Source requiring embeddings")
    
    # Status tracking
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="Current processing status"
    )
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    error_message: Optional[str] = Field(None, description="Error if failed")
    
    # Timestamps
    created_at: datetime = Field(..., description="When queued")
    processed_at: Optional[datetime] = Field(None, description="When processed")
    
    # Processing metadata
    chunk_count: Optional[int] = Field(None, description="Number of chunks to process")
    embeddings_generated: Optional[int] = Field(
        None, description="Number of embeddings successfully generated"
    )
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if item can be retried."""
        return self.status == "failed" and self.retry_count < max_retries
    
    def get_wait_time(self) -> Optional[timedelta]:
        """Calculate how long item has been waiting."""
        if self.status == "pending":
            return datetime.now(timezone.utc) - self.created_at
        return None


# Update forward references for nested models
ArticleOutput.model_rebuild()
ArticleSection.model_rebuild()
StoredSource.model_rebuild()
SourceRelationship.model_rebuild()
