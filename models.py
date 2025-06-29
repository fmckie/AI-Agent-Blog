"""
Pydantic models for structured agent outputs.

These models define the data structures that our PydanticAI agents
will produce, ensuring type safety and validation throughout the system.
"""

# Import Pydantic for data modeling
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional
from datetime import datetime


class AcademicSource(BaseModel):
    """
    Represents a single academic source found during research.
    
    This model captures all the metadata we need about each source
    to properly cite it and assess its credibility.
    """
    
    # Basic source information
    title: str = Field(
        ...,
        description="Title of the academic paper or article"
    )
    url: str = Field(
        ...,
        description="Direct URL to the source"
    )
    
    # Author and publication details
    authors: Optional[List[str]] = Field(
        default=None,
        description="List of author names"
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Publication date in ISO format or human-readable format"
    )
    journal_name: Optional[str] = Field(
        default=None,
        description="Name of the journal or publication"
    )
    
    # Content and credibility
    excerpt: str = Field(
        ...,
        description="Relevant excerpt or abstract from the source",
        max_length=500  # Limit excerpt length for readability
    )
    domain: str = Field(
        ...,
        description="Domain of the source (e.g., .edu, .gov, .org)"
    )
    credibility_score: float = Field(
        ...,
        ge=0.0,  # Greater than or equal to 0
        le=1.0,  # Less than or equal to 1
        description="Credibility score between 0 and 1"
    )
    
    # Additional metadata
    source_type: str = Field(
        default="web",
        description="Type of source: journal, book, web, report, etc."
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
    keyword: str = Field(
        ...,
        description="The keyword/topic that was researched"
    )
    research_summary: str = Field(
        ...,
        description="Executive summary of research findings",
        min_length=100,  # Ensure meaningful summary
        max_length=1000  # Keep it concise
    )
    
    # Academic sources found
    academic_sources: List[AcademicSource] = Field(
        ...,
        description="List of academic sources found",
        min_items=1  # At least one source required
    )
    
    # Extracted insights
    key_statistics: List[str] = Field(
        default_factory=list,
        description="Important statistics and data points found"
    )
    research_gaps: List[str] = Field(
        default_factory=list,
        description="Identified gaps in current research"
    )
    main_findings: List[str] = Field(
        ...,
        description="Main findings from the research",
        min_items=3  # At least 3 main findings
    )
    
    # Metadata
    total_sources_analyzed: int = Field(
        ...,
        ge=1,
        description="Total number of sources analyzed"
    )
    search_query_used: str = Field(
        ...,
        description="The actual search query sent to Tavily"
    )
    research_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the research was conducted"
    )
    
    @field_validator("academic_sources")
    def validate_source_credibility(cls, v: List[AcademicSource]) -> List[AcademicSource]:
        """
        Ensure we have credible sources.
        
        Args:
            v: List of academic sources
            
        Returns:
            Validated list of sources
            
        Raises:
            ValueError: If no credible sources found
        """
        # Check if we have at least one highly credible source
        credible_sources = [s for s in v if s.credibility_score >= 0.7]
        
        if not credible_sources:
            raise ValueError("At least one source with credibility >= 0.7 required")
            
        # Sort by credibility score (highest first)
        return sorted(v, key=lambda x: x.credibility_score, reverse=True)
    
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
            "\n## Main Findings"
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
        max_length=70  # Optimal for search engines
    )
    meta_description: str = Field(
        ...,
        description="SEO meta description",
        min_length=120,
        max_length=160  # Google's recommended length
    )
    focus_keyword: str = Field(
        ...,
        description="Primary keyword for SEO optimization"
    )
    
    # Article sections
    introduction: str = Field(
        ...,
        description="Engaging introduction with hook",
        min_length=150
    )
    main_sections: List['ArticleSection'] = Field(
        ...,
        description="Main body sections of the article",
        min_items=3  # At least 3 sections for depth
    )
    conclusion: str = Field(
        ...,
        description="Compelling conclusion with call-to-action",
        min_length=100
    )
    
    # Content metrics
    word_count: int = Field(
        ...,
        ge=1000,  # Minimum 1000 words for SEO
        description="Total word count of the article"
    )
    reading_time_minutes: int = Field(
        ...,
        ge=1,
        description="Estimated reading time in minutes"
    )
    
    # SEO optimization data
    keyword_density: float = Field(
        ...,
        ge=0.005,  # At least 0.5%
        le=0.03,   # Maximum 3%
        description="Keyword density percentage"
    )
    internal_links: List[str] = Field(
        default_factory=list,
        description="Suggested internal links"
    )
    external_links: List[str] = Field(
        default_factory=list,
        description="External reference links"
    )
    
    # Research connection
    sources_used: List[str] = Field(
        ...,
        description="List of source URLs used in the article"
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
            f"  <div class='introduction'>{self.introduction}</div>"
        ]
        
        # Add main sections
        for section in self.main_sections:
            html_parts.append(f"  <h2>{section.heading}</h2>")
            html_parts.append(f"  <div class='section-content'>{section.content}</div>")
            
            if section.subsections:
                for subsection in section.subsections:
                    html_parts.append(f"    <h3>{subsection.heading}</h3>")
                    html_parts.append(f"    <div class='subsection-content'>{subsection.content}</div>")
        
        # Add conclusion
        html_parts.extend([
            f"  <div class='conclusion'>{self.conclusion}</div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)


class ArticleSection(BaseModel):
    """
    Represents a main section within an article.
    
    Articles are structured with main sections (H2) and
    optional subsections (H3) for better organization.
    """
    
    heading: str = Field(
        ...,
        description="Section heading (H2 level)",
        min_length=5,
        max_length=100
    )
    content: str = Field(
        ...,
        description="Section content",
        min_length=200  # Each section should be substantial
    )
    subsections: Optional[List['ArticleSubsection']] = Field(
        default=None,
        description="Optional subsections (H3 level)"
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
        ...,
        description="Subsection heading (H3 level)",
        min_length=5,
        max_length=80
    )
    content: str = Field(
        ...,
        description="Subsection content",
        min_length=100
    )


# Update forward references for nested models
ArticleOutput.model_rebuild()
ArticleSection.model_rebuild()