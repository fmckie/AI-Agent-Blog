"""
Writer Agent module for SEO content generation.

This module provides the Writer Agent that transforms research findings
into SEO-optimized articles with comprehensive SEO optimization tools.
"""

from .agent import create_writer_agent, run_writer_agent
from .tools import (
    get_research_context,
    calculate_keyword_density,
    format_sources_for_citation,
    check_seo_requirements,
    generate_keyword_variations
)
from .utilities import (
    calculate_readability_score,
    extract_headers_structure,
    validate_header_hierarchy,
    find_transition_words,
    analyze_keyword_placement,
    calculate_content_score
)

__all__ = [
    'create_writer_agent',
    'run_writer_agent',
    'get_research_context',
    'calculate_keyword_density',
    'format_sources_for_citation',
    'check_seo_requirements',
    'generate_keyword_variations',
    'calculate_readability_score',
    'extract_headers_structure',
    'validate_header_hierarchy',
    'find_transition_words',
    'analyze_keyword_placement',
    'calculate_content_score'
]