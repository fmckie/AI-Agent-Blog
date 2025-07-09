# Cache CLI Tests - Detailed Explanation

## Purpose

These tests ensure that the cache management CLI commands work correctly, handle errors gracefully, and provide a good user experience. They use mocking to avoid actual database connections and API calls during testing.

## Architecture

### Testing Strategy
1. **Unit Tests**: Test each command in isolation
2. **Mock Everything**: Mock external dependencies (database, APIs)
3. **Test User Interactions**: Verify CLI output and behavior
4. **Error Scenarios**: Ensure graceful error handling

### Test Organization
- One test class per command
- Multiple test methods for different scenarios
- Fixtures for common mocks
- Utility functions for assertions

## Key Concepts

### 1. Click Testing
**CliRunner**: Click's test utility for invoking commands
```python
runner = CliRunner()
result = runner.invoke(command, args)
```

**Benefits**:
- Captures output (stdout/stderr)
- Simulates user input
- Returns exit codes
- Isolates command execution

### 2. Mocking Async Code
**AsyncMock**: Mock for async functions and context managers
```python
mock_storage = AsyncMock()
mock_storage.__aenter__.return_value = mock_storage
mock_storage.__aexit__.return_value = None
```

**Why**: Allows testing async code synchronously

### 3. Patch Decorators
**patch**: Replace real objects with mocks
```python
with patch("main.VectorStorage") as mock_storage_class:
    # mock_storage_class is now a MagicMock
```

**Scope**: Only within the context manager

## Decision Rationale

### Why Mock Everything?
1. **Speed**: No network calls or database queries
2. **Isolation**: Test only the CLI logic
3. **Reliability**: Tests don't depend on external services
4. **Control**: Can simulate any scenario

### Why Test Output?
1. **User Experience**: CLI output is the interface
2. **Regression Prevention**: Catch unintended changes
3. **Documentation**: Tests show expected behavior

### Why Multiple Test Cases?
1. **Edge Cases**: Empty results, errors, etc.
2. **Options**: Different command-line flags
3. **Interactions**: User confirmations, input

## Learning Path

### 1. Start Simple
Begin with `test_cache_search_basic`:
- Single mock setup
- Verify basic functionality
- Check output format

### 2. Add Complexity
Move to `test_cache_search_with_options`:
- Multiple parameters
- Verify mock calls
- Test option parsing

### 3. Error Handling
Study `test_cache_warm_error_handling`:
- Simulate failures
- Verify graceful degradation
- Check error messages

### 4. User Interaction
Examine `test_cache_clear_with_confirmation`:
- Simulate user input
- Test confirmation flow
- Verify safety features

## Test Patterns Explained

### 1. Basic Command Test
```python
def test_command_basic(self):
    runner = CliRunner()
    with patch("module.Class") as mock:
        # Setup mock
        mock.return_value.method.return_value = expected
        
        # Run command
        result = runner.invoke(command, ["args"])
        
        # Verify
        assert result.exit_code == 0
        assert "expected output" in result.output
```

### 2. Async Mock Pattern
```python
# Mock async context manager
mock_storage = AsyncMock()
mock_storage.__aenter__.return_value = mock_storage
mock_storage.__aexit__.return_value = None

# Mock async method
mock_storage.async_method.return_value = result
```

### 3. Multiple Mock Pattern
```python
with patch("main.ClassA") as mock_a:
    with patch("main.ClassB") as mock_b:
        # Setup both mocks
        # Test interactions
```

## Common Pitfalls

### 1. Forgetting Async Context
**Problem**: Mock doesn't support `async with`
**Solution**: Add `__aenter__` and `__aexit__` methods

### 2. Wrong Mock Level
**Problem**: Mocking too deep or shallow
**Solution**: Mock at the import level in the tested module

### 3. Output Assertions Too Strict
**Problem**: Tests break with minor output changes
**Solution**: Check for key phrases, not exact matches

### 4. Not Testing Error Cases
**Problem**: Only testing happy path
**Solution**: Add tests for failures, empty results, etc.

## Best Practices

### 1. Descriptive Test Names
```python
def test_cache_search_no_results(self):  # Clear what's being tested
def test_cache_clear_dry_run(self):      # Specific scenario
```

### 2. Arrange-Act-Assert
```python
# Arrange: Set up mocks and data
mock_storage.search_similar.return_value = []

# Act: Execute the command
result = runner.invoke(cache_search, ["query"])

# Assert: Verify the outcome
assert "No matching results" in result.output
```

### 3. Test Data Builders
```python
def make_search_result(similarity=0.9, keyword="test"):
    return {
        "similarity": similarity,
        "keyword": keyword,
        "content": "Test content",
        "created_at": "2024-01-01T00:00:00Z"
    }
```

### 4. Fixture Reuse
```python
@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    # Common setup
    return storage
```

## Real-world Applications

### 1. Regression Testing
- Catch breaking changes early
- Ensure backward compatibility
- Verify bug fixes stay fixed

### 2. Documentation
- Tests show how commands should work
- Examples of expected input/output
- Edge case handling

### 3. Refactoring Safety
- Change implementation confidently
- Tests verify behavior unchanged
- Catch subtle bugs

## Advanced Testing Topics

### 1. Integration Tests
```python
@pytest.mark.integration
async def test_real_database():
    # Use real connections
    # Slower but more thorough
```

### 2. Property-Based Testing
```python
@given(text=strategies.text())
def test_search_handles_any_input(text):
    # Test with random inputs
```

### 3. Performance Tests
```python
def test_search_performance():
    with timer:
        result = runner.invoke(cache_search, ["query"])
    assert timer.elapsed < 1.0  # Should be fast
```

## Security Considerations

1. **Don't Test Real Credentials**: Always mock authentication
2. **Sanitize Test Data**: No real user data in tests
3. **Test Input Validation**: Ensure malicious input handled
4. **Mock External Services**: Never hit production APIs

## What questions do you have about these tests, Finn?
Would you like me to explain any specific mocking pattern in more detail?

Try this exercise: Add a test that verifies the cache search command properly handles malformed similarity scores from the database!