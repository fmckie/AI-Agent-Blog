"""
Tests for OpenRouter integration.

This module tests the OpenRouter model factory and integration with agents.
"""

# Import required testing libraries
import os
from unittest.mock import Mock, patch, MagicMock
import pytest

# Import our OpenRouter implementation
from models.openrouter import (
    create_openrouter_model,
    create_openrouter_model_from_config,
    get_model_info,
)
from config import Config
from research_agent.agent import create_research_agent
from writer_agent.agent import create_writer_agent


class TestOpenRouterModelFactory:
    """Test the OpenRouter model factory functions."""
    
    def test_create_openrouter_model_success(self):
        """Test successful model creation with valid inputs."""
        # Create a model with valid parameters
        model = create_openrouter_model(
            model_name="anthropic/claude-3.5-sonnet",
            api_key="sk-or-v1-test-key-with-sufficient-length",
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Verify the model was created
        assert model is not None
        assert model.model == "anthropic/claude-3.5-sonnet"
    
    def test_create_openrouter_model_with_headers(self):
        """Test model creation with extra headers."""
        # Create model with custom headers
        extra_headers = {
            "HTTP-Referer": "https://myapp.com",
            "X-Title": "Test App"
        }
        
        model = create_openrouter_model(
            model_name="openai/gpt-4o",
            api_key="sk-or-v1-test-key-with-sufficient-length",
            extra_headers=extra_headers
        )
        
        # Verify model was created
        assert model is not None
        assert model.model == "openai/gpt-4o"
    
    def test_create_openrouter_model_empty_model_name(self):
        """Test that empty model name raises ValueError."""
        # Should raise ValueError for empty model name
        with pytest.raises(ValueError, match="model_name cannot be empty"):
            create_openrouter_model(
                model_name="",
                api_key="sk-or-v1-test-key"
            )
    
    def test_create_openrouter_model_empty_api_key(self):
        """Test that empty API key raises ValueError."""
        # Should raise ValueError for empty API key
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            create_openrouter_model(
                model_name="anthropic/claude-3.5-sonnet",
                api_key=""
            )
    
    def test_create_openrouter_model_invalid_format(self):
        """Test that invalid model format raises ValueError."""
        # Should raise ValueError for model without provider prefix
        with pytest.raises(ValueError, match="provider/model"):
            create_openrouter_model(
                model_name="gpt-4o",  # Missing provider prefix
                api_key="sk-or-v1-test-key"
            )
    
    def test_get_model_info_known_model(self):
        """Test getting info for a known model."""
        # Get info for a known model
        info = get_model_info("anthropic/claude-3.5-sonnet")
        
        # Verify expected fields
        assert info["provider"] == "Anthropic"
        assert info["context_window"] == 200000
        assert "reasoning" in info["strengths"]
        assert info["supports_tools"] is True
        assert info["supports_vision"] is True
    
    def test_get_model_info_unknown_model(self):
        """Test getting info for an unknown model."""
        # Get info for unknown model
        info = get_model_info("unknown/model-123")
        
        # Should return generic info
        assert info["provider"] == "unknown"
        assert info["context_window"] == "Unknown"
        assert info["supports_tools"] is False


class TestOpenRouterConfigIntegration:
    """Test OpenRouter integration with configuration."""
    
    def test_create_model_from_config_enabled(self):
        """Test creating model when OpenRouter is enabled."""
        # Mock config with OpenRouter enabled
        config = Mock()
        config.use_openrouter = True
        config.openrouter_api_key = "sk-or-v1-test-key-with-sufficient-length"
        config.get_openrouter_config.return_value = {
            "api_key": "sk-or-v1-test-key-with-sufficient-length",
            "base_url": "https://openrouter.ai/api/v1",
            "extra_headers": {"X-Title": "Test"}
        }
        config.get_model_for_task.return_value = "anthropic/claude-3.5-sonnet"
        
        # Create model from config
        model = create_openrouter_model_from_config(config, task="research")
        
        # Verify model was created
        assert model is not None
        assert model.model == "anthropic/claude-3.5-sonnet"
    
    def test_create_model_from_config_disabled(self):
        """Test creating model when OpenRouter is disabled."""
        # Mock config with OpenRouter disabled
        config = Mock()
        config.use_openrouter = False
        
        # Create model from config
        model = create_openrouter_model_from_config(config)
        
        # Should return None when disabled
        assert model is None
    
    def test_create_model_from_config_no_config(self):
        """Test creating model with missing config."""
        # Mock config without OpenRouter settings
        config = Mock()
        config.get_openrouter_config.return_value = {}
        
        # Should handle gracefully
        model = create_openrouter_model_from_config(config)
        assert model is None


class TestAgentIntegration:
    """Test OpenRouter integration with agents."""
    
    @patch('research_agent.agent.create_openrouter_model')
    def test_research_agent_with_openrouter(self, mock_create_model):
        """Test research agent uses OpenRouter when configured."""
        # Mock the model creation
        mock_model = Mock()
        mock_create_model.return_value = mock_model
        
        # Mock config with OpenRouter enabled
        config = Mock()
        config.use_openrouter = True
        config.openrouter_api_key = "sk-or-v1-test-key"
        config.openrouter_base_url = "https://openrouter.ai/api/v1"
        config.openrouter_site_url = "https://myapp.com"
        config.openrouter_app_name = "Test App"
        config.get_model_for_task.return_value = "anthropic/claude-3.5-sonnet"
        
        # Create research agent
        agent = create_research_agent(config)
        
        # Verify OpenRouter model was used
        mock_create_model.assert_called_once_with(
            model_name="anthropic/claude-3.5-sonnet",
            api_key="sk-or-v1-test-key",
            base_url="https://openrouter.ai/api/v1",
            extra_headers={
                "HTTP-Referer": "https://myapp.com",
                "X-Title": "Test App"
            }
        )
    
    def test_research_agent_without_openrouter(self):
        """Test research agent falls back to OpenAI."""
        # Mock config with OpenRouter disabled
        config = Mock()
        config.use_openrouter = False
        config.llm_model = "gpt-4"
        config.get_openai_config.return_value = {
            "api_key": "test-key",
            "model": "gpt-4"
        }
        
        # Create research agent
        agent = create_research_agent(config)
        
        # Agent should be created successfully
        assert agent is not None
    
    @patch('writer_agent.agent.create_openrouter_model')
    def test_writer_agent_with_openrouter(self, mock_create_model):
        """Test writer agent uses OpenRouter when configured."""
        # Mock the model creation
        mock_model = Mock()
        mock_create_model.return_value = mock_model
        
        # Mock config with OpenRouter enabled
        config = Mock()
        config.use_openrouter = True
        config.openrouter_api_key = "sk-or-v1-test-key"
        config.openrouter_base_url = "https://openrouter.ai/api/v1"
        config.openrouter_site_url = None  # Test without site URL
        config.openrouter_app_name = "Test App"
        config.get_model_for_task.return_value = "openai/gpt-4o"
        
        # Create writer agent
        agent = create_writer_agent(config)
        
        # Verify OpenRouter model was used with correct task
        config.get_model_for_task.assert_called_with("writer")
        mock_create_model.assert_called_once()


class TestConfigurationValidation:
    """Test configuration validation for OpenRouter."""
    
    def test_config_use_openrouter_property(self):
        """Test the use_openrouter property."""
        # Create config instance with API key
        config = Config(
            tavily_api_key="test-tavily-key-with-sufficient-length",
            openai_api_key="test-openai-key-with-sufficient-length",
            openrouter_api_key="sk-or-v1-test-key-with-sufficient-length"
        )
        
        # Should return True when API key is set
        assert config.use_openrouter is True
        
        # Create config without OpenRouter key
        config_no_or = Config(
            tavily_api_key="test-tavily-key-with-sufficient-length",
            openai_api_key="test-openai-key-with-sufficient-length",
            openrouter_api_key=None
        )
        
        # Should return False when no API key
        assert config_no_or.use_openrouter is False
    
    def test_config_get_model_for_task(self):
        """Test getting model for specific tasks."""
        # Create config with OpenRouter
        config = Config(
            tavily_api_key="test-tavily-key-with-sufficient-length",
            openai_api_key="test-openai-key-with-sufficient-length",
            openrouter_api_key="sk-or-v1-test-key-with-sufficient-length",
            openrouter_research_model="anthropic/claude-3.5-sonnet",
            openrouter_writer_model="openai/gpt-4o"
        )
        
        # Test research task
        assert config.get_model_for_task("research") == "anthropic/claude-3.5-sonnet"
        
        # Test writer task
        assert config.get_model_for_task("writer") == "openai/gpt-4o"
        
        # Test unknown task (should default to research)
        assert config.get_model_for_task("unknown") == "anthropic/claude-3.5-sonnet"
    
    def test_config_get_openrouter_config(self):
        """Test getting OpenRouter configuration dict."""
        # Create config with all OpenRouter settings
        config = Config(
            tavily_api_key="test-tavily-key-with-sufficient-length",
            openai_api_key="test-openai-key-with-sufficient-length",
            openrouter_api_key="sk-or-v1-test-key-with-sufficient-length",
            openrouter_site_url="https://myapp.com",
            openrouter_app_name="My App"
        )
        
        # Get OpenRouter config
        or_config = config.get_openrouter_config()
        
        # Verify all fields
        assert or_config["api_key"] == "sk-or-v1-test-key-with-sufficient-length"
        assert or_config["base_url"] == "https://openrouter.ai/api/v1"
        assert or_config["research_model"] == "anthropic/claude-3.5-sonnet"
        assert or_config["writer_model"] == "openai/gpt-4o"
        assert or_config["extra_headers"]["HTTP-Referer"] == "https://myapp.com"
        assert or_config["extra_headers"]["X-Title"] == "My App"


# Integration test requiring real API key
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OpenRouter API key not available"
)
async def test_real_openrouter_api_call():
    """Test actual API call through OpenRouter (requires API key)."""
    # This test only runs if OPENROUTER_API_KEY is set
    from pydantic_ai import Agent
    
    # Create model with real API key
    model = create_openrouter_model(
        model_name="anthropic/claude-3.5-sonnet",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    
    # Create simple agent
    agent = Agent(model)
    
    # Make a simple request
    result = await agent.run("Say 'OpenRouter test successful' and nothing else.")
    
    # Verify response
    assert "OpenRouter test successful" in result.lower()


if __name__ == "__main__":
    """Run tests when module is executed directly."""
    pytest.main([__file__, "-v"])