"""
Models package for SEO Content Automation System.

This package contains model factories and utilities for creating
AI models from different providers (OpenAI, OpenRouter, etc.).
"""

# Import model factories for easy access
from .openrouter import create_openrouter_model

# Note: Data models (AcademicSource, ResearchFindings, etc.) are in models.py at the root level
# This package is specifically for AI model factories

__all__ = ["create_openrouter_model"]