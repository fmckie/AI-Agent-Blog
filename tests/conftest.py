"""
Global test fixtures and configuration.

This file provides common fixtures that can be used across all test files
to avoid duplication and ensure consistent test setup.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from pydantic_ai import RunContext

from config import Config
from models import (
    AcademicSource,
    ArticleOutput,
    ArticleSection,
    ResearchFindings,
    TavilySearchResponse,
    TavilySearchResult,
)
from tools import TavilyClient


# Configuration Fixtures
@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = Mock(spec=Config)
    config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
    config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
    config.tavily_search_depth = "advanced"
    config.tavily_include_domains = [".edu", ".gov", ".org"]
    config.tavily_max_results = 10
    config.request_timeout = 30
    config.max_retries = 3
    config.output_dir = Path("/tmp/test_output")
    config.log_level = "INFO"
    config.llm_model = "gpt-4"
    return config


@pytest.fixture
def basic_config():
    """Create basic mock configuration with minimal settings."""
    config = Mock(spec=Config)
    config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
    config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
    config.tavily_search_depth = "basic"
    config.tavily_include_domains = None
    config.tavily_max_results = 5
    config.request_timeout = 30
    config.max_retries = 3
    config.output_dir = Path("/tmp/test_output")
    return config


# Tavily Client Fixtures
@pytest.fixture
def tavily_client(mock_config):
    """Create Tavily client instance with mock configuration."""
    return TavilyClient(mock_config)


@pytest.fixture
def mock_tavily_response():
    """Create mock Tavily API response."""
    return TavilySearchResponse(
        query="test query",
        results=[
            TavilySearchResult(
                title="Test Research Paper",
                url="https://university.edu/paper",
                content="This is test research content with important findings.",
                credibility_score=0.9,
                domain=".edu",
            ),
            TavilySearchResult(
                title="Government Report",
                url="https://agency.gov/report",
                content="Official government findings on the topic.",
                credibility_score=0.8,
                domain=".gov",
            ),
        ],
        answer="Test summary of research findings",
        processing_metadata={
            "total_results": 2,
            "academic_results": 2,
            "search_time": 0.5,
        },
    )


# Research Data Fixtures
@pytest.fixture
def mock_academic_sources():
    """Create mock academic sources for testing."""
    return [
        AcademicSource(
            title="AI Research Paper",
            url="https://journal.edu/paper1",
            authors=["Smith, J.", "Doe, A."],
            publication_date="2024-01-15",
            excerpt="Important findings about artificial intelligence applications.",
            domain=".edu",
            credibility_score=0.9,
        ),
        AcademicSource(
            title="Machine Learning Study",
            url="https://university.edu/paper2",
            authors=["Johnson, M."],
            publication_date="2024-02-10",
            excerpt="Comprehensive analysis of ML algorithms and performance.",
            domain=".edu",
            credibility_score=0.85,
        ),
        AcademicSource(
            title="Technical Report",
            url="https://institute.org/report",
            authors=["Brown, K.", "Wilson, L."],
            publication_date="2024-01-20",
            excerpt="Technical analysis of emerging technologies.",
            domain=".org",
            credibility_score=0.75,
        ),
    ]


@pytest.fixture
def mock_research_findings(mock_academic_sources):
    """Create mock research findings for testing."""
    return ResearchFindings(
        keyword="artificial intelligence",
        research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
        academic_sources=mock_academic_sources,
        key_statistics=["85% improvement in efficiency", "2x faster processing"],
        research_gaps=["Long-term societal effects need more study"],
        main_findings=[
            "AI transforms industries through automation and optimization",
            "Ethical considerations are crucial for responsible AI deployment",
            "Rapid advancement continues in machine learning capabilities",
        ],
        total_sources_analyzed=10,
        search_query_used="artificial intelligence research applications",
    )


# Article Content Fixtures
@pytest.fixture
def mock_article_sections():
    """Create mock article sections for testing."""
    return [
        ArticleSection(
            heading="Introduction to Artificial Intelligence",
            content="Artificial intelligence represents a paradigm shift in technology that is transforming how we live and work. This comprehensive introduction explores the fundamental concepts of AI, its historical development, and its growing importance in modern society. We'll examine how AI is revolutionizing various industries and shaping our future.",
        ),
        ArticleSection(
            heading="Applications and Use Cases",
            content="AI applications span numerous industries, from healthcare and finance to transportation and entertainment. In healthcare, AI assists with diagnosis and treatment planning, while in finance, it powers fraud detection and algorithmic trading. This section explores these diverse applications in comprehensive detail.",
        ),
        ArticleSection(
            heading="Future Prospects and Challenges",
            content="The future holds exciting possibilities for artificial intelligence technology. As systems become more sophisticated, we can expect AI capable of complex reasoning and decision-making. However, this also brings challenges including ethical considerations, job displacement, and the need for responsible development.",
        ),
    ]


@pytest.fixture
def mock_article_output(mock_article_sections):
    """Create mock article output for testing."""
    return ArticleOutput(
        title="Complete Guide to AI: Applications and Future",
        meta_description="Explore the world of artificial intelligence, its practical applications across industries, benefits for businesses, and future prospects.",
        focus_keyword="artificial intelligence",
        introduction="Artificial intelligence (AI) is revolutionizing how we live and work in the modern digital age. This comprehensive guide explores the latest developments in AI technology, its practical applications across various industries, and its potential to transform our future through innovative solutions and enhanced decision-making capabilities.",
        main_sections=mock_article_sections,
        conclusion="In conclusion, artificial intelligence will continue to shape our future in profound ways. As we embrace these technologies, we must ensure responsible development and deployment while maximizing the benefits for society and business innovation.",
        word_count=1500,
        reading_time_minutes=6,
        keyword_density=0.015,
        sources_used=[
            "https://journal.edu/paper1",
            "https://university.edu/paper2",
            "https://institute.org/report",
        ],
    )


# Agent and Context Fixtures
@pytest.fixture
def mock_run_context():
    """Create mock PydanticAI RunContext for testing."""
    context = Mock(spec=RunContext)
    context.deps = None
    return context


@pytest.fixture
def mock_agent_result():
    """Create mock agent result with data attribute."""
    mock_result = Mock()
    mock_result.data = {}
    return mock_result


# Async Test Helpers
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Utility Fixtures
@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for testing."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def mock_datetime():
    """Create mock datetime for consistent testing."""
    return datetime(2024, 6, 30, 12, 0, 0)


# Test Data Fixtures
@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        {
            "title": "Academic Research on AI",
            "url": "https://university.edu/ai-research",
            "content": "This peer-reviewed study examines artificial intelligence applications in healthcare and shows significant improvements in diagnostic accuracy.",
            "score": 0.95,
        },
        {
            "title": "Government AI Policy Report",
            "url": "https://tech.gov/ai-policy",
            "content": "Official analysis of AI regulation frameworks and recommendations for ethical AI development in government applications.",
            "score": 0.88,
        },
        {
            "title": "Industry AI Implementation",
            "url": "https://tech.org/ai-industry",
            "content": "Comprehensive analysis of AI adoption across industries with case studies and performance metrics from real-world implementations.",
            "score": 0.82,
        },
    ]


@pytest.fixture
def long_text_content():
    """Create long text content for testing text processing functions."""
    return """
    This is a comprehensive text that contains multiple paragraphs and various types of content.
    It includes statistical information such as 85% improvement rates and mentions that over 1,200 
    participants were involved in the study. The research shows a 2.5x increase in effectiveness 
    compared to traditional methods.
    
    The success rate was 92.3 percent among the control group, while the experimental group 
    achieved even better results. Studies indicate that approximately 75% of organizations 
    reported positive outcomes when implementing these solutions.
    
    Additional findings suggest that costs were reduced by 40% on average, with some cases 
    showing reductions of up to 60%. The implementation timeline averaged 3.2 months across 
    all participating organizations.
    
    Furthermore, user satisfaction scores increased by 25 points on a 100-point scale, 
    demonstrating significant improvements in user experience and overall system performance.
    """


# Mock API Response Fixtures
@pytest.fixture
def mock_api_error_responses():
    """Create mock API error responses for testing error handling."""
    return {
        "auth_error": {
            "status": 401,
            "message": "Unauthorized - Invalid API key",
            "error_type": "authentication_error",
        },
        "rate_limit_error": {
            "status": 429,
            "message": "Too Many Requests - Rate limit exceeded",
            "error_type": "rate_limit_error",
            "retry_after": 60,
        },
        "server_error": {
            "status": 500,
            "message": "Internal Server Error",
            "error_type": "server_error",
        },
        "timeout_error": {
            "status": 408,
            "message": "Request Timeout",
            "error_type": "timeout_error",
        },
    }


# Workflow Test Fixtures
@pytest.fixture
def mock_workflow_config(mock_config, temp_output_dir):
    """Create configuration specifically for workflow testing."""
    mock_config.output_dir = temp_output_dir
    return mock_config


@pytest.fixture
def minimal_research_findings():
    """Create minimal research findings with required attributes for workflow tests."""
    mock_findings = Mock(spec=ResearchFindings)
    mock_findings.academic_sources = [Mock()]
    mock_findings.main_findings = ["Test finding"]
    mock_findings.key_statistics = ["85% improvement"]
    mock_findings.research_gaps = ["Need more data"]
    mock_findings.keyword = "test"
    mock_findings.research_summary = "Test summary"
    mock_findings.total_sources_analyzed = 1
    mock_findings.search_query_used = "test query"
    return mock_findings


# Integration Test Fixtures
@pytest.fixture
def integration_test_data():
    """Create comprehensive test data for integration tests."""
    return {
        "keywords": [
            "artificial intelligence",
            "machine learning",
            "data science",
            "blockchain technology",
        ],
        "expected_min_sources": 3,
        "expected_min_word_count": 1000,
        "expected_sections": 3,
    }