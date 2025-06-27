# config.py Explanation

## Purpose
The `config.py` module centralizes all configuration management for our SEO Content Automation System. It uses Pydantic Settings to provide type-safe, validated configuration loaded from environment variables.

## Architecture

### Core Components
1. **Environment Loading**: Uses python-dotenv to read .env files
2. **Validation**: Pydantic ensures all settings meet requirements
3. **Type Safety**: Strong typing prevents configuration errors
4. **Singleton Pattern**: One configuration instance for the entire app

### Configuration Flow
```
.env file → Environment Variables → Pydantic Validation → Config Instance → Application
```

## Key Concepts

### Pydantic Settings
```python
class Config(BaseSettings):
```
- Extends `BaseSettings` instead of regular `BaseModel`
- Automatically reads from environment variables
- Provides validation and type conversion
- Supports .env file loading

### Field Definitions
```python
tavily_api_key: str = Field(..., description="...")
```
- `...` (Ellipsis) means the field is required
- `Field()` adds metadata and validation rules
- Type hints ensure proper data types

### Validators
```python
@validator("field_name")
def validate_something(cls, v):
```
- Custom validation logic beyond type checking
- Runs automatically when Config is instantiated
- Can transform values (e.g., create directories)

### Configuration Groups

1. **Required Settings**
   - `tavily_api_key`: For web search functionality
   - `openai_api_key`: For PydanticAI agents

2. **Optional with Defaults**
   - `log_level`: Controls verbosity (default: INFO)
   - `max_retries`: API retry attempts (default: 3)
   - `output_dir`: Where articles are saved (default: ./drafts)

3. **Service-Specific**
   - `tavily_search_depth`: Quality of search results
   - `llm_model`: Which OpenAI model to use

## Decision Rationale

### Why Pydantic Settings?
1. **Automatic env var loading**: No manual `os.getenv()` calls
2. **Type conversion**: "30" → 30 automatically
3. **Validation**: Catches errors at startup, not runtime
4. **Documentation**: Self-documenting with descriptions

### Why Validators?
1. **API Key Validation**: Prevents common mistakes
   - Empty keys
   - Placeholder values
   - Too-short keys

2. **Directory Creation**: Ensures output dir exists
   - No manual directory creation needed
   - Prevents "directory not found" errors

3. **Domain Parsing**: Cleans user input
   - Handles "edu" or ".edu" equally
   - Splits comma-separated lists properly

### Why Helper Methods?
```python
def get_tavily_config(self) -> dict:
```
- Packages related settings together
- Removes None values automatically
- Ready-to-use for API clients

## Learning Path

### Basic Usage
```python
from config import get_config

config = get_config()
api_key = config.tavily_api_key
```

### Understanding Validation
1. Try running with missing .env file
2. See how Pydantic reports missing fields
3. Try invalid values (empty strings, wrong types)
4. Watch validators transform and validate data

### Advanced Patterns
1. **Environment prefixes**: Could use `APP_` prefix
2. **Nested configuration**: Could have sub-models
3. **Multiple environments**: Dev/staging/prod configs
4. **Secrets management**: Could integrate with vaults

## Real-world Applications

### Development Workflow
```bash
# Copy example configuration
cp .env.example .env

# Edit with your API keys
nano .env

# Test configuration
python config.py
```

### Production Considerations
- Never commit .env files
- Use environment variables in cloud deployments
- Consider secrets management services
- Validate configuration at container startup

### Team Collaboration
- .env.example shows required variables
- Validators prevent misconfiguration
- Type hints enable IDE autocomplete
- Clear error messages help debugging

## Common Pitfalls

1. **Forgetting .env file**
   ```
   ValidationError: tavily_api_key field required
   ```
   Solution: Copy .env.example to .env

2. **Wrong types in .env**
   ```
   MAX_RETRIES=three  # Should be number
   ```
   Pydantic handles this gracefully

3. **Placeholder values**
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   Our validator catches this

4. **Import cycles**
   - Don't import config in modules that config imports
   - Use `get_config()` function instead of direct import

5. **Multiple Config instances**
   - Always use `get_config()` singleton
   - Don't create `Config()` directly

## Best Practices

### Environment Variables
```bash
# Development
export TAVILY_API_KEY="dev_key_here"

# Production (Docker)
docker run -e TAVILY_API_KEY="prod_key" app

# CI/CD
echo "TAVILY_API_KEY=${{ secrets.TAVILY_KEY }}" >> $GITHUB_ENV
```

### Testing Configuration
```python
def test_config_with_mocked_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test_key")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    config = Config()
    assert config.tavily_api_key == "test_key"
```

### Security Patterns
1. Never log API keys
2. Use `repr` to show key presence, not value
3. Validate keys have reasonable format
4. Consider encryption for sensitive data

## Debugging Tips

### Check loaded configuration
```bash
python config.py
```

### Debug environment variables
```python
import os
print(os.environ.get("TAVILY_API_KEY"))
```

### Validation errors
```python
from pydantic import ValidationError
try:
    config = Config()
except ValidationError as e:
    print(e.json(indent=2))
```

What questions do you have about the configuration system, Finn? Would you like me to explain any specific part in more detail?

Try this exercise: Create a .env file with just one API key and run `python config.py` to see what happens!