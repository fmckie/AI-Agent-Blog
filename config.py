"""
Configuration management for SEO Content Automation System.

This module handles all configuration settings including API keys,
output directories, and runtime parameters using Pydantic for validation.
"""

# Import required libraries for configuration management
import os
from pathlib import Path
from typing import List, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file if it exists
# Note: python-dotenv doesn't strip inline comments by default
load_dotenv()


class Config(BaseSettings):
    """
    Main configuration class using Pydantic Settings.

    This class automatically loads values from environment variables
    and validates them according to the specified types and constraints.
    """

    # Required API Keys
    # These are essential for the system to function
    tavily_api_key: str = Field(
        ...,  # ... means this field is required
        description="Tavily API key for academic web search",
    )
    openai_api_key: str = Field(..., description="OpenAI API key for PydanticAI agents")

    # LLM Configuration
    # Model selection for our PydanticAI agents
    llm_model: str = Field(
        default="gpt-4", description="OpenAI model to use for content generation"
    )

    # Output Configuration
    # Where we save our generated articles
    output_dir: Path = Field(
        default=Path("./drafts"), description="Directory for saving article drafts"
    )

    # Google Drive Configuration
    # These settings are for Google Drive integration
    google_drive_credentials_path: Path = Field(
        default=Path("credentials.json"),
        description="Path to Google OAuth credentials JSON file",
    )
    google_drive_token_path: Path = Field(
        default=Path("token.json"), description="Path to store OAuth token"
    )
    google_drive_folder_id: Optional[str] = Field(
        default=None, description="Google Drive folder ID to watch for documents"
    )
    google_drive_upload_folder_id: Optional[str] = Field(
        default=None,
        description="Google Drive folder ID for uploading generated articles",
    )
    google_drive_sync_interval: int = Field(
        default=300, ge=60, description="Sync interval in seconds (minimum 60)"
    )

    # Optional Settings with Defaults
    # These enhance functionality but aren't required
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging verbosity level"
    )
    max_retries: int = Field(
        default=3,
        ge=1,  # Greater than or equal to 1
        le=10,  # Less than or equal to 10
        description="Maximum retry attempts for API calls",
    )
    request_timeout: int = Field(
        default=30,
        ge=5,  # Minimum 5 seconds
        le=300,  # Maximum 5 minutes
        description="API request timeout in seconds",
    )

    # Tavily Search Configuration
    # Controls the depth and quality of research
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth - advanced provides better academic sources",
    )
    tavily_include_domains: Optional[List[str]] = Field(
        default=None,
        description="List of domains to prioritize (e.g., ['.edu', '.gov', '.org'])",
    )
    tavily_max_results: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of search results to return",
    )

    # Tavily Extract Configuration
    tavily_extract_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Extraction depth for full content - advanced includes tables and media",
    )
    tavily_extract_max_urls: int = Field(
        default=20,
        ge=1,
        le=20,
        description="Maximum URLs to extract in a single request",
    )

    # Tavily Crawl Configuration
    tavily_crawl_max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum crawl depth from starting URL",
    )
    tavily_crawl_max_breadth: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Maximum pages to crawl per depth level",
    )
    tavily_crawl_timeout: int = Field(
        default=60,
        ge=30,
        le=300,
        description="Crawl timeout in seconds",
    )

    # Research Strategy Configuration
    research_strategy: Literal["basic", "standard", "comprehensive"] = Field(
        default="standard",
        description="Research depth strategy - affects tool usage",
    )
    enable_multi_step_research: bool = Field(
        default=True,
        description="Enable automated multi-step research workflows",
    )
    min_credibility_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum credibility score for source inclusion",
    )

    # Workflow Configuration
    workflow_max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum retries for failed workflow stages",
    )
    workflow_stage_timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Timeout for individual workflow stages in seconds",
    )
    workflow_progress_reporting: bool = Field(
        default=True,
        description="Enable progress reporting during workflow execution",
    )
    workflow_fail_fast: bool = Field(
        default=False,
        description="Stop workflow immediately on first critical failure",
    )
    workflow_cache_results: bool = Field(
        default=True,
        description="Cache intermediate workflow results for retry/resume",
    )

    # Dynamic Tool Selection Configuration
    enable_adaptive_strategy: bool = Field(
        default=True,
        description="Allow strategy to adapt based on intermediate results",
    )
    tool_priority_threshold: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Minimum priority score for optional tool execution",
    )
    max_parallel_tools: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum number of tools to run in parallel",
    )
    prefer_recent_sources: bool = Field(
        default=True,
        description="Prioritize sources from the last 2 years",
    )

    # Performance Optimization
    enable_result_caching: bool = Field(
        default=True,
        description="Cache search and extraction results to avoid duplicate API calls",
    )
    cache_ttl_minutes: int = Field(
        default=60,
        ge=10,
        le=1440,  # Max 24 hours
        description="Cache time-to-live in minutes",
    )
    batch_extract_urls: bool = Field(
        default=True,
        description="Batch URL extraction requests for efficiency",
    )

    # Quality Control Configuration
    require_minimum_sources: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum number of credible sources required",
    )
    diversity_check: bool = Field(
        default=True,
        description="Ensure sources come from diverse domains",
    )
    fact_verification_level: Literal["none", "basic", "strict"] = Field(
        default="basic",
        description="Level of fact cross-verification between sources",
    )

    # Model configuration for Pydantic Settings
    model_config = SettingsConfigDict(
        # Look for env vars with this prefix (e.g., APP_TAVILY_API_KEY)
        env_prefix="",
        # Case-insensitive env var names
        case_sensitive=False,
        # Allow loading from .env file
        env_file=".env",
        # UTF-8 encoding for .env file
        env_file_encoding="utf-8",
        # Allow extra fields for forward compatibility
        extra="ignore",
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_inline_comments(cls, v):
        """
        Strip inline comments from environment variable values.

        Python-dotenv doesn't remove inline comments by default,
        so we need to handle values like "advanced  # Options: basic, advanced"

        Args:
            v: The value to clean

        Returns:
            The cleaned value without inline comments
        """
        if isinstance(v, str):
            # Find the first # that's preceded by whitespace
            # This avoids stripping # that might be part of the actual value
            if "#" in v:
                # Split on # and take the first part
                parts = v.split("#")
                if len(parts) > 1:
                    # Only strip if there's whitespace before the #
                    cleaned = parts[0].rstrip()
                    # Check if we actually had a comment (whitespace before #)
                    if cleaned != v.rstrip():
                        return cleaned
            return v
        return v

    @field_validator("output_dir")
    def create_output_directory(cls, v: Path) -> Path:
        """
        Ensure the output directory exists, creating it if necessary.

        Args:
            v: The path to validate and potentially create

        Returns:
            The validated (and created) path
        """
        # Convert to Path object if string was provided
        path = Path(v)

        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Return the path for use
        return path

    @field_validator("tavily_api_key", "openai_api_key")
    def validate_api_keys(cls, v: str, info) -> str:
        """
        Validate that API keys are not empty and have reasonable format.

        Args:
            v: The API key value to validate
            info: Validation info containing field name

        Returns:
            The validated API key

        Raises:
            ValueError: If the API key is invalid
        """
        # Check if the key is empty or just whitespace
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")

        # Check for placeholder values first (before length check)
        if v.lower() in ["your_api_key_here", "placeholder", "todo"]:
            raise ValueError(f"{info.field_name} contains a placeholder value")

        # Check minimum length (most API keys are at least 20 characters)
        if len(v.strip()) < 20:
            raise ValueError(f"{info.field_name} appears to be invalid (too short)")

        return v.strip()

    @field_validator("tavily_include_domains", mode="before")
    def parse_domains(cls, v: Optional[str]) -> Optional[List[str]]:
        """
        Parse comma-separated domain list into a clean list.

        Args:
            v: Comma-separated string of domains or list

        Returns:
            List of cleaned domain strings or None
        """
        # If it's already a list, return it
        if isinstance(v, list):
            return v

        # If it's None, use default domains
        if v is None:
            return [".edu", ".gov", ".org"]

        # If it's empty string or just whitespace, return None
        if isinstance(v, str) and not v.strip():
            return None

        # If it's a string, parse it
        if isinstance(v, str):
            # Split by comma and clean each domain
            domains = [d.strip() for d in v.split(",") if d.strip()]

            # Ensure each domain starts with a dot
            cleaned_domains = []
            for domain in domains:
                if not domain.startswith("."):
                    domain = f".{domain}"
                cleaned_domains.append(domain)

            return cleaned_domains if cleaned_domains else None

        return None

    def get_tavily_config(self) -> dict:
        """
        Get Tavily-specific configuration as a dictionary.

        Returns:
            Dictionary with Tavily API configuration
        """
        config = {
            "api_key": self.tavily_api_key,
            "search_depth": self.tavily_search_depth,
            "max_results": self.tavily_max_results,
            "include_domains": self.tavily_include_domains,
        }

        # Remove None values
        return {k: v for k, v in config.items() if v is not None}

    def get_openai_config(self) -> dict:
        """
        Get OpenAI-specific configuration for PydanticAI.

        Returns:
            Dictionary with OpenAI configuration
        """
        return {
            "api_key": self.openai_api_key,
            "model": self.llm_model,
            "timeout": self.request_timeout,
            "max_retries": self.max_retries,
        }

    def get_drive_base_config(self) -> dict:
        """
        Get Google Drive base configuration.

        Returns:
            Dictionary with Drive configuration needed by the DriveConfig class
        """
        return {
            "credentials_path": self.google_drive_credentials_path,
            "token_path": self.google_drive_token_path,
            "folder_id": self.google_drive_folder_id,
            "upload_folder_id": self.google_drive_upload_folder_id,
            "sync_interval": self.google_drive_sync_interval,
        }

    def get_workflow_config(self) -> dict:
        """
        Get workflow-specific configuration.

        Returns:
            Dictionary with workflow configuration settings
        """
        return {
            "research_strategy": self.research_strategy,
            "max_retries": self.workflow_max_retries,
            "stage_timeout": self.workflow_stage_timeout,
            "progress_reporting": self.workflow_progress_reporting,
            "fail_fast": self.workflow_fail_fast,
            "cache_results": self.workflow_cache_results,
            "enable_adaptive": self.enable_adaptive_strategy,
            "tool_priority_threshold": self.tool_priority_threshold,
            "max_parallel_tools": self.max_parallel_tools,
            "prefer_recent": self.prefer_recent_sources,
            "enable_caching": self.enable_result_caching,
            "cache_ttl": self.cache_ttl_minutes,
            "min_sources": self.require_minimum_sources,
            "diversity_check": self.diversity_check,
            "fact_verification": self.fact_verification_level,
        }

    def get_strategy_config(self) -> dict:
        """
        Get strategy-specific configuration for ResearchStrategy.

        Returns:
            Dictionary with strategy configuration settings
        """
        return {
            "enable_adaptive": self.enable_adaptive_strategy,
            "tool_priority_threshold": self.tool_priority_threshold,
            "prefer_recent_sources": self.prefer_recent_sources,
            "min_credibility": self.min_credibility_threshold,
            "require_minimum_sources": self.require_minimum_sources,
            "diversity_check": self.diversity_check,
        }


# Create a singleton instance of the configuration
# This will be imported and used throughout the application
def get_config() -> Config:
    """
    Get the configuration instance, creating it if necessary.

    This function ensures we only create one Config instance
    and reuse it throughout the application lifetime.

    Returns:
        The validated configuration instance

    Raises:
        ValidationError: If required environment variables are missing
    """
    try:
        # Config will automatically load from environment variables
        # No need to pass arguments as they're loaded from env/settings
        return Config()  # type: ignore[call-arg]
    except Exception as e:
        # Provide helpful error message for missing configuration
        print("\n❌ Configuration Error!")
        print("Please ensure you have created a .env file with required values.")
        print("You can copy .env.example to .env and fill in your API keys.")
        print(f"\nError details: {e}")
        raise


# Example usage and testing
if __name__ == "__main__":
    """
    Test the configuration by running this module directly.
    This helps verify that all settings are loading correctly.
    """
    try:
        # Attempt to load configuration
        config = get_config()

        # Print loaded configuration (hiding sensitive values)
        print("✅ Configuration loaded successfully!")
        print(f"Output directory: {config.output_dir}")
        print(f"Log level: {config.log_level}")
        print(f"LLM Model: {config.llm_model}")
        print(f"Tavily search depth: {config.tavily_search_depth}")
        print(f"Max retries: {config.max_retries}")
        print(f"Request timeout: {config.request_timeout}s")

        # Show API key status without revealing the actual keys
        print(f"\nAPI Keys:")
        print(f"  Tavily: {'✓' if config.tavily_api_key else '✗'} configured")
        print(f"  OpenAI: {'✓' if config.openai_api_key else '✗'} configured")

    except Exception as e:
        print(f"\n❌ Failed to load configuration: {e}")
        exit(1)
