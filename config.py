"""
Configuration management for SEO Content Automation System.

This module handles all configuration settings including API keys,
output directories, and runtime parameters using Pydantic for validation.
"""

# Import required libraries for configuration management
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
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
        description="Tavily API key for academic web search"
    )
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for PydanticAI agents"
    )
    
    # LLM Configuration
    # Model selection for our PydanticAI agents
    llm_model: str = Field(
        default="gpt-4",
        description="OpenAI model to use for content generation"
    )
    
    # Output Configuration
    # Where we save our generated articles
    output_dir: Path = Field(
        default=Path("./drafts"),
        description="Directory for saving article drafts"
    )
    
    # Optional Settings with Defaults
    # These enhance functionality but aren't required
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity level"
    )
    max_retries: int = Field(
        default=3,
        ge=1,  # Greater than or equal to 1
        le=10,  # Less than or equal to 10
        description="Maximum retry attempts for API calls"
    )
    request_timeout: int = Field(
        default=30,
        ge=5,  # Minimum 5 seconds
        le=300,  # Maximum 5 minutes
        description="API request timeout in seconds"
    )
    
    # Tavily Search Configuration
    # Controls the depth and quality of research
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth - advanced provides better academic sources"
    )
    tavily_include_domains: Optional[str] = Field(
        default=".edu,.gov,.org",
        description="Comma-separated list of domains to prioritize"
    )
    tavily_max_results: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of search results to return"
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
        extra="ignore"
    )
    
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
    
    @field_validator("tavily_include_domains")
    def parse_domains(cls, v: Optional[str]) -> Optional[list[str]]:
        """
        Parse comma-separated domain list into a clean list.
        
        Args:
            v: Comma-separated string of domains
            
        Returns:
            List of cleaned domain strings or None
        """
        if not v:
            return None
        
        # Split by comma and clean each domain
        domains = [d.strip() for d in v.split(",") if d.strip()]
        
        # Ensure each domain starts with a dot
        cleaned_domains = []
        for domain in domains:
            if not domain.startswith("."):
                domain = f".{domain}"
            cleaned_domains.append(domain)
        
        return cleaned_domains if cleaned_domains else None
    
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
        return Config()
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