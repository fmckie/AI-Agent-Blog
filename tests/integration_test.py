"""
Integration test to verify all components work together.

This script tests the complete flow without actually calling external APIs.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

# Set test environment variables
os.environ["TAVILY_API_KEY"] = "test-key-12345678901234567890"
os.environ["OPENAI_API_KEY"] = "test-key-12345678901234567890"
os.environ["OUTPUT_DIR"] = "./test_output"
os.environ["LOG_LEVEL"] = "DEBUG"

# Now import our modules
from config import Config
from models import (
    AcademicSource,
    ArticleOutput,
    ArticleSection,
    ResearchFindings,
    TavilySearchResponse,
    TavilySearchResult,
)
from tools import TavilyAPIError, TavilyClient
from workflow import WorkflowOrchestrator


def test_imports():
    """Test that all imports work correctly."""
    print("✓ All imports successful")


def test_config():
    """Test configuration loading."""
    try:
        config = Config()
        print("✓ Config loaded successfully")
        assert config.tavily_api_key == "test-key-12345678901234567890"
        assert config.openai_api_key == "test-key-12345678901234567890"
        print("✓ Config values correct")
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        raise


def test_models():
    """Test Pydantic models."""
    try:
        # Test TavilySearchResult
        result = TavilySearchResult(
            title="Test Article",
            url="https://example.edu/test",
            content="Test content about research",
            credibility_score=0.9,
            domain=".edu",
        )
        print("✓ TavilySearchResult model works")

        # Test TavilySearchResponse
        response = TavilySearchResponse(
            query="test query",
            results=[result],
            processing_metadata={"total_results": 1},
        )
        print("✓ TavilySearchResponse model works")

        # Test AcademicSource
        source = AcademicSource(
            title="Academic Paper",
            url="https://journal.org/paper",
            excerpt="Important findings...",
            domain=".org",
            credibility_score=0.85,
        )
        print("✓ AcademicSource model works")

        # Test ResearchFindings
        findings = ResearchFindings(
            keyword="machine learning",
            research_summary="Comprehensive research summary "
            * 10,  # Make it long enough
            academic_sources=[source],
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=5,
            search_query_used="machine learning research",
        )
        print("✓ ResearchFindings model works")

        # Test ArticleSection
        section = ArticleSection(
            heading="Introduction to ML",
            content="Machine learning is a fascinating field... "
            * 50,  # Make it long enough
        )
        print("✓ ArticleSection model works")

        # Test ArticleOutput
        article = ArticleOutput(
            title="Understanding Machine Learning",
            meta_description="A comprehensive guide to machine learning concepts and applications for beginners and experts alike. Learn the fundamentals and advanced techniques.",
            focus_keyword="machine learning",
            introduction="Machine learning has revolutionized... " * 20,
            main_sections=[section, section, section],  # 3 sections minimum
            conclusion="In conclusion, machine learning... " * 10,
            word_count=1500,
            reading_time_minutes=7,
            keyword_density=0.02,
            sources_used=["https://example.edu/paper"],
        )
        print("✓ ArticleOutput model works")

        # Test model methods
        assert len(response.get_academic_results()) == 1
        print("✓ Model methods work correctly")

    except Exception as e:
        print(f"✗ Model test failed: {e}")
        raise


async def test_tavily_client():
    """Test TavilyClient initialization."""
    try:
        config = Config()
        async with TavilyClient(config) as client:
            print("✓ TavilyClient initializes correctly")

            # Test rate limiter exists
            assert hasattr(client, "_request_times")
            assert hasattr(client, "_rate_limit_lock")
            print("✓ Rate limiting components initialized")

    except Exception as e:
        print(f"✗ TavilyClient test failed: {e}")
        raise


async def test_workflow():
    """Test WorkflowOrchestrator initialization."""
    try:
        config = Config()
        orchestrator = WorkflowOrchestrator(config)
        print("✓ WorkflowOrchestrator initializes correctly")

        # Check agents are created
        assert hasattr(orchestrator, "research_agent")
        assert hasattr(orchestrator, "writer_agent")
        print("✓ Agents created successfully")

        # Check output directory
        assert orchestrator.output_dir.exists()
        print("✓ Output directory created")

    except Exception as e:
        print(f"✗ Workflow test failed: {e}")
        raise


def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "config.py",
        "models.py",
        "tools.py",
        "workflow.py",
        "main.py",
        "research_agent/__init__.py",
        "research_agent/agent.py",
        "research_agent/prompts.py",
        "research_agent/tools.py",
        "writer_agent/__init__.py",
        "writer_agent/agent.py",
        "writer_agent/prompts.py",
        "writer_agent/tools.py",
        "tests/test_config.py",
        "tests/test_tools.py",
        "requirements.txt",
        "CLAUDE.md",
        "README.md",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        raise FileNotFoundError(f"Missing required files: {missing_files}")
    else:
        print("✓ All required files exist")


async def main():
    """Run all integration tests."""
    print("=" * 50)
    print("Running Integration Tests")
    print("=" * 50)
    print()

    # Run synchronous tests
    test_imports()
    test_config()
    test_models()
    test_file_structure()

    # Run async tests
    await test_tavily_client()
    await test_workflow()

    print()
    print("=" * 50)
    print("✅ All integration tests passed!")
    print("=" * 50)

    # Cleanup test output directory
    import shutil

    if Path("./test_output").exists():
        shutil.rmtree("./test_output")
        print("\nCleaned up test output directory")


if __name__ == "__main__":
    asyncio.run(main())
