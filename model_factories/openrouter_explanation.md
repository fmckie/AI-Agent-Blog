# OpenRouter Model Factory - Learning Documentation

## Purpose

The OpenRouter model factory provides a clean abstraction for creating AI models that route through OpenRouter's unified API. This module bridges the gap between PydanticAI's expectations and OpenRouter's capabilities.

## Architecture

### Factory Pattern Implementation

The module implements the Factory pattern, one of the most fundamental design patterns in software engineering:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client Code   │────▶│  Model Factory   │────▶│  OpenAI Model   │
│   (agents.py)   │     │  (openrouter.py) │     │  (PydanticAI)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         │ Requests model        │ Creates configured     │ Routes through
         │ for specific task     │ model instance         │ OpenRouter API
```

### Why Factory Pattern?

1. **Encapsulation**: Hides complex model creation logic
2. **Flexibility**: Easy to add new model types
3. **Consistency**: Ensures all models are created correctly
4. **Testing**: Can easily mock model creation

## Key Concepts

### 1. OpenAI Compatibility

OpenRouter is designed to be OpenAI-compatible:

```python
return OpenAIModel(
    model_name,
    base_url=base_url,  # This is the key difference
    api_key=api_key,
)
```

**Key Insight**: By changing just the `base_url`, we redirect all requests through OpenRouter while maintaining the same interface.

### 2. Model Naming Convention

OpenRouter uses a specific naming format:

```
provider/model-name
```

Examples:
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o`
- `meta-llama/llama-3.1-70b-instruct`

This convention allows OpenRouter to route requests to the correct provider.

### 3. Validation Philosophy

The factory validates inputs early:

```python
if "/" not in model_name:
    raise ValueError(
        f"Invalid model name format: '{model_name}'. "
        "OpenRouter models should be in 'provider/model' format"
    )
```

**Why?** Early validation provides:
- Clear error messages
- Prevents wasted API calls
- Better debugging experience

## Decision Rationale

### Why Use OpenAIModel?

1. **Compatibility**: OpenRouter mimics OpenAI's API
2. **Simplicity**: No need to create custom model class
3. **Maintenance**: Updates to PydanticAI automatically work

### Why Extra Headers?

```python
extra_headers={
    "HTTP-Referer": "https://myapp.com",
    "X-Title": "My App"
}
```

These headers:
- Track usage in OpenRouter dashboard
- Help with debugging
- Contribute to model popularity metrics

### Why Static Model Info?

The `get_model_info()` function provides offline model details:

1. **Performance**: No API call needed
2. **Reliability**: Works even if API is down
3. **Documentation**: Helps developers choose models

## Learning Path

### Step 1: Understanding Factories

Before diving into this code, understand:
- Factory design pattern
- Why factories are useful
- Difference between factory method and abstract factory

### Step 2: API Compatibility

Learn about:
- REST API design
- How APIs can be compatible
- Base URL routing

### Step 3: Error Handling

Study:
- Input validation best practices
- When to validate vs when to let fail
- User-friendly error messages

## Real-World Applications

### 1. Multi-Provider Chatbot

```python
def create_chatbot_model(provider: str, quality: str = "standard"):
    """Create model based on provider preference."""
    models = {
        ("anthropic", "premium"): "anthropic/claude-3-opus",
        ("anthropic", "standard"): "anthropic/claude-3.5-sonnet",
        ("openai", "premium"): "openai/gpt-4",
        ("openai", "standard"): "openai/gpt-4o",
        ("meta", "standard"): "meta-llama/llama-3.1-70b-instruct",
    }
    
    model_name = models.get((provider, quality))
    if not model_name:
        raise ValueError(f"No model found for {provider}/{quality}")
    
    return create_openrouter_model(model_name, api_key)
```

### 2. Cost-Aware Model Selection

```python
def create_budget_model(max_cost_per_1k_tokens: float):
    """Select model based on budget constraints."""
    # Model costs (example values)
    model_costs = {
        "meta-llama/llama-3.1-8b-instruct": 0.01,
        "mistral/mixtral-8x7b-instruct": 0.05,
        "anthropic/claude-3-haiku": 0.25,
        "anthropic/claude-3.5-sonnet": 0.75,
        "openai/gpt-4o": 1.00,
    }
    
    # Find most capable model within budget
    suitable_models = [
        model for model, cost in model_costs.items()
        if cost <= max_cost_per_1k_tokens
    ]
    
    if not suitable_models:
        raise ValueError(f"No models within budget of ${max_cost_per_1k_tokens}")
    
    # Return the most expensive (likely most capable) affordable model
    selected = max(suitable_models, key=lambda m: model_costs[m])
    return create_openrouter_model(selected, api_key)
```

