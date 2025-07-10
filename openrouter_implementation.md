# OpenRouter Implementation Guide

## Overview

OpenRouter provides a unified API for accessing hundreds of AI models through a single endpoint. This guide covers the complete implementation for integrating OpenRouter into the SEO Content Automation System, enabling easy model switching and customization.

## Key Features

- **Unified API**: Access 100+ AI models through a single API endpoint
- **OpenAI Compatibility**: Works seamlessly with OpenAI SDK and PydanticAI
- **Model Flexibility**: Easy switching between models for different tasks
- **Cost Optimization**: Automatic routing to most cost-effective models
- **Fallback Support**: Built-in reliability with automatic fallbacks

## API Documentation

### Authentication

OpenRouter uses Bearer token authentication with API keys.

```python
headers = {
    "Authorization": "Bearer sk-or-...",
    "HTTP-Referer": "https://your-site.com",  # Optional
    "X-Title": "Your App Name",  # Optional
    "Content-Type": "application/json"
}
```

### Base URL

```
https://openrouter.ai/api/v1
```

### Endpoints

1. **Chat Completions**: `POST /api/v1/chat/completions`
2. **List Models**: `GET /api/v1/models`
3. **Generation Stats**: `GET /api/v1/generation`

## Integration Methods

### Method 1: Using OpenAI SDK (Recommended)

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

completion = client.chat.completions.create(
    extra_headers={
        "HTTP-Referer": "https://your-site.com",  # Optional
        "X-Title": "SEO Content Automation",      # Optional
    },
    model="openai/gpt-4o",  # or any OpenRouter model
    messages=[
        {
            "role": "user",
            "content": "What is the meaning of life?"
        }
    ]
)

print(completion.choices[0].message.content)
```

### Method 2: Direct API Requests

```python
import requests
import json

response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "HTTP-Referer": "https://your-site.com",  # Optional
        "X-Title": "SEO Content Automation",      # Optional
    },
    data=json.dumps({
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {
                "role": "user",
                "content": "What is the meaning of life?"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    })
)

result = response.json()
```

### Method 3: PydanticAI Integration (For Our System)

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Create OpenRouter model
model = OpenAIModel(
    "anthropic/claude-3.5-sonnet",  # Any OpenRouter model
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Use with PydanticAI Agent
agent = Agent(model)
result = await agent.run("What is the meaning of life?")
```

## Available Parameters

### Required Parameters
- None (model selection defaults to user preference if not specified)

### Optional Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `temperature` | Float | 0.0-2.0 | 1.0 | Controls response diversity |
| `top_p` | Float | 0.0-1.0 | 1.0 | Nucleus sampling threshold |
| `top_k` | Integer | ≥0 | 0 | Limits token choices |
| `frequency_penalty` | Float | -2.0-2.0 | 0.0 | Reduces repetition |
| `presence_penalty` | Float | -2.0-2.0 | 0.0 | Discourages repeated tokens |
| `repetition_penalty` | Float | 0.0-2.0 | 1.0 | Alternative repetition control |
| `min_p` | Float | 0.0-1.0 | 0.0 | Minimum token probability |
| `top_a` | Float | 0.0-1.0 | 0.0 | Maximum probability filter |
| `seed` | Integer | Any | None | Deterministic sampling |
| `max_tokens` | Integer | ≥1 | Model default | Maximum generation length |
| `stream` | Boolean | - | false | Enable streaming responses |
| `tools` | Array | - | None | Function calling support |
| `tool_choice` | String/Object | - | None | Tool selection strategy |

## Model Selection

### Listing Available Models

```python
import requests

response = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

models = response.json()["data"]
for model in models:
    print(f"{model['id']}: ${model['pricing']['prompt']}/1k tokens")
```

### Popular Models

1. **For Research Tasks**:
   - `anthropic/claude-3.5-sonnet` - Best for analysis and research
   - `google/gemini-pro` - Good balance of cost and capability
   - `perplexity/llama-3.1-sonar-large-128k-online` - Internet access

2. **For Writing Tasks**:
   - `openai/gpt-4o` - High quality content generation
   - `anthropic/claude-3-opus` - Premium long-form writing
   - `meta-llama/llama-3.1-70b-instruct` - Cost-effective option

3. **For Code Tasks**:
   - `anthropic/claude-3.5-sonnet` - Excellent code understanding
   - `deepseek/deepseek-coder` - Specialized for coding
   - `openai/gpt-4o` - Strong all-around performance

## Implementation in SEO Content System

### Configuration Structure

```python
# config.py additions
class OpenRouterConfig(BaseSettings):
    openrouter_api_key: str
    openrouter_research_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_writer_model: str = "openai/gpt-4o"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: Optional[str] = "SEO Content Automation"
    
    # Model-specific overrides
    openrouter_temperature: Optional[float] = None
    openrouter_max_tokens: Optional[int] = None
```

### Model Factory Pattern

```python
# models/openrouter.py
from pydantic_ai.models.openai import OpenAIModel
from typing import Optional, Dict, Any

def create_openrouter_model(
    model_name: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> OpenAIModel:
    """
    Factory function to create OpenRouter models for PydanticAI.
    
    Args:
        model_name: OpenRouter model identifier (e.g., "anthropic/claude-3.5-sonnet")
        api_key: OpenRouter API key
        base_url: OpenRouter API endpoint
        extra_headers: Optional headers for referer and title
        **kwargs: Additional model configuration
        
    Returns:
        Configured OpenAIModel instance
    """
    return OpenAIModel(
        model_name,
        base_url=base_url,
        api_key=api_key,
        http_client=kwargs.get("http_client"),
        custom_headers=extra_headers
    )
```

