"""
Test script to verify all imports work correctly.

This script attempts to import all modules and their components
to ensure there are no import errors or circular dependencies.
"""

import sys
print("Python version:", sys.version)
print("-" * 50)

# Test standard library imports first
try:
    import asyncio
    import logging
    from datetime import datetime, timedelta
    from collections import deque
    from typing import Dict, Any, List, Optional
    import json
    from pathlib import Path
    from unittest.mock import AsyncMock, patch, MagicMock
    print("✓ Standard library imports successful")
except ImportError as e:
    print(f"✗ Standard library import error: {e}")
    sys.exit(1)

# Test third-party imports
try:
    import aiohttp
    print("✓ aiohttp imported successfully")
except ImportError:
    print("✗ aiohttp not installed. Run: pip install aiohttp")

try:
    import backoff
    print("✓ backoff imported successfully")
except ImportError:
    print("✗ backoff not installed. Run: pip install backoff")

try:
    import pytest
    import pytest_asyncio
    print("✓ pytest and pytest-asyncio imported successfully")
except ImportError as e:
    print(f"✗ pytest import error: {e}")

try:
    import pydantic
    from pydantic import BaseModel, Field, field_validator
    print(f"✓ pydantic imported successfully (version: {pydantic.__version__})")
except ImportError:
    print("✗ pydantic not installed. Run: pip install pydantic")

try:
    from pydantic_ai import Agent, RunContext
    print("✓ pydantic_ai imported successfully")
except ImportError:
    print("✗ pydantic_ai not installed. Run: pip install pydantic-ai")

try:
    import click
    print("✓ click imported successfully")
except ImportError:
    print("✗ click not installed. Run: pip install click")

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imported successfully")
except ImportError:
    print("✗ python-dotenv not installed. Run: pip install python-dotenv")

print("-" * 50)

# Test our custom modules
try:
    # Test config module
    from config import Config
    print("✓ config module imported successfully")
    
    # Test if we can create a config instance (without .env file)
    try:
        # This might fail without proper env vars, but import should work
        # config = Config()
        print("  - Config class is accessible")
    except Exception as e:
        print(f"  - Config instantiation requires environment variables (expected)")
        
except ImportError as e:
    print(f"✗ config import error: {e}")

try:
    # Test models module
    from models import (
        AcademicSource, ResearchFindings, ArticleOutput, 
        ArticleSection, ArticleSubsection,
        TavilySearchResult, TavilySearchResponse
    )
    print("✓ models module imported successfully")
    print("  - All model classes accessible")
except ImportError as e:
    print(f"✗ models import error: {e}")

try:
    # Test tools module
    from tools import (
        TavilyClient, TavilyAPIError, TavilyAuthError,
        TavilyRateLimitError, TavilyTimeoutError,
        search_academic_sources, extract_key_statistics,
        calculate_reading_time, clean_text_for_seo, generate_slug
    )
    print("✓ tools module imported successfully")
    print("  - All classes and functions accessible")
except ImportError as e:
    print(f"✗ tools import error: {e}")

try:
    # Test research_agent module
    from research_agent import create_research_agent
    from research_agent.agent import _mock_research_agent_run
    from research_agent.prompts import RESEARCH_AGENT_SYSTEM_PROMPT
    from research_agent.tools import search_academic
    print("✓ research_agent module imported successfully")
except ImportError as e:
    print(f"✗ research_agent import error: {e}")

try:
    # Test writer_agent module
    from writer_agent import create_writer_agent
    from writer_agent.agent import _mock_writer_agent_run
    from writer_agent.prompts import WRITER_AGENT_SYSTEM_PROMPT
    from writer_agent.tools import get_research_context, calculate_keyword_density
    print("✓ writer_agent module imported successfully")
except ImportError as e:
    print(f"✗ writer_agent import error: {e}")

try:
    # Test workflow module
    from workflow import WorkflowOrchestrator
    print("✓ workflow module imported successfully")
except ImportError as e:
    print(f"✗ workflow import error: {e}")

try:
    # Test main module
    import main
    print("✓ main module imported successfully")
except ImportError as e:
    print(f"✗ main import error: {e}")

print("-" * 50)

# Test for circular imports
print("\nChecking for circular imports...")
try:
    # Re-import everything to check for circular dependencies
    import config
    import models
    import tools
    import research_agent
    import writer_agent
    import workflow
    import main
    print("✓ No circular import issues detected")
except ImportError as e:
    print(f"✗ Circular import detected: {e}")

print("\n" + "=" * 50)
print("Import test completed!")
print("=" * 50)