### 3. Task-Specific Model Router

```python
def create_task_optimized_model(task_type: str, priority: str = "balanced"):
    """Create model optimized for specific task types."""
    task_models = {
        ("code", "quality"): "anthropic/claude-3.5-sonnet",
        ("code", "speed"): "deepseek/deepseek-coder",
        ("research", "quality"): "perplexity/llama-3.1-sonar-large-128k-online",
        ("research", "balanced"): "anthropic/claude-3.5-sonnet",
        ("creative", "quality"): "anthropic/claude-3-opus",
        ("creative", "balanced"): "openai/gpt-4o",
    }
    
    model_name = task_models.get((task_type, priority))
    if not model_name:
        # Fallback to general purpose model
        model_name = "openai/gpt-4o"
    
    return create_openrouter_model(
        model_name, 
        api_key,
        extra_headers={"X-Task-Type": task_type}
    )
```

## Common Pitfalls

### 1. Forgetting Provider Prefix

**Pitfall:**
```python
# Wrong - missing provider
model = create_openrouter_model("gpt-4o", api_key)
```

**Solution:**
```python
# Correct - includes provider
model = create_openrouter_model("openai/gpt-4o", api_key)
```

### 2. Assuming All Models Support All Features

**Pitfall:**
```python
# Not all models support function calling
model = create_openrouter_model("meta-llama/llama-3.1-70b-instruct", api_key)
# This might fail:
agent = Agent(model, tools=[my_tool])
```

**Solution:**
```python
# Check model capabilities first
info = get_model_info("meta-llama/llama-3.1-70b-instruct")
if info["supports_tools"]:
    agent = Agent(model, tools=[my_tool])
else:
    agent = Agent(model)  # No tools
```

### 3. Hardcoding API Configuration

**Pitfall:**
```python
# Bad - hardcoded values
model = create_openrouter_model(
    "anthropic/claude-3.5-sonnet",
    "sk-or-v1-hardcoded-key",
    "https://openrouter.ai/api/v1"
)
```

**Solution:**
```python
# Good - configuration-driven
model = create_openrouter_model(
    config.get_model_for_task("research"),
    config.openrouter_api_key,
    config.openrouter_base_url
)
```

## Best Practices

### 1. Always Validate Early

```python
# Validate at factory level, not at usage
if not model_name:
    raise ValueError("model_name cannot be empty")
```

This provides immediate feedback and clearer error messages.

### 2. Provide Helpful Error Messages

```python
# Bad
raise ValueError("Invalid model")

# Good
raise ValueError(
    f"Invalid model name format: '{model_name}'. "
    "OpenRouter models should be in 'provider/model' format "
    "(e.g., 'anthropic/claude-3.5-sonnet')"
)
```

### 3. Use Type Hints

```python
def create_openrouter_model(
    model_name: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> OpenAIModel:
```

Type hints provide:
- Better IDE support
- Self-documenting code
- Runtime validation with tools like mypy

## Security Considerations

### 1. API Key Handling

Never log or print API keys:
```python
# Bad
print(f"Creating model with key: {api_key}")

# Good
print(f"Creating model with key: sk-or-...{api_key[-4:]}")
```

### 2. Header Injection

Be careful with user-provided headers:
```python
# Validate headers before use
if extra_headers:
    # Only allow specific headers
    allowed_headers = {"HTTP-Referer", "X-Title"}
    extra_headers = {
        k: v for k, v in extra_headers.items()
        if k in allowed_headers
    }
```

### 3. Model Name Validation

Prevent injection attacks:
```python
# Additional validation for security
import re
if not re.match(r'^[a-z0-9-]+/[a-z0-9-]+$', model_name):
    raise ValueError("Invalid model name format")
```

## Performance Optimization

### 1. Model Caching

For applications creating many models:

