"""
OpenRouter model factory for PydanticAI integration.

This module provides factory functions to create OpenRouter-compatible
models that work seamlessly with PydanticAI agents.
"""

# Import required libraries for OpenRouter integration
import os
from typing import Any, Dict, Optional

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


def create_openrouter_model(
    model_name: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> OpenAIModel:
    """
    Factory function to create OpenRouter models for PydanticAI.
    
    This function creates an OpenAI-compatible model that routes through
    OpenRouter's unified API, providing access to multiple AI providers.
    
    Args:
        model_name: OpenRouter model identifier (e.g., "anthropic/claude-3.5-sonnet")
        api_key: OpenRouter API key (starts with "sk-or-")
        base_url: OpenRouter API endpoint (default: https://openrouter.ai/api/v1)
        extra_headers: Optional headers for referer and title tracking
        **kwargs: Additional model configuration parameters
        
    Returns:
        Configured OpenAIModel instance ready for use with PydanticAI
        
    Example:
        >>> model = create_openrouter_model(
        ...     model_name="anthropic/claude-3.5-sonnet",
        ...     api_key="sk-or-v1-...",
        ...     extra_headers={
        ...         "HTTP-Referer": "https://myapp.com",
        ...         "X-Title": "My App"
        ...     }
        ... )
        >>> agent = Agent(model, result_type=MyResult)
    """
    # Validate inputs to catch common errors early
    if not model_name:
        raise ValueError("model_name cannot be empty")
    
    if not api_key:
        raise ValueError("api_key cannot be empty")
    
    # Check for common model name format issues
    if "/" not in model_name:
        raise ValueError(
            f"Invalid model name format: '{model_name}'. "
            "OpenRouter models should be in 'provider/model' format "
            "(e.g., 'anthropic/claude-3.5-sonnet')"
        )
    
    # Create the OpenAIModel with OpenRouter configuration
    # OpenRouter uses OpenAI-compatible endpoints, so we can use OpenAIModel
    # We need to use OpenAIProvider to set custom base_url
    
    # Create provider with OpenRouter configuration
    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key,
        # TODO: Add custom headers support when available in provider
    )
    
    return OpenAIModel(
        model_name,
        provider=provider,
        # Pass through any additional kwargs
        **kwargs
    )


def create_openrouter_model_from_config(
    config: Any,
    task: str = "research"
) -> Optional[OpenAIModel]:
    """
    Create an OpenRouter model using configuration object.
    
    This is a convenience function that extracts OpenRouter settings
    from a Config object and creates the appropriate model.
    
    Args:
        config: Configuration object with OpenRouter settings
        task: Task type ("research" or "writer") to select appropriate model
        
    Returns:
        Configured OpenAIModel instance or None if OpenRouter not configured
        
    Example:
        >>> from config import get_config
        >>> config = get_config()
        >>> model = create_openrouter_model_from_config(config, task="research")
        >>> if model:
        ...     agent = Agent(model, result_type=ResearchFindings)
    """
    # Check if OpenRouter is configured
    if not hasattr(config, "use_openrouter") or not config.use_openrouter:
        return None
    
    # Get OpenRouter configuration
    or_config = config.get_openrouter_config()
    if not or_config:
        return None
    
    # Determine which model to use based on task
    model_name = config.get_model_for_task(task)
    
    # Create and return the model
    return create_openrouter_model(
        model_name=model_name,
        api_key=or_config["api_key"],
        base_url=or_config["base_url"],
        extra_headers=or_config.get("extra_headers")
    )


def get_model_info(model_name: str) -> Dict[str, Any]:
    """
    Get information about a specific OpenRouter model.
    
    This function returns known information about OpenRouter models,
    including their capabilities, context windows, and recommended use cases.
    
    Args:
        model_name: OpenRouter model identifier
        
    Returns:
        Dictionary with model information
        
    Note:
        This is a static lookup. For real-time model info,
        use the OpenRouter API's /models endpoint.
    """
    # Common model information
    # In production, this could be fetched from OpenRouter's API
    model_info = {
        "anthropic/claude-3.5-sonnet": {
            "provider": "Anthropic",
            "context_window": 200000,
            "strengths": ["reasoning", "analysis", "code", "research"],
            "use_cases": ["research", "technical writing", "code generation"],
            "supports_tools": True,
            "supports_vision": True,
        },
        "openai/gpt-4o": {
            "provider": "OpenAI",
            "context_window": 128000,
            "strengths": ["general", "creative writing", "conversation"],
            "use_cases": ["content generation", "creative tasks", "chat"],
            "supports_tools": True,
            "supports_vision": True,
        },
        "google/gemini-pro": {
            "provider": "Google",
            "context_window": 32000,
            "strengths": ["reasoning", "multimodal", "efficiency"],
            "use_cases": ["analysis", "general tasks", "cost-effective"],
            "supports_tools": True,
            "supports_vision": True,
        },
        "meta-llama/llama-3.1-70b-instruct": {
            "provider": "Meta",
            "context_window": 128000,
            "strengths": ["open source", "efficiency", "instruction following"],
            "use_cases": ["general tasks", "cost optimization", "high volume"],
            "supports_tools": False,
            "supports_vision": False,
        },
    }
    
    # Return model info if found, otherwise return generic info
    return model_info.get(model_name, {
        "provider": model_name.split("/")[0] if "/" in model_name else "Unknown",
        "context_window": "Unknown",
        "strengths": ["general purpose"],
        "use_cases": ["general tasks"],
        "supports_tools": False,
        "supports_vision": False,
    })


# Example usage and testing
if __name__ == "__main__":
    """
    Test the OpenRouter model factory by creating a model
    and displaying its configuration.
    """
    # Example: Create a model for research tasks
    try:
        # Check if API key is available
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("❌ OPENROUTER_API_KEY not found in environment")
            print("Please set your OpenRouter API key to test this module")
            exit(1)
        
        # Create a research model
        research_model = create_openrouter_model(
            model_name="anthropic/claude-3.5-sonnet",
            api_key=api_key,
            extra_headers={
                "HTTP-Referer": "https://seo-automation.local",
                "X-Title": "SEO Content Automation Test"
            }
        )
        
        print("✅ Successfully created OpenRouter model!")
        print(f"Model: anthropic/claude-3.5-sonnet")
        print(f"Base URL: https://openrouter.ai/api/v1")
        
        # Get model info
        info = get_model_info("anthropic/claude-3.5-sonnet")
        print(f"\nModel Information:")
        print(f"  Provider: {info['provider']}")
        print(f"  Context Window: {info['context_window']} tokens")
        print(f"  Strengths: {', '.join(info['strengths'])}")
        print(f"  Use Cases: {', '.join(info['use_cases'])}")
        
    except Exception as e:
        print(f"❌ Error creating model: {e}")