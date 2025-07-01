"""
Test helpers and utilities.

This module provides helper functions and utilities for creating
consistent test mocks and fixtures across the test suite.
"""

from typing import Any, Dict, TypeVar
from unittest.mock import Mock

from models import ArticleOutput, ArticleSection, ArticleSubsection, ResearchFindings


T = TypeVar("T")


class MockAgentRunResult:
    """Mock for PydanticAI AgentRunResult."""
    
    def __init__(self, data: T):
        """Initialize with result data."""
        self.data = data
        self.messages = []
        self.cost = Mock(total=0.0)
        self.model_usage = Mock()


def create_valid_article_output(
    keyword: str = "test keyword",
    title: str = None,
    sources_count: int = 3
) -> ArticleOutput:
    """
    Create a valid ArticleOutput that meets all validation requirements.
    
    Args:
        keyword: The focus keyword
        title: Optional custom title
        sources_count: Number of sources to include
        
    Returns:
        Valid ArticleOutput instance
    """
    if title is None:
        title = f"Comprehensive Guide to {keyword.title()}: Expert Insights"
    
    # Ensure meta description fits within 120-160 char limit
    meta_desc = f"Discover everything about {keyword} with our comprehensive guide. Expert insights, practical tips, and proven strategies for success included."
    if len(meta_desc) > 160:
        # Truncate keyword if needed to fit
        truncated_keyword = keyword[:15] + "..." if len(keyword) > 15 else keyword
        meta_desc = f"Learn about {truncated_keyword} with our comprehensive guide featuring expert insights, practical tips, and proven strategies for success."
    elif len(meta_desc) < 120:
        # Extend if too short
        meta_desc = f"Discover everything about {keyword} in our comprehensive guide. Learn from expert insights, practical implementation tips, and proven strategies."
    
    return ArticleOutput(
        title=title,
        meta_description=meta_desc,
        focus_keyword=keyword,
        introduction=(
            f"Welcome to our comprehensive guide on {keyword}. This article provides "
            f"in-depth insights, expert analysis, and practical information about {keyword}. "
            f"Whether you're a beginner or an experienced professional, you'll find valuable "
            f"information to enhance your understanding and application of {keyword} concepts."
        ),
        main_sections=[
            ArticleSection(
                heading=f"Understanding {keyword.title()} Fundamentals",
                content=(
                    f"The fundamentals of {keyword} are essential for anyone looking to "
                    f"master this topic. In this section, we'll explore the core concepts, "
                    f"basic principles, and foundational knowledge needed to understand {keyword}. "
                    f"Our comprehensive analysis covers theoretical aspects and practical applications, "
                    f"ensuring you gain a complete understanding of {keyword} fundamentals."
                )
            ),
            ArticleSection(
                heading=f"Advanced {keyword.title()} Techniques",
                content=(
                    f"Building on the fundamentals, advanced {keyword} techniques offer "
                    f"sophisticated approaches to maximize effectiveness. This section delves into "
                    f"expert-level strategies, cutting-edge methodologies, and proven best practices. "
                    f"Learn how professionals leverage advanced {keyword} techniques to achieve "
                    f"exceptional results in real-world applications."
                )
            ),
            ArticleSection(
                heading=f"Practical Applications of {keyword.title()}",
                content=(
                    f"Understanding how to apply {keyword} in practice is crucial for success. "
                    f"This section provides real-world examples, case studies, and implementation "
                    f"strategies. Discover how various industries and professionals use {keyword} "
                    f"to solve problems, improve processes, and achieve their goals. Learn from "
                    f"successful implementations and avoid common pitfalls."
                ),
                subsections=[
                    ArticleSubsection(
                        heading="Industry Case Studies",
                        content=(
                            f"Examining real-world case studies helps illustrate the practical value "
                            f"of {keyword}. Here we analyze successful implementations across different "
                            f"industries, highlighting key strategies, challenges overcome, and results "
                            f"achieved. These examples provide valuable insights for your own {keyword} "
                            f"implementation efforts."
                        )
                    )
                ]
            ),
            ArticleSection(
                heading=f"Future Trends in {keyword.title()}",
                content=(
                    f"The landscape of {keyword} continues to evolve rapidly. This section explores "
                    f"emerging trends, future predictions, and potential developments that will shape "
                    f"the field. Stay ahead of the curve by understanding where {keyword} is heading "
                    f"and how to prepare for upcoming changes. Expert insights provide valuable "
                    f"perspective on the future direction of {keyword}."
                )
            )
        ],
        conclusion=(
            f"In conclusion, mastering {keyword} requires understanding both fundamental concepts "
            f"and advanced techniques. This guide has provided comprehensive coverage of essential "
            f"aspects, practical applications, and future trends. Apply these insights to enhance "
            f"your {keyword} expertise and achieve better results in your endeavors."
        ),
        word_count=1500,
        reading_time_minutes=7,
        keyword_density=0.015,
        sources_used=[f"https://example{i}.edu/research" for i in range(sources_count)]
    )


def create_minimal_valid_article_output(keyword: str = "test") -> ArticleOutput:
    """
    Create a minimal valid ArticleOutput that just meets validation requirements.
    
    Args:
        keyword: The focus keyword
        
    Returns:
        Minimal valid ArticleOutput instance
    """
    return ArticleOutput(
        title=f"Guide to {keyword}",  # Min 10 chars
        meta_description="x" * 120,  # Exactly 120 chars
        focus_keyword=keyword,
        introduction="x" * 150,  # Exactly 150 chars
        main_sections=[
            ArticleSection(
                heading=f"Section {i}",
                content="x" * 100  # Exactly 100 chars
            )
            for i in range(3)  # Exactly 3 sections
        ],
        conclusion="x" * 100,  # Exactly 100 chars
        word_count=1000,
        reading_time_minutes=5,
        keyword_density=0.01,
        sources_used=["https://example.com"]
    )