```python
from functools import lru_cache

@lru_cache(maxsize=10)
def get_cached_model(model_name: str, api_key: str) -> OpenAIModel:
    """Cache model instances to avoid recreation."""
    return create_openrouter_model(model_name, api_key)
```

### 2. Connection Pooling

OpenRouter supports HTTP keep-alive:
```python
# Reuse connections for better performance
import httpx

http_client = httpx.Client(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=5)
)

model = create_openrouter_model(
    model_name,
    api_key,
    http_client=http_client
)
```

### 3. Batch Requests

When possible, batch multiple requests:
```python
# Instead of multiple single calls
results = []
for prompt in prompts:
    result = await agent.run(prompt)
    results.append(result)

# Consider batching (if supported by your use case)
all_context = "\n".join(prompts)
result = await agent.run(all_context)
```

## Testing Strategies

### 1. Unit Testing

```python
def test_model_creation():
    """Test successful model creation."""
    model = create_openrouter_model(
        "anthropic/claude-3.5-sonnet",
        "test-api-key"
    )
    assert model is not None
    assert model.model == "anthropic/claude-3.5-sonnet"
```

### 2. Error Testing

```python
def test_invalid_model_name():
    """Test validation of model names."""
    with pytest.raises(ValueError, match="provider/model"):
        create_openrouter_model("invalid-model", "test-key")
```

### 3. Integration Testing

```python
@pytest.mark.integration
async def test_real_api_call():
    """Test actual API call through OpenRouter."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("No API key available")
    
    model = create_openrouter_model(
        "anthropic/claude-3.5-sonnet",
        os.getenv("OPENROUTER_API_KEY")
    )
    
    agent = Agent(model)
    result = await agent.run("Say 'test successful'")
    assert "test successful" in result.lower()
```

## Advanced Topics

### 1. Custom Model Classes

For advanced use cases, extend the factory:

```python
class OpenRouterModelWithMetrics(OpenAIModel):
    """OpenRouter model that tracks usage metrics."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_count = 0
        self.total_tokens = 0
    
    async def request(self, *args, **kwargs):
        self.request_count += 1
        result = await super().request(*args, **kwargs)
        # Track token usage
        if hasattr(result, 'usage'):
            self.total_tokens += result.usage.total_tokens
        return result
```

### 2. Dynamic Model Selection

Implement intelligent model selection:

```python
async def create_adaptive_model(initial_prompt: str):
    """Select model based on prompt analysis."""
    # Analyze prompt complexity
    word_count = len(initial_prompt.split())
    has_code = "```" in initial_prompt
    needs_internet = any(word in initial_prompt.lower() 
                        for word in ["latest", "current", "today"])
    
    if needs_internet:
        model_name = "perplexity/llama-3.1-sonar-large-128k-online"
    elif has_code:
        model_name = "anthropic/claude-3.5-sonnet"
    elif word_count > 500:
        model_name = "anthropic/claude-3-opus"
    else:
        model_name = "openai/gpt-4o"
    
    return create_openrouter_model(model_name, api_key)
```

### 3. Fallback Chains

Implement automatic fallbacks:

```python
class FallbackModelChain:
    """Chain of models with automatic fallback."""
    
    def __init__(self, model_names: List[str], api_key: str):
        self.models = [
            create_openrouter_model(name, api_key)
            for name in model_names
        ]
    
    async def run(self, prompt: str):
        """Try each model until one succeeds."""
        for i, model in enumerate(self.models):
            try:
                agent = Agent(model)
                return await agent.run(prompt)
            except Exception as e:
                if i == len(self.models) - 1:
                    raise
                print(f"Model {i} failed, trying next: {e}")
```

## Exercise Suggestions

1. **Add Model Aliasing**: Create a function that maps friendly names like "fast", "balanced", "quality" to specific models

2. **Implement Rate Limiting**: Add rate limiting to the factory to prevent exceeding API quotas

3. **Create Model Profiler**: Build a tool that tests different models and profiles their speed, quality, and cost

4. **Add Caching Layer**: Implement a caching mechanism that stores responses for identical prompts

5. **Build Model Recommendation**: Create a system that recommends the best model based on task description

What questions do you have about this code, Finn?

Would you like me to explain any specific part in more detail?

Try this exercise: Extend the `get_model_info()` function to fetch real-time model information from OpenRouter's `/api/v1/models` endpoint. This will help you understand how to integrate external APIs with factory patterns.