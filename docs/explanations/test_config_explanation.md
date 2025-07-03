# test_config.py Explanation

## Purpose
This test suite ensures our configuration system works correctly under all conditions - valid configs, missing values, invalid inputs, and edge cases. It's our safety net that catches configuration problems before they reach production.

## Architecture

### Test Organization
1. **Class-based structure**: Groups related tests together
2. **Descriptive names**: Each test clearly states what it validates
3. **Comprehensive coverage**: Tests both happy paths and error cases
4. **Fixtures**: Reusable test setup for common scenarios

### Testing Strategy
```
Valid Cases → Edge Cases → Error Cases → Integration
```

## Key Concepts

### Pytest Basics
```python
def test_something():
    assert expected == actual
```
- Tests are functions starting with `test_`
- `assert` statements verify behavior
- Pytest automatically discovers and runs tests

### Monkeypatch
```python
def test_config(monkeypatch):
    monkeypatch.setenv("KEY", "value")
```
- Temporarily modifies environment variables
- Changes are automatically undone after test
- Prevents tests from affecting each other

### Testing Validation Errors
```python
with pytest.raises(ValidationError) as exc_info:
    Config()
```
- Expects specific exception to be raised
- `exc_info` captures exception details
- Can inspect error messages and fields

## Test Categories

### 1. Happy Path Tests
- `test_valid_configuration`: Everything works correctly
- `test_output_directory_creation`: Features work as expected

### 2. Validation Tests
- `test_missing_required_api_keys`: Required fields enforced
- `test_empty_api_keys_validation`: No empty values
- `test_placeholder_api_keys_rejected`: No example values
- `test_short_api_keys_rejected`: Reasonable key length

### 3. Type Conversion Tests
- `test_numeric_validation`: Numbers within bounds
- `test_domain_parsing`: String parsing works correctly

### 4. Edge Cases
- `test_case_insensitive_env_vars`: Flexible input
- Whitespace handling
- Empty strings vs None

## Decision Rationale

### Why Test Configuration?
1. **First point of failure**: Bad config breaks everything
2. **User experience**: Clear errors save debugging time
3. **Security**: Ensures API keys are validated
4. **Regression prevention**: Changes don't break existing behavior

### Why Monkeypatch?
1. **Isolation**: Tests don't affect system environment
2. **Control**: Exact environment for each test
3. **Repeatability**: Same results every time
4. **Speed**: No file I/O needed

### Why Comprehensive API Key Tests?
Users commonly make these mistakes:
- Forget to set API keys
- Leave placeholder values
- Copy partial keys
- Add extra whitespace

Our tests catch all of these!

## Learning Path

### Running Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestConfig::test_valid_configuration

# Run with coverage
pytest --cov=config tests/test_config.py
```

### Understanding Test Output
```
tests/test_config.py::TestConfig::test_valid_configuration PASSED [10%]
tests/test_config.py::TestConfig::test_missing_required_api_keys PASSED [20%]
```
- Green dots = passing tests
- Red F = failing tests
- Percentages show progress

### Writing New Tests
1. Start with expected behavior
2. Set up test environment (monkeypatch)
3. Execute code under test
4. Assert expected outcomes
5. Test edge cases

## Real-world Applications

### Continuous Integration
```yaml
# GitHub Actions example
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=. --cov-report=xml
```

### Pre-commit Hooks
```bash
# Run tests before committing
git commit -m "feat: add config" 
# Tests run automatically
```

### Test-Driven Development (TDD)
1. Write failing test for new feature
2. Write minimal code to pass
3. Refactor while tests pass
4. Repeat

## Common Pitfalls

### 1. Testing Implementation, Not Behavior
❌ Bad:
```python
def test_uses_pydantic():
    assert isinstance(config, BaseSettings)
```

✅ Good:
```python
def test_validates_api_keys():
    # Test the behavior, not how it's done
```

### 2. Insufficient Error Testing
❌ Bad:
```python
with pytest.raises(Exception):
    Config()  # Too generic
```

✅ Good:
```python
with pytest.raises(ValidationError) as exc_info:
    Config()
assert "tavily_api_key" in str(exc_info.value)
```

### 3. Test Interdependence
❌ Bad:
```python
def test_1():
    os.environ["KEY"] = "value"  # Affects other tests

def test_2():
    # Might fail due to test_1
```

✅ Good:
```python
def test_1(monkeypatch):
    monkeypatch.setenv("KEY", "value")  # Isolated
```

## Best Practices

### Test Naming
```python
def test_what_when_expected():
    """Test that {what} when {condition} should {expected}."""
```

### Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange - Set up test data
    monkeypatch.setenv("KEY", "value")
    
    # Act - Execute the code
    result = function_under_test()
    
    # Assert - Verify outcome
    assert result == expected
```

### Fixture Usage
```python
@pytest.fixture
def valid_config(monkeypatch):
    """Reusable valid configuration."""
    monkeypatch.setenv("TAVILY_API_KEY", "valid_key")
    return Config()

def test_something(valid_config):
    # Use the fixture
    assert valid_config.tavily_api_key
```

## Debugging Tips

### See Actual vs Expected
```python
# Pytest shows helpful diffs
assert config.llm_model == "gpt-3.5"
# Shows: AssertionError: assert 'gpt-4' == 'gpt-3.5'
```

### Print Debugging in Tests
```python
def test_debug():
    print(f"Config: {config}")  # Use pytest -s to see output
```

### Test Single Scenarios
```python
@pytest.mark.focus  # Custom marker
def test_specific_case():
    pass

# Run: pytest -m focus
```

What questions do you have about testing, Finn? 

Try this exercise: Add a new test that verifies the LLM model must be one of the GPT models (gpt-3.5-turbo, gpt-4, etc.)!