### Agent Integration

```python
# Updated agent initialization
from pydantic_ai import Agent
from models.openrouter import create_openrouter_model

# Research Agent with OpenRouter
research_model = create_openrouter_model(
    model_name=config.openrouter_research_model,
    api_key=config.openrouter_api_key,
    extra_headers={
        "HTTP-Referer": config.openrouter_site_url,
        "X-Title": config.openrouter_app_name
    }
)

research_agent = Agent(
    research_model,
    system_prompt=RESEARCH_SYSTEM_PROMPT,
    result_type=ResearchFindings
)

# Writer Agent with different model
writer_model = create_openrouter_model(
    model_name=config.openrouter_writer_model,
    api_key=config.openrouter_api_key,
    extra_headers={
        "HTTP-Referer": config.openrouter_site_url,
        "X-Title": config.openrouter_app_name
    }
)

writer_agent = Agent(
    writer_model,
    system_prompt=WRITER_SYSTEM_PROMPT,
    result_type=ArticleOutput
)
```

## Environment Variables

```bash
# .env configuration
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_RESEARCH_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_WRITER_MODEL=openai/gpt-4o
OPENROUTER_SITE_URL=https://your-site.com
OPENROUTER_APP_NAME=SEO Content Automation

# Optional model-specific settings
OPENROUTER_TEMPERATURE=0.7
OPENROUTER_MAX_TOKENS=4000
```

## Error Handling

### Common Error Codes

1. **401 Unauthorized**: Invalid API key
2. **402 Payment Required**: Insufficient credits
3. **429 Too Many Requests**: Rate limit exceeded
4. **500 Internal Server Error**: OpenRouter service issue

### Implementation Example

```python
import asyncio
from typing import Optional

async def call_openrouter_with_retry(
    agent: Agent,
    prompt: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Optional[Any]:
    """
    Call OpenRouter with exponential backoff retry logic.
    """
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt)
            return result
        except Exception as e:
            if "429" in str(e):  # Rate limit
                wait_time = backoff_factor ** attempt
                await asyncio.sleep(wait_time)
            elif "402" in str(e):  # Payment required
                raise Exception("OpenRouter credits exhausted")
            else:
                if attempt == max_retries - 1:
                    raise
    return None
```

## Testing Strategy

```python
# tests/test_openrouter.py
import pytest
from unittest.mock import Mock, patch
from models.openrouter import create_openrouter_model

@pytest.fixture
def mock_openrouter_response():
    return {
        "choices": [{
            "message": {
                "content": "Test response",
                "role": "assistant"
            }
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20
        }
    }

def test_create_openrouter_model():
    """Test OpenRouter model creation."""
    model = create_openrouter_model(
        model_name="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        extra_headers={"X-Title": "Test"}
    )
    
    assert model is not None
    assert model.model == "anthropic/claude-3.5-sonnet"

@patch('openai.OpenAI')
def test_openrouter_api_call(mock_client, mock_openrouter_response):
    """Test API call through OpenRouter."""
    mock_client.return_value.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Test response"))]
    )
    
    # Test implementation here
```

## Migration Guide

### From OpenAI to OpenRouter

1. **Update Environment Variables**:
   ```bash
   # Old
   OPENAI_API_KEY=sk-...
   
   # New
   OPENROUTER_API_KEY=sk-or-...
   OPENROUTER_RESEARCH_MODEL=openai/gpt-4o
   OPENROUTER_WRITER_MODEL=openai/gpt-4o
   ```

2. **Update Agent Initialization**:
   ```python
   # Old
   from openai import OpenAI
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   
   # New
   from models.openrouter import create_openrouter_model
   model = create_openrouter_model(
       model_name=config.openrouter_research_model,
       api_key=config.openrouter_api_key
   )
   ```

3. **Maintain Backward Compatibility**:
   ```python
   # config.py
   @property
   def use_openrouter(self) -> bool:
       return bool(self.openrouter_api_key)
   
   def get_model(self, task: str = "research"):
       if self.use_openrouter:
           model_name = getattr(self, f"openrouter_{task}_model")
           return create_openrouter_model(model_name, self.openrouter_api_key)
       else:
           # Fallback to OpenAI
           return create_openai_model(self.openai_api_key)
   ```

## Best Practices

1. **Model Selection**:
   - Use different models for different tasks
   - Consider cost vs. quality tradeoffs
   - Test model performance for your specific use case

2. **Error Handling**:
   - Implement retry logic for transient failures
   - Handle rate limits gracefully
   - Monitor API usage and costs

3. **Performance Optimization**:
   - Cache model responses when appropriate
   - Use streaming for long responses
   - Batch requests when possible

4. **Security**:
   - Never commit API keys to version control
   - Use environment variables for configuration
   - Rotate API keys regularly

## Monitoring and Debugging

### Usage Tracking

```python
# Track API usage
async def track_usage(response):
    usage = response.usage
    logger.info(f"Tokens used - Prompt: {usage.prompt_tokens}, "
                f"Completion: {usage.completion_tokens}, "
                f"Total: {usage.total_tokens}")
```

### Debug Headers

```python
# Enable debug mode
extra_headers = {
    "HTTP-Referer": config.openrouter_site_url,
    "X-Title": config.openrouter_app_name,
    "X-Debug": "true"  # OpenRouter debug mode
}
```

## Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenRouter API Reference](https://openrouter.ai/docs/api-reference/overview)
- [Model Pricing](https://openrouter.ai/models)
- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [OpenRouter GitHub Examples](https://github.com/OpenRouterTeam/openrouter-examples)