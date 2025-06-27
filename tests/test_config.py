"""
Comprehensive tests for configuration management.

These tests ensure our configuration system properly validates
API keys, handles missing values, and creates necessary directories.
"""

# Import testing utilities
import pytest
from pathlib import Path
import tempfile
import os
from pydantic import ValidationError

# Import our configuration module
import sys
sys.path.insert(0, '/Users/willmckie/AI_agent_article')
from config import Config, get_config


class TestConfig:
    """Test suite for the Config class."""
    
    def test_valid_configuration(self, monkeypatch):
        """
        Test that valid configuration loads successfully.
        
        This test simulates a properly configured environment
        with all required API keys and valid settings.
        """
        # Set up mock environment variables
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        # Create configuration instance
        config = Config()
        
        # Verify all values loaded correctly
        assert config.tavily_api_key == "test_tavily_key_that_is_long_enough"
        assert config.openai_api_key == "test_openai_key_that_is_long_enough"
        assert config.llm_model == "gpt-4"
        assert config.log_level == "DEBUG"
        
    def test_missing_required_api_keys(self, monkeypatch):
        """
        Test that missing required API keys raise validation errors.
        
        This ensures users get clear error messages when
        they haven't configured their API keys.
        """
        # Clear any existing environment variables
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        # Disable .env file loading for this test
        monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
        
        # Attempting to create config should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Config(_env_file=None)  # Don't load .env file
        
        # Check that both missing keys are reported
        error_dict = exc_info.value.errors()
        field_names = [error["loc"][0] for error in error_dict]
        assert "tavily_api_key" in field_names
        assert "openai_api_key" in field_names
        
    def test_empty_api_keys_validation(self, monkeypatch):
        """
        Test that empty or whitespace API keys are rejected.
        
        This prevents users from accidentally using empty strings
        as API keys, which would fail at runtime.
        """
        # Set empty API keys
        monkeypatch.setenv("TAVILY_API_KEY", "   ")  # Just whitespace
        monkeypatch.setenv("OPENAI_API_KEY", "")     # Empty string
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            Config()
        
        # Check error messages mention empty keys
        errors = str(exc_info.value)
        assert "cannot be empty" in errors
        
    def test_placeholder_api_keys_rejected(self, monkeypatch):
        """
        Test that placeholder values in API keys are rejected.
        
        This catches the common mistake of not replacing
        example values with real API keys.
        """
        # Set placeholder values
        monkeypatch.setenv("TAVILY_API_KEY", "your_api_key_here")
        monkeypatch.setenv("OPENAI_API_KEY", "TODO")
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            Config()
        
        # Check error mentions placeholder
        errors = str(exc_info.value)
        assert "placeholder value" in errors.lower()
        
    def test_short_api_keys_rejected(self, monkeypatch):
        """
        Test that suspiciously short API keys are rejected.
        
        Most real API keys are at least 20 characters,
        so this catches typos or partial keys.
        """
        # Set short keys
        monkeypatch.setenv("TAVILY_API_KEY", "short")
        monkeypatch.setenv("OPENAI_API_KEY", "also_short")
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            Config()
        
        # Check error mentions key being too short
        errors = str(exc_info.value)
        assert "too short" in errors.lower()
        
    def test_output_directory_creation(self, monkeypatch, tmp_path):
        """
        Test that output directory is created if it doesn't exist.
        
        This ensures users don't need to manually create
        the drafts directory before running the system.
        """
        # Set up valid API keys
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Set output directory to a non-existent path
        output_dir = tmp_path / "test_output" / "drafts"
        monkeypatch.setenv("OUTPUT_DIR", str(output_dir))
        
        # Create config (should create directory)
        config = Config()
        
        # Verify directory was created
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert config.output_dir == output_dir
        
    def test_domain_parsing(self, monkeypatch):
        """
        Test that domain lists are parsed correctly.
        
        This ensures the domain filtering for Tavily
        works with various input formats.
        """
        # Set up valid API keys
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Test various domain formats
        test_cases = [
            ("edu,gov,org", [".edu", ".gov", ".org"]),
            (".edu,.gov,.org", [".edu", ".gov", ".org"]),
            ("edu, gov , org", [".edu", ".gov", ".org"]),  # With spaces
            ("", None),  # Empty string
            ("   ", None),  # Just whitespace
        ]
        
        for input_domains, expected in test_cases:
            monkeypatch.setenv("TAVILY_INCLUDE_DOMAINS", input_domains)
            config = Config()
            assert config.tavily_include_domains == expected
            
    def test_numeric_validation(self, monkeypatch):
        """
        Test that numeric fields are validated properly.
        
        This ensures retry counts and timeouts stay
        within reasonable bounds.
        """
        # Set up valid API keys
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Test valid numeric values
        monkeypatch.setenv("MAX_RETRIES", "5")
        monkeypatch.setenv("REQUEST_TIMEOUT", "60")
        monkeypatch.setenv("TAVILY_MAX_RESULTS", "15")
        
        config = Config()
        assert config.max_retries == 5
        assert config.request_timeout == 60
        assert config.tavily_max_results == 15
        
        # Test out-of-range values
        monkeypatch.setenv("MAX_RETRIES", "20")  # Too high (max is 10)
        with pytest.raises(ValidationError):
            Config()
            
    def test_log_level_validation(self, monkeypatch):
        """
        Test that log level only accepts valid values.
        
        This prevents typos in log level configuration
        from causing runtime errors.
        """
        # Set up valid API keys
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Test valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            monkeypatch.setenv("LOG_LEVEL", level)
            config = Config()
            assert config.log_level == level
            
        # Test invalid log level
        monkeypatch.setenv("LOG_LEVEL", "TRACE")  # Not a valid level
        with pytest.raises(ValidationError):
            Config()
            
    def test_search_depth_validation(self, monkeypatch):
        """
        Test that Tavily search depth only accepts valid values.
        
        Tavily API only supports 'basic' or 'advanced' search depth.
        """
        # Set up valid API keys
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Test valid search depths
        for depth in ["basic", "advanced"]:
            monkeypatch.setenv("TAVILY_SEARCH_DEPTH", depth)
            config = Config()
            assert config.tavily_search_depth == depth
            
        # Test invalid search depth
        monkeypatch.setenv("TAVILY_SEARCH_DEPTH", "deep")
        with pytest.raises(ValidationError):
            Config()
            
    def test_get_tavily_config(self, monkeypatch):
        """
        Test the get_tavily_config helper method.
        
        This method packages Tavily settings for easy use
        in the Tavily API client.
        """
        # Set up environment
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        monkeypatch.setenv("TAVILY_SEARCH_DEPTH", "advanced")
        monkeypatch.setenv("TAVILY_INCLUDE_DOMAINS", ".edu,.gov")
        monkeypatch.setenv("TAVILY_MAX_RESULTS", "10")
        
        config = Config()
        tavily_config = config.get_tavily_config()
        
        # Verify all Tavily settings are included
        assert tavily_config["api_key"] == "test_tavily_key_that_is_long_enough"
        assert tavily_config["search_depth"] == "advanced"
        assert tavily_config["max_results"] == 10
        assert tavily_config["include_domains"] == [".edu", ".gov"]
        
    def test_get_openai_config(self, monkeypatch):
        """
        Test the get_openai_config helper method.
        
        This method packages OpenAI settings for PydanticAI agents.
        """
        # Set up environment
        monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("REQUEST_TIMEOUT", "45")
        monkeypatch.setenv("MAX_RETRIES", "5")
        
        config = Config()
        openai_config = config.get_openai_config()
        
        # Verify all OpenAI settings are included
        assert openai_config["api_key"] == "test_openai_key_that_is_long_enough"
        assert openai_config["model"] == "gpt-4"
        assert openai_config["timeout"] == 45
        assert openai_config["max_retries"] == 5
        
    def test_case_insensitive_env_vars(self, monkeypatch):
        """
        Test that environment variables are case-insensitive.
        
        This makes configuration more forgiving of typos.
        """
        # Use mixed case environment variables
        monkeypatch.setenv("TAVILY_api_KEY", "test_tavily_key_that_is_long_enough")
        monkeypatch.setenv("openai_API_KEY", "test_openai_key_that_is_long_enough")
        
        # Should still load correctly
        config = Config()
        assert config.tavily_api_key == "test_tavily_key_that_is_long_enough"
        assert config.openai_api_key == "test_openai_key_that_is_long_enough"
        
    def test_get_config_singleton_behavior(self, monkeypatch):
        """
        Test that get_config provides helpful error messages.
        
        When configuration fails, users should get clear
        guidance on how to fix the problem.
        """
        # Clear API keys to trigger error
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        # Disable .env file loading
        monkeypatch.setattr("config.Config", lambda: Config(_env_file=None))
        
        # get_config should raise with helpful message
        with pytest.raises(Exception):
            get_config()


# Pytest fixtures for common test setup
@pytest.fixture
def valid_env(monkeypatch):
    """
    Fixture that sets up a valid environment for testing.
    
    Use this in tests that need a working configuration
    but aren't specifically testing configuration validation.
    """
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key_that_is_long_enough")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_that_is_long_enough")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("OUTPUT_DIR", "./test_drafts")
    yield
    # Cleanup happens automatically after test


if __name__ == "__main__":
    # Allow running tests directly with python test_config.py
    pytest.main([__file__, "-